# 회귀 테스트: passwords 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app import passwords
from backend.app.accounts import COOKIE
from backend.app.config import settings
from backend.app.models import User
from backend.tests.test_accounts import accounts, register

REAL_SENDER = passwords.send_reset_email


# setup_reset: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
@pytest.fixture
def setup_reset(accounts, monkeypatch):
    client, engine = accounts
    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'frontend_origin', 'http://localhost:5174')
    monkeypatch.setattr(settings, 'password_reset_secret', 'test-only-secret-' * 3)
    monkeypatch.setattr(settings, 'smtp_host', 'smtp.gmail.com')
    monkeypatch.setattr(settings, 'smtp_from', 'sender@example.com')
    monkeypatch.setattr(settings, 'smtp_username', 'sender@example.com')
    monkeypatch.setattr(settings, 'smtp_password', 'test-app-password')
    passwords._attempts.clear()
    sent = []
    monkeypatch.setattr(passwords, 'send_reset_email', lambda email, token: sent.append((email, token)))
    register(client)
    return client, engine, sent


# 회귀 검사: 재설정 · 단일 · 사용 · 폐기 · 전체 · 세션.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_reset_single_use_and_revokes_all_sessions(setup_reset):
    client, _, sent = setup_reset
    old_cookie = client.cookies.get(COOKIE)
    client.post('/auth/login', json={'email':'one@example.com', 'password':'secure-test-password'})
    current_cookie = client.cookies.get(COOKIE)
    response = client.post('/auth/password/forgot', json={'email':'ONE@example.com'})
    assert response.status_code == 200
    assert 'token' not in response.json()
    token = sent[0][1]
    assert client.post('/auth/password/reset', json={'token':token, 'new_password':'replacement-password'}).status_code == 200
    assert client.post('/auth/password/reset', json={'token':token, 'new_password':'another-password'}).status_code == 400
    for cookie in (old_cookie, current_cookie):
        client.cookies.clear()
        client.cookies.set(COOKIE, cookie)
        assert client.get('/users/me').status_code == 401
    client.cookies.clear()
    assert client.post('/auth/login', json={'email':'one@example.com', 'password':'secure-test-password'}).status_code == 401
    assert client.post('/auth/login', json={'email':'one@example.com', 'password':'replacement-password'}).status_code == 200


# 회귀 검사: 미가입 · 소셜 · 동일 · 응답 · 발송.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_unknown_and_social_same_response_no_delivery(setup_reset):
    client, engine, sent = setup_reset
    known = client.post('/auth/password/forgot', json={'email':'one@example.com'})
    unknown = client.post('/auth/password/forgot', json={'email':'unknown@example.com'})
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.oauth_provider = 'google'
        user.oauth_subject = 'test-subject'
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit()
    social = client.post('/auth/password/forgot', json={'email':'one@example.com'})
    assert known.json() == unknown.json() == social.json()
    assert len(sent) == 1
    assert client.get('/users/me').json()['user']['password_login_enabled'] is False
    csrf = client.get('/users/me').json()['csrf_token']
    assert client.post('/users/me/password', json={'current_password':'secure-test-password', 'new_password':'new-password'},
                       headers={'X-CSRF-Token':csrf}).status_code == 403
    assert client.post('/auth/password/reset', json={'token':sent[0][1], 'new_password':'replacement-password'}).status_code == 400
    assert client.post('/auth/login', json={'email':'one@example.com', 'password':'secure-test-password'}).status_code == 401


# 회귀 검사: 변경 · 현재 · 비밀번호 · CSRF · 재설정 · 무효화.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_change_current_password_csrf_and_reset_invalidation(setup_reset):
    client, _, sent = setup_reset
    csrf = client.get('/users/me').json()['csrf_token']
    assert client.get('/users/me').json()['user']['password_login_enabled'] is True
    client.post('/auth/password/forgot', json={'email':'one@example.com'})
    body = {'current_password':'secure-test-password', 'new_password':'changed-password'}
    assert client.post('/users/me/password', json=body).status_code == 403
    headers = {'X-CSRF-Token':csrf}
    assert client.post('/users/me/password', json={**body, 'current_password':'incorrect-password'}, headers=headers).status_code == 400
    assert client.post('/users/me/password', json={**body, 'new_password':'secure-test-password'}, headers=headers).status_code == 422
    assert client.post('/users/me/password', json=body, headers=headers).status_code == 200
    assert client.get('/users/me').status_code == 401
    assert client.post('/auth/password/reset', json={'token':sent[0][1], 'new_password':'replacement-password'}).status_code == 400
    assert client.post('/auth/login', json={'email':'one@example.com', 'password':'changed-password'}).status_code == 200


# 회귀 검사: 만료 · 변조 · 짧은 · 비밀번호 · 요청 출처.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_expired_tampered_short_password_and_origin(setup_reset, monkeypatch):
    client, _, sent = setup_reset
    client.post('/auth/password/forgot', json={'email':'one@example.com'})
    token = sent[0][1]
    body = {'token':token, 'new_password':'replacement-password'}
    assert client.post('/auth/password/reset', json={**body, 'new_password':'short'}).status_code == 422
    assert client.post('/auth/password/reset', json={**body, 'token':token + 'a'}).status_code == 400
    assert client.post('/auth/password/reset', json={**body, 'token':'invalid'}).status_code == 400
    assert client.post('/auth/password/reset', json=body, headers={'Origin':'https://attacker.example'}).status_code == 403
    assert client.post('/auth/password/forgot', json={'email':'one@example.com'}, headers={'Origin':'https://attacker.example'}).status_code == 403
    expiry = int(token.split('.')[1])
    monkeypatch.setattr(passwords.time, 'time', lambda: expiry + 1)
    assert client.post('/auth/password/reset', json=body).status_code == 400


# 회귀 검사: 설정 · 횟수 · 제한.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_configuration_and_rate_limits(setup_reset, monkeypatch):
    client, _, _ = setup_reset
    monkeypatch.setattr(settings, 'password_reset_secret', None)
    assert client.get('/auth/policy').json()['password_reset_enabled'] is False
    assert client.post('/auth/password/forgot', json={'email':'one@example.com'}).status_code == 503
    monkeypatch.setattr(settings, 'password_reset_secret', 'a' * 32)
    monkeypatch.setattr(settings, 'app_env', 'production')
    assert not passwords.reset_enabled()  # production reset links must be HTTPS
    monkeypatch.setattr(settings, 'app_env', 'development')
    for _ in range(3):
        assert client.post('/auth/password/forgot', json={'email':'missing@example.com'}).status_code == 200
    assert client.post('/auth/password/forgot', json={'email':'missing@example.com'}).status_code == 429


# 회귀 검사: Gmail · 발송 · STARTTLS · fragment · 링크.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_gmail_delivery_starttls_and_fragment_link(setup_reset, monkeypatch):
    # Restore the real sender that this fixture replaced for endpoint tests.
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    factory = MagicMock(return_value=smtp)
    monkeypatch.setattr(passwords.smtplib, 'SMTP', factory)
    monkeypatch.setattr(settings, 'smtp_security', 'starttls')
    REAL_SENDER('one@example.com', 'test-reset-token')
    factory.assert_called_once_with('smtp.gmail.com', settings.smtp_port, timeout=10)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with('sender@example.com', 'test-app-password')
    message = smtp.send_message.call_args.args[0]
    assert message['To'] == 'one@example.com'
    assert '/#password_reset=test-reset-token' in message.get_content()


# 회귀 검사: 메일 · 실패 · 로그 · 민감 · 데이터.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_mail_failure_logs_no_sensitive_data(setup_reset, monkeypatch, caplog):
    monkeypatch.setattr(passwords.smtplib, 'SMTP', MagicMock(side_effect=OSError('private SMTP details')))
    REAL_SENDER('private@example.com', 'secret-reset-token')
    assert 'delivery failed' in caplog.text
    assert 'private@example.com' not in caplog.text
    assert 'secret-reset-token' not in caplog.text
    assert 'private SMTP details' not in caplog.text
