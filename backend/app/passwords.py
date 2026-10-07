"""Email-only password changes and short-lived, password-bound reset links."""
import hashlib
import hmac
import logging
import secrets
import smtplib
import ssl
import time
from collections import OrderedDict
from email.message import EmailMessage
from threading import Lock
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import Field, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .accounts import COOKIE, Credentials, current_session, database, hash_password, require_origin, verify_password
from .config import settings
from .models import AuthSession, User
from .schemas import RequestModel

router = APIRouter()
RESET_SECONDS = 900
RESET_MESSAGE = '이메일 가입 계정이 있다면 재설정 링크를 보내드립니다. 메일함과 스팸함을 확인해 주세요.'
_attempts = OrderedDict()
_lock = Lock()


def reset_enabled():
    origin = urlparse(settings.frontend_origin)
    safe_origin = origin.scheme == 'https' or (
        settings.app_env == 'development' and origin.scheme == 'http'
        and origin.hostname in ('localhost', '127.0.0.1', '::1'))
    return bool(settings.password_reset_secret and settings.smtp_host and settings.smtp_from
                and safe_origin and settings.smtp_username and settings.smtp_password)


class ForgotPassword(RequestModel):
    email: str = Field(max_length=254)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        return Credentials.valid_email(value)


class NewPassword(RequestModel):
    new_password: str = Field(min_length=8, max_length=128)


class ResetPassword(NewPassword):
    token: str = Field(min_length=1, max_length=256)


class ChangePassword(NewPassword):
    current_password: str = Field(min_length=8, max_length=128)


def check_rate(request, email, namespace='forgot', ip_limit=10, email_limit=3):
    # Per-process protection; deployments with multiple workers also need gateway limits.
    now = time.monotonic()
    keys = [(f'{namespace}:ip', request.client.host if request.client else 'unknown', ip_limit),
            (f'{namespace}:email', hashlib.sha256(email.encode()).hexdigest(), email_limit)]
    with _lock:
        for kind, value, limit in keys:
            key = (kind, value)
            previous = [stamp for stamp in _attempts.get(key, []) if now - stamp < RESET_SECONDS]
            _attempts[key] = previous
            if len(previous) >= limit:
                raise HTTPException(429, '요청이 많습니다. 15분 후 다시 시도해 주세요.')
        for kind, value, _ in keys:
            key = (kind, value)
            _attempts[key].append(now)
            _attempts.move_to_end(key)
        while len(_attempts) > 10000:
            _attempts.popitem(last=False)


def token_signature(payload, password_hash):
    return hmac.new(settings.password_reset_secret.encode(),
                    f'password-reset:{payload}:{password_hash}'.encode(), hashlib.sha256).hexdigest()


def make_reset_token(user):
    payload = f'{user.id}.{int(time.time()) + RESET_SECONDS}.{secrets.token_hex(16)}'
    return f'{payload}.{token_signature(payload, user.password_hash)}'


def send_reset_email(email, token):
    message = EmailMessage()
    message['Subject'] = 'CaloDetect 비밀번호 재설정'
    message['From'] = settings.smtp_from
    message['To'] = email
    link = f'{settings.frontend_origin.rstrip("/")}/#' + urlencode({'password_reset': token})
    message.set_content(f'아래 링크에서 새 비밀번호를 설정해 주세요. 링크는 15분 동안 유효합니다.\n\n{link}\n\n요청하지 않았다면 이 메일을 무시하세요.')
    try:
        context = ssl.create_default_context()
        if settings.smtp_security == 'ssl':
            connection = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10, context=context)
        else:
            connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        with connection as smtp:
            if settings.smtp_security == 'starttls':
                smtp.starttls(context=context)
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        # No recipient, credential, token or SMTP exception text in logs.
        logging.getLogger(__name__).error('Password reset email delivery failed; check SMTP configuration.')


@router.post('/auth/password/forgot')
def forgot(body: ForgotPassword, request: Request, response: Response,
           tasks: BackgroundTasks, db: Session = Depends(database)):
    require_origin(request)
    response.headers['Cache-Control'] = 'no-store'
    if not reset_enabled():
        raise HTTPException(503, '재설정 이메일 발송 설정이 준비되지 않았습니다. 운영자에게 문의해 주세요.')
    check_rate(request, body.email)
    user = db.scalar(select(User).where(User.email == body.email))
    if user and not user.oauth_provider:
        tasks.add_task(send_reset_email, user.email, make_reset_token(user))
    return {'message': RESET_MESSAGE}


def replace_password(db, user, new_password):
    if verify_password(new_password, user.password_hash):
        raise HTTPException(422, '기존 비밀번호와 다른 비밀번호를 입력하세요.')
    # Conditional update makes simultaneous use of the same reset link fail safely.
    result = db.execute(update(User).where(User.id == user.id, User.password_hash == user.password_hash)
                        .values(password_hash=hash_password(new_password)),
                        execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(400, '비밀번호가 이미 변경되었습니다. 다시 진행해 주세요.')
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.commit()


def clear_cookie(response):
    response.delete_cookie(COOKIE, path='/', secure=settings.cookie_secure, httponly=True, samesite='lax')
    response.headers['Cache-Control'] = 'no-store'
    return {'message': '비밀번호를 변경했습니다. 새 비밀번호로 다시 로그인해 주세요.'}


@router.post('/auth/password/reset')
def reset(body: ResetPassword, request: Request, response: Response, db: Session = Depends(database)):
    require_origin(request)
    check_rate(request, '', namespace='reset', ip_limit=20, email_limit=10000)
    if not settings.password_reset_secret:
        raise HTTPException(503, '비밀번호 재설정 설정이 필요합니다.')
    invalid = HTTPException(400, '재설정 링크가 만료되었거나 유효하지 않습니다. 새 링크를 요청해 주세요.')
    try:
        user_id, expires, nonce, signature = body.token.split('.')
        if int(expires) <= time.time() or int(expires) > time.time() + RESET_SECONDS or len(nonce) != 32:
            raise invalid
        user = db.get(User, int(user_id))
    except ValueError:
        raise invalid
    if not user or user.oauth_provider or not hmac.compare_digest(
            token_signature(f'{user_id}.{expires}.{nonce}', user.password_hash), signature):
        raise invalid
    replace_password(db, user, body.new_password)
    return clear_cookie(response)


@router.post('/users/me/password')
def change(body: ChangePassword, request: Request, response: Response,
           session=Depends(current_session), db: Session = Depends(database)):
    user = db.get(User, session.user_id)
    if user.oauth_provider:
        raise HTTPException(403, 'Google 계정의 비밀번호는 Google에서 변경해 주세요.')
    check_rate(request, str(user.id), namespace='change', ip_limit=20, email_limit=5)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, '현재 비밀번호를 확인해 주세요.')
    replace_password(db, user, body.new_password)
    return clear_cookie(response)
