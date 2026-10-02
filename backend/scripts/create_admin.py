import argparse
from getpass import getpass
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import TypeAdapter, EmailStr
from backend.app.db import get_engine
from backend.app.models import User
from backend.app.security import password_hash


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Internal first admin bootstrap')
    parser.add_argument('--email', required=True)
    parser.add_argument('--age', type=int, required=True)
    args = parser.parse_args()
    email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    password = getpass('Admin password (10+ characters): ')
    if len(password) < 10 or len(password) > 128:
        raise SystemExit('Invalid password length')
    from backend.app.config import settings
    if settings.age_min is None or args.age < settings.age_min:
        raise SystemExit('Age policy must be configured and met')
    with Session(get_engine()) as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit('Existing user: no automatic promotion')
        db.add(User(email=email, name='관리자', service_consent_text='내부 운영 계정',
                    password_hash=password_hash(password), role='admin', age=args.age))
        db.commit()
    print('Admin created')
