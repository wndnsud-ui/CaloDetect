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


@pytest.fixture
def accounts(monkeypatch):
    # Test-only wording/age, deliberately never configured in production.
    monkeypatch.setattr(settings, 'age_min', 20)
    monkeypatch.setattr(settings, 'service_consent_text', 'TEST ONLY CONSENT')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    def connection():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[database] = connection
    with TestClient(app) as client:
        yield client, engine
    app.dependency_overrides.clear()
    engine.dispose()


def register(client, email='one@example.com'):
    return client.post('/auth/signup', json={'email': email, 'password': 'secure-test-password',
        'name': '테스트 회원', 'age': 30, 'service_consent': True, 'consent_text': 'TEST ONLY CONSENT'})


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
        db.commit()
    assert client.get('/users/me').status_code == 401


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


def test_admin_qa_token_is_not_exposed_to_browser(accounts):
    client, engine = accounts
    register(client)
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.role = 'admin'  # Internal test seed, never an API promotion.
        db.commit()
    body = {'email':'one@example.com', 'password':'secure-test-password'}
    browser = client.post('/auth/login', json=body, headers={'Origin':settings.frontend_origin})
    assert browser.status_code == 200
    assert 'access_token' not in browser.json()
    internal = client.post('/auth/login', json=body)
    assert internal.status_code == 200
    assert internal.json()['access_token'] == client.cookies.get(COOKIE)
