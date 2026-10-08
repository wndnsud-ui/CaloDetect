# 회귀 테스트: social_auth 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
from datetime import timedelta
from types import SimpleNamespace

import jwt
import pytest
from urllib.parse import parse_qs, urlparse
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.accounts import COOKIE, database
from backend.app.config import settings
from backend.app.main import app
from backend.app.models import AuthSession, Base, User, utcnow
from backend.app.social_auth import (
    GOOGLE_SIGNUP_COOKIE,
    GOOGLE_STATE_COOKIE,
    KEYS,
    cookie_name,
)
from backend.app import social_auth


# signing_key: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
@pytest.fixture(scope='module')
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


# social: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
@pytest.fixture
def social(monkeypatch, signing_key):
    monkeypatch.setattr(settings, 'local_test_signup', False)
    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'age_min', 18)
    monkeypatch.setattr(settings, 'service_consent_text', 'TEST ONLY CONSENT')
    monkeypatch.setattr(settings, 'oauth_state_secret', 'test-only-secret-with-more-than-32-characters')
    monkeypatch.setattr(settings, 'google_client_id', 'test-google-client')
    monkeypatch.setattr(settings, 'google_client_secret', 'test-google-secret')
    monkeypatch.setattr(settings, 'google_redirect_uri', 'http://localhost:8000/api/auth/google/callback')
    monkeypatch.setattr(settings, 'apple_client_id', 'test-apple-client')
    monkeypatch.setattr(settings, 'apple_redirect_uri', 'https://example.com/login')
    for client in KEYS.values():
        monkeypatch.setattr(client, 'get_signing_key_from_jwt',
                            lambda token: SimpleNamespace(key=signing_key.public_key()))
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


# identity: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
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


# enrollment: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
def enrollment(body, **changes):
    return {**body, 'name': 'Social User', 'age': 18, 'service_consent': True,
            'consent_text': 'TEST ONLY CONSENT', **changes}


# 회귀 검사: 소셜 · 가입 · 로그인 · 연령.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
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
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit()
    assert client.get('/users/me').status_code == 403
    assert client.post(route, json=identity(client, provider, signing_key)).status_code == 403


# 회귀 검사: 거부 · 잘못된 · 신원.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
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


# 회귀 검사: 서명 · state · 요청 출처.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
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


# 회귀 검사: 이메일 · 계정 · 자동 · 연결.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
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


# 회귀 검사: 제공자 · 설정 · 동의 · 차단 조건.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_provider_settings_and_consent_gate(social, signing_key, monkeypatch):
    client, engine = social
    monkeypatch.setattr(settings, 'oauth_state_secret', None)
    config = client.get('/auth/social/policy').json()
    assert config['google']['enabled'] is False
    assert config['apple']['enabled'] is False
    assert client.post('/auth/social/google/challenge', json={}).status_code == 503
    monkeypatch.setattr(settings, 'oauth_state_secret', 'test-only-secret-with-more-than-32-characters')
    assert client.get('/auth/social/policy').json()['google']['authorization_code_enabled'] is True
    monkeypatch.setattr(settings, 'google_client_secret', None)
    assert client.get('/auth/social/policy').json()['google']['authorization_code_enabled'] is False
    monkeypatch.setattr(settings, 'google_client_secret', 'test-google-secret')
    monkeypatch.setattr(settings, 'app_env', 'production')
    monkeypatch.setattr(settings, 'google_redirect_uri', 'https://api.example.com/api/auth/google/callback')
    monkeypatch.setattr(settings, 'frontend_origin', 'https://app.example.com')
    assert client.get('/auth/social/policy').json()['google']['authorization_code_enabled'] is False
    monkeypatch.setattr(settings, 'cookie_secure', True)
    assert client.get('/auth/social/policy').json()['google']['authorization_code_enabled'] is True
    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'cookie_secure', False)
    monkeypatch.setattr(settings, 'google_redirect_uri', 'http://localhost:8000/api/auth/google/callback')
    monkeypatch.setattr(settings, 'apple_redirect_uri', 'http://localhost/login')
    assert client.get('/auth/social/policy').json()['apple']['enabled'] is False
    monkeypatch.setattr(settings, 'service_consent_text', None)
    body = identity(client, 'google', signing_key)
    assert client.post('/auth/social/google/complete', json=enrollment(body)).status_code == 503
    with Session(engine) as db:
        assert db.scalar(select(User)) is None


# 회귀 검사: Google · 인증 · code · 로그인 · 리디렉션 · state · nonce · PKCE.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_google_authorization_code_login_redirect_uses_state_nonce_and_pkce(social):
    client, _ = social
    response = client.get('/auth/google/login', follow_redirects=False)
    assert response.status_code == 307
    location = urlparse(response.headers['location'])
    params = parse_qs(location.query)
    assert location.netloc == 'accounts.google.com'
    assert params['redirect_uri'] == ['http://localhost:8000/api/auth/google/callback']
    assert params['response_type'] == ['code']
    assert params['scope'] == ['openid email profile']
    assert params['code_challenge_method'] == ['S256']
    assert GOOGLE_STATE_COOKIE in client.cookies
    assert 'HttpOnly' in response.headers['set-cookie']
    pending = jwt.decode(client.cookies.get(GOOGLE_STATE_COOKIE),
                         settings.oauth_state_secret, algorithms=['HS256'])
    assert params['state'] == [pending['state']]
    assert params['nonce'] == [pending['nonce']]


# 회귀 검사: Google · 인증 · code · 가입 · 기존 · 회원 · 로그인.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_google_authorization_code_signup_and_existing_user_login(social, signing_key, monkeypatch):
    client, engine = social
    captured = {}

    # TokenResponse: 를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
    class TokenResponse:
        # raise_for_status: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
        def raise_for_status(self):
            return None

        # json: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
        def json(self):
            return {'id_token': captured['id_token']}

    # TokenClient: 를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
    class TokenClient:
        # __init__: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
        def __init__(self, timeout):
            assert timeout == 10

        # __aenter__: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
        async def __aenter__(self):
            return self

        # __aexit__: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
        async def __aexit__(self, *args):
            return None

        # post: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
        async def post(self, url, data):
            captured['url'] = url
            captured['data'] = data
            return TokenResponse()

    monkeypatch.setattr(social_auth.httpx, 'AsyncClient', TokenClient)
    monkeypatch.setattr(KEYS['google'], 'get_signing_key_from_jwt',
                        lambda token: SimpleNamespace(key=signing_key.public_key()))

    # callback: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
    def callback():
        start = client.get('/auth/google/login', follow_redirects=False)
        pending = jwt.decode(client.cookies.get(GOOGLE_STATE_COOKIE),
                             settings.oauth_state_secret, algorithms=['HS256'])
        captured['id_token'] = jwt.encode({
            'iss': 'https://accounts.google.com', 'aud': 'test-google-client',
            'sub': 'google-subject', 'iat': utcnow(), 'exp': utcnow() + timedelta(minutes=5),
            'nonce': pending['nonce'], 'email': 'google@example.com',
            'email_verified': True, 'name': 'Google User',
        }, signing_key, algorithm='RS256', headers={'kid': 'test-key'})
        return client.get('/api/auth/google/callback', params={
            'code': 'authorization-code', 'state': pending['state'],
        }, follow_redirects=False)

    response = callback()
    assert response.status_code == 303
    assert response.headers['location'] == f'{settings.frontend_origin}/?social_signup=google'
    assert GOOGLE_SIGNUP_COOKIE in client.cookies
    assert 'google@example.com' not in client.cookies.get(GOOGLE_SIGNUP_COOKIE)
    assert captured['url'] == social_auth.GOOGLE_TOKEN_ENDPOINT
    assert captured['data']['code_verifier']
    assert 'client_secret' in captured['data']
    pending = client.get('/auth/social/google/pending')
    assert pending.status_code == 200
    assert pending.json()['email'] == 'google@example.com'
    assert pending.json()['name'] == 'Google User'

    registration = {
        'name': 'Google User', 'age': 25, 'service_consent': True,
        'consent_text': 'TEST ONLY CONSENT',
    }
    assert client.post('/auth/social/google/register', json={**registration, 'age': 17}).status_code == 422
    assert client.post('/auth/social/google/register',
                       json={**registration, 'service_consent': False}).status_code == 422
    assert client.post('/auth/social/google/register',
                       json={**registration, 'consent_text': 'outdated'}).status_code == 422
    signup = client.post('/auth/social/google/register', json=registration)
    assert signup.status_code == 200
    assert signup.json()['user']['role'] == 'user'
    assert GOOGLE_SIGNUP_COOKIE not in client.cookies
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.oauth_provider == 'google'
        assert user.oauth_subject == 'google-subject'

    client.cookies.clear()
    response = callback()
    assert response.status_code == 303
    assert response.headers['location'] == f'{settings.frontend_origin}/?social_success=google'
    assert client.get('/users/me').status_code == 200


# 회귀 검사: Google · 인증 · code · 거부 · state · 리디렉션 · URI.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_google_authorization_code_rejects_bad_state_and_redirect_uri(social, monkeypatch):
    client, _ = social
    start = client.get('/auth/google/login', follow_redirects=False)
    assert start.status_code == 307
    response = client.get('/api/auth/google/callback', params={
        'code': 'authorization-code', 'state': 'wrong-state',
    }, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'].endswith('?social_error=google_auth_failed')
    assert GOOGLE_STATE_COOKIE not in client.cookies

    monkeypatch.setattr(settings, 'google_redirect_uri', 'http://attacker.example/api/auth/google/callback')
    assert client.get('/auth/social/policy').json()['google']['authorization_code_enabled'] is False


# 회귀 검사: Google · 가입 · 쿠키 · 거부 · 변조 · 암호문.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_google_signup_cookie_rejects_modified_ciphertext(social):
    import base64
    client, _ = social
    encoded = social_auth.seal_google_signup({'provider':'google', 'sub':'test',
        'email':'test@example.com', 'exp':int(social_auth.time.time()) + 300})
    raw = bytearray(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
    raw[-1] ^= 1
    client.cookies.set(GOOGLE_SIGNUP_COOKIE, base64.urlsafe_b64encode(raw).decode().rstrip('='))
    response = client.get('/auth/social/google/pending')
    assert response.status_code == 401
