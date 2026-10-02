import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from .config import settings
from .db import get_engine
from .models import AuthSession, Profile, User, utcnow
from .schemas import CalorieRequest, RequestModel
from .services.profile import calculate_calorie_range

router = APIRouter()
COOKIE = 'calodetect_session'


class Credentials(RequestModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('올바른 이메일을 입력하세요.')
        return value


class Signup(Credentials):
    name: str = Field(min_length=1, max_length=80)
    age: int = Field(gt=0, le=120)
    service_consent: bool
    consent_text: str = Field(max_length=4000)

    @field_validator('name')
    @classmethod
    def valid_name(cls, value):
        if not value.strip():
            raise ValueError('이름을 입력하세요.')
        return value.strip()


class MemberUpdate(RequestModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator('name')
    @classmethod
    def valid_name(cls, value):
        return Signup.valid_name(value)


def database():
    try:
        engine = get_engine()
    except RuntimeError:
        raise HTTPException(503, '회원 DB 연결 설정이 필요합니다.')
    with Session(engine) as db:
        try:
            yield db
        except SQLAlchemyError:
            db.rollback()
            raise HTTPException(503, '회원 DB 또는 migration 실행 상태를 확인하세요.')


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password, stored):
    _, salt, _ = stored.split('$')
    return hmac.compare_digest(hash_password(password, salt), stored)


def require_origin(request: Request):
    # Same-origin proxy requests and the configured frontend are allowed.
    allowed = {settings.frontend_origin.rstrip('/'), str(request.base_url).rstrip('/')}
    if settings.frontend_origin == 'http://localhost:5173':
        allowed.add('http://127.0.0.1:5173')
    if request.headers.get('origin') and request.headers['origin'].rstrip('/') not in allowed:
        raise HTTPException(403, '허용되지 않은 요청 출처입니다.')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, '허용되지 않은 요청 출처입니다.')


def current_session(request: Request, db: Session = Depends(database)):
    token = request.cookies.get(COOKIE, '')
    session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if session is None:
        raise HTTPException(401, '로그인이 필요합니다.')
    expiry = session.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=utcnow().tzinfo)
    if expiry <= utcnow():
        raise HTTPException(401, '로그인이 만료되었습니다.')
    if request.method not in ('GET', 'HEAD'):
        require_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session.csrf_token):
            raise HTTPException(403, '세션을 새로고침한 뒤 다시 시도하세요.')
    return session


def public_user(user):
    return {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role}


def open_session(db, user, response, request=None):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_hex(32)
    db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                       expires_at=utcnow() + timedelta(hours=settings.session_hours), csrf_token=csrf))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.cookie_secure,
                        samesite='lax', max_age=settings.session_hours * 3600, path='/')
    response.headers['Cache-Control'] = 'no-store'
    result = {'user': public_user(user), 'csrf_token': csrf}
    # Browser accounts use only HttpOnly cookies. An internal admin CLI needs
    # an API credential for the separate Streamlit QA client.
    if user.role == 'admin' and request is not None and not request.headers.get('origin'):
        result.update(access_token=token, token_type='bearer')
    return result


@router.get('/auth/policy')
def policy():
    ready = settings.age_min is not None and bool(settings.service_consent_text)
    return {'signup_enabled': ready, 'age_min': settings.age_min,
            'service_consent_text': settings.service_consent_text,
            'model_improvement_consent_text': settings.model_improvement_consent_text,
            'notice': None if ready else '가입 연령과 서비스 이용·개인정보 동의 문구 확정 후 가입할 수 있습니다.'}


@router.post('/auth/signup', status_code=201)
def signup(body: Signup, request: Request, response: Response, db: Session = Depends(database)):
    require_origin(request)
    if not policy()['signup_enabled']:
        raise HTTPException(503, policy()['notice'])
    if body.age < settings.age_min:
        raise HTTPException(422, '가입 가능한 연령을 확인하세요.')
    if not body.service_consent or body.consent_text != settings.service_consent_text:
        raise HTTPException(422, '현재 서비스 이용·개인정보 동의 내용을 확인하세요.')
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password),
                role='user', age=body.age, service_consent_text=body.consent_text)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '이미 가입된 이메일입니다.')
    return open_session(db, user, response, request)


@router.post('/auth/login')
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(database)):
    require_origin(request)
    user = db.scalar(select(User).where(User.email == body.email))
    # Do the same expensive hash for unknown accounts.
    stored = user.password_hash if user else hash_password('unknown-account')
    valid = verify_password(body.password, stored)
    if not user or not valid:
        raise HTTPException(401, '이메일 또는 비밀번호를 확인하세요.')
    return open_session(db, user, response, request)


@router.post('/auth/logout')
def logout(response: Response, session=Depends(current_session), db: Session = Depends(database)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE, path='/', secure=settings.cookie_secure, httponly=True, samesite='lax')
    return {'status': 'ok'}


@router.get('/users/me')
def me(response: Response, session=Depends(current_session), db: Session = Depends(database)):
    response.headers['Cache-Control'] = 'no-store'
    return {'user': public_user(db.get(User, session.user_id)), 'csrf_token': session.csrf_token}


@router.put('/users/me')
def update_me(body: MemberUpdate, session=Depends(current_session), db: Session = Depends(database)):
    user = db.get(User, session.user_id)
    user.name = body.name
    db.commit()
    return {'user': public_user(user)}


@router.get('/users/me/profile')
def profile(response: Response, session=Depends(current_session), db: Session = Depends(database)):
    response.headers['Cache-Control'] = 'no-store'
    stored = db.get(Profile, session.user_id)
    return {'profile': stored.data if stored else None}


@router.put('/users/me/profile')
def save_profile(body: CalorieRequest, session=Depends(current_session), db: Session = Depends(database)):
    if settings.age_min is None:
        raise HTTPException(503, '프로필 저장을 위한 연령 정책 확정이 필요합니다.')
    if body.age < settings.age_min:
        raise HTTPException(422, '서비스 이용 연령을 확인하세요.')
    try:
        result = calculate_calorie_range(body)
    except ValueError as error:
        raise HTTPException(422, str(error))
    data = {**body.model_dump(), **result}
    if body.target_calories is None:
        raise HTTPException(422, '목표 칼로리를 입력하세요.')
    row = db.get(Profile, session.user_id)
    if row:
        row.data = data
    else:
        db.add(Profile(user_id=session.user_id, data=data))
    db.commit()
    return {'profile': data}
