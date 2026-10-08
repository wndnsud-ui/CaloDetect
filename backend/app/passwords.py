# 이메일 계정의 비밀번호 찾기·재설정·변경 처리.
# 15분 유효 링크를 현재 비밀번호 해시에 결합하고 변경 시 모든 세션을 폐기한다. SMTP 비밀과 토큰은 서버 내부에서만 사용한다.
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


# SMTP·재설정 비밀키와 HTTPS 또는 허용된 로컬 HTTP 원본이 준비됐는지 확인한다.
def reset_enabled():
    origin = urlparse(settings.frontend_origin)
    safe_origin = origin.scheme == 'https' or (
        settings.app_env == 'development' and origin.scheme == 'http'
        and origin.hostname in ('localhost', '127.0.0.1', '::1'))
    return bool(settings.password_reset_secret and settings.smtp_host and settings.smtp_from
                and safe_origin and settings.smtp_username and settings.smtp_password)


# ForgotPassword: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class ForgotPassword(RequestModel):
    # 가입 이메일. 인증 경로에서 정규화하고 DB의 unique 제약으로 중복 가입을 막는다.
    email: str = Field(max_length=254)

    # 이메일 공백과 대소문자를 정리하고 가입/로그인에 사용할 주소 형식을 검증한다.
    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        return Credentials.valid_email(value)


# NewPassword: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class NewPassword(RequestModel):
    # 8~128자 새 비밀번호 입력. 저장 시 새 salt의 해시로 변환한다.
    new_password: str = Field(min_length=8, max_length=128)


# ResetPassword: NewPassword를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class ResetPassword(NewPassword):
    token: str = Field(min_length=1, max_length=256)


# ChangePassword: NewPassword를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class ChangePassword(NewPassword):
    # 로그인 중 변경에서 현재 비밀번호 확인에 쓰는 입력.
    current_password: str = Field(min_length=8, max_length=128)


# 잠금 안에서 15분 창의 IP/이메일 해시별 요청 횟수를 검사하고 오래된 항목과 메모리 크기를 정리한다.
# 프로세스별 제한이므로 여러 worker를 묶는 전역 제한과는 다르다.
def check_rate(request, email, namespace='forgot', ip_limit=10, email_limit=3):
    # Per-process protection; deployments with multiple workers also need gateway limits.
    now = time.monotonic()
    # IP와 이메일(원문 대신 SHA-256)의 별도 제한을 함께 검사한다.
    keys = [(f'{namespace}:ip', request.client.host if request.client else 'unknown', ip_limit),
            (f'{namespace}:email', hashlib.sha256(email.encode()).hexdigest(), email_limit)]
    # 같은 프로세스의 동시 요청이 횟수 검사/추가 사이에 제한을 우회하지 않도록 잠근다.
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
        # 기억하는 제한 키 수를 제한해 요청 주소가 계속 달라져도 메모리가 무한 증가하지 않게 한다.
        while len(_attempts) > 10000:
            _attempts.popitem(last=False)


# 서버 비밀키로 payload와 현재 비밀번호 해시를 함께 HMAC 서명한다. 비밀번호 변경 시 기존 서명은 무효가 된다.
def token_signature(payload, password_hash):
    return hmac.new(settings.password_reset_secret.encode(),
                    f'password-reset:{payload}:{password_hash}'.encode(), hashlib.sha256).hexdigest()


# 회원 ID·15분 만료 시각·무작위 nonce와 서명을 결합한 재설정 토큰을 만든다.
def make_reset_token(user):
    payload = f'{user.id}.{int(time.time()) + RESET_SECONDS}.{secrets.token_hex(16)}'
    return f'{payload}.{token_signature(payload, user.password_hash)}'


# 토큰을 URL fragment에 넣은 메일을 SMTP SSL 또는 STARTTLS로 발송한다. 실패 로그에는 주소·토큰·자격정보를 담지 않는다.
def send_reset_email(email, token):
    message = EmailMessage()
    message['Subject'] = 'CaloDetect 비밀번호 재설정'
    message['From'] = settings.smtp_from
    message['To'] = email
    # fragment의 토큰은 메일 링크 접속 시 HTTP 요청 경로/쿼리로 서버에 전달되지 않는다.
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
                # 인증과 메일 전송 전에 TLS를 시작해 SMTP 자격정보를 평문으로 전송하지 않는다.
                smtp.starttls(context=context)
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        # No recipient, credential, token or SMTP exception text in logs.
        logging.getLogger(__name__).error('Password reset email delivery failed; check SMTP configuration.')


# 출처·설정·요청 제한을 검사하고 이메일 계정에만 백그라운드 메일 작업을 등록한다. 계정 존재 여부와 무관하게 같은 안내를 반환한다.
# HTTP POST /auth/password/forgot: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/auth/password/forgot')
def forgot(body: ForgotPassword, request: Request, response: Response,
           tasks: BackgroundTasks, db: Session = Depends(database)):
    require_origin(request)
    response.headers['Cache-Control'] = 'no-store'
    if not reset_enabled():
        raise HTTPException(503, '재설정 이메일 발송 설정이 준비되지 않았습니다. 운영자에게 문의해 주세요.')
    check_rate(request, body.email)
    user = db.scalar(select(User).where(User.email == body.email))
    # 이메일 비밀번호 기능과 소셜 인증 계정의 처리 경로를 구분한다.
    if user and not user.oauth_provider:
        tasks.add_task(send_reset_email, user.email, make_reset_token(user))
    return {'message': RESET_MESSAGE}


# 기존 해시가 일치할 때만 새 해시로 조건부 갱신하고 모든 회원 세션을 삭제한 뒤 확정한다.
# 동시에 같은 재설정 링크를 쓰더라도 이미 변경된 비밀번호를 덮어쓰지 않는다.
def replace_password(db, user, new_password):
    if verify_password(new_password, user.password_hash):
        raise HTTPException(422, '기존 비밀번호와 다른 비밀번호를 입력하세요.')
    # Conditional update makes simultaneous use of the same reset link fail safely.
    # 조회 당시 해시가 아직 같을 때만 갱신한다. 토큰 동시 사용 시 한 요청만 조건을 충족한다.
    result = db.execute(update(User).where(User.id == user.id, User.password_hash == user.password_hash)
                        .values(password_hash=hash_password(new_password)),
                        execution_options={'synchronize_session': False})
    if result.rowcount != 1:
        # 실패한 트랜잭션을 되돌려 부분 변경이 확정되지 않도록 한다.
        db.rollback()
        raise HTTPException(400, '비밀번호가 이미 변경되었습니다. 다시 진행해 주세요.')
    # 비밀번호 교체와 같은 트랜잭션에서 모든 기기의 기존 세션을 폐기한다.
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit()


# 비밀번호 변경 완료 후 세션 쿠키를 제거하고 새 비밀번호 재로그인 안내를 반환한다.
def clear_cookie(response):
    response.delete_cookie(COOKIE, path='/', secure=settings.cookie_secure, httponly=True, samesite='lax')
    response.headers['Cache-Control'] = 'no-store'
    return {'message': '비밀번호를 변경했습니다. 새 비밀번호로 다시 로그인해 주세요.'}


# 토큰 구조·유효 시간·nonce 길이·회원 로그인 방식·현재 해시의 서명을 검증한 뒤 비밀번호를 교체한다.
# HTTP POST /auth/password/reset: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/auth/password/reset')
def reset(body: ResetPassword, request: Request, response: Response, db: Session = Depends(database)):
    require_origin(request)
    check_rate(request, '', namespace='reset', ip_limit=20, email_limit=10000)
    if not settings.password_reset_secret:
        raise HTTPException(503, '비밀번호 재설정 설정이 필요합니다.')
    invalid = HTTPException(400, '재설정 링크가 만료되었거나 유효하지 않습니다. 새 링크를 요청해 주세요.')
    try:
        # 점으로 나눈 네 부분의 구조와 시간·nonce 형식을 먼저 확인한 뒤 회원/서명을 조회한다.
        user_id, expires, nonce, signature = body.token.split('.')
        if int(expires) <= time.time() or int(expires) > time.time() + RESET_SECONDS or len(nonce) != 32:
            raise invalid
        user = db.get(User, int(user_id))
    except ValueError:
        raise invalid
    # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
    if not user or user.oauth_provider or not hmac.compare_digest(
            token_signature(f'{user_id}.{expires}.{nonce}', user.password_hash), signature):
        raise invalid
    replace_password(db, user, body.new_password)
    return clear_cookie(response)


# 인증된 이메일 회원의 현재 비밀번호와 요청 제한을 검사한 뒤 새 비밀번호로 교체한다.
# HTTP POST /users/me/password: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/users/me/password')
def change(body: ChangePassword, request: Request, response: Response,
           session=Depends(current_session), db: Session = Depends(database)):
    user = db.get(User, session.user_id)
    # 이메일 비밀번호 기능과 소셜 인증 계정의 처리 경로를 구분한다.
    if user.oauth_provider:
        raise HTTPException(403, 'Google 계정의 비밀번호는 Google에서 변경해 주세요.')
    check_rate(request, str(user.id), namespace='change', ip_limit=20, email_limit=5)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, '현재 비밀번호를 확인해 주세요.')
    replace_password(db, user, body.new_password)
    return clear_cookie(response)
