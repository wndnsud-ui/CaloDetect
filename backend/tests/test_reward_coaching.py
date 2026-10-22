"""리워드몰 v1.3 M4: 전문 코칭 이용권 검사(지시서 §11 T14~T22)."""
import logging
import os
import threading
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models_rewards import RewardCoachPass as Pass, RewardPointSpend as Spend, RewardPointAllocation as Allocation
from backend.app.services import rewards, reward_coaching
from backend.tests.test_p0_flow import env, account
from backend.tests.reward_helpers import NOON, clock
from backend.tests.test_rewards_exchange import exchange_on, member, make_admin

PHONE = reward_coaching.PHONE


@pytest.fixture
def coach_on(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    monkeypatch.setattr(settings, 'reward_coaching_enabled', True)
    return client, engine, member(client, engine, 'coachee@example.com', points=1500), monkeypatch


def buy(client, coach='kim', key='key-00000001'):
    return client.post(f'/rewards/coaches/{coach}/passes', json={'idem_key': key})


# T14. 플래그 off → 코칭 API 전부 404, 코칭 상품은 몰 목록에 없다(몰은 시안 화면 유지).
def test_flag_off(coach_on):
    client, _, _, mp = coach_on
    mp.setattr(settings, 'reward_coaching_enabled', False)
    for path in ('/rewards/coaches', '/rewards/coaches/feed', '/rewards/coaches/kim', '/rewards/coach-passes'):
        assert client.get(path).status_code == 404
    assert buy(client).status_code == 404
    assert not any(i['coach_id'] for i in client.get('/rewards/products').json()['items'])
    assert client.put('/rewards/goal', json={'ref': 'product:coach_kim'}).status_code == 400


# T15·T21. 구매 성공: spend coach_pass·allocation·이용권 in_use·응답에 연락처. 월 교환 횟수·상한에는 영향 없음.
def test_buy(coach_on):
    client, engine, user, _ = coach_on
    before = client.get('/rewards/me').json()
    response = buy(client)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['status'] == 'in_use' and data['sessions'] == 7 and data['phone'] == PHONE and data['kakao_link']
    assert data['balance'] == before['balance'] - 700
    with Session(engine) as db:
        row = db.get(Pass, data['id'])
        spend = db.get(Spend, row.spend_id)
        assert spend.kind == 'coach_pass' and spend.amount == 700
        assert db.scalar(select(func.sum(Allocation.amount)).where(Allocation.spend_id == spend.id)) == 700
    after = client.get('/rewards/me').json()['exchange']
    assert after['monthly_used'] == before['exchange']['monthly_used']
    assert client.post('/rewards/exchanges', json={'product_id': 'energy_bar', 'option': '오리지널 견과'}).status_code == 201
    detail = client.get('/rewards/coaches/kim').json()
    assert detail['pass_status'] == 'in_use' and detail['pass']['phone'] == PHONE
    assert client.get('/rewards/coach-passes').json()['items'][0]['phone'] == PHONE


# T16. 같은 idem_key 두 번 → 이용권 1건, 차감 1회, 같은 응답.
def test_idempotent(coach_on):
    client, engine, *_ = coach_on
    first, second = buy(client).json(), buy(client).json()
    assert first == second
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Pass)) == 1
        assert db.scalar(select(func.count()).select_from(Spend).where(Spend.kind == 'coach_pass')) == 1


# T17. 같은 코치 in_use 상태에서 다른 키로 구매 → 409 PASS_IN_USE. 다른 코치는 가능.
def test_pass_in_use(coach_on):
    client, *_ = coach_on
    assert buy(client).status_code == 200
    again = buy(client, key='key-00000002')
    assert again.status_code == 409 and again.json()['error']['code'] == 'PASS_IN_USE'
    assert buy(client, 'park', key='key-00000003').status_code == 200


# T18. 잔액 부족·제외 출처만 → 409, 차감 없음.
def test_insufficient(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    monkeypatch.setattr(settings, 'reward_coaching_enabled', True)
    member(client, engine, 'bonus-only@example.com', points=900, source='onboarding')
    response = buy(client)
    assert response.status_code == 409 and response.json()['error']['code'] == 'INSUFFICIENT_POINTS'
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Spend)) == 0


# T19. 목록·피드·비구매자 상세 응답과 로그에 연락처 없음.
def test_contact_hidden(coach_on, caplog):
    client, *_ = coach_on
    caplog.set_level(logging.INFO, logger='calodetect')
    for path in ('/rewards/coaches', '/rewards/coaches/feed', '/rewards/coaches/kim'):
        text = client.get(path).text
        assert PHONE not in text and 'pf.kakao.com' not in text
    buy(client)
    assert PHONE not in caplog.text and 'pf.kakao.com' not in caplog.text
    assert client.get('/rewards/coaches?specialty=exercise').json()['items'][0]['id'] == 'park'
    assert client.get('/rewards/coaches?specialty=nope').status_code == 422


# T20. 관리자 환불: admin만, allocation 역순 복원, refunded. 일반 사용자 403.
def test_admin_refund(coach_on):
    client, engine, user, _ = coach_on
    before = client.get('/rewards/me').json()['balance']
    pass_id = buy(client).json()['id']
    assert client.post(f'/admin/rewards/coach-passes/{pass_id}/refund').status_code == 403
    make_admin(engine, user['id'])
    assert client.get('/admin/rewards/coach-passes').json()['items'][0]['id'] == pass_id
    response = client.post(f'/admin/rewards/coach-passes/{pass_id}/refund')
    assert response.status_code == 200 and response.json()['status'] == 'refunded'
    assert client.get('/rewards/me').json()['balance'] == before
    assert client.post(f'/admin/rewards/coach-passes/{pass_id}/refund').status_code == 409
    assert buy(client, key='key-00000009').status_code == 200


# T22. (PostgreSQL) 다른 키로 같은 코치 동시 구매 2건 → 1건만 성공.
@pytest.mark.skipif(os.environ.get('RUN_POSTGRES_TESTS') != '1', reason='PostgreSQL concurrency')
def test_concurrent_buy_postgres(coach_on):
    client, engine, user, _ = coach_on
    results = []

    def run(key):
        with Session(engine) as db:
            try:
                reward_coaching.buy(db, db.get(rewards.User, user['id']), 'kim', key)
                results.append(200)
            except Exception as error:
                results.append(getattr(error, 'status_code', 500))
    threads = [threading.Thread(target=run, args=(f'key-concurrent-{i}',)) for i in range(2)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(results) == [200, 409]
