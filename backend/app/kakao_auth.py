"""Kakao authorization code login. Provider credentials stay on the server."""
import base64
import hmac
import json
import logging
import secrets
import time
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .accounts import Signup, database, hash_password, open_session, policy, require_origin
from .config import settings
from .models import User, utcnow
from .security import require_service_age
from .services import rewards
from .social_auth import GoogleRegistration, google_signup_cipher, oauth_cookie_options

router = APIRouter()
log = logging.getLogger('calodetect')
STATE_COOKIE = 'calodetect_oauth_kakao'
SIGNUP_COOKIE = 'calodetect_kakao_signup'
AAD = b'calodetect-kakao-signup-v1'


def kakao_config():
    redirect = urlparse(settings.kakao_redirect_uri)
    local = (redirect.scheme == 'http' and redirect.hostname in ('localhost', '127.0.0.1')
             and redirect.port == 8000)
    secure = (redirect.scheme == 'https' and bool(redirect.hostname) and settings.cookie_secure
              and urlparse(settings.frontend_origin).scheme == 'https')
    valid = (local if settings.app_env == 'development' else secure)
    enabled = bool(settings.kakao_client_id and settings.oauth_state_secret and valid
                   and redirect.path == '/api/auth/kakao/callback'
                   and not redirect.username and not redirect.password
                   and not redirect.query and not redirect.fragment)
    return {'enabled': enabled, 'authorization_code_enabled': enabled}


def clear_cookie(response, name):
    response.delete_cookie(name, path='/', secure=settings.cookie_secure, httponly=True, samesite='lax')


def outcome(key, value):
    response = RedirectResponse(f"{settings.frontend_origin.rstrip('/')}/?{urlencode({key: value})}",
                                status_code=303)
    response.headers['Cache-Control'] = 'no-store'
    clear_cookie(response, STATE_COOKIE)
    clear_cookie(response, SIGNUP_COOKIE)
    return response


def seal_signup(claims):
    nonce = secrets.token_bytes(12)
    encrypted = google_signup_cipher().encrypt(nonce, json.dumps(claims).encode(), AAD)
    return base64.urlsafe_b64encode(nonce + encrypted).decode().rstrip('=')


def pending_claims(request):
    try:
        raw = request.cookies.get(SIGNUP_COOKIE, '')
        data = base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4))
        claims = json.loads(google_signup_cipher().decrypt(data[:12], data[12:], AAD))
        if (claims.get('provider') != 'kakao' or not isinstance(claims.get('sub'), str)
                or not isinstance(claims.get('exp'), int) or claims['exp'] <= int(time.time())):
            raise ValueError
        return claims
    except (ValueError, TypeError, KeyError, AttributeError, InvalidTag):
        raise HTTPException(401, '카카오 회원가입 요청이 만료되었습니다. 다시 시작하세요.')


@router.get('/auth/kakao/login')
def login(request: Request):
    require_origin(request)
    if not kakao_config()['enabled']:
        raise HTTPException(503, '카카오 REST API 키와 리다이렉트 URI 설정이 필요합니다.')
    state = secrets.token_urlsafe(32)
    token = jwt.encode({'provider': 'kakao', 'state': state, 'exp': utcnow() + timedelta(minutes=5)},
                       settings.oauth_state_secret, algorithm='HS256')
    params = urlencode({'client_id': settings.kakao_client_id,
                        'redirect_uri': settings.kakao_redirect_uri,
                        'response_type': 'code', 'state': state})
    response = RedirectResponse(f'https://kauth.kakao.com/oauth/authorize?{params}', status_code=307)
    response.set_cookie(STATE_COOKIE, token, **oauth_cookie_options())
    clear_cookie(response, SIGNUP_COOKIE)
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.get('/api/auth/kakao/callback')
async def callback(request: Request, code: str | None = None, state: str | None = None,
                   error: str | None = None, db: Session = Depends(database)):
    try:
        pending = jwt.decode(request.cookies.get(STATE_COOKIE, ''), settings.oauth_state_secret,
                             algorithms=['HS256'], options={'require': ['exp', 'state', 'provider']})
        if (pending['provider'] != 'kakao' or not state or not code or error
                or not hmac.compare_digest(state.encode(), pending['state'].encode())):
            raise ValueError
    except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
        log.warning('kakao callback rejected: state verification failed')
        return outcome('social_error', 'kakao_auth_failed')
    if not kakao_config()['enabled']:
        return outcome('social_error', 'kakao_unavailable')
    try:
        data = {'grant_type': 'authorization_code', 'client_id': settings.kakao_client_id,
                'redirect_uri': settings.kakao_redirect_uri, 'code': code}
        if settings.kakao_client_secret:
            data['client_secret'] = settings.kakao_client_secret
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post('https://kauth.kakao.com/oauth/token', data=data)
            token_response.raise_for_status()
            access_token = token_response.json()['access_token']
            if not isinstance(access_token, str) or not access_token:
                raise ValueError
            identity_response = await client.get('https://kapi.kakao.com/v2/user/me',
                                                  headers={'Authorization': f'Bearer {access_token}'})
            identity_response.raise_for_status()
            identity = identity_response.json()
        subject = identity['id']
        if type(subject) is not int or subject <= 0:
            raise ValueError
        subject = str(subject)
        account = identity.get('kakao_account') or {}
        if not isinstance(account, dict) or not isinstance(account.get('profile') or {}, dict):
            raise ValueError
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        # URL·인가 코드·토큰·제공자 응답 본문은 기록하지 않는다.
        log.warning('kakao callback failed: provider request/identity validation (%s)', type(exc).__name__)
        return outcome('social_error', 'kakao_auth_failed')
    user = db.scalar(select(User).where(User.oauth_provider == 'kakao', User.oauth_subject == subject))
    if user is not None:
        try:
            require_service_age(user)
        except HTTPException:
            return outcome('social_error', 'kakao_auth_failed')
        response = outcome('social_success', 'kakao')
        open_session(db, user, response, request)
        return response
    try:
        if account.get('is_email_valid') is not True or account.get('is_email_verified') is not True:
            raise ValueError
        email = Signup.valid_email(account.get('email', ''))
        if len(email) > 254:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        # The existing DB requires a unique email. This reserved, non-deliverable
        # value is storage-only; authentication always uses the Kakao subject.
        email = f'{secrets.token_hex(24)}@kakao.calodetect.invalid'
    if db.scalar(select(User).where(User.email == email)):
        return outcome('social_error', 'account_conflict')
    if not policy(request)['signup_enabled']:
        return outcome('social_error', 'signup_unavailable')
    profile = account.get('profile') or {}
    claims = {'provider': 'kakao', 'sub': subject, 'email': email,
              'name': str(profile.get('nickname', ''))[:80], 'exp': int(time.time()) + 300}
    response = outcome('social_signup', 'kakao')
    response.set_cookie(SIGNUP_COOKIE, seal_signup(claims), **oauth_cookie_options())
    return response


@router.get('/auth/social/kakao/pending')
def pending(request: Request, response: Response):
    require_origin(request)
    claims = pending_claims(request)
    response.headers['Cache-Control'] = 'no-store'
    return {'registration_required': True, 'provider': 'kakao',
            'email': None if claims['email'].endswith('@kakao.calodetect.invalid') else claims['email'],
            'name': claims['name']}


@router.post('/auth/social/kakao/register')
def register(body: GoogleRegistration, request: Request, response: Response,
             db: Session = Depends(database)):
    require_origin(request)
    claims = pending_claims(request)
    current = policy(request)
    if not current['signup_enabled']:
        raise HTTPException(503, current['notice'])
    if body.age < settings.age_min:
        raise HTTPException(422, f'만 {settings.age_min}세 이상만 가입할 수 있습니다.')
    if not body.service_consent or body.consent_text != current['service_consent_text']:
        raise HTTPException(422, '현재 서비스 이용·개인정보 동의 내용을 확인하세요.')
    try:
        name = Signup.valid_name(body.name)
    except ValueError:
        raise HTTPException(422, '이름을 입력하세요.')
    user = User(email=claims['email'], name=name, age=body.age, role='user',
                password_hash=hash_password(secrets.token_urlsafe(64)),
                service_consent_text=body.consent_text, oauth_provider='kakao', oauth_subject=claims['sub'])
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '이미 가입된 계정 또는 이메일입니다. 기존 방식으로 로그인하세요.')
    rewards.signup_hook(db, user)  # 리워드 가입 온보딩(SAVEPOINT 격리)
    result = open_session(db, user, response, request)
    clear_cookie(response, SIGNUP_COOKIE)
    return result
