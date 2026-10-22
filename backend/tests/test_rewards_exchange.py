"""리워드 Stage C: 건강상품 교환·쿠폰함·관리자 처리(지시서 v3 §13 #27~34-1)."""
import logging
import os
import threading
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.config import settings
from backend.app.models import User
from backend.app.models_rewards import RewardExchange as Exchange, RewardPointLot as Lot, RewardExchangeMonthCounter as Counter
from backend.app.services import rewards, reward_exchange
from backend.tests.test_p0_flow import env, account
from backend.tests.reward_helpers import NOON, clock, lots, pin_signup

CODE = 'CPN-7788-TEST'


@pytest.fixture(autouse=True)
def exchange_on(monkeypatch):
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    monkeypatch.setattr(settings, 'reward_exchange_enabled', True)
    monkeypatch.setattr(settings, 'reward_exchange_global_monthly_cap', 100)
    # 로컬 .env 값과 무관하게 지시서 기본값으로 검사한다.
    monkeypatch.setattr(settings, 'reward_exchange_min_account_days', 14)
    monkeypatch.setattr(settings, 'reward_exchange_monthly_limit', 1)
    monkeypatch.setattr(settings, 'reward_exchange_first_hold', True)
    monkeypatch.setattr(settings, 'oauth_state_secret', 'test-secret-for-coupon-encryption-0123456789')


def member(client, engine, email, days=20, points=500, source='meal'):
    user = account(client, email)
    pin_signup(engine, user['id'], NOON - timedelta(days=days))
    with Session(engine) as db:
        reward_exchange.ensure_products(db)
        rewards.account(db, user['id'])
        if points:
            rewards.grant_points(db, user['id'], source, points, f'seed:{source}')
        db.commit()
    return user


@pytest.fixture
def one(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    return client, engine, member(client, engine, 'buyer@example.com'), monkeypatch


def first_option(product):
    # 리워드몰 v1.3: 옵션 있는 상품은 option이 필수다. 기존 검사는 첫 옵션으로 신청한다.
    from backend.app.services.reward_catalog import PRODUCTS
    options = next(row[8] for row in PRODUCTS if row[0] == product)
    return options[0] if options else None


def ask(client, product='protein_bar'):
    return client.post('/rewards/exchanges', json={'product_id': product, 'option': first_option(product)})


def make_admin(engine, user_id):
    with Session(engine) as db:
        db.get(User, user_id).role = 'admin'; db.commit()


# 27. 플래그 off 또는 월 전체 상한 미설정 → 모든 교환·쿠폰 API 404, /rewards/me에 교환 필드 없음.
def test_flag_off_is_404(one):
    client, engine, user, mp = one
    for flag, cap in ((False, 100), (True, None), (True, 0)):
        mp.setattr(settings, 'reward_exchange_enabled', flag)
        mp.setattr(settings, 'reward_exchange_global_monthly_cap', cap)
        assert client.get('/rewards/products').status_code == 404
        assert ask(client).status_code == 404
        assert client.get('/rewards/coupons').status_code == 404
        assert client.post('/rewards/exchanges/x/cancel').status_code == 404
        assert client.post('/rewards/coupons/x/used').status_code == 404
        assert 'exchange' not in client.get('/rewards/me').json()
        assert 'reward_exchange' not in client.get('/system/status').json()['available']


# 28. 가입 13일째 거부, 14일째 허용(KST 날짜).
def test_account_days(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    user = member(client, engine, 'young@example.com', days=13)
    denied = ask(client)
    assert denied.status_code == 403 and denied.json()['error']['message'] == '실물 교환은 가입 14일 이후에 할 수 있어요.'
    pin_signup(engine, user['id'], NOON - timedelta(days=14))
    assert ask(client).status_code == 201


# 29·29-1. 교환 제외 출처는 차감에 안 쓰임, 첫 교환은 held, 다음 교환은 requested.
def test_restricted_sources_and_first_hold(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    user = member(client, engine, 'mixed@example.com', points=0)
    with Session(engine) as db:
        rewards.grant_points(db, user['id'], 'onboarding', 300, 'onboarding:signup')
        rewards.grant_points(db, user['id'], 'community_legacy', 300, 'community_legacy')
        db.commit()
    blocked = ask(client)
    assert blocked.status_code == 422 and blocked.json()['error']['message'] == '가입 보너스와 커뮤니티 포인트는 꾸미기에만 쓸 수 있어요.'
    products = {p['id']: p for p in client.get('/rewards/products').json()['items']}
    # 리워드몰 v1.3 §5-2: AI 서비스(ai_report)·기존 코칭(pro_coaching)은 비활성이라 목록에 없다.
    assert products['protein_bar']['reason'] == 'restricted' and 'ai_report' not in products and 'pro_coaching' not in products
    with Session(engine) as db:
        rewards.grant_points(db, user['id'], 'meal', 250, 'meal:x'); db.commit()
    first = ask(client)
    assert first.status_code == 201 and first.json()['status'] == 'held' and first.json()['first_exchange']
    left = lots(engine, user['id'])
    assert left['onboarding:signup'][2] == 300 and left['community_legacy'][2] == 300 and left['meal:x'][2] == 50
    me = client.get('/rewards/me').json()
    assert me['exchange']['exchangeable'] == 50 and me['exchange']['monthly_used'] == 1
    make_admin(engine, user['id'])
    assert client.post(f'/admin/rewards/exchanges/{first.json()["id"]}/issue',
                       json={'coupon_code': CODE, 'coupon_expires_at': (NOON + timedelta(days=30)).isoformat()}).status_code == 200
    clock(monkeypatch, NOON + timedelta(days=15))  # 다음 달
    with Session(engine) as db:
        rewards.grant_points(db, user['id'], 'meal', 200, 'meal:y'); db.commit()
    second = ask(client)
    assert second.status_code == 201 and second.json()['status'] == 'requested' and not second.json()['first_exchange']


# 29-2. 월 전체 상한: 도달 시 거부, 취소하면 카운터가 줄어 다시 신청 가능.
def test_global_cap(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    monkeypatch.setattr(settings, 'reward_exchange_global_monthly_cap', 1)
    member(client, engine, 'a@example.com')
    first = ask(client)
    assert first.status_code == 201
    with TestClient(app) as other:
        member(other, engine, 'b@example.com')
        full = ask(other)
        assert full.status_code == 409 and full.json()['error']['message'] == '이번 달 교환 수량이 모두 찼어요. 다음 달에 다시 신청해 주세요.'
        assert client.post(f'/rewards/exchanges/{first.json()["id"]}/cancel').status_code == 200
        assert ask(other).status_code == 201
    with Session(engine) as db:
        assert db.get(Counter, '2026-10').active_count == 1


# 30·31. 월 1회, 취소 후 같은 달 재신청, 취소는 requested·held만, 만료된 lot은 새 refund lot으로 환불.
def test_monthly_cancel_and_refund(one):
    client, engine, user, mp = one
    first = ask(client).json()
    again = ask(client)
    assert again.status_code == 409 and again.json()['error']['message'] == '이번 달 교환을 이미 신청했어요. 다음 달에 다시 신청할 수 있어요.'
    with Session(engine) as db:
        db.scalar(select(Lot).where(Lot.idem_key == 'seed:meal')).expires_at = NOON - timedelta(seconds=1)
        db.commit()
    canceled = client.post(f'/rewards/exchanges/{first["id"]}/cancel')
    assert canceled.status_code == 200 and canceled.json()['status'] == 'canceled'
    with Session(engine) as db:
        refunded = db.scalar(select(Lot).where(Lot.user_id == user['id'], Lot.source == 'refund'))
        assert refunded.amount == 200 and refunded.restricted is False
    assert client.post(f'/rewards/exchanges/{first["id"]}/cancel').status_code == 409
    second = ask(client)
    assert second.status_code == 201
    make_admin(engine, user['id'])
    client.post(f'/admin/rewards/exchanges/{second.json()["id"]}/issue', json={'coupon_code': CODE, 'coupon_expires_at': (NOON + timedelta(days=30)).isoformat()})
    issued = client.post(f'/rewards/exchanges/{second.json()["id"]}/cancel')
    assert issued.status_code == 409 and issued.json()['error']['message'] == '발급된 쿠폰은 취소할 수 없어요.'


# 32. 관리자 보류·발급·실패, 비관리자 403, 실패 시 전액 환불.
def test_admin_flow(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    member(client, engine, 'second@example.com')
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == 'second@example.com'))
    with TestClient(app) as admin_client:
        admin = member(admin_client, engine, 'ops@example.com', points=0)
        make_admin(engine, admin['id'])
        first = ask(client).json()
        assert client.get('/admin/rewards/exchanges').status_code == 403
        listing = admin_client.get('/admin/rewards/exchanges').json()['items'][0]
        assert listing['first_exchange'] and listing['status'] == 'held' and 'recorded_days_30' in listing and listing['coupon_code'] is None
        before = rewards_balance(engine, user.id)
        assert admin_client.post(f'/admin/rewards/exchanges/{first["id"]}/fail').json()['status'] == 'failed'
        assert rewards_balance(engine, user.id) == before + 200
        second = ask(client).json()
        assert admin_client.post(f'/admin/rewards/exchanges/{second["id"]}/issue', json={'coupon_code': 'x', 'coupon_expires_at': (NOON + timedelta(days=9)).isoformat()}).status_code == 422
        assert admin_client.post(f'/admin/rewards/exchanges/{second["id"]}/issue', json={'coupon_code': CODE, 'coupon_expires_at': (NOON - timedelta(days=1)).isoformat()}).status_code == 422
        issued = admin_client.post(f'/admin/rewards/exchanges/{second["id"]}/issue', json={'coupon_code': CODE, 'coupon_expires_at': (NOON + timedelta(days=9)).isoformat()})
        assert issued.status_code == 200 and issued.json()['coupon_code'] is None
        assert admin_client.post(f'/admin/rewards/exchanges/{second["id"]}/fail').status_code == 409
    with TestClient(app) as third:
        member(third, engine, 'third@example.com')
        requested = ask(third).json()
        assert requested['status'] == 'held'


def rewards_balance(engine, user_id):
    with Session(engine) as db:
        return rewards.balance_info(db, user_id)['balance']


# 33. 쿠폰 번호: 본인 응답에만, DB 평문 아님, 로그에 없음. 사용 표시는 되돌릴 수 없음.
def test_coupon_privacy_and_used(one, caplog):
    client, engine, user, mp = one
    with caplog.at_level(logging.INFO, logger='calodetect'):
        exchange = ask(client).json()
        make_admin(engine, user['id'])
        client.post(f'/admin/rewards/exchanges/{exchange["id"]}/issue', json={'coupon_code': CODE, 'coupon_expires_at': (NOON + timedelta(days=5)).isoformat()})
        box = client.get('/rewards/coupons?status=active').json()
        assert box['items'][0]['coupon_code'] == CODE and box['items'][0]['days_left'] == 5 and box['summary']['expiring_soon'] == 1
        assert client.post(f'/rewards/coupons/{exchange["id"]}/used').json()['status'] == 'used'
        assert client.post(f'/rewards/coupons/{exchange["id"]}/used').status_code == 409
        assert client.get('/rewards/coupons?status=closed').json()['items'][0]['coupon_code'] == CODE
    assert CODE not in caplog.text
    with Session(engine) as db:
        stored = db.scalar(select(Exchange.coupon_code_enc))
        assert stored and CODE not in stored
    with TestClient(app) as other:
        member(other, engine, 'peek@example.com')
        assert other.get('/rewards/coupons').json()['items'] == []
        assert other.post(f'/rewards/coupons/{exchange["id"]}/used').status_code == 404
        assert CODE not in str(other.get('/rewards/ranking').json())


# 상품 목표: 교환 가능 포인트 기준(§6-12), 플래그가 켜졌을 때만 product: 목표 허용.
def test_product_goal(one):
    client, engine, user, mp = one
    assert client.put('/rewards/goal', json={'ref': 'product:salad_box'}).status_code == 200
    goal = client.get('/rewards/me').json()['goal']
    assert goal['basis'] == 'exchangeable' and goal['price'] == 300 and goal['remaining'] == 0
    assert client.put('/rewards/goal', json={'ref': 'product:ai_report'}).status_code == 404


# 34·34-1. (PostgreSQL) 같은 회원 동시 신청 → 1건, 서로 다른 회원이 상한 직전 동시 신청 → 상한 초과 없음.
@pytest.mark.skipif(os.environ.get('RUN_POSTGRES_TESTS') != '1', reason='PostgreSQL concurrency')
def test_concurrency_postgres(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    member(client, engine, 'race@example.com', points=1000)
    results = []

    def run(c):
        results.append(ask(c).status_code)
    clones = []
    for _ in range(2):
        c = TestClient(app); c.cookies.update(client.cookies); c.headers.update(client.headers); clones.append(c)
    threads = [threading.Thread(target=run, args=(c,)) for c in clones]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(results) == [201, 409]

    monkeypatch.setattr(settings, 'reward_exchange_global_monthly_cap', 2)
    others = []
    for index in range(3):
        c = TestClient(app); member(c, engine, f'cap{index}@example.com'); others.append(c)
    results.clear()
    threads = [threading.Thread(target=run, args=(c,)) for c in others]
    [t.start() for t in threads]; [t.join() for t in threads]
    with Session(engine) as db:
        active = db.scalar(select(func.count()).select_from(Exchange).where(Exchange.status.in_(('requested', 'held'))))
        assert active == 2 and db.get(Counter, '2026-10').active_count == 2
    assert sorted(results) == [201, 409, 409]
