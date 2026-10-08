# 회귀 테스트: accounts 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.app.accounts import COOKIE, database
from backend.app.config import settings
from backend.app.main import app
from backend.app.models import AuthSession, Base, User, utcnow


# accounts: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
@pytest.fixture
def accounts(monkeypatch):
    monkeypatch.setattr(settings, 'local_test_signup', False)
    # Test-only wording/age, deliberately never configured in production.
    monkeypatch.setattr(settings, 'age_min', 20)
    monkeypatch.setattr(settings, 'service_consent_text', 'TEST ONLY CONSENT')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    # connection: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
    def connection():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[database] = connection
    with TestClient(app) as client:
        yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()


# register: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
def register(client, email='one@example.com'):
    return client.post('/auth/signup', json={'email': email, 'password': 'secure-test-password',
        'name': '테스트 회원', 'age': 30, 'service_consent': True, 'consent_text': 'TEST ONLY CONSENT'})


# 회귀 검사: 가입 정책 · 차단 조건 · 동의.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_policy_gate_and_consent(accounts, monkeypatch):
    client, _ = accounts
    monkeypatch.setattr(settings, 'age_min', None)
    assert client.get('/auth/policy').json()['signup_enabled'] is False
    assert register(client).status_code == 503
    monkeypatch.setattr(settings, 'age_min', 20)
    body = {'email':'one@example.com', 'password':'secure-test-password', 'name':'테스트',
            'age':19, 'service_consent':True, 'consent_text':'TEST ONLY CONSENT'}
    assert client.post('/auth/signup', json=body).status_code == 422
    assert client.post('/auth/signup', json={**body, 'age':30, 'service_consent':False}).status_code == 422
    assert client.post('/auth/signup', json={**body, 'age':30, 'consent_text':'stale consent'}).status_code == 422


# 회귀 검사: 가입 · 해시 · 중복 · 권한.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_signup_hash_duplicate_and_role(accounts):
    client, engine = accounts
    response = register(client)
    assert response.status_code == 201
    assert response.json()['user']['role'] == 'user'
    assert 'password_hash' not in response.json()['user']
    assert 'access_token' not in response.json()
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=lax' in response.headers['set-cookie']
    assert register(client, 'ONE@example.com').status_code == 409
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith('scrypt$')
        assert 'secure-test-password' not in user.password_hash
        assert db.scalar(select(AuthSession)).token_hash != client.cookies.get(COOKIE)
    csrf = response.json()['csrf_token']
    assert client.put('/users/me', json={'name':'관리자', 'role':'admin'}, headers={'X-CSRF-Token':csrf}).status_code == 422
    assert client.get('/users/me').json()['user']['role'] == 'user'


# 회귀 검사: 세션 · 복원 · 새 · 클라이언트.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_session_restores_in_new_client(accounts):
    client, _ = accounts
    response = register(client)
    assert f'Max-Age={settings.session_hours * 3600}' in response.headers['set-cookie']
    with TestClient(app) as restored:
        restored.cookies.set(COOKIE, client.cookies.get(COOKIE))
        me = restored.get('/users/me')
        assert me.status_code == 200
        assert me.json()['user']['id'] == response.json()['user']['id']
        assert me.json()['csrf_token'] == response.json()['csrf_token']
        assert restored.put('/users/me', json={'name':'복원 확인'},
            headers={'X-CSRF-Token':me.json()['csrf_token']}).status_code == 200


# 회귀 검사: 로그인 · 로그아웃 · 폐기.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_login_logout_revocation(accounts):
    client, _ = accounts
    csrf = register(client).json()['csrf_token']
    stolen = client.cookies.get(COOKIE)
    assert client.post('/auth/logout', json={}, headers={'X-CSRF-Token':csrf}).status_code == 200
    client.cookies.set(COOKIE, stolen)
    assert client.get('/users/me').status_code == 401
    client.cookies.clear()
    assert client.post('/auth/login', json={'email':'one@example.com','password':'incorrect-pass'}).status_code == 401
    assert client.post('/auth/login', json={'email':'missing@example.com','password':'incorrect-pass'}).status_code == 401
    assert client.post('/auth/login', json={'email':'one@example.com','password':'secure-test-password'}).status_code == 200


# 회귀 검사: CSRF · 요청 출처 · 만료.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_csrf_origin_and_expiry(accounts):
    client, engine = accounts
    csrf = register(client).json()['csrf_token']
    assert client.put('/users/me', json={'name':'새 이름'}).status_code == 403
    assert client.put('/users/me', json={'name':'새 이름'}, headers={'X-CSRF-Token':csrf,'Origin':'https://untrusted.example'}).status_code == 403
    assert client.post('/auth/login', json={'email':'one@example.com','password':'secure-test-password'}, headers={'Origin':'https://untrusted.example'}).status_code == 403
    assert client.put('/users/me', json={'name':'새 이름'}, headers={'X-CSRF-Token':csrf}).status_code == 200
    assert client.get('/users/me').json()['user']['name'] == '새 이름'
    with Session(engine) as db:
        row = db.scalar(select(AuthSession))
        row.expires_at = utcnow() - timedelta(seconds=1)
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit()
    assert client.get('/users/me').status_code == 401


# 회귀 검사: 프로필 · 저장 유지 · 분리.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_profile_persists_and_isolated(accounts):
    client, _ = accounts
    assert client.get('/users/me/profile').status_code == 401
    csrf = register(client).json()['csrf_token']
    body={'height':175,'weight':70,'age':30,'sex':'male','activity_level':'moderate',
          'goal_type':'maintain','target_calories':2500}
    assert client.get('/users/me/profile').json()['profile'] is None
    saved = client.put('/users/me/profile', json=body, headers={'X-CSRF-Token':csrf})
    assert saved.status_code == 200
    assert saved.json()['profile']['bmr'] == 1648.75
    assert client.put('/users/me/profile', json={**body,'target_calories':1200}, headers={'X-CSRF-Token':csrf}).status_code == 422
    assert client.put('/users/me/profile', json={**body,'age':19}, headers={'X-CSRF-Token':csrf}).status_code == 422
    assert client.get('/users/me/profile').json()['profile']['target_calories'] == 2500
    client.post('/auth/logout', json={}, headers={'X-CSRF-Token':csrf})
    register(client, 'two@example.com')
    assert client.get('/users/me/profile').json()['profile'] is None
    client.cookies.clear()
    client.post('/auth/login', json={'email':'one@example.com','password':'secure-test-password'})
    assert client.get('/users/me/profile').json()['profile']['target_calories'] == 2500


# 회귀 검사: 관리자 · QA · 토큰 · 노출 · 브라우저.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_admin_qa_token_is_not_exposed_to_browser(accounts):
    client, engine = accounts
    register(client)
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.role = 'admin'  # Internal test seed, never an API promotion.
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit()
    body = {'email':'one@example.com', 'password':'secure-test-password'}
    browser = client.post('/auth/login', json=body, headers={'Origin':settings.frontend_origin})
    assert browser.status_code == 200
    assert 'access_token' not in browser.json()
    internal = client.post('/auth/login', json=body)
    assert internal.status_code == 200
    assert internal.json()['access_token'] == client.cookies.get(COOKIE)


# 회귀 검사: 18세 · 연령 · 연령 · 경계.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_eighteen_year_age_boundary(accounts, monkeypatch):
    client, engine = accounts
    monkeypatch.setattr(settings, 'age_min', 18)
    assert client.get('/auth/policy').json()['age_min'] == 18
    body = {'email': 'adult@example.com', 'password': 'secure-test-password',
            'name': 'Adult', 'age': 17, 'service_consent': True,
            'consent_text': 'TEST ONLY CONSENT'}
    assert client.post('/auth/signup', json=body).status_code == 422
    with Session(engine) as db:
        assert db.scalar(select(User)) is None
    response = client.post('/auth/signup', json={**body, 'age': 18})
    assert response.status_code == 201
    csrf = response.json()['csrf_token']
    credentials = {'email': body['email'], 'password': body['password']}
    assert client.post('/auth/login', json=credentials).status_code == 200
    csrf = client.get('/users/me').json()['csrf_token']
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.age = 17
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit()
        count = len(db.scalars(select(AuthSession)).all())
    # Already-issued sessions cannot bypass the age policy.
    assert client.get('/users/me').status_code == 403
    from backend.app.db import get_db
    app.dependency_overrides[get_db] = app.dependency_overrides[database]
    assert client.get('/meals/history').status_code == 403
    client.cookies.clear()
    rejected = client.post('/auth/login', json=credentials)
    assert rejected.status_code == 403
    assert 'set-cookie' not in rejected.headers
    with Session(engine) as db:
        assert len(db.scalars(select(AuthSession)).all()) == count


# 회귀 검사: 연령 · 가입 정책 · 미승인 · 동의.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_age_policy_does_not_enable_unapproved_consent(accounts, monkeypatch):
    client, _ = accounts
    monkeypatch.setattr(settings, 'age_min', 18)
    monkeypatch.setattr(settings, 'service_consent_text', None)
    policy = client.get('/auth/policy').json()
    assert policy['age_min'] == 18
    assert policy['signup_enabled'] is False
    assert register(client).status_code == 503


# 회귀 검사: 로컬 · 가입 · 개발 환경 · loopback · 명시적 · 동의.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_local_signup_requires_development_loopback_and_explicit_consent(accounts, monkeypatch):
    _, engine = accounts
    monkeypatch.setattr(settings, 'age_min', 18)
    monkeypatch.setattr(settings, 'service_consent_text', None)
    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'local_test_signup', True)
    monkeypatch.setattr(settings, 'frontend_origin', 'http://localhost:5173')
    with TestClient(app, base_url='http://localhost:8000', client=('127.0.0.1', 50000)) as client:
        policy = client.get('/auth/policy').json()
        assert policy['signup_enabled'] is True
        assert policy['local_test_mode'] is True
        body = {'email': 'local-test@example.com', 'password': 'secure-test-password', 'name': 'Test',
                'age': 18, 'service_consent': True, 'consent_text': policy['service_consent_text']}
        assert client.post('/auth/signup', json={**body, 'service_consent': False}).status_code == 422
        assert client.post('/auth/signup', json={**body, 'age': 17}).status_code == 422
        assert client.post('/auth/signup', json={**body, 'consent_text': 'stale'}).status_code == 422
        assert client.post('/auth/signup', json=body, headers={'X-Forwarded-For': '203.0.113.1'}).status_code == 503
        response = client.post('/auth/signup', json=body, headers={'Origin': settings.frontend_origin})
        assert response.status_code == 201
        assert response.json()['user']['role'] == 'user'
        assert client.get('/users/me').status_code == 200
        with Session(engine) as db:
            user = db.scalar(select(User))
            assert user.service_consent_text == policy['service_consent_text']
            assert user.model_improvement_consent is False
        monkeypatch.setattr(settings, 'app_env', 'production')
        assert client.get('/auth/policy').json()['signup_enabled'] is False
        assert client.post('/auth/signup', json={**body, 'email': 'production@example.com'}).status_code == 503
    monkeypatch.setattr(settings, 'app_env', 'development')
    with TestClient(app, base_url='http://localhost:8000', client=('203.0.113.1', 50000)) as remote:
        assert remote.get('/auth/policy').json()['signup_enabled'] is False
        assert remote.post('/auth/signup', json=body).status_code == 503
    with TestClient(app, base_url='https://public.example.com', client=('127.0.0.1', 50000)) as public:
        assert public.get('/auth/policy').json()['signup_enabled'] is False
        assert public.post('/auth/signup', json=body).status_code == 503
    monkeypatch.setattr(settings, 'frontend_origin', 'https://public.example.com')
    with TestClient(app, base_url='http://localhost:8000', client=('127.0.0.1', 50000)) as client:
        assert client.get('/auth/policy').json()['signup_enabled'] is False
