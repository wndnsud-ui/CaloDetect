"""리워드 Stage A: 식단 보상·온보딩·구매·만료·회수·커뮤니티 미러링(지시서 v3 §13 Stage A)."""
import os
import threading
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.config import settings
from backend.app.models import Meal
from backend.app.models_rewards import (RewardPointLot as Lot, RewardPointSpend as Spend, RewardDebt as Debt,
    RewardAccount as Account)
from backend.app.services import rewards as service
from backend.tests.test_p0_flow import env, account
from backend.tests.reward_helpers import NOON, clock, photo, save, lots, xps, balance, pin_signup

pytestmark = pytest.mark.usefixtures('env')


# 로컬 .env의 출시 시각과 무관하게 테스트마다 기본값(미설정 = 모두 출시 전 회원)에서 시작한다.
@pytest.fixture(autouse=True)
def launch_unset(monkeypatch):
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    monkeypatch.setattr(settings, 'reward_exchange_enabled', False)  # Stage C는 별도 테스트에서만 켠다.

@pytest.fixture
def member(env, monkeypatch):
    client, engine, _ = env
    day = clock(monkeypatch, NOON)
    user = account(client, 'reward@example.com')
    pin_signup(engine, user['id'])
    return client, engine, user, day


# 1. 사진 끼니 +2P·+10XP, 사진 없는 끼니 +1P·+10XP. 채팅 첨부도 사진 판정(chat_attachment_id).
def test_photo_and_text_meal_points(member):
    client, engine, user, day = member
    save(client, 'breakfast', day, photo(engine, user['id']))
    save(client, 'lunch', day)
    granted = lots(engine, user['id'])
    assert granted[f'meal:{day}:breakfast'][1] == 2 and granted[f'meal:{day}:lunch'][1] == 1
    assert xps(engine, user['id'])[f'meal:{day}:lunch'] == 10
    with Session(engine) as db:
        meal = Meal(user_id=user['id'], meal_date=day, meal_type='dinner', chat_attachment_id='x')
        assert service.is_photo_meal(meal)


# 2. 같은 날 같은 끼니 두 번 → 두 번째 미지급, 간식 하루 1회. 4. 첫 식단 온보딩은 1회.
def test_once_per_meal_and_first_meal_onboarding(member):
    client, engine, user, day = member
    first = save(client, 'lunch', day)
    grant = client.get(f'/rewards/grants?meal_id={first["id"]}').json()
    assert {i['key'] for i in grant['items']} == {f'meal:{day}:lunch', 'onboarding:first_meal'}
    assert grant['total_points'] == 11 and grant['first_meal']
    assert grant['total_xp'] == 10 and grant['xp_total'] == 10
    assert grant['next_level_xp'] == 300 and grant['xp_to_next'] == 290
    second = save(client, 'lunch', day)
    again = client.get(f'/rewards/grants?meal_id={second["id"]}').json()
    assert again['items'] == [] and again['skip_reason'] == 'duplicate_meal' and again['skip_message']
    save(client, 'snack', day); save(client, 'snack', day)
    granted = lots(engine, user['id'])
    assert granted[f'snack:{day}'][1] == 1 and sum(1 for k in granted if k.startswith('snack:')) == 1
    assert sum(1 for k in granted if k == 'onboarding:first_meal') == 1


# 3. 그저께 → 미지급(연속 미반영), 어제 → 지급.
def test_grant_window(member):
    client, engine, user, day = member
    old = save(client, 'dinner', day - timedelta(days=2))
    assert client.get(f'/rewards/grants?meal_id={old["id"]}').json()['skip_reason'] == 'date_window'
    save(client, 'dinner', day - timedelta(days=1))
    assert f'meal:{day - timedelta(days=1)}:dinner' in lots(engine, user['id'])
    assert f'meal:{day - timedelta(days=2)}:dinner' not in xps(engine, user['id'])


# 5·17-6. 가입 온보딩은 출시 이후 가입자만, 미설정이면 미지급. 목표 온보딩은 첫 저장 1회.
def test_signup_and_goal_onboarding(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    old = account(client, 'old@example.com')
    assert 'onboarding:signup' not in lots(engine, old['id'])
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', NOON - timedelta(days=365))
    with TestClient(app) as other:
        new = account(other, 'new@example.com')
        assert lots(engine, new['id'])['onboarding:signup'][:2] == ('onboarding', 10)
        profile = {'sex': 'female', 'age': 30, 'height': 165, 'weight': 60, 'activity_level': 'light',
                   'goal_type': 'maintain', 'target_calories': 1800}
        assert other.put('/users/me/profile', json=profile).status_code == 200
        assert other.put('/users/me/profile', json={**profile, 'target_calories': 1850}).status_code == 200
        assert lots(engine, new['id'])['onboarding:goal'][1] == 10
        assert other.get('/rewards/me').json()['deco_only'] == 20


# 6. 3끼 완료: 간격 충족 시 +3, 120분 미만이면 미지급.
def test_three_meals_gap(member):
    client, engine, user, day = member
    ids = [save(client, t, day)['id'] for t in ('breakfast', 'lunch')]
    with Session(engine) as db:
        for offset, meal_id in zip((6, 3), ids):
            db.get(Meal, meal_id).created_at = NOON - timedelta(hours=offset)
        db.commit()
    save(client, 'dinner', day)
    assert lots(engine, user['id'])[f'three:{day}'][1] == 3

    with TestClient(app) as other:
        second = account(other, 'gap@example.com')
        for t in ('breakfast', 'lunch', 'dinner'):
            save(other, t, day)
        assert f'three:{day}' not in lots(engine, second['id'])


# 7. 같은 사진(SHA-256) 재사용 → 끼니 미지급(다른 회원 포함), 저장 비활성이면 검사 생략.
def test_photo_reuse(member, monkeypatch):
    client, engine, user, day = member
    save(client, 'breakfast', day, photo(engine, user['id'], b'same-bytes'))
    second = save(client, 'lunch', day, photo(engine, user['id'], b'same-bytes'))
    assert client.get(f'/rewards/grants?meal_id={second["id"]}').json()['skip_reason'] == 'photo_reused'
    with TestClient(app) as other:
        stranger = account(other, 'other@example.com')
        save(other, 'lunch', day, photo(engine, stranger['id'], b'same-bytes'))
        assert f'meal:{day}:lunch' not in lots(engine, stranger['id'])
        detection = photo(engine, stranger['id'], b'same-bytes')
        monkeypatch.setattr(settings, 'image_storage_dir', None)
        save(other, 'dinner', day, detection)
        assert lots(engine, stranger['id'])[f'meal:{day}:dinner'][1] == 2


def test_first_meal_reused_photo_has_points_but_no_xp(member):
    client, engine, user, day = member
    save(client, 'breakfast', day, photo(engine, user['id'], b'already-rewarded'))
    with TestClient(app) as other:
        stranger = account(other, 'first-photo-reuse@example.com')
        meal = save(other, 'lunch', day, photo(engine, stranger['id'], b'already-rewarded'))
        grant = other.get(f'/rewards/grants?meal_id={meal["id"]}').json()
        assert grant['total_points'] == 10 and grant['first_meal']
        assert grant['total_xp'] == 0 and grant['xp_total'] == 0
        assert grant['skip_reason'] == 'photo_reused' and grant['skip_message']
        assert grant['next_level_xp'] == 300


def test_recorded_meals_are_done_even_when_photo_reward_is_skipped(member):
    client, engine, user, day = member
    with TestClient(app) as other:
        stranger = account(other, 'status-photo-source@example.com')
        save(other, 'breakfast', day, photo(engine, stranger['id'], b'status-reused-photo'))
    breakfast = save(client, 'breakfast', day, photo(engine, user['id'], b'status-reused-photo'))
    save(client, 'lunch', day)
    snack = save(client, 'snack', day)
    grant = client.get(f'/rewards/grants?meal_id={snack["id"]}').json()
    status = grant['today_meals']
    assert status['breakfast']['done'] is True
    assert status['breakfast']['rewarded'] is False
    assert status['lunch']['done'] is True
    assert status['snack']['done'] is True
    assert status['dinner']['done'] is False
    assert client.get('/rewards/me').json()['today_meals'] == status
    skipped = client.get(f'/rewards/grants?meal_id={breakfast["id"]}').json()
    assert skipped['skip_reason'] == 'photo_reused'
    assert f'meal:{day}:breakfast' not in lots(engine, user['id'])


# 8. 보상 훅 예외 → 식단은 저장되고 보상만 없음, POST /meals 응답 본문 형태 동일.
def test_hook_failure_isolated(member, monkeypatch):
    client, engine, user, day = member
    normal = save(client, 'breakfast', day)

    def boom(*args):
        raise RuntimeError('boom')
    monkeypatch.setattr(service, 'grant_for_meal', boom)
    failed = save(client, 'lunch', day)
    assert set(failed) == set(normal)
    with Session(engine) as db:
        assert db.get(Meal, failed['id']) is not None
    assert f'meal:{day}:lunch' not in lots(engine, user['id'])


# 9. 시드·데모 스크립트 식단은 보상 없음(훅을 거치지 않는다).
def test_seeded_meals_have_no_rewards(member):
    client, engine, user, day = member
    with Session(engine) as db:
        db.add(Meal(user_id=user['id'], meal_date=day, meal_type='lunch')); db.commit()
    assert lots(engine, user['id']) == {}


# 10·17-2. 구매: 차감, 온보딩 → 커뮤니티 → 나머지 순서, 부족 422 문구, 중복 409, 레벨 조건 403.
def test_purchase_rules(member):
    client, engine, user, day = member
    with Session(engine) as db:
        service.account(db, user['id'])
        for idem, source, amount, days in (('a', 'meal', 35, 10), ('b', 'community', 4, 300), ('c', 'onboarding', 3, 365)):
            lot = service.grant_points(db, user['id'], source, amount, idem)
            lot.expires_at = NOON + timedelta(days=days)
        db.commit()
    bought = client.post('/rewards/items/prop_water/purchase')
    assert bought.status_code == 200, bought.text
    assert bought.json()['restricted_used'] == 7 and bought.json()['balance'] == 2
    assert lots(engine, user['id'])['a'][2] == 2
    assert client.post('/rewards/items/prop_water/purchase').status_code == 409
    short = client.post('/rewards/items/prop_salad/purchase')
    assert short.status_code == 422 and short.json()['error']['message'] == '포인트가 부족해요. 48P 더 모으면 돼요.'
    assert client.post('/rewards/items/bg_lv3/purchase').status_code == 403


# 11. 장착: 미보유 403, slot당 1개, 해제(null).
def test_equipment(member):
    client, engine, user, day = member
    assert client.put('/rewards/equipment', json={'slot': 'prop', 'item_id': 'prop_water'}).status_code == 403
    assert client.get('/rewards/me').json()['equipment'] == {'background': 'bg_lv1'}
    with Session(engine) as db:
        service.grant_points(db, user['id'], 'meal', 100, 'x'); db.commit()
    for item in ('starter_hat', 'starter_bg'):
        assert client.post(f'/rewards/items/{item}/purchase').status_code == 403
    assert client.put('/rewards/equipment', json={'slot': 'hat', 'item_id': 'starter_hat'}).status_code == 200
    assert client.put('/rewards/equipment', json={'slot': 'background', 'item_id': 'starter_bg'}).json()['equipment'] == \
        {'background': 'starter_bg', 'hat': 'starter_hat'}
    assert client.put('/rewards/equipment', json={'slot': 'hat', 'item_id': 'starter_bg'}).status_code == 422
    assert client.put('/rewards/equipment', json={'slot': 'hat', 'item_id': None}).json()['equipment'] == {'background': 'starter_bg'}


def test_clothing_switch_keeps_ownership_and_regular_props(member):
    from backend.app.models_rewards import RewardUserItem as UserItem
    client, engine, user, _ = member
    client.get('/rewards/me')
    with Session(engine) as db:
        for item_id in ('outfit_workout', 'outfit_lv3', 'prop_water'):
            db.add(UserItem(user_id=user['id'], item_id=item_id, quantity=1, acquired_via='level'))
        db.commit()

    def wear(slot, item_id):
        result = client.put('/rewards/equipment', json={'slot': slot, 'item_id': item_id})
        assert result.status_code == 200
        return result.json()['equipment']

    assert wear('prop', 'outfit_workout')['prop'] == 'outfit_workout'
    # 미보유 코스튬 착용 실패 시 현재 운동복을 유지한다.
    assert client.put('/rewards/equipment', json={'slot': 'outfit', 'item_id': 'costume_lv4'}).status_code == 403
    assert client.get('/rewards/me').json()['equipment']['prop'] == 'outfit_workout'
    clothes = wear('outfit', 'outfit_lv3')
    assert clothes['outfit'] == 'outfit_lv3' and 'prop' not in clothes
    clothes = wear('prop', 'outfit_workout')
    assert clothes['prop'] == 'outfit_workout' and 'outfit' not in clothes
    wear('prop', 'prop_water')
    clothes = wear('outfit', 'outfit_lv3')
    assert clothes['prop'] == 'prop_water' and clothes['outfit'] == 'outfit_lv3'
    assert wear('outfit', None)['prop'] == 'prop_water'
    with Session(engine) as db:
        for item_id in ('outfit_workout', 'outfit_lv3', 'prop_water'):
            assert db.get(UserItem, (user['id'], item_id)).quantity == 1


# 12. 만료: 유효기간 지난 lot은 잔액에서 빠지고 expire spend 생성, 30일 내 만료 예정 합계.
def test_expiry(member, monkeypatch):
    client, engine, user, day = member
    with Session(engine) as db:
        service.account(db, user['id'])
        service.grant_points(db, user['id'], 'meal', 4, 'old').expires_at = NOON - timedelta(seconds=1)
        service.grant_points(db, user['id'], 'meal', 6, 'soon').expires_at = NOON + timedelta(days=10)
        service.grant_points(db, user['id'], 'meal', 7, 'later')
        db.commit()
    data = client.get('/rewards/me').json()
    assert data['balance'] == 13 and data['expiring_soon'] == 6
    with Session(engine) as db:
        spend = db.scalar(select(Spend).where(Spend.user_id == user['id'], Spend.kind == 'expire'))
        assert spend.amount == 4


# 13. 커뮤니티 미러링: 반응 지급 → community lot, 취소 → 회수, 기존 /community/points/me 불변.
def test_community_mirror(member):
    client, engine, user, day = member
    meal = save(client, 'lunch', day)
    post = client.post('/community/posts', json={'meal_id': meal['id']}).json()
    with TestClient(app) as other:
        fan = account(other, 'fan@example.com')
        before = other.get('/community/points/me').json()
        assert other.post(f'/community/posts/{post["id"]}/reactions/recommend').status_code == 201
        mirrored = lots(engine, user['id'])
        key = next(k for k in mirrored if k.startswith('reaction:'))
        assert mirrored[key][:2] == ('community', settings.community_recommend_received_points)
        assert other.get('/community/points/me').json()['balance'] == before['balance'] + settings.community_reaction_given_points
        assert other.delete(f'/community/posts/{post["id"]}/reactions/recommend').status_code == 200
        assert lots(engine, user['id'])[key][2] == 0
        assert lots(engine, fan['id'])[next(k for k in lots(engine, fan['id']) if k.startswith('reaction:'))][2] == 0


# 14. /rewards/grants는 그 저장으로 생긴 지급만, 타인 식단은 404.
def test_grants_owner_only(member):
    client, engine, user, day = member
    meal = save(client, 'lunch', day)
    with TestClient(app) as other:
        account(other, 'peek@example.com')
        assert other.get(f'/rewards/grants?meal_id={meal["id"]}').status_code == 404


# 15. idem UNIQUE: 같은 키 직접 2회 INSERT → IntegrityError, 서비스 경로는 건너뜀.
def test_idem_unique(member):
    client, engine, user, day = member
    with Session(engine) as db:
        service.account(db, user['id'])
        assert service.grant_points(db, user['id'], 'meal', 1, 'k')
        assert service.grant_points(db, user['id'], 'meal', 1, 'k') is False
        db.commit()
        stamp = NOON + timedelta(days=1)
        db.add(Lot(user_id=user['id'], source='meal', amount=1, remaining=1, earned_at=NOON, expires_at=stamp, idem_key='k'))
        with pytest.raises(IntegrityError):
            db.flush()


# 17-1. 두 번째 사진 끼니 저장 시 끼니 +2P와 오늘의 미션 +2P가 같은 묶음.
def test_mission_in_same_batch(member):
    client, engine, user, day = member
    save(client, 'breakfast', day, photo(engine, user['id']))
    second = save(client, 'lunch', day, photo(engine, user['id']))
    grant = client.get(f'/rewards/grants?meal_id={second["id"]}').json()
    assert {i['key'] for i in grant['items']} == {f'meal:{day}:lunch', f'mission:{day}'}
    assert (grant['total_points'], grant['total_xp']) == (4, 20)


# 17-4. 회수액이 잔액보다 크면 reward_debts, 다음 적립에서 먼저 상계, 잔액 음수 없음.
def test_revoke_debt(member):
    client, engine, user, day = member
    with Session(engine) as db:
        service.account(db, user['id'])
        service.grant_points(db, user['id'], 'community', 5, 'reaction:r1:like_received')
        db.commit()
    with Session(engine) as db:
        service.spend_points(db, user['id'], 4, 'item', 'item', 'x'); db.commit()
    with Session(engine) as db:
        service.revoke_lot(db, user['id'], 'reaction:r1:like_received'); db.commit()
        assert db.scalar(select(func.sum(Debt.remaining)).where(Debt.user_id == user['id'])) == 4
        assert service.revoke_lot(db, user['id'], 'reaction:r1:like_received') == 0
    with Session(engine) as db:
        service.grant_points(db, user['id'], 'meal', 10, 'next'); db.commit()
        assert service.balance_info(db, user['id'])['balance'] == 6
        assert db.scalar(select(func.sum(Debt.remaining)).where(Debt.user_id == user['id'])) == 0


# 17-5. 다음 목표·예상 일수: 창 W = min(7, 가입 후 일수), 온보딩 제외, 평균 0이면 숫자 없음.
def test_goal_and_eta(member):
    client, engine, user, day = member
    goal = client.get('/rewards/me').json()['goal']
    assert goal['item_id'] == 'prop_water' and goal['remaining'] == 40 and goal['eta_days'] is None
    save(client, 'lunch', day)  # +1 끼니, +10 온보딩(예상 일수에서 제외)
    goal = client.get('/rewards/me').json()['goal']
    assert goal['base_points'] == 11 and goal['remaining'] == 29
    assert client.put('/rewards/goal', json={'ref': 'item:prop_salad'}).status_code == 200
    goal = client.get('/rewards/me').json()['goal']
    assert goal['chosen'] and goal['remaining'] == 39 and goal['eta_days'] == 39
    assert client.put('/rewards/goal', json={'ref': 'product:protein'}).status_code == 404


# 응답 형태: 미설정 리워드 기능 없이도 /rewards/me가 동작하고 Stage C 필드는 없다.
def test_me_shape(member):
    client, engine, user, day = member
    data = client.get('/rewards/me').json()
    assert {'balance', 'exchangeable', 'deco_only', 'actions', 'goal', 'equipment', 'level', 'streak'} <= set(data)
    assert not {'products', 'coupons', 'exchange'} & set(data)
    assert client.get('/rewards/products').status_code == 404


# 16·17. (PostgreSQL) 동시 구매 2건 → 1건만 성공, 같은 끼니 동시 저장 → 지급 1건.
@pytest.mark.skipif(os.environ.get('RUN_POSTGRES_TESTS') != '1', reason='PostgreSQL concurrency')
def test_concurrency_postgres(member):
    client, engine, user, day = member
    with Session(engine) as db:
        service.account(db, user['id'])
        service.grant_points(db, user['id'], 'meal', 50, 'only'); db.commit()
    results = []

    def buy(item):
        with Session(engine) as db:
            try:
                service.purchase(db, db.get(service.User, user['id']), item)
                results.append(200)
            except Exception as error:
                results.append(getattr(error, 'status_code', 500))
    threads = [threading.Thread(target=buy, args=(i,)) for i in ('prop_water', 'prop_salad')]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(results) == [200, 422]
    with Session(engine) as db:
        assert service.balance_info(db, user['id'])['balance'] in (0, 10)
        assert db.scalar(select(func.min(Lot.remaining)).where(Lot.user_id == user['id'])) >= 0

    def meal():
        with TestClient(app) as c:
            c.cookies.update(client.cookies); c.headers.update(client.headers)
            save(c, 'dinner', day)
    threads = [threading.Thread(target=meal) for _ in range(2)]
    [t.start() for t in threads]; [t.join() for t in threads]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Lot).where(Lot.user_id == user['id'],
                                                                      Lot.idem_key == f'meal:{day}:dinner')) == 1


def test_default_items_no_points_and_existing_account(member):
    client, engine, user, day = member
    client.get('/rewards/me')
    with Session(engine) as db:
        from backend.app.models_rewards import RewardUserItem, RewardItem
        db.query(RewardUserItem).filter(RewardUserItem.user_id == user['id'], RewardUserItem.item_id == 'starter_hat').delete()
        db.get(RewardItem, 'starter_hat').price = 20
        db.get(RewardItem, 'starter_hat').sellable = True
        db.commit()
    items = {item['id']: item for item in client.get('/rewards/items').json()['items']}
    for item_id in service.DEFAULT_ITEMS:
        assert items[item_id]['owned'] and items[item_id]['default_provided']
        assert items[item_id]['price'] is None and not items[item_id]['sellable']
        assert not items[item_id]['purchasable']
    assert client.put('/rewards/equipment', json={'slot': 'hat', 'item_id': 'starter_hat'}).status_code == 200
    assert client.put('/rewards/equipment', json={'slot': 'hat', 'item_id': None}).status_code == 200
    assert client.get('/rewards/me').json()['balance'] == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Spend)) == 0
