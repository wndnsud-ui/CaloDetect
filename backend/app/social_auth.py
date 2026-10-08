# 소셜 인증의 제공자 설정, challenge, Google Authorization Code + PKCE와 가입 완료 처리.
# 서명·발급자·앱 대상·만료·state/nonce를 검증하고 계정 식별은 제공자와 subject로 수행한다. 이메일 일치만으로 기존 계정을 연결하지 않는다.
"""Google/Apple identity verification; secrets and provider tokens stay out of logs."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import timedelta
from typing import Literal
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .accounts import Signup, database, hash_password, open_session, policy, require_origin
from .config import settings
from .models import User, utcnow
from .schemas import RequestModel
from .security import require_service_age

router = APIRouter()
Provider = Literal['google', 'apple']
GOOGLE_STATE_COOKIE = 'calodetect_oauth_google'
GOOGLE_SIGNUP_COOKIE = 'calodetect_google_signup'
GOOGLE_AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
GOOGLE_SIGNUP_COOKIE_AAD = b'calodetect-google-signup-v1'
KEYS = {
    'google': jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs', timeout=5),
    'apple': jwt.PyJWKClient('https://appleid.apple.com/auth/keys', timeout=5),
}


# 제공자별 공개 Client ID·리디렉션·기능 준비 상태를 구성한다.
def provider_config(provider):
    client_id = settings.google_client_id if provider == 'google' else settings.apple_client_id
    enabled = bool(client_id and settings.oauth_state_secret)
    if provider == 'apple':
        redirect = urlparse(settings.apple_redirect_uri or '')
        enabled = enabled and redirect.scheme == 'https' and bool(redirect.hostname)
    if provider == 'google':
        redirect = urlparse(settings.google_redirect_uri)
        local_redirect = (redirect.scheme == 'http' and redirect.hostname in ('localhost', '127.0.0.1')
                          and redirect.port == 8000)
        secure_redirect = (redirect.scheme == 'https' and bool(redirect.hostname)
                           and settings.cookie_secure
                           and urlparse(settings.frontend_origin).scheme == 'https')
        redirect_valid = (local_redirect if settings.app_env == 'development' else secure_redirect)
        authorization_code_enabled = bool(enabled and settings.google_client_secret and redirect_valid
                                          and redirect.path == '/api/auth/google/callback'
                                          and not redirect.username and not redirect.password
                                          and not redirect.query and not redirect.fragment)
        return {'enabled': enabled, 'authorization_code_enabled': authorization_code_enabled,
                'client_id': client_id if enabled else None,
                'redirect_uri': settings.google_redirect_uri if authorization_code_enabled else None}
    return {'enabled': enabled, 'client_id': client_id if enabled else None,
            'redirect_uri': settings.apple_redirect_uri if enabled and provider == 'apple' else None}


# 프런트엔드가 표시할 제공자 설정과 소셜 가입 가능 상태를 반환한다.
# HTTP GET /auth/social/policy: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/auth/social/policy')
def social_policy():
    return {provider: provider_config(provider) for provider in ('google', 'apple')}


# 선택한 제공자의 인증 설정이 준비됐는지 검사하고 미설정이면 안내 오류를 발생시킨다.
def require_provider(provider):
    config = provider_config(provider)
    if not config['enabled']:
        raise HTTPException(503, '소셜 로그인 서비스 등록과 서버 설정이 필요합니다.')
    return config


# 제공자별 인증 challenge 쿠키 이름을 구성해 서로 다른 인증 흐름을 구분한다.
def cookie_name(provider):
    return f'calodetect_oauth_{provider}'


# 짧은 유효기간·HttpOnly·SameSite 등 임시 인증 쿠키의 공통 옵션을 만든다.
def oauth_cookie_options(max_age=300):
    return {'httponly': True, 'secure': settings.cookie_secure,
            'samesite': 'lax', 'max_age': max_age, 'path': '/'}


# Google 인증 완료/실패 뒤 state와 신규 가입 임시 쿠키를 정리한다.
def clear_google_oauth_cookies(response):
    response.delete_cookie(GOOGLE_STATE_COOKIE, path='/', secure=settings.cookie_secure,
                            httponly=True, samesite='lax')
    clear_google_signup_cookie(response)


# 신규 Google 회원가입 보완 단계의 임시 쿠키를 같은 옵션으로 제거한다.
def clear_google_signup_cookie(response):
    response.delete_cookie(GOOGLE_SIGNUP_COOKIE, path='/', secure=settings.cookie_secure,
                           httponly=True, samesite='lax')


# 서버 state 비밀키에서 AES-GCM 키를 만들어 가입 임시 데이터의 기밀성과 무결성을 보호한다.
def google_signup_cipher():
    # 비밀키에서 고정 길이 32바이트 AES 키를 파생한다. 원문 설정을 클라이언트에 전송하지 않는다.
    key = hashlib.sha256(settings.oauth_state_secret.encode()).digest()
    return AESGCM(key)


# 가입용 claims를 무작위 nonce로 AES-GCM 암호화하고 쿠키에 담을 URL-safe 문자열로 인코딩한다.
def seal_google_signup(claims):
    # AES-GCM 암호화마다 새 96비트 nonce를 사용한다. 고정 AAD는 다른 쿠키 용도와 구분한다.
    nonce = secrets.token_bytes(12)
    payload = json.dumps(claims, separators=(',', ':')).encode()
    encrypted = google_signup_cipher().encrypt(nonce, payload, GOOGLE_SIGNUP_COOKIE_AAD)
    return base64.urlsafe_b64encode(nonce + encrypted).decode().rstrip('=')


# 가입 쿠키를 복호화하고 provider·subject·만료를 확인한다. 변조/형식 오류는 동일한 인증 실패로 처리한다.
def open_google_signup(request):
    value = request.cookies.get(GOOGLE_SIGNUP_COOKIE, '')
    try:
        encoded = value + '=' * (-len(value) % 4)
        ciphertext = base64.urlsafe_b64decode(encoded.encode())
        if len(ciphertext) < 29:
            raise ValueError
        # 인증 태그를 함께 확인하므로 암호문 변조는 InvalidTag로 거부된다.
        payload = google_signup_cipher().decrypt(ciphertext[:12], ciphertext[12:], GOOGLE_SIGNUP_COOKIE_AAD)
        claims = json.loads(payload)
        if (claims.get('provider') != 'google' or not isinstance(claims.get('sub'), str)
                or not isinstance(claims.get('exp'), int) or claims['exp'] <= int(time.time())):
            raise ValueError
        return claims
    except (ValueError, TypeError, AttributeError, InvalidTag):
        raise HTTPException(401, 'Google 회원가입 요청이 만료되었습니다. 다시 시작하세요.')


# 출처와 제공자 설정을 확인해 5분 유효 state/nonce challenge를 서명 쿠키로 보관한다.
# HTTP POST /auth/social/{provider}/challenge: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/auth/social/{provider}/challenge')
def challenge(provider: Provider, request: Request, response: Response):
    require_origin(request)
    require_provider(provider)
    nonce, state = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    token = jwt.encode({'nonce': nonce, 'state': state, 'provider': provider,
                        'exp': utcnow() + timedelta(minutes=5)}, settings.oauth_state_secret, algorithm='HS256')
    response.set_cookie(cookie_name(provider), token, httponly=True, secure=settings.cookie_secure,
                        samesite='lax', max_age=300, path='/')
    response.headers['Cache-Control'] = 'no-store'
    return {'nonce': nonce, 'state': state}


# state·nonce·PKCE verifier를 준비하고 S256 challenge를 포함한 Google 인증 URL로 이동시킨다.
# HTTP GET /auth/google/login: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/auth/google/login')
def google_login(request: Request):
    require_origin(request)
    config = require_provider('google')
    if not config['authorization_code_enabled']:
        raise HTTPException(503, 'Google OAuth 클라이언트 ID·보안 키·리디렉션 URI 설정이 필요합니다.')

    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    # PKCE verifier는 서버 임시 쿠키에만 보관하고 인증 URL에는 SHA-256 challenge만 보낸다.
    verifier = secrets.token_urlsafe(64)
    challenge_value = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    pending = jwt.encode({'state': state, 'nonce': nonce, 'verifier': verifier,
                          'provider': 'google', 'exp': utcnow() + timedelta(minutes=5)},
                         settings.oauth_state_secret, algorithm='HS256')
    params = urlencode({
        'client_id': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'nonce': nonce,
        'code_challenge': challenge_value,
        'code_challenge_method': 'S256',
        'prompt': 'select_account',
    })
    response = RedirectResponse(f'{GOOGLE_AUTHORIZATION_ENDPOINT}?{params}', status_code=307)
    response.set_cookie(GOOGLE_STATE_COOKIE, pending, **oauth_cookie_options())
    response.headers['Cache-Control'] = 'no-store'
    return response


# 서명된 임시 state를 확인하고 code를 PKCE로 교환한 뒤 Google ID 토큰을 검증한다.
# 기존 subject는 로그인하고 신규 subject는 암호화된 가입 쿠키로 보완 입력을 연결한다.
# HTTP GET /api/auth/google/callback: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/api/auth/google/callback')
async def google_callback(request: Request, code: str | None = None,
                          state: str | None = None, error: str | None = None,
                          db: Session = Depends(database)):
    frontend = settings.frontend_origin.rstrip('/')
    fallback = f'{frontend}/?social_error=google_auth_failed'
    # callback 쿼리의 state만 믿지 않고 서버가 서명해 둔 임시 인증 쿠키와 대조한다.
    raw_pending = request.cookies.get(GOOGLE_STATE_COOKIE, '')
    try:
        pending = jwt.decode(raw_pending, settings.oauth_state_secret, algorithms=['HS256'],
                             options={'require': ['exp', 'state', 'nonce', 'verifier', 'provider']})
    except (jwt.PyJWTError, AttributeError):
        response = RedirectResponse(fallback, status_code=303)
        clear_google_oauth_cookies(response)
        return response
    if (pending['provider'] != 'google' or not state
            or not hmac.compare_digest(state.encode(), pending['state'].encode())):
        response = RedirectResponse(fallback, status_code=303)
        clear_google_oauth_cookies(response)
        return response
    if error or not code:
        response = RedirectResponse(fallback, status_code=303)
        clear_google_oauth_cookies(response)
        return response

    config = provider_config('google')
    if not config['authorization_code_enabled']:
        response = RedirectResponse(f'{frontend}/?social_error=google_unavailable', status_code=303)
        clear_google_oauth_cookies(response)
        return response
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(GOOGLE_TOKEN_ENDPOINT, data={
                'code': code,
                'client_id': config['client_id'],
                'client_secret': settings.google_client_secret,
                'redirect_uri': config['redirect_uri'],
                'grant_type': 'authorization_code',
                'code_verifier': pending['verifier'],
            })
            token_response.raise_for_status()
            token_data = token_response.json()
    except (httpx.HTTPError, ValueError):
        response = RedirectResponse(fallback, status_code=303)
        clear_google_oauth_cookies(response)
        return response
    if not isinstance(token_data, dict):
        response = RedirectResponse(fallback, status_code=303)
        clear_google_oauth_cookies(response)
        return response
    id_token = token_data.get('id_token')
    if not isinstance(id_token, str) or not id_token:
        response = RedirectResponse(fallback, status_code=303)
        clear_google_oauth_cookies(response)
        return response
    try:
        claims = verify_identity('google', id_token, pending['nonce'], config['client_id'])
        if claims.get('email_verified') not in (True, 'true'):
            raise HTTPException(401, '확인된 이메일이 필요합니다.')
        email = Signup.valid_email(claims.get('email', ''))
        if len(email) > 254:
            raise ValueError('Invalid email length')
    except (HTTPException, ValueError, TypeError, AttributeError) as exc:
        target = f'{frontend}/?social_error=google_auth_failed'
        if isinstance(exc, HTTPException) and exc.status_code == 503:
            target = f'{frontend}/?social_error=google_unavailable'
        response = RedirectResponse(target, status_code=303)
        clear_google_oauth_cookies(response)
        return response

    user = db.scalar(select(User).where(User.oauth_provider == 'google',
                                        User.oauth_subject == claims['sub']))
    if user is not None:
        try:
            require_service_age(user)
        except HTTPException:
            response = RedirectResponse(f'{frontend}/?social_error=google_auth_failed', status_code=303)
            clear_google_oauth_cookies(response)
            return response
        response = RedirectResponse(f'{frontend}/?social_success=google', status_code=303)
        open_session(db, user, response, request)
        clear_google_oauth_cookies(response)
        return response
    if db.scalar(select(User).where(User.email == email)):
        response = RedirectResponse(f'{frontend}/?social_error=account_conflict', status_code=303)
        clear_google_oauth_cookies(response)
        return response

    current_policy = policy(request)
    if not current_policy['signup_enabled']:
        response = RedirectResponse(f'{frontend}/?social_error=signup_unavailable', status_code=303)
        clear_google_oauth_cookies(response)
        return response
    signup_claims = {'provider': 'google', 'sub': claims['sub'], 'email': email,
                     'name': str(claims.get('name', ''))[:80], 'exp': int(time.time()) + 300}
    response = RedirectResponse(f'{frontend}/?social_signup=google', status_code=303)
    clear_google_oauth_cookies(response)
    response.set_cookie(GOOGLE_SIGNUP_COOKIE, seal_google_signup(signup_claims),
                        **oauth_cookie_options())
    return response


# 검증된 임시 Google 가입 정보를 화면에 전달한다.
# HTTP GET /auth/social/google/pending: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/auth/social/google/pending')
def google_pending(request: Request, response: Response):
    require_origin(request)
    claims = open_google_signup(request)
    response.headers['Cache-Control'] = 'no-store'
    return {'registration_required': True, 'provider': 'google',
            'email': claims['email'], 'name': claims.get('name', '')}


# GoogleRegistration: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class GoogleRegistration(RequestModel):
    # 사용자 표시 이름. 앞뒤 공백과 길이는 요청 모델에서 검증한다.
    name: str = Field(min_length=1, max_length=80)
    # 만 나이. 타입/범위 검사 외에 가입·로그인 서비스가 최소 연령을 확인한다.
    age: int = Field(gt=0, le=120)
    # 현재 서비스 필수 동의의 수락 여부. 실제 허용은 정책 검사에서 판단한다.
    service_consent: bool
    # 화면에서 확인한 필수 동의 문구. 서버 현재 문구와 정확히 일치해야 가입할 수 있다.
    consent_text: str = Field(max_length=4000)


# 인증된 Google 가입 정보와 현재 필수 동의·만 나이를 검사해 신규 계정과 세션을 만든다.
# HTTP POST /auth/social/google/register: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/auth/social/google/register')
def google_register(body: GoogleRegistration, request: Request, response: Response,
                    db: Session = Depends(database)):
    require_origin(request)
    claims = open_google_signup(request)
    current_policy = policy(request)
    if not current_policy['signup_enabled']:
        raise HTTPException(503, current_policy['notice'])
    if body.age < settings.age_min:
        raise HTTPException(422, f'만 {settings.age_min}세 이상만 가입할 수 있습니다.')
    if not body.service_consent or body.consent_text != current_policy['service_consent_text']:
        raise HTTPException(422, '현재 서비스 이용·개인정보 동의 내용을 확인하세요.')
    try:
        name = Signup.valid_name(body.name)
    except ValueError:
        raise HTTPException(422, '이름을 입력하세요.')
    # 이메일 비밀번호 기능과 소셜 인증 계정의 처리 경로를 구분한다.
    if db.scalar(select(User).where(User.oauth_provider == 'google',
                                    User.oauth_subject == claims['sub'])):
        response.delete_cookie(GOOGLE_SIGNUP_COOKIE, path='/', secure=settings.cookie_secure,
                               httponly=True, samesite='lax')
        raise HTTPException(409, '이미 등록된 Google 계정입니다. 다시 로그인하세요.')
    if db.scalar(select(User).where(User.email == claims['email'])):
        response.delete_cookie(GOOGLE_SIGNUP_COOKIE, path='/', secure=settings.cookie_secure,
                               httponly=True, samesite='lax')
        raise HTTPException(409, '이미 가입된 이메일입니다. 기존 로그인 방식으로 로그인하세요. 계정은 자동 연결하지 않습니다.')
    user = User(email=claims['email'], name=name, age=body.age, role='user',
                password_hash=hash_password(secrets.token_urlsafe(64)),
                service_consent_text=body.consent_text,
                oauth_provider='google', oauth_subject=claims['sub'])
    db.add(user)
    try:
        # commit 전 SQL을 반영해 생성 ID·제약 오류를 확인한다. 아직 변경을 최종 확정한 것은 아니다.
        db.flush()
    except IntegrityError:
        # 실패한 트랜잭션을 되돌려 부분 변경이 확정되지 않도록 한다.
        db.rollback()
        raise HTTPException(409, '이미 등록된 Google 계정 또는 이메일입니다. 다시 로그인하세요.')
    result = open_session(db, user, response, request)
    clear_google_signup_cookie(response)
    return result


# SocialCompletion: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class SocialCompletion(RequestModel):
    id_token: str = Field(min_length=1, max_length=16000)
    state: str | None = Field(default=None, max_length=256)
    # 사용자 표시 이름. 앞뒤 공백과 길이는 요청 모델에서 검증한다.
    name: str | None = Field(default=None, min_length=1, max_length=80)
    # 만 나이. 타입/범위 검사 외에 가입·로그인 서비스가 최소 연령을 확인한다.
    age: int | None = Field(default=None, gt=0, le=120)
    # 현재 서비스 필수 동의의 수락 여부. 실제 허용은 정책 검사에서 판단한다.
    service_consent: bool = False
    # 화면에서 확인한 필수 동의 문구. 서버 현재 문구와 정확히 일치해야 가입할 수 있다.
    consent_text: str | None = Field(default=None, max_length=4000)


# 제공자 공개키로 ID 토큰 서명·issuer·audience·만료·nonce와 필요한 claims를 검증한다.
def verify_identity(provider, token, nonce, client_id):
    try:
        key = KEYS[provider].get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=['RS256'], audience=client_id,
                            issuer=['https://accounts.google.com', 'accounts.google.com'] if provider == 'google'
                            else 'https://appleid.apple.com',
                            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub', 'nonce']})
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, '인증 제공자에 연결하지 못했습니다. 잠시 후 다시 시도하세요.')
    except jwt.PyJWTError:
        raise HTTPException(401, '소셜 인증 정보가 유효하지 않습니다. 다시 로그인하세요.')
    if not isinstance(claims['nonce'], str) or not hmac.compare_digest(claims['nonce'].encode(), nonce.encode()):
        raise HTTPException(401, '소셜 인증 요청이 일치하지 않습니다. 다시 로그인하세요.')
    if not isinstance(claims['sub'], str) or not claims['sub'] or len(claims['sub']) > 255:
        raise HTTPException(401, '소셜 계정 식별자가 유효하지 않습니다.')
    return claims


# challenge와 ID 토큰 검증 후 기존 제공자/subject 계정을 로그인하거나 신규 가입 입력을 처리한다.
# HTTP POST /auth/social/{provider}/complete: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/auth/social/{provider}/complete')
def complete(provider: Provider, body: SocialCompletion, request: Request, response: Response,
             db: Session = Depends(database)):
    require_origin(request)
    config = require_provider(provider)
    try:
        pending = jwt.decode(request.cookies.get(cookie_name(provider), ''), settings.oauth_state_secret,
                             algorithms=['HS256'], options={'require': ['exp', 'nonce', 'state', 'provider']})
    except jwt.PyJWTError:
        raise HTTPException(401, '소셜 로그인 요청이 만료되었습니다. 다시 시작하세요.')
    if pending['provider'] != provider or (provider == 'apple' and
            not hmac.compare_digest((body.state or '').encode(), pending['state'].encode())):
        raise HTTPException(401, '소셜 로그인 요청이 일치하지 않습니다.')
    claims = verify_identity(provider, body.id_token, pending['nonce'], config['client_id'])
    user = db.scalar(select(User).where(User.oauth_provider == provider, User.oauth_subject == claims['sub']))
    if user is None:
        if claims.get('email_verified') not in (True, 'true'):
            raise HTTPException(401, '확인된 이메일이 필요합니다.')
        try:
            email = Signup.valid_email(claims.get('email', ''))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(401, '소셜 계정 이메일을 확인할 수 없습니다.')
        if len(email) > 254:
            raise HTTPException(401, '소셜 계정 이메일을 확인할 수 없습니다.')
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(409, '이미 가입된 이메일입니다. 기존 로그인 방식으로 로그인하세요. 계정은 자동 연결하지 않습니다.')
        if body.age is None or body.name is None:
            response.headers['Cache-Control'] = 'no-store'
            return {'registration_required': True, 'email': email,
                    'name': str(claims.get('name', ''))[:80]}
        if settings.age_min is None or not settings.service_consent_text:
            raise HTTPException(503, '소셜 회원가입은 확정된 서비스 이용·개인정보 동의 문구 설정 후 가능합니다.')
        if body.age < settings.age_min:
            raise HTTPException(422, f'만 {settings.age_min}세 이상만 가입할 수 있습니다.')
        if not body.service_consent or body.consent_text != settings.service_consent_text:
            raise HTTPException(422, '현재 서비스 이용·개인정보 동의 내용을 확인하세요.')
        try:
            name = Signup.valid_name(body.name)
        except ValueError:
            raise HTTPException(422, '이름을 입력하세요.')
        # Preserve the existing non-null password column; the random secret is never returned or stored in plaintext.
        user = User(email=email, name=name, age=body.age, role='user',
                    password_hash=hash_password(secrets.token_urlsafe(64)),
                    service_consent_text=body.consent_text, oauth_provider=provider, oauth_subject=claims['sub'])
        db.add(user)
        try:
            # commit 전 SQL을 반영해 생성 ID·제약 오류를 확인한다. 아직 변경을 최종 확정한 것은 아니다.
            db.flush()
        except IntegrityError:
            # 실패한 트랜잭션을 되돌려 부분 변경이 확정되지 않도록 한다.
            db.rollback()
            raise HTTPException(409, '이미 등록된 소셜 계정 또는 이메일입니다. 다시 로그인하세요.')
    require_service_age(user)
    result = open_session(db, user, response, request)
    response.delete_cookie(cookie_name(provider), path='/', secure=settings.cookie_secure,
                           httponly=True, samesite='lax')
    return result
