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


@router.get('/auth/social/policy')
def social_policy():
    return {provider: provider_config(provider) for provider in ('google', 'apple')}


def require_provider(provider):
    config = provider_config(provider)
    if not config['enabled']:
        raise HTTPException(503, '소셜 로그인 서비스 등록과 서버 설정이 필요합니다.')
    return config


def cookie_name(provider):
    return f'calodetect_oauth_{provider}'


def oauth_cookie_options(max_age=300):
    return {'httponly': True, 'secure': settings.cookie_secure,
            'samesite': 'lax', 'max_age': max_age, 'path': '/'}


def clear_google_oauth_cookies(response):
    response.delete_cookie(GOOGLE_STATE_COOKIE, path='/', secure=settings.cookie_secure,
                            httponly=True, samesite='lax')
    clear_google_signup_cookie(response)


def clear_google_signup_cookie(response):
    response.delete_cookie(GOOGLE_SIGNUP_COOKIE, path='/', secure=settings.cookie_secure,
                           httponly=True, samesite='lax')


def google_signup_cipher():
    key = hashlib.sha256(settings.oauth_state_secret.encode()).digest()
    return AESGCM(key)


def seal_google_signup(claims):
    nonce = secrets.token_bytes(12)
    payload = json.dumps(claims, separators=(',', ':')).encode()
    encrypted = google_signup_cipher().encrypt(nonce, payload, GOOGLE_SIGNUP_COOKIE_AAD)
    return base64.urlsafe_b64encode(nonce + encrypted).decode().rstrip('=')


def open_google_signup(request):
    value = request.cookies.get(GOOGLE_SIGNUP_COOKIE, '')
    try:
        encoded = value + '=' * (-len(value) % 4)
        ciphertext = base64.urlsafe_b64decode(encoded.encode())
        if len(ciphertext) < 29:
            raise ValueError
        payload = google_signup_cipher().decrypt(ciphertext[:12], ciphertext[12:], GOOGLE_SIGNUP_COOKIE_AAD)
        claims = json.loads(payload)
        if (claims.get('provider') != 'google' or not isinstance(claims.get('sub'), str)
                or not isinstance(claims.get('exp'), int) or claims['exp'] <= int(time.time())):
            raise ValueError
        return claims
    except (ValueError, TypeError, AttributeError, InvalidTag):
        raise HTTPException(401, 'Google 회원가입 요청이 만료되었습니다. 다시 시작하세요.')


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


@router.get('/auth/google/login')
def google_login(request: Request):
    require_origin(request)
    config = require_provider('google')
    if not config['authorization_code_enabled']:
        raise HTTPException(503, 'Google OAuth 클라이언트 ID·보안 키·리디렉션 URI 설정이 필요합니다.')

    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
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


@router.get('/api/auth/google/callback')
async def google_callback(request: Request, code: str | None = None,
                          state: str | None = None, error: str | None = None,
                          db: Session = Depends(database)):
    frontend = settings.frontend_origin.rstrip('/')
    fallback = f'{frontend}/?social_error=google_auth_failed'
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


@router.get('/auth/social/google/pending')
def google_pending(request: Request, response: Response):
    require_origin(request)
    claims = open_google_signup(request)
    response.headers['Cache-Control'] = 'no-store'
    return {'registration_required': True, 'provider': 'google',
            'email': claims['email'], 'name': claims.get('name', '')}


class GoogleRegistration(RequestModel):
    name: str = Field(min_length=1, max_length=80)
    age: int = Field(gt=0, le=120)
    service_consent: bool
    consent_text: str = Field(max_length=4000)


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
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '이미 등록된 Google 계정 또는 이메일입니다. 다시 로그인하세요.')
    result = open_session(db, user, response, request)
    clear_google_signup_cookie(response)
    return result


class SocialCompletion(RequestModel):
    id_token: str = Field(min_length=1, max_length=16000)
    state: str | None = Field(default=None, max_length=256)
    name: str | None = Field(default=None, min_length=1, max_length=80)
    age: int | None = Field(default=None, gt=0, le=120)
    service_consent: bool = False
    consent_text: str | None = Field(default=None, max_length=4000)


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
        # Preserve the existing non-null password column; the random secret is never returned or stored in plaintext.
        user = User(email=email, name=name, age=body.age, role='user',
                    password_hash=hash_password(secrets.token_urlsafe(64)),
                    service_consent_text=body.consent_text, oauth_provider=provider, oauth_subject=claims['sub'])
        db.add(user)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, '이미 등록된 소셜 계정 또는 이메일입니다. 다시 로그인하세요.')
    require_service_age(user)
    result = open_session(db, user, response, request)
    response.delete_cookie(cookie_name(provider), path='/', secure=settings.cookie_secure,
                           httponly=True, samesite='lax')
    return result
