import hashlib
import hmac
import re
import secrets
from urllib.parse import urlparse
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
from .security import require_service_age

router = APIRouter()
COOKIE = 'calodetect_session'
LOCAL_TEST_CONSENT = (
    '로컬 개발 테스트용 가입 동의: 이 환경은 CaloDetect 기능 확인용입니다. '
    '만 18세 이상만 테스트 계정을 만들 수 있습니다. 실제 개인정보 대신 테스트용 이름·이메일을 입력해 주세요. '
    '이름, 이메일, 만 나이, 비밀번호 해시와 동의 내용이 개발 DB에 저장됩니다. '
    '로그인과 식단 기능 테스트에 사용하며 운영용 동의 문구가 아닙니다. '
    '테스트 가입에 동의하지 않으면 계정을 만들 수 없고 비회원 계산 기능은 사용할 수 있습니다. '
    '사진의 모델 개선 활용은 이 동의에 포함하지 않습니다.'
)


def local_development_environment():
    return (settings.app_env == 'development'
            and urlparse(settings.frontend_origin).hostname in ('localhost', '127.0.0.1', '::1'))


def local_test_enabled():
    return settings.local_test_signup and local_development_environment()


def local_test_request(request):
    return (request.url.hostname in ('localhost', '127.0.0.1', '::1') and request.client is not None
            and request.client.host in ('localhost', '127.0.0.1', '::1')
            and not request.headers.get('x-forwarded-for') and not request.headers.get('forwarded'))


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
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, '로그인이 필요합니다.')
    # Allow logout even if an existing account no longer meets the age policy.
    if request.url.path != '/auth/logout':
        require_service_age(user)
    if request.method not in ('GET', 'HEAD'):
        require_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session.csrf_token):
            raise HTTPException(403, '세션을 새로고침한 뒤 다시 시도하세요.')
    return session


def public_user(user):
    return {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role,
            'password_login_enabled': not bool(user.oauth_provider)}


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
def policy(request: Request = None):
    from .passwords import reset_enabled
    testing = not settings.service_consent_text and local_test_enabled()
    consent = settings.service_consent_text or (LOCAL_TEST_CONSENT if testing else None)
    ready = settings.age_min is not None and bool(consent)
    if testing and request is not None and not local_test_request(request):
        ready = False
    return {'signup_enabled': ready, 'age_min': settings.age_min,
            'password_reset_enabled': reset_enabled(),
            'service_consent_text': consent if ready else settings.service_consent_text,
            'local_test_mode': bool(testing and ready),
            'model_improvement_consent_text': settings.model_improvement_consent_text,
            'notice': None if ready else '서비스 이용·개인정보 동의 문구 설정 후 가입할 수 있습니다.'}


@router.post('/auth/signup', status_code=201)
def signup(body: Signup, request: Request, response: Response, db: Session = Depends(database)):
    require_origin(request)
    current_policy = policy(request)
    if not current_policy['signup_enabled']:
        raise HTTPException(503, current_policy['notice'])
    if body.age < settings.age_min:
        raise HTTPException(422, f'만 {settings.age_min}세 이상만 가입할 수 있습니다.')
    if not body.service_consent or body.consent_text != current_policy['service_consent_text']:
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
    if not user or not valid or user.oauth_provider:
        raise HTTPException(401, '이메일 또는 비밀번호를 확인하세요.')
    require_service_age(user)
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
