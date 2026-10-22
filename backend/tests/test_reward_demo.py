"""개발용 리워드 더미(테스트 페이지·스크립트) 검사."""
import pytest
from fastapi.testclient import TestClient
from backend.app.config import settings
from backend.app.main import app
from backend.app import dev_demo
from backend.tests.test_p0_flow import env, account
from backend.tests.reward_helpers import NOON, clock


@pytest.fixture
def member(env, monkeypatch):
    client, engine, _ = env
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    clock(monkeypatch, NOON)
    user = account(client, dev_demo.TEST_ACCOUNT_EMAIL)
    if not any(getattr(r, 'path', '') == '/dev/demo/status' for r in app.routes):
        app.include_router(dev_demo.router)  # 로컬 .env와 무관하게 경로를 검사한다.
    return client, engine, user


# 더미: 포인트·XP·연속·보호권이 들어가고 레벨이 계산되며, 같은 날 같은 값은 중복되지 않는다. 초기화는 리워드만 지운다.
def test_seed_and_reset(member):
    client, engine, user = member
    first = client.post('/dev/demo/rewards', json={'points': 200, 'xp': 1200, 'streak': 5, 'protectors': 1})
    assert first.status_code == 200, first.text
    data = first.json()
    assert (data['level'], data['xp_total'], data['streak_days'], data['protectors']) == (3, 1200, 5, 1)
    assert data['balance'] == 250 and data['new_levels'] == [2, 3]
    assert client.post('/dev/demo/rewards', json={'points': 200, 'xp': 1200, 'streak': 5, 'protectors': 1}).json()['balance'] == 250
    assert client.get('/rewards/me').json()['pending_levelup']['level'] == 3
    reset = client.post('/dev/demo/rewards/reset', json={}).json()
    assert (reset['balance'], reset['level'], reset['xp_total']) == (0, 1, 0)
    assert client.get('/rewards/me').json()['equipment'] == {'background': 'bg_lv1'}
    again = client.post('/dev/demo/rewards', json={'points': 30, 'xp': 0, 'streak': 0, 'protectors': 0, 'reset': True}).json()
    assert (again['balance'], again['level']) == (30, 1)


# 테스트 계정이 아니면 403, 범위 밖 값은 422.
def test_guards(member, env):
    client, engine, user = member
    assert client.post('/dev/demo/rewards', json={'points': 99999}).status_code == 422
    with TestClient(app) as other:
        account(other, 'someone@example.com')
        assert other.get('/dev/demo/status').json()['test_account'] is False
        assert other.post('/dev/demo/rewards', json={}).status_code == 403
        assert other.post('/dev/demo/rewards/reset', json={}).status_code == 403


# 초기화는 교환 신청도 지우고 월 카운터를 되돌린다(교환을 다시 시험할 수 있게).
def test_reset_clears_exchanges(member, monkeypatch):
    from datetime import timedelta
    from backend.tests.reward_helpers import pin_signup
    client, engine, user = member
    monkeypatch.setattr(settings, 'reward_exchange_enabled', True)
    monkeypatch.setattr(settings, 'reward_exchange_global_monthly_cap', 5)
    monkeypatch.setattr(settings, 'oauth_state_secret', 'test-secret-for-coupon-encryption-0123456789')
    pin_signup(engine, user['id'], NOON - timedelta(days=30))
    client.post('/dev/demo/rewards', json={'points': 300, 'xp': 0, 'streak': 0, 'protectors': 0})
    client.get('/rewards/products')
    assert client.post('/rewards/exchanges', json={'product_id': 'energy_bar', 'option': '오리지널 견과'}).status_code == 201
    assert client.post('/dev/demo/rewards', json={'points': 300, 'xp': 0, 'streak': 0, 'protectors': 0, 'reset': True}).status_code == 200
    assert client.get('/rewards/coupons').json()['items'] == []
    assert client.post('/rewards/exchanges', json={'product_id': 'energy_bar', 'option': '오리지널 견과'}).status_code == 201
