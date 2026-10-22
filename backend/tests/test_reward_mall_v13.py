"""리워드몰 v1.3 M1·M2·M3·M5 검사(지시서 §11 T1~T13, T23)."""
from datetime import timedelta
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.main import app
from backend.app import dev_demo
from backend.app.models_rewards import (RewardExchange as Exchange, RewardPointAllocation as Allocation, RewardProduct as Product,
    RewardPointLot as Lot)
from backend.app.services import rewards, reward_exchange, reward_catalog as catalog
from backend.tests.test_p0_flow import env, account
from backend.tests.reward_helpers import NOON, clock, pin_signup
from backend.tests.test_rewards_exchange import exchange_on, member, make_admin, CODE


@pytest.fixture
def buyer(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    monkeypatch.setattr(settings, 'reward_collab_demo_enabled', True)
    return client, engine, member(client, engine, 'mall@example.com', points=3000), monkeypatch


def ask(client, product, option=None, quantity=1):
    return client.post('/rewards/exchanges', json={'product_id': product, 'option': option, 'quantity': quantity})


def balance(client):
    return client.get('/rewards/me').json()['exchangeable']


# T1. 옵션 있는 상품: 옵션 없이 → 422 OPTION_REQUIRED, 목록에 없는 옵션 → 422.
def test_option_required(buyer):
    client, *_ = buyer
    for option in (None, '없는 맛'):
        response = ask(client, 'pita_sandwich', option)
        assert response.status_code == 422 and response.json()['error']['code'] == 'OPTION_REQUIRED'
    ok = ask(client, 'pita_sandwich', '바질토마토치즈')
    assert ok.status_code == 201 and ok.json()['option_label'] == '바질토마토치즈' and ok.json()['quantity'] == 1


# T2. 수량 경계 422, 홍삼 3개 → 차감 = 단가 × 3, Exchange.points와 allocation 합 일치.
def test_quantity_and_total(buyer):
    client, engine, user, _ = buyer
    for quantity in (0, 4):
        response = ask(client, 'ginseng_daily10', quantity=quantity)
        assert response.status_code == 422 and response.json()['error']['code'] == 'QTY_LIMIT_EXCEEDED'
    assert ask(client, 'pita_sandwich', '바질치즈', quantity=2).json()['error']['code'] == 'QTY_LIMIT_EXCEEDED'
    before = balance(client)
    done = ask(client, 'ginseng_daily10', quantity=3).json()
    assert done['points'] == 540 and done['quantity'] == 3 and done['option_label'] is None and done['unit_points'] == 180
    assert balance(client) == before - 540
    with Session(engine) as db:
        row = db.get(Exchange, done['id'])
        assert row.points == 540 == db.scalar(select(func.sum(Allocation.amount)).where(Allocation.spend_id == row.spend_id))


# T3·T4. 수량 교환도 월 1건 → 다른 교환 409. 취소하면 전체 환불·월 횟수 복구·재신청 가능.
def test_quantity_counts_once_and_refund(buyer):
    client, *_ = buyer
    before = balance(client)
    first = ask(client, 'ginseng_daily10', quantity=3).json()
    assert ask(client, 'energy_bar', '오리지널 견과').status_code == 409
    assert client.post(f"/rewards/exchanges/{first['id']}/cancel").status_code == 200
    assert balance(client) == before
    assert client.get('/rewards/me').json()['exchange']['monthly_used'] == 0
    assert ask(client, 'energy_bar', '오리지널 견과').status_code == 201


# T5. 교환 제외 출처 lot만 있으면 수량 교환도 부족.
def test_restricted_only_cannot_exchange(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    monkeypatch.setattr(settings, 'reward_collab_demo_enabled', True)
    member(client, engine, 'bonus@example.com', points=1000, source='onboarding')
    response = ask(client, 'ginseng_daily10', quantity=2)
    assert response.status_code == 422 and balance(client) == 0


# T6. 기존 교환 행(quantity 기본 1)과 기존 응답 필드 유지.
def test_existing_fields_kept(buyer):
    client, *_ = buyer
    done = ask(client, 'protein_bar', '초코 크런치').json()
    keys = {'id', 'product_id', 'product_name', 'partner_label', 'image_key', 'points', 'status', 'state', 'first_exchange',
            'requested_at', 'issued_at', 'coupon_code', 'coupon_expires_at', 'days_left', 'used_marked_at', 'cancelable'}
    assert keys <= set(done) and done['quantity'] == 1
    item = client.get('/rewards/products').json()['items'][0]
    assert {'id', 'name', 'category', 'price', 'available', 'shortfall', 'eta_days', 'can_exchange', 'reason', 'message'} <= set(item)


# T7. 시드 재실행: 기존 price·available 미변경, 이름·content 갱신, 신규 상품 1회만 추가.
def test_seed_rerun(buyer):
    client, engine, *_ = buyer
    with Session(engine) as db:
        row = db.get(Product, 'energy_bar')
        row.price, row.available, row.name, row.content = 999, False, '옛 이름', {}
        db.commit()
        reward_exchange.ensure_products(db); reward_exchange.ensure_products(db); db.commit()
        row = db.get(Product, 'energy_bar')
        assert (row.price, row.available, row.name) == (999, False, '고소한 견과 에너지바') and row.content['summary']
        assert db.scalar(select(func.count()).select_from(Product).where(Product.id == 'pita_sandwich')) == 1
        assert db.scalar(select(func.count()).select_from(Product)) == len(catalog.PRODUCTS) + len(catalog.COACH_PRODUCTS)


# T8. listed=false: 목록 기본 응답에서 빠지고 상세·신청은 가능.
def test_unlisted_detail_and_exchange(buyer):
    client, *_ = buyer
    ids = {i['id'] for i in client.get('/rewards/products').json()['items']}
    assert 'ginseng_lady30' not in ids and 'ginseng_lady30' in {i['id'] for i in client.get('/rewards/products?listed=false').json()['items']}
    detail = client.get('/rewards/products/ginseng_lady30')
    assert detail.status_code == 200 and detail.json()['content']['summary']
    assert ask(client, 'ginseng_lady30').status_code == 201


# T9. 기획전 플래그 off → 콜라보 상품이 목록·상세·신청·related·슬라이더·기획전에서 모두 제외.
def test_collab_flag_off(buyer):
    client, _, _, mp = buyer
    mp.setattr(settings, 'reward_collab_demo_enabled', False)
    items = client.get('/rewards/products?listed=false').json()['items']
    assert not any(i['collab_brand'] for i in items)
    assert client.get('/rewards/products/bristick15').status_code == 404
    assert ask(client, 'bristick15').status_code == 404
    assert client.get('/rewards/collab').status_code == 404
    slides = client.get('/rewards/promotions').json()['items']
    assert [s['id'] for s in slides] == ['pita', 'salad', 'drink']
    mp.setattr(settings, 'reward_collab_demo_enabled', True)
    assert [s['id'] for s in client.get('/rewards/promotions').json()['items']] == ['collab', 'pita', 'salad', 'drink', 'premium30']
    collab = client.get('/rewards/collab').json()
    assert [p['id'] for p in collab['picks']] == ['bristick15', 'ginseng_daily10', 'ginseng_premium30'] and len(collab['lineup']) == 7


# T10. related_ids에 자기 자신 없음, 존재하는 ID만.
def test_related_ids_valid():
    ids = {row[0] for row in catalog.PRODUCTS}
    for row in catalog.PRODUCTS:
        related = row[12].get('related_ids', [])
        assert row[0] not in related and set(related) <= ids


# T11. 쿠폰 closed_reason: used / 만료된 issued → expired / canceled / failed.
def test_closed_reason(buyer):
    client, engine, user, mp = buyer
    mp.setattr(settings, 'reward_exchange_monthly_limit', 9)
    made = [ask(client, 'energy_bar', '오리지널 견과').json()['id'] for _ in range(4)]
    with Session(engine) as db:
        rows = [db.get(Exchange, i) for i in made]
        rows[0].status = 'used'
        rows[1].status, rows[1].coupon_expires_at = 'issued', NOON - timedelta(days=1)
        rows[2].status = 'canceled'
        rows[3].status = 'failed'
        db.commit()
    reasons = {c['id']: c['closed_reason'] for c in client.get('/rewards/coupons').json()['items']}
    assert [reasons[i] for i in made] == ['used', 'expired', 'canceled', 'failed']


# T12. 목표 설정 후 목록·상세 is_goal=true는 그 상품 하나뿐.
def test_is_goal_single(buyer):
    client, *_ = buyer
    assert client.put('/rewards/goal', json={'ref': 'product:ginseng_premium30'}).status_code == 200
    goals = [i['id'] for i in client.get('/rewards/products').json()['items'] if i['is_goal']]
    assert goals == ['ginseng_premium30'] and client.get('/rewards/products/ginseng_premium30').json()['is_goal']
    assert not client.get('/rewards/products/salad_box').json()['is_goal']
    assert client.get('/rewards/me').json()['goal']['product_id'] == 'ginseng_premium30'


# T13. 포인트 내역 kind 필터·요약, 전날 기록의 정산 대상일(target_date).
def test_ledger_kind_and_target_date(buyer):
    client, engine, user, _ = buyer
    with Session(engine) as db:
        rewards.grant_points(db, user['id'], 'meal', 3, f'meal:{(NOON - timedelta(days=1)).date().isoformat()}:dinner', 'meal', None)
        db.commit()
    ask(client, 'energy_bar', '오리지널 견과')
    every = client.get('/rewards/ledger').json()
    earned = client.get('/rewards/ledger?kind=earn').json()['items']
    spent = client.get('/rewards/ledger?kind=spend').json()['items']
    assert {r['kind'] for r in earned} == {'earn'} and {r['kind'] for r in spent} <= {'spend', 'revoke'}
    assert len(every['items']) == len(earned) + len(spent)
    assert spent[0]['label'] == '고소한 견과 에너지바 교환 신청'
    assert any(r['target_date'] == '2026-10-20' for r in earned)
    assert every['summary']['month_spent'] == 120 and every['summary']['balance'] == balance(client)


# §3-2: earn_rules는 설정값에서 만든다.
def test_earn_rules_follow_settings(buyer):
    client, _, _, mp = buyer
    mp.setattr(settings, 'reward_meal_photo_points', 3)
    rules = {r['id']: r['points'] for r in client.get('/rewards/me').json()['earn_rules']}
    assert rules['meal_photo'] == 3 and rules['three_meals'] == settings.reward_three_meals_points


# 관리자 교환 목록에 수량·옵션.
def test_admin_sees_quantity(buyer):
    client, engine, user, _ = buyer
    ask(client, 'ginseng_daily10', quantity=2)
    make_admin(engine, user['id'])
    row = client.get('/admin/rewards/exchanges').json()['items'][0]
    assert (row['quantity'], row['option_label'], row['points']) == (2, None, 360)


# T23. 시나리오 v13: 테스트 계정 외 403, 생성 후 교환 가능 320P·지난 쿠폰 2건·목표 프리미엄 30포. 코칭 변형 760P.
def test_demo_scenario_v13(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    monkeypatch.setattr(settings, 'reward_collab_demo_enabled', True)
    if not any(getattr(r, 'path', '') == '/dev/demo/status' for r in app.routes):
        app.include_router(dev_demo.router)
    account(client, 'other@example.com')
    assert client.post('/dev/demo/rewards', json={'scenario': 'v13'}).status_code == 403
    user = account(client, dev_demo.TEST_ACCOUNT_EMAIL)
    pin_signup(engine, user['id'], NOON - timedelta(days=30))
    result = client.post('/dev/demo/rewards', json={'scenario': 'v13'})
    assert result.status_code == 200, result.text
    me = client.get('/rewards/me').json()
    assert me['exchangeable'] == 320 and me['exchange']['monthly_used'] == 0 and me['goal']['product_id'] == 'ginseng_premium30'
    coupons = client.get('/rewards/coupons').json()['items']
    assert sorted(c['status'] for c in coupons) == ['issued', 'used']
    spends = client.get('/rewards/ledger?kind=spend').json()['items']
    assert {'물병 소품 구매', '하트 쿠션 구매'} <= {r['label'] for r in spends}
    assert client.post('/dev/demo/rewards', json={'scenario': 'v13_coaching'}).status_code == 200
    assert client.get('/rewards/me').json()['exchangeable'] == 760
