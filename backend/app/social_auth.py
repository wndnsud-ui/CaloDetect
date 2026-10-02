"""Google/Apple identity verification; secrets and provider tokens stay out of logs."""
import hmac
import secrets
from datetime import timedelta
from typing import Literal
from urllib.parse import urlparse

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, '이미 등록된 소셜 계정 또는 이메일입니다. 다시 로그인하세요.')
    require_service_age(user)
    result = open_session(db, user, response, request)
    response.delete_cookie(cookie_name(provider), path='/', secure=settings.cookie_secure,
                           httponly=True, samesite='lax')
    return result
