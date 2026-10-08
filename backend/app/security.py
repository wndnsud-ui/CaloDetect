# 비밀번호·세션 토큰 해시와 인증·관리자 권한 의존성.
# 브라우저 쿠키 요청에는 변경 작업의 출처/CSRF 검사를 적용하며 관리자 QA 클라이언트는 Bearer 토큰으로 인증한다.
import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import User, AuthSession


# 16바이트 salt를 생성하고 scrypt 비밀번호 해시를 저장 가능한 문자열로 인코딩한다.
def password_hash(password):
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f'scrypt${salt.hex()}${value.hex()}'


# 저장 형식에서 salt를 복원해 scrypt 해시를 비교하며 잘못된 해시 형식은 불일치로 처리한다.
def password_matches(password, encoded):
    try:
        _, salt, value = encoded.split('$')
        calculated = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(calculated.hex(), value)
    except (ValueError, TypeError):
        return False


# 원문 세션 토큰의 SHA-256을 계산해 DB 조회/저장 키로 사용한다.
def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


# 기존 회원도 서비스 최소 연령을 충족하는지 검사한다.
def require_service_age(user):
    minimum = settings.age_min or 18
    if user.age is None or user.age < minimum:
        raise HTTPException(403, f'만 {minimum}세 이상만 로그인하고 서비스를 이용할 수 있습니다.')


# 세션 토큰을 생성해 해시와 만료 시각을 DB 세션에 추가한다. commit은 호출 측에서 수행한다.
def new_session(db, user):
    token = secrets.token_urlsafe(48)
    db.add(AuthSession(token_hash=hash_token(token), user_id=user.id,
                       expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)))
    return token


# Bearer 또는 HttpOnly 쿠키의 세션을 검증해 회원을 반환하고 쿠키 기반 변경 요청은 CSRF도 확인한다.
def get_user(request: Request, db: Session = Depends(get_db)):
    bearer = request.headers.get('authorization', '')
    # Bearer 자격정보가 있으면 이를 사용하고 아니면 웹앱의 세션 쿠키를 읽는다.
    token = bearer[7:] if bearer.startswith('Bearer ') else request.cookies.get('calodetect_session')
    if not token:
        raise HTTPException(401, '로그인이 필요합니다.')
    auth_session = db.get(AuthSession, hash_token(token))
    if not auth_session:
        raise HTTPException(401, '로그인이 만료되었습니다.')
    expiry = auth_session.expires_at
    # DB 드라이버가 timezone 없는 datetime을 반환하면 저장 기준인 UTC로 명시한다.
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(401, '로그인이 만료되었습니다.')
    user = db.get(User, auth_session.user_id)
    if not user:
        raise HTTPException(401, '로그인이 필요합니다.')
    require_service_age(user)
    # 쿠키는 브라우저가 자동 전송하므로 변경 요청에는 출처와 세션별 CSRF 값 검사가 추가로 필요하다.
    if request.method not in ('GET', 'HEAD') and not bearer.startswith('Bearer '):
        from .accounts import require_origin
        require_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), auth_session.csrf_token):
            raise HTTPException(403, '세션을 새로고침한 뒤 다시 시도하세요.')
    return user


# 인증된 회원 role이 admin인지 확인하고 일반 회원은 403으로 차단한다.
def get_admin(user: User = Depends(get_user)):
    if user.role != 'admin':
        raise HTTPException(403, '관리자만 접근할 수 있습니다.')
    return user
