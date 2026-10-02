import hashlib
import hmac
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import User, AuthSession


def password_hash(password):
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f'scrypt${salt.hex()}${value.hex()}'


def password_matches(password, encoded):
    try:
        _, salt, value = encoded.split('$')
        calculated = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(calculated.hex(), value)
    except (ValueError, TypeError):
        return False


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(db, user):
    token = secrets.token_urlsafe(48)
    db.add(AuthSession(token_hash=hash_token(token), user_id=user.id,
                       expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)))
    return token


def get_user(request: Request, db: Session = Depends(get_db)):
    bearer = request.headers.get('authorization', '')
    token = bearer[7:] if bearer.startswith('Bearer ') else request.cookies.get('calodetect_session')
    if not token:
        raise HTTPException(401, '로그인이 필요합니다.')
    auth_session = db.get(AuthSession, hash_token(token))
    if not auth_session:
        raise HTTPException(401, '로그인이 만료되었습니다.')
    expiry = auth_session.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(401, '로그인이 만료되었습니다.')
    user = db.get(User, auth_session.user_id)
    if not user:
        raise HTTPException(401, '로그인이 필요합니다.')
    if request.method not in ('GET', 'HEAD') and not bearer.startswith('Bearer '):
        from .accounts import require_origin
        require_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), auth_session.csrf_token):
            raise HTTPException(403, '세션을 새로고침한 뒤 다시 시도하세요.')
    return user


def get_admin(user: User = Depends(get_user)):
    if user.role != 'admin':
        raise HTTPException(403, '관리자만 접근할 수 있습니다.')
    return user
