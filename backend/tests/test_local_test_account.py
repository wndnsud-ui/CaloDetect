from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from backend.app.accounts import COOKIE, database, verify_password
from backend.app.config import settings
from backend.app.main import app
from backend.app.models import Base, User
from backend.scripts.seed_local_test_account import (
    TEST_ACCOUNT_EMAIL,
    TEST_ACCOUNT_PASSWORD,
    local_test_account_enabled,
    main,
    seed_local_test_account,
)


def test_local_test_account_is_created_once_and_is_a_regular_user():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def connection():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[database] = connection
    try:
        with Session(engine) as db:
            assert seed_local_test_account(db) is True
            assert seed_local_test_account(db) is False
            user = db.query(User).filter_by(email=TEST_ACCOUNT_EMAIL).one()
            assert user.role == 'user'
            assert verify_password(TEST_ACCOUNT_PASSWORD, user.password_hash)
        with TestClient(app) as client:
            response = client.post('/auth/login', json={
                'email': TEST_ACCOUNT_EMAIL,
                'password': TEST_ACCOUNT_PASSWORD,
            })
            assert response.status_code == 200
            assert client.cookies.get(COOKIE)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_local_test_account_setup_is_blocked_outside_local_development(monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'local_test_signup', True)
    monkeypatch.setattr(settings, 'frontend_origin', 'http://localhost:5174')
    try:
        main()
    except SystemExit as error:
        assert 'local development settings' in str(error)
    else:
        raise AssertionError('Production settings must not seed the local test account.')


def test_local_test_account_setup_requires_loopback_development_settings(monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'local_test_signup', True)
    monkeypatch.setattr(settings, 'frontend_origin', 'https://example.com')
    assert local_test_account_enabled() is False
