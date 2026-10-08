# 회귀 테스트: local_test_account 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
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


# 회귀 검사: 로컬 · 계정 · 생성 · 한 번 · 일반 회원 · 회원.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_local_test_account_is_created_once_and_is_a_regular_user():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    # connection: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
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


# 회귀 검사: 로컬 · 계정 · 차단 · 외부 · 로컬 · 개발 환경.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
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


# 회귀 검사: 로컬 · 계정 · loopback · 개발 환경 · 설정.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_local_test_account_setup_requires_loopback_development_settings(monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'local_test_signup', True)
    monkeypatch.setattr(settings, 'frontend_origin', 'https://example.com')
    assert local_test_account_enabled() is False
