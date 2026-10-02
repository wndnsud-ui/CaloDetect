from datetime import timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.accounts import COOKIE, database
from backend.app.config import settings
from backend.app.main import app
from backend.app.models import AuthSession, Base, User, utcnow
from backend.app.social_auth import KEYS, cookie_name


@pytest.fixture(scope='module')
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def social(monkeypatch, signing_key):
    monkeypatch.setattr(settings, 'local_test_signup', False)
    monkeypatch.setattr(settings, 'age_min', 18)
    monkeypatch.setattr(settings, 'service_consent_text', 'TEST ONLY CONSENT')
    monkeypatch.setattr(settings, 'oauth_state_secret', 'test-only-secret-with-more-than-32-characters')
    monkeypatch.setattr(settings, 'google_client_id', 'test-google-client')
    monkeypatch.setattr(settings, 'apple_client_id', 'test-apple-client')
    monkeypatch.setattr(settings, 'apple_redirect_uri', 'https://example.com/login')
    for client in KEYS.values():
        monkeypatch.setattr(client, 'get_signing_key_from_jwt',
                            lambda token: SimpleNamespace(key=signing_key.public_key()))
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


def identity(client, provider, signing_key, **changes):
    challenge = client.post(f'/auth/social/{provider}/challenge', json={})
    assert challenge.status_code == 200
    pending = challenge.json()
    claims = {'iss': 'https://accounts.google.com' if provider == 'google' else 'https://appleid.apple.com',
              'aud': f'test-{provider}-client', 'sub': 'provider-subject',
              'iat': utcnow(), 'exp': utcnow() + timedelta(minutes=5), 'nonce': pending['nonce'],
              'email': 'social@example.com', 'email_verified': True, 'name': 'Social User', **changes}
    return {'id_token': jwt.encode(claims, signing_key, algorithm='RS256', headers={'kid': 'test-key'}),
            'state': pending['state']}


def enrollment(body, **changes):
    return {**body, 'name': 'Social User', 'age': 18, 'service_consent': True,
            'consent_text': 'TEST ONLY CONSENT', **changes}


@pytest.mark.parametrize('provider', ['google', 'apple'])
def test_social_signup_login_and_age(social, signing_key, provider):
    client, engine = social
    route = f'/auth/social/{provider}/complete'
    body = identity(client, provider, signing_key)
    assert client.post(route, json=body).json()['registration_required'] is True
    assert client.post(route, json=enrollment(body, age=17)).status_code == 422
    assert client.post(route, json=enrollment(body, service_consent=False)).status_code == 422
    assert client.post(route, json=enrollment(body, consent_text='old wording')).status_code == 422
    assert client.post(route, json=enrollment(body, name='  ')).status_code == 422
    assert client.post(route, json=enrollment(body, role='admin')).status_code == 422
    response = client.post(route, json=enrollment(body))
    assert response.status_code == 200
    assert response.json()['user']['role'] == 'user'
    assert 'HttpOnly' in response.headers['set-cookie']
    assert cookie_name(provider) not in client.cookies
    assert client.get('/users/me').status_code == 200
    assert client.post(route, json=body).status_code == 401
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.oauth_provider == provider
        assert user.oauth_subject == 'provider-subject'
        assert user.password_hash.startswith('scrypt$')
        assert user.service_consent_text == 'TEST ONLY CONSENT'
    client.cookies.clear()
    # Provider subject is the identity; a changed email is not a new account or a member update.
    login = client.post(route, json=identity(client, provider, signing_key, email='changed@example.com'))
    assert login.status_code == 200
    assert login.json()['user']['email'] == 'social@example.com'
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.age = 17
        db.commit()
    assert client.get('/users/me').status_code == 403
    assert client.post(route, json=identity(client, provider, signing_key)).status_code == 403


@pytest.mark.parametrize('provider', ['google', 'apple'])
@pytest.mark.parametrize('changes', [
    {'aud': 'different-app'}, {'iss': 'https://attacker.example'}, {'nonce': 'wrong-nonce'},
    {'exp': utcnow() - timedelta(minutes=1)}, {'email_verified': False}, {'sub': ''},
    {'nonce': '잘못된 인증 요청'},
])
def test_rejects_invalid_identity(social, signing_key, provider, changes):
    client, engine = social
    body = identity(client, provider, signing_key, **changes)
    assert client.post(f'/auth/social/{provider}/complete', json=enrollment(body)).status_code == 401
    with Session(engine) as db:
        assert db.scalar(select(User)) is None
        assert db.scalar(select(AuthSession)) is None


def test_signature_state_and_origin(social, signing_key):
    client, _ = social
    assert client.post('/auth/social/google/challenge', json={},
                       headers={'Origin': 'https://attacker.example'}).status_code == 403
    body = identity(client, 'apple', signing_key)
    assert client.post('/auth/social/apple/complete', json={**body, 'state': 'wrong'}).status_code == 401
    assert client.post('/auth/social/apple/complete', json={**body, 'state': '잘못된 상태'}).status_code == 401
    body = identity(client, 'google', signing_key)
    claims = jwt.decode(body['id_token'], options={'verify_signature': False})
    forged = jwt.encode(claims, rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm='RS256')
    assert client.post('/auth/social/google/complete', json={**body, 'id_token': forged}).status_code == 401
    client.cookies.set(cookie_name('google'), 'forged-cookie')
    assert client.post('/auth/social/google/complete', json=body).status_code == 401


def test_email_accounts_are_not_automatically_linked(social, signing_key):
    client, engine = social
    signup = {'email': 'social@example.com', 'password': 'secure-test-password', 'name': 'Email Member',
              'age': 18, 'service_consent': True, 'consent_text': 'TEST ONLY CONSENT'}
    assert client.post('/auth/signup', json=signup).status_code == 201
    client.cookies.clear()
    body = identity(client, 'google', signing_key)
    assert client.post('/auth/social/google/complete', json=enrollment(body)).status_code == 409
    assert COOKIE not in client.cookies
    with Session(engine) as db:
        assert db.scalar(select(User)).oauth_provider is None


def test_provider_settings_and_consent_gate(social, signing_key, monkeypatch):
    client, engine = social
    monkeypatch.setattr(settings, 'oauth_state_secret', None)
    config = client.get('/auth/social/policy').json()
    assert config['google']['enabled'] is False
    assert config['apple']['enabled'] is False
    assert client.post('/auth/social/google/challenge', json={}).status_code == 503
    monkeypatch.setattr(settings, 'oauth_state_secret', 'test-only-secret-with-more-than-32-characters')
    monkeypatch.setattr(settings, 'apple_redirect_uri', 'http://localhost/login')
    assert client.get('/auth/social/policy').json()['apple']['enabled'] is False
    monkeypatch.setattr(settings, 'service_consent_text', None)
    body = identity(client, 'google', signing_key)
    assert client.post('/auth/social/google/complete', json=enrollment(body)).status_code == 503
    with Session(engine) as db:
        assert db.scalar(select(User)) is None
