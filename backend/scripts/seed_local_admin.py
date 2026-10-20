# 로컬 개발 환경에서만 팀 공용 관리자 계정을 한 번 준비하는 seed 도구(쿠폰 발급·교환 처리·닉네임 초기화 확인용).
# 개발 설정(APP_ENV=development, LOCAL_TEST_SIGNUP=true, 프런트 localhost)일 때만 동작한다. 운영 관리자는 create_admin으로 따로 만든다.
# 이미 있는 계정은 덮어쓰거나 역할을 바꾸지 않는다.
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.accounts import LOCAL_TEST_CONSENT, hash_password
from backend.app.db import get_engine
from backend.app.models import User
from backend.scripts.seed_local_test_account import local_test_account_enabled

ADMIN_ACCOUNT_EMAIL = 'admin@calodetect.local'
ADMIN_ACCOUNT_PASSWORD = 'CaloAdmin!2026'


def seed_local_admin(db):
    existing = db.scalar(select(User).where(User.email == ADMIN_ACCOUNT_EMAIL))
    if existing:
        return 'exists' if existing.role == 'admin' else 'not-admin'
    db.add(User(email=ADMIN_ACCOUNT_EMAIL, name='CaloDetect 관리자', password_hash=hash_password(ADMIN_ACCOUNT_PASSWORD),
                role='admin', age=30, service_consent_text=LOCAL_TEST_CONSENT))
    db.commit()
    return 'created'


if __name__ == '__main__':
    if not local_test_account_enabled():
        raise SystemExit('Local development test settings required (APP_ENV=development, LOCAL_TEST_SIGNUP=true).')
    with Session(get_engine()) as db:
        result = seed_local_admin(db)
    print({'created': f'Local admin created: {ADMIN_ACCOUNT_EMAIL}',
           'exists': 'Local admin already exists; unchanged.',
           'not-admin': f'{ADMIN_ACCOUNT_EMAIL} exists as a normal user; not promoted.'}[result])
