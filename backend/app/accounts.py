# 이메일 회원가입·로그인, HttpOnly 세션 쿠키, 회원정보와 프로필 저장 라우트.
# 가입 정책·요청 출처·CSRF를 검사하고, DB에는 비밀번호와 세션 토큰의 해시만 보관한다.
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
# 회원 웹앱의 세션 쿠키 이름. 서버는 이 쿠키의 원문을 해시해 AuthSession에서 조회한다.
COOKIE = 'calodetect_session'
# 명시적으로 허용된 로컬 테스트에서만 쓰는 문구다. 운영 서비스 동의나 사진 모델 개선 동의를 대신하지 않는다.
LOCAL_TEST_CONSENT = (
    '로컬 개발 테스트용 가입 동의: 이 환경은 CaloDetect 기능 확인용입니다. '
    '만 18세 이상만 테스트 계정을 만들 수 있습니다. 실제 개인정보 대신 테스트용 이름·이메일을 입력해 주세요. '
    '이름, 이메일, 만 나이, 비밀번호 해시와 동의 내용이 개발 DB에 저장됩니다. '
    '로그인과 식단 기능 테스트에 사용하며 운영용 동의 문구가 아닙니다. '
    '테스트 가입에 동의하지 않으면 계정을 만들 수 없고 비회원 계산 기능은 사용할 수 있습니다. '
    '사진의 모델 개선 활용은 이 동의에 포함하지 않습니다.'
)


# development 설정과 프런트엔드 loopback 주소를 함께 확인해 로컬 개발 환경인지 판단한다.
def local_development_environment():
    return (settings.app_env == 'development'
            and urlparse(settings.frontend_origin).hostname in ('localhost', '127.0.0.1', '::1'))


# 로컬 가입 테스트 플래그와 개발 환경 조건이 모두 충족되는지 반환한다.
def local_test_enabled():
    return settings.local_test_signup and local_development_environment()


# 요청 URL·클라이언트가 loopback이고 전달 프록시 헤더가 없는지 확인한다.
def local_test_request(request):
    return (request.url.hostname in ('localhost', '127.0.0.1', '::1') and request.client is not None
            and request.client.host in ('localhost', '127.0.0.1', '::1')
            and not request.headers.get('x-forwarded-for') and not request.headers.get('forwarded'))


# Credentials: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class Credentials(RequestModel):
    # 가입 이메일. 인증 경로에서 정규화하고 DB의 unique 제약으로 중복 가입을 막는다.
    email: str = Field(max_length=254)
    # 인증용 입력 비밀번호. 이 요청 필드는 DB 저장용 해시와 다르다.
    password: str = Field(min_length=8, max_length=128)

    # 이메일 공백과 대소문자를 정리하고 가입/로그인에 사용할 주소 형식을 검증한다.
    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('올바른 이메일을 입력하세요.')
        return value


# Signup: Credentials를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class Signup(Credentials):
    # 사용자 표시 이름. 앞뒤 공백과 길이는 요청 모델에서 검증한다.
    name: str = Field(min_length=1, max_length=80)
    # 만 나이. 타입/범위 검사 외에 가입·로그인 서비스가 최소 연령을 확인한다.
    age: int = Field(gt=0, le=120)
    # 현재 서비스 필수 동의의 수락 여부. 실제 허용은 정책 검사에서 판단한다.
    service_consent: bool
    # 화면에서 확인한 필수 동의 문구. 서버 현재 문구와 정확히 일치해야 가입할 수 있다.
    consent_text: str = Field(max_length=4000)

    # 이름의 앞뒤 공백을 정리하고 빈 이름을 거부한다.
    @field_validator('name')
    @classmethod
    def valid_name(cls, value):
        if not value.strip():
            raise ValueError('이름을 입력하세요.')
        return value.strip()


# MemberUpdate: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class MemberUpdate(RequestModel):
    # 사용자 표시 이름. 앞뒤 공백과 길이는 요청 모델에서 검증한다.
    name: str = Field(min_length=1, max_length=80)

    # 이름의 앞뒤 공백을 정리하고 빈 이름을 거부한다.
    @field_validator('name')
    @classmethod
    def valid_name(cls, value):
        return Signup.valid_name(value)


# 회원 API에 DB 세션을 공급하고 SQLAlchemy 오류 시 rollback 후 일반 오류를 반환한다.
def database():
    try:
        engine = get_engine()
    except RuntimeError:
        raise HTTPException(503, '회원 DB 연결 설정이 필요합니다.')
    with Session(engine) as db:
        try:
            yield db
        except SQLAlchemyError:
            # 실패한 트랜잭션을 되돌려 부분 변경이 확정되지 않도록 한다.
            db.rollback()
            raise HTTPException(503, '회원 DB 또는 migration 실행 상태를 확인하세요.')


# 새 salt 또는 전달된 salt로 scrypt 해시를 만들어 알고리즘·salt·해시 문자열을 반환한다.
def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'scrypt${salt}${digest}'


# 저장된 salt로 입력 비밀번호를 다시 해시하고 상수 시간 비교로 일치 여부를 확인한다.
def verify_password(password, stored):
    _, salt, _ = stored.split('$')
    return hmac.compare_digest(hash_password(password, salt), stored)


# 설정된 프런트엔드/동일 원본만 허용하고 cross-site 변경 요청을 거부한다.
def require_origin(request: Request):
    # Same-origin proxy requests and the configured frontend are allowed.
    # 동일 원본 Vite 프록시와 설정된 프런트엔드 원본을 함께 허용한다.
    allowed = {settings.frontend_origin.rstrip('/'), str(request.base_url).rstrip('/')}
    if settings.frontend_origin == 'http://localhost:5173':
        allowed.add('http://127.0.0.1:5173')
    if request.headers.get('origin') and request.headers['origin'].rstrip('/') not in allowed:
        raise HTTPException(403, '허용되지 않은 요청 출처입니다.')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, '허용되지 않은 요청 출처입니다.')


# 쿠키 토큰 해시로 세션을 찾아 만료·회원 연령·변경 요청의 출처와 CSRF를 검사한다.
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
    # 연령 정책에서 제외된 기존 계정도 이미 발급된 세션을 종료할 수 있도록 로그아웃은 허용한다.
    if request.url.path != '/auth/logout':
        require_service_age(user)
    if request.method not in ('GET', 'HEAD'):
        require_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session.csrf_token):
            raise HTTPException(403, '세션을 새로고침한 뒤 다시 시도하세요.')
    return session


# 회원 응답에 필요한 공개 필드와 이메일 비밀번호 로그인 가능 여부만 반환한다.
def public_user(user):
    return {'id': user.id, 'email': user.email, 'name': user.name, 'role': user.role,
            'password_login_enabled': not bool(user.oauth_provider)}


# 무작위 세션/CSRF 토큰을 생성하고 DB에 세션 해시를 저장한 뒤 HttpOnly 쿠키를 설정한다.
# 브라우저에는 원문 세션 토큰을 JSON으로 제공하지 않으며 Origin 없는 관리자 클라이언트에만 Bearer 자격정보를 제공한다.
def open_session(db, user, response, request=None):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_hex(32)
    db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id,
                       expires_at=utcnow() + timedelta(hours=settings.session_hours), csrf_token=csrf))
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
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


# 동의 문구·연령·로컬 테스트 설정으로 현재 가입 가능 여부와 비밀번호 찾기 설정 상태를 반환한다.
# HTTP GET /auth/policy: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
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


# 현재 동의 문구와 연령을 검사해 일반 회원을 생성하고 중복 이메일을 처리한 뒤 로그인 세션을 연다.
# HTTP POST /auth/signup: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
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
        # commit 전 SQL을 반영해 생성 ID·제약 오류를 확인한다. 아직 변경을 최종 확정한 것은 아니다.
        db.flush()
    except IntegrityError:
        # 실패한 트랜잭션을 되돌려 부분 변경이 확정되지 않도록 한다.
        db.rollback()
        raise HTTPException(409, '이미 가입된 이메일입니다.')
    return open_session(db, user, response, request)


# 이메일/비밀번호를 검증하고 소셜 계정의 비밀번호 로그인을 차단한 뒤 연령 검사와 세션 발급을 수행한다.
# HTTP POST /auth/login: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/auth/login')
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(database)):
    require_origin(request)
    user = db.scalar(select(User).where(User.email == body.email))
    # Do the same expensive hash for unknown accounts.
    # 존재하지 않는 이메일도 비싼 해시 계산을 수행해 계정 유무에 따른 처리 시간 차이를 줄인다.
    stored = user.password_hash if user else hash_password('unknown-account')
    valid = verify_password(body.password, stored)
    # 이메일 비밀번호 기능과 소셜 인증 계정의 처리 경로를 구분한다.
    if not user or not valid or user.oauth_provider:
        raise HTTPException(401, '이메일 또는 비밀번호를 확인하세요.')
    require_service_age(user)
    return open_session(db, user, response, request)


# 인증된 세션을 DB에서 삭제하고 동일 옵션으로 브라우저 쿠키도 제거한다.
# HTTP POST /auth/logout: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/auth/logout')
def logout(response: Response, session=Depends(current_session), db: Session = Depends(database)):
    db.delete(session)
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit()
    response.delete_cookie(COOKIE, path='/', secure=settings.cookie_secure, httponly=True, samesite='lax')
    return {'status': 'ok'}


# 현재 세션의 공개 회원정보와 변경 요청용 CSRF 토큰을 반환한다.
# HTTP GET /users/me: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/users/me')
def me(response: Response, session=Depends(current_session), db: Session = Depends(database)):
    response.headers['Cache-Control'] = 'no-store'
    return {'user': public_user(db.get(User, session.user_id)), 'csrf_token': session.csrf_token}


# 인증된 회원의 이름만 갱신한다. 역할·이메일·비밀번호 변경 입력은 받지 않는다.
# HTTP PUT /users/me: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.put('/users/me')
def update_me(body: MemberUpdate, session=Depends(current_session), db: Session = Depends(database)):
    user = db.get(User, session.user_id)
    user.name = body.name
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit()
    return {'user': public_user(user)}


# 현재 회원의 저장된 프로필을 반환하고 아직 없으면 null로 표시한다.
# HTTP GET /users/me/profile: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/users/me/profile')
def profile(response: Response, session=Depends(current_session), db: Session = Depends(database)):
    response.headers['Cache-Control'] = 'no-store'
    stored = db.get(Profile, session.user_id)
    return {'profile': stored.data if stored else None}


# 연령과 목표 칼로리를 검사하고 서버 계산 결과를 입력값과 함께 신규 저장 또는 갱신한다.
# HTTP PUT /users/me/profile: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
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
    # 검증된 신체 입력과 서버 계산 결과를 하나의 JSON에 보관한다. 계산 결과가 동일 키를 우선한다.
    data = {**body.model_dump(), **result}
    if body.target_calories is None:
        raise HTTPException(422, '목표 칼로리를 입력하세요.')
    # 회원 ID가 프로필 기본키이므로 같은 회원은 한 프로필을 갱신하고 새 회원은 처음 생성한다.
    row = db.get(Profile, session.user_id)
    if row:
        row.data = data
    else:
        db.add(Profile(user_id=session.user_id, data=data))
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit()
    return {'profile': data}
