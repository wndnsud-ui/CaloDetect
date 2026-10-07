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


def local_test_account_enabled():
    frontend_host = urlparse(settings.frontend_origin).hostname
    return (settings.app_env == 'development' and settings.local_test_signup
            and frontend_host in ('localhost', '127.0.0.1', '::1'))


def seed_local_test_account(db):
    existing = db.scalar(select(User).where(User.email == TEST_ACCOUNT_EMAIL))
    if existing:
        return False

    db.add(User(email=TEST_ACCOUNT_EMAIL, name='CaloDetect 테스트',
                password_hash=hash_password(TEST_ACCOUNT_PASSWORD), role='user',
                age=TEST_ACCOUNT_AGE, service_consent_text=LOCAL_TEST_CONSENT))
    db.commit()
    return True


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
