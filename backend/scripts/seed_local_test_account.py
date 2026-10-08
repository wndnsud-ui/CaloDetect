# 로컬 개발 환경에서만 테스트 일반 계정을 한 번 준비하는 seed 도구.
# 재실행 시 기존 회원을 덮어쓰지 않으며 운영 환경에서는 생성을 차단한다.
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.accounts import LOCAL_TEST_CONSENT, hash_password
from backend.app.config import settings
from backend.app.db import get_engine
from backend.app.models import User

TEST_ACCOUNT_EMAIL = 'test@calodetect.local'
TEST_ACCOUNT_PASSWORD = 'CaloTest!2026'
TEST_ACCOUNT_AGE = 25


# 명시적 로컬 테스트 가입 플래그와 개발/loopback 조건을 확인한다.
def local_test_account_enabled():
    frontend_host = urlparse(settings.frontend_origin).hostname
    return (settings.app_env == 'development' and settings.local_test_signup
            and frontend_host in ('localhost', '127.0.0.1', '::1'))


# 허용된 로컬 환경에서 테스트 이메일을 조회하고 기존 계정은 보존하며 없을 때만 일반 계정을 생성한다.
def seed_local_test_account(db):
    existing = db.scalar(select(User).where(User.email == TEST_ACCOUNT_EMAIL))
    if existing:
        return False

    db.add(User(email=TEST_ACCOUNT_EMAIL, name='CaloDetect 테스트',
                password_hash=hash_password(TEST_ACCOUNT_PASSWORD), role='user',
                age=TEST_ACCOUNT_AGE, service_consent_text=LOCAL_TEST_CONSENT))
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit()
    return True


# 로컬 개발 환경에서만 테스트 일반 계정을 한 번 준비하는 seed 도구.
# 명령행으로 실행할 때 아래 초기화·검사·출력 순서를 수행한다.
def main():
    if not local_test_account_enabled():
        raise SystemExit('Local test account setup requires local development settings.')
    if settings.age_min is None or settings.age_min > TEST_ACCOUNT_AGE:
        raise SystemExit('The configured minimum age is not met by the local test account.')

    with Session(get_engine()) as db:
        created = seed_local_test_account(db)
    print('Local test account created.' if created else 'Local test account already exists; unchanged.')


if __name__ == '__main__':
    main()
