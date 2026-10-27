"""리워드 닉네임(지시서 v3 §6-13, §13 N1~N16)."""
import logging
import os
import threading
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.config import settings
from backend.app.models import User
from backend.app.models_rewards import RewardNickname as Nickname
from backend.app.services import rewards as service, reward_rules as rules
from backend.tests.test_p0_flow import env, account
from backend.tests.reward_helpers import NOON, clock


@pytest.fixture(autouse=True)
def fresh_limits():
    service._rate.clear()


# 로컬 .env의 출시 시각과 무관하게 테스트마다 기본값(미설정 = 모두 출시 전 회원)에서 시작한다.
@pytest.fixture(autouse=True)
def launch_unset(monkeypatch):
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    monkeypatch.setattr(settings, 'reward_exchange_enabled', False)  # Stage C는 별도 테스트에서만 켠다.

@pytest.fixture
def new_member(env, monkeypatch):
    client, engine, _ = env
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', NOON - timedelta(days=400))
    clock(monkeypatch, NOON)
    user = account(client, 'nick@example.com')
    return client, engine, user, monkeypatch


def put(client, nickname, via='account'):
    return client.put('/rewards/nickname', json={'nickname': nickname, 'via': via})


# N1·N13. 출시 이전 회원: 처음 /rewards/me에서 자동 생성(1회), 안내 카드 → 닫으면 다시 안 뜸.
def test_existing_member_generated(env, monkeypatch):
    client, engine, _ = env
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    user = account(client, 'old@example.com')
    first = client.get('/rewards/me').json()
    assert first['nickname']['generated'] and first['nickname_prompt'] == 'card'
    assert client.get('/rewards/me').json()['nickname']['nickname'] == first['nickname']['nickname']
    nickname = first['nickname']['nickname']
    assert len(nickname.split()) == 3 and rules.nickname_problem(nickname) is None
    assert client.post('/rewards/nickname/prompt/dismiss').json()['nickname_prompt'] is None
    assert client.get('/rewards/me').json()['nickname_prompt'] is None


# N2·N3. 길이·문자·정규화, 금칙어·이메일·전화번호·사칭·이름·이메일 앞부분.
def test_format_rules():
    problem = lambda v, **kw: rules.nickname_problem(v, **kw)
    assert problem('가') == 'length' and problem('가' * 13) == 'length'
    assert problem('가나') is None and problem('가' * 12) is None
    assert problem('a!b') == 'chars' and problem('가  나') == 'chars' and problem('  건강 왕  ') is None
    assert rules.normalize_nickname('  한글  ') == '한글'
    assert problem('a@b.com') == 'blocked' and problem('01012345678') == 'blocked'
    assert problem('운영자님') == 'blocked' and problem('CaloDetect짱') == 'blocked' and problem('시발놈') == 'blocked'
    assert problem('홍길동', name='홍 길동') == 'same_as_name'
    assert problem('runner', email='Runner@example.com') == 'same_as_email'


# N9·N10·N11·N12. 신규 가입자는 가입 단계 필요 → signup 저장 후 null, 다시 signup은 409, 대기기간 없이 반복 변경 가능.
def test_signup_flow(new_member):
    client, engine, user, mp = new_member
    me = client.get('/rewards/me').json()
    assert me['nickname_prompt'] == 'signup' and me['nickname']['nickname'] is None
    suggestion = client.get('/rewards/nickname/suggestion').json()['nickname']
    saved = put(client, suggestion, 'signup')
    assert saved.status_code == 200, saved.text
    with Session(engine) as db:
        row = db.get(Nickname, user['id'])
        assert (row.generated, row.set_via, row.changed_at) == (False, 'signup', None)
    assert client.get('/rewards/me').json()['nickname_prompt'] is None
    assert put(client, '다른이름', 'signup').status_code == 409
    assert put(client, suggestion.upper()).json()['changed'] is False
    assert put(client, '첫 변경').status_code == 200
    mp.setattr(settings, 'reward_nickname_change_days', 30)
    assert put(client, '두번째변경').status_code == 200
    assert put(client, '세번째변경').status_code == 200
    info = client.get('/rewards/nickname').json()
    assert info['next_change_date'] is None and info['next_change_at'] is None


# N4·N5·N6. 대소문자·공백만 다른 값은 중복, 관리자 초기화(비관리자 403) 후 즉시 변경 가능.
def test_duplicates_and_admin_reset(new_member):
    client, engine, user, mp = new_member
    assert put(client, 'Happy Day', 'signup').status_code == 200
    with TestClient(app) as other:
        account(other, 'second@example.com')
        taken = put(other, 'happyday', 'signup')
        assert taken.status_code == 409 and taken.json()['error']['message'] == '이미 쓰고 있는 닉네임이에요.'
        assert other.post(f'/admin/rewards/nicknames/{user["id"]}/reset').status_code == 403
    assert put(client, '바뀐닉').status_code == 200
    with Session(engine) as db:
        db.get(User, user['id']).role = 'admin'; db.commit()
    assert [row['user_id'] for row in client.get('/admin/rewards/nicknames?q=바뀐').json()['items']] == [user['id']]
    assert client.post(f'/admin/rewards/nicknames/{user["id"]}/reset').status_code == 200
    with Session(engine) as db:
        row = db.get(Nickname, user['id'])
        assert row.generated and row.set_via == 'admin_reset' and row.changed_at is None
    assert put(client, '곧바로변경').status_code == 200


# N14·N15. 검사·추천: 이유 코드, 저장 없음, 분당 한도 초과 429.
def test_check_and_suggest_limits(new_member):
    client, engine, user, mp = new_member
    check = lambda v: client.get('/rewards/nickname/check', params={'nickname': v}).json()
    assert check('좋은닉네임') == {'ok': True, 'reason': None, 'message': '쓸 수 있는 닉네임이에요.'}
    assert check('a')['reason'] == 'length' and check('a#b')['reason'] == 'chars' and check('관리자')['reason'] == 'blocked'
    assert check('Tester')['reason'] == 'same_as_name' and check('nick')['reason'] == 'same_as_email'
    with Session(engine) as db:
        assert db.get(Nickname, user['id']) is None
    mp.setattr(settings, 'reward_nickname_check_per_min', 6)
    assert client.get('/rewards/nickname/check', params={'nickname': 'x1'}).status_code == 429
    mp.setattr(settings, 'reward_nickname_suggest_per_min', 2)
    for _ in range(2):
        assert client.get('/rewards/nickname/suggestion').status_code == 200
    assert client.get('/rewards/nickname/suggestion').status_code == 429


# 가입 단계를 다시 닫으면 자동 생성 닉네임을 유지하고 안내 카드 규칙으로 넘어간다.
def test_signup_dismissed(new_member):
    client, engine, user, mp = new_member
    assert client.post('/rewards/nickname/prompt/dismiss').json()['nickname_prompt'] == 'card'
    assert client.get('/rewards/me').json()['nickname']['generated']


# N8. 로그에 닉네임 문자열이 없다.
def test_nickname_not_logged(new_member, caplog):
    client, engine, user, mp = new_member
    with caplog.at_level(logging.INFO, logger='calodetect'):
        put(client, '로그금지닉', 'signup')
        put(client, '로그금지둘')
        client.get('/rewards/ranking')
    assert '로그금지' not in caplog.text and 'reward nickname changed' in caplog.text


# N16. 기존 가입·회원정보 API 응답 본문은 그대로다.
def test_existing_account_api_unchanged(new_member):
    client, engine, user, mp = new_member
    # age는 2026-10-27 목표 설정 화면 표시용으로 추가한 키다(기존 키는 그대로).
    assert set(user) == {'id', 'email', 'name', 'role', 'password_login_enabled', 'age'}
    # 계정 이름 변경 API는 2026-10-27 사용자 결정으로 없앴다. 조회 응답 본문은 그대로다.
    assert client.put('/users/me', json={'name': '새이름'}).status_code == 405
    assert set(client.get('/users/me').json()['user']) == set(user)


# N7. (PostgreSQL) 같은 닉네임 동시 요청 2건 → 1건만 성공, 다른 1건은 중복 문구.
@pytest.mark.skipif(os.environ.get('RUN_POSTGRES_TESTS') != '1', reason='PostgreSQL concurrency')
def test_concurrent_same_nickname(env, monkeypatch):
    _, engine, _ = env
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    clients = [TestClient(app) for _ in range(2)]
    for index, c in enumerate(clients):
        account(c, f'race{index}@example.com')
    results = []
    threads = [threading.Thread(target=lambda c=c: results.append(put(c, '동시닉네임').status_code)) for c in clients]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(results) == [200, 409]
