from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.accounts import database
from backend.app.config import settings
from backend.app.main import app
from backend.app.models import Base, User
from backend.app import kakao_auth


@pytest.fixture
def kakao(monkeypatch):
    for key, value in {'app_env': 'development', 'cookie_secure': False,
                       'frontend_origin': 'http://localhost:5174', 'age_min': 18,
                       'service_consent_text': 'TEST CONSENT',
                       'oauth_state_secret': 'test-secret-at-least-32-characters-long',
                       'kakao_client_id': 'test-rest-key', 'kakao_client_secret': 'test-secret',
                       'kakao_redirect_uri': 'http://localhost:8000/api/auth/kakao/callback'}.items():
        monkeypatch.setattr(settings, key, value)
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


def mock_provider(monkeypatch, email=True):
    def handler(request):
        if request.url.host == 'kauth.kakao.com':
            assert b'client_secret=test-secret' in request.content
            return httpx.Response(200, json={'access_token': 'provider-token'})
        assert request.headers['Authorization'] == 'Bearer provider-token'
        account = {'profile': {'nickname': '카카오 회원'}}
        if email:
            account.update(email='kakao@example.com', is_email_valid=True, is_email_verified=True)
        return httpx.Response(200, json={'id': 123, 'kakao_account': account})
    original = httpx.AsyncClient
    monkeypatch.setattr(kakao_auth.httpx, 'AsyncClient',
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


def start(client):
    response = client.get('/auth/kakao/login', follow_redirects=False)
    assert response.status_code == 307
    params = parse_qs(urlparse(response.headers['location']).query)
    assert params['redirect_uri'] == [settings.kakao_redirect_uri]
    assert 'client_secret' not in params
    return params['state'][0]


def test_invalid_state_never_contacts_provider(kakao, monkeypatch):
    client, _ = kakao
    def forbidden(**kwargs):
        pytest.fail('Invalid state must not contact Kakao')
    monkeypatch.setattr(kakao_auth.httpx, 'AsyncClient', forbidden)
    start(client)
    response = client.get('/api/auth/kakao/callback?code=secret&state=wrong', follow_redirects=False)
    assert 'kakao_auth_failed' in response.headers['location']
    assert kakao_auth.STATE_COOKIE not in client.cookies


def test_signup_age_consent_and_existing_login(kakao, monkeypatch):
    client, engine = kakao
    mock_provider(monkeypatch)
    state = start(client)
    response = client.get(f'/api/auth/kakao/callback?code=test&state={state}', follow_redirects=False)
    assert 'social_signup=kakao' in response.headers['location']
    assert client.get('/auth/social/kakao/pending').json()['email'] == 'kakao@example.com'
    body = {'name': '카카오 회원', 'age': 17, 'service_consent': True, 'consent_text': 'TEST CONSENT'}
    assert client.post('/auth/social/kakao/register', json=body).status_code == 422
    body['age'] = 18
    assert client.post('/auth/social/kakao/register', json={**body, 'service_consent': False}).status_code == 422
    assert client.post('/auth/social/kakao/register', json=body).status_code == 200
    assert client.get('/users/me').json()['user']['password_login_enabled'] is False
    assert kakao_auth.SIGNUP_COOKIE not in client.cookies
    client.cookies.clear()
    state = start(client)
    response = client.get(f'/api/auth/kakao/callback?code=test&state={state}', follow_redirects=False)
    assert 'social_success=kakao' in response.headers['location']
    with Session(engine) as db:
        assert len(db.scalars(select(User)).all()) == 1


def test_missing_verified_email_can_signup_and_login(kakao, monkeypatch):
    client, engine = kakao
    mock_provider(monkeypatch, email=False)
    state = start(client)
    response = client.get(f'/api/auth/kakao/callback?code=test&state={state}', follow_redirects=False)
    assert 'social_signup=kakao' in response.headers['location']
    assert client.get('/auth/social/kakao/pending').json()['email'] is None
    body = {'name': '카카오 회원', 'age': 18, 'service_consent': True, 'consent_text': 'TEST CONSENT'}
    result = client.post('/auth/social/kakao/register', json=body)
    assert result.status_code == 200
    assert result.json()['user']['email'] is None
    assert result.json()['user']['password_login_enabled'] is False
    assert kakao_auth.SIGNUP_COOKIE not in client.cookies
    client.cookies.clear()
    state = start(client)
    response = client.get(f'/api/auth/kakao/callback?code=test&state={state}', follow_redirects=False)
    assert 'social_success=kakao' in response.headers['location']
    assert client.get('/users/me').json()['user']['email'] is None
    with Session(engine) as db:
        assert len(db.scalars(select(User)).all()) == 1


def test_email_conflict_not_linked(kakao, monkeypatch):
    client, engine = kakao
    with Session(engine) as db:
        db.add(User(email='kakao@example.com', name='기존 회원', age=18, password_hash='unused',
                    service_consent_text='TEST CONSENT'))
        db.commit()
    mock_provider(monkeypatch)
    state = start(client)
    response = client.get(f'/api/auth/kakao/callback?code=test&state={state}', follow_redirects=False)
    assert 'account_conflict' in response.headers['location']
    assert client.get('/users/me').status_code == 401


def test_tampered_signup_cookie_and_bad_redirect(kakao, monkeypatch):
    client, _ = kakao
    client.cookies.set(kakao_auth.SIGNUP_COOKIE, 'tampered')
    assert client.get('/auth/social/kakao/pending').status_code == 401
    monkeypatch.setattr(settings, 'kakao_redirect_uri', 'https://untrusted.example/callback')
    assert client.get('/auth/social/policy').json()['kakao']['enabled'] is False
    assert client.get('/auth/kakao/login').status_code == 503
