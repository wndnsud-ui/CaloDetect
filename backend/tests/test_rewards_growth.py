"""리워드 Stage B: 연속 기록·보호권·레벨업·미션·XP 모드·랭킹(지시서 v3 §13 Stage B)."""
from datetime import timedelta, date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.config import settings
from backend.app.models_rewards import (RewardLevelEvent as LevelEvent, RewardUserItem as UserItem,
    RewardStreakProtection as Protection, RewardXpEvent as Xp)
from backend.app.services import rewards as service
from backend.tests.test_p0_flow import env, account
from backend.tests.reward_helpers import NOON, clock, photo, save, lots, xps, pin_signup


# 로컬 .env의 출시 시각과 무관하게 테스트마다 기본값(미설정 = 모두 출시 전 회원)에서 시작한다.
@pytest.fixture(autouse=True)
def launch_unset(monkeypatch):
    monkeypatch.setattr(settings, 'reward_onboarding_start_at', None)
    monkeypatch.setattr(settings, 'reward_exchange_enabled', False)  # Stage C는 별도 테스트에서만 켠다.

@pytest.fixture
def member(env, monkeypatch):
    client, engine, _ = env
    clock(monkeypatch, NOON)
    user = account(client, 'grow@example.com')
    pin_signup(engine, user['id'], NOON - timedelta(days=60))
    return client, engine, user, monkeypatch


def on(monkeypatch, offset):
    return clock(monkeypatch, NOON + timedelta(days=offset))


# 18. 연속 3일째 +5P·+20XP, 7일째 +10P·+50XP, 10일째 반복, 하루 빠지면 0부터.
def test_streak_bonus(member):
    client, engine, user, mp = member
    for offset in range(10):
        save(client, 'lunch', on(mp, offset))
    d = lambda o: NOON.date() + timedelta(days=o)
    granted, xp = lots(engine, user['id']), xps(engine, user['id'])
    assert granted[f'streak3:{d(2)}'][1] == 5 and xp[f'streak3:{d(2)}'] == 20
    assert granted[f'streak7:{d(6)}'][1] == 10 and xp[f'streak7:{d(6)}'] == 50
    assert f'streak3:{d(9)}' in granted and f'streak3:{d(3)}' not in granted
    save(client, 'lunch', on(mp, 12))
    assert client.get('/rewards/me').json()['streak']['days'] == 1


# 19·26-1. 보호권: 오늘 기록 후 어제 보호 → 연속 재계산·보너스, 보유 0 거부, 월 상한.
def test_protector(member):
    client, engine, user, mp = member
    save(client, 'lunch', on(mp, 0))
    today = on(mp, 2)
    save(client, 'lunch', today)
    assert client.post('/rewards/streak/protect').status_code == 422
    with Session(engine) as db:
        db.add(UserItem(user_id=user['id'], item_id='protector', quantity=2, acquired_via='purchase')); db.commit()
    state = client.get('/rewards/me').json()['streak']
    assert state['protect_available'] and state['streak_if_protected'] == 3
    result = client.post('/rewards/streak/protect')
    assert result.status_code == 200 and result.json()['streak']['days'] == 3
    assert lots(engine, user['id'])[f'streak3:{today}'][1] == 5
    assert f'meal:{today - timedelta(days=1)}:lunch' not in lots(engine, user['id'])
    assert client.post('/rewards/streak/protect').status_code == 409
    with Session(engine) as db:
        assert db.get(UserItem, (user['id'], 'protector')).quantity == 1
        db.add(Protection(user_id=user['id'], protected_date=date(2026, 10, 1), created_at=NOON + timedelta(days=2)))
        db.commit()
    save(client, 'lunch', on(mp, 5))
    on(mp, 7)
    assert client.post('/rewards/streak/protect').status_code == 409  # 이번 달 2회 사용


# 20·26-3. 레벨업: 300XP LV.2·배경, LV.3 +50P·의상·배경, 동시 2단계, 회수 후 유지, 미확인 이벤트는 가장 높은 1건.
def test_level_up(member):
    client, engine, user, mp = member
    with Session(engine) as db:
        service.account(db, user['id'])
        service.grant_xp(db, user['id'], 'meal', 1000, 'seed', NOON.date())
        db.commit()
    data = client.get('/rewards/me').json()
    assert data['level'] == 3 and data['pending_levelup']['level'] == 3
    assert lots(engine, user['id'])['level:3'][1] == 50 and 'level:2' not in lots(engine, user['id'])
    with Session(engine) as db:
        events = {e.level: e.seen_at for e in db.scalars(select(LevelEvent).where(LevelEvent.user_id == user['id']))}
        assert events[2] is not None and events[3] is None
        owned = {u.item_id for u in db.scalars(select(UserItem).where(UserItem.user_id == user['id']))}
        assert {'bg_lv1', 'bg_lv2', 'bg_lv3'} <= owned
        assert 'outfit_lv3' not in owned and 'costume_lv4' not in owned
    assert client.post(f'/rewards/levelups/{data["pending_levelup"]["id"]}/seen').status_code == 200
    with Session(engine) as db:
        service.grant_xp(db, user['id'], 'revoke', -900, 'revoke:seed', NOON.date()); db.commit()
    again = client.get('/rewards/me').json()
    assert again['level'] == 3 and again['pending_levelup'] is None
    assert client.post('/rewards/items/bg_lv3/purchase').status_code == 403
    assert client.put('/rewards/equipment', json={'slot': 'background', 'item_id': 'bg_lv3'}).status_code == 200
    assert client.put('/rewards/equipment', json={'slot': 'background', 'item_id': 'bg_lv4'}).status_code == 403


# 21. 영양 균형 XP: 당류·나트륨 기준이 TBD라 판정하지 않는다(임의 기준 금지). 규칙 함수는 ±15% 범위만 통과.
def test_balance_xp_not_granted(member):
    client, engine, user, mp = member
    from backend.app.services import reward_rules as rules
    totals = {'cal': 1000, 'sugar': 10, 'sodium': 500}
    assert not rules.balance_ok(totals, 1000, None, None)
    assert rules.balance_ok(totals, 1000, 50, 2000) and not rules.balance_ok(totals, 2000, 50, 2000)
    save(client, 'lunch', on(mp, 0))
    assert not any(k.startswith('balance') for k in xps(engine, user['id']))


# 22·26-2. 주간 미션 5일, 가입 주는 축소(금요일 가입 → 3일).
def test_weekly_mission(member):
    client, engine, user, mp = member
    monday = date(2026, 10, 26)
    for offset in range(5):
        clock(mp, NOON + timedelta(days=5 + offset))
        save(client, 'lunch', monday + timedelta(days=offset))
    assert lots(engine, user['id'])['weekly:2026-W44'][1] == 15
    with TestClient(app) as other:
        friday = NOON + timedelta(days=2)  # 2026-10-23(금)
        clock(mp, friday)
        late = account(other, 'friday@example.com')
        pin_signup(engine, late['id'], friday)
        for offset in range(3):
            clock(mp, friday + timedelta(days=offset))
            save(other, 'lunch', friday.date() + timedelta(days=offset))
        assert 'weekly:2026-W43' in lots(engine, late['id'])


def test_late_signup_and_demo_streak_explain_62_points(member):
    from backend.app.models import User
    from backend.app.services import reward_demo, reward_rules as rules
    client, engine, user, mp = member
    sunday = NOON.replace(month=11, day=29)
    day = clock(mp, sunday)
    pin_signup(engine, user['id'], sunday)
    with Session(engine) as db:
        reward_demo.seed(db, db.get(User, user['id']), points=0, xp=20, streak=2, protectors=0)
        db.commit()
    assert rules.weekly_required_days(day, rules.week_monday(day)) == 1
    assert rules.monthly_required_days(day, day) == 1
    meal = save(client, 'lunch', day, photo(engine, user['id']))
    grant = client.get(f'/rewards/grants?meal_id={meal["id"]}').json()
    assert (grant['total_points'], grant['total_xp']) == (62, 30)
    assert {row['key']: row['points'] for row in grant['items']} == {
        f'meal:{day}:lunch': 2, 'onboarding:first_meal': 10,
        f'streak3:{day}': 5, f'weekly:{rules.iso_week_key(day)}': 15,
        f'monthly:{rules.month_key(day)}': 30}


# 23. XP 모드: 반응 XP(추천 10·누르기 2), 받기 일 상한, 공유 +1P·+10XP 하루 1회, 랭킹 제외.
def test_community_xp_mode(member):
    client, engine, user, mp = member
    mp.setattr(settings, 'reward_community_xp_mode', True)
    mp.setattr(settings, 'reward_reaction_received_daily_cap', 12)
    for name in ('community_like_received_points', 'community_recommend_received_points', 'community_reaction_given_points'):
        mp.setattr(settings, name, 0)
    day = on(mp, 0)
    posts = [client.post('/community/posts', json={'meal_id': save(client, t, day)['id']}).json() for t in ('lunch', 'dinner')]
    assert lots(engine, user['id'])[f'share:{day}'][1] == 1
    summary = client.get('/community/points/me').json()
    assert summary['reward_view']['balance'] == client.get('/rewards/me').json()['balance']
    assert summary['reward_view']['share_points'] == 1
    assert summary['reward_view']['share_xp'] == 10
    assert summary['reward_view']['recommend_xp'] == 10
    assert any(row['source'] == 'community' and row['amount'] == 1 for row in summary['reward_view']['recent'])
    with TestClient(app) as other:
        fan = account(other, 'xpfan@example.com')
        for post in posts:
            assert other.post(f'/community/posts/{post["id"]}/reactions/recommend').status_code == 201
        received = [v for k, v in xps(engine, user['id']).items() if k.endswith(':received')]
        assert received == [10, 2]
        assert sorted(v for k, v in xps(engine, fan['id']).items() if k.endswith(':given')) == [2, 2]
        assert not any(k.startswith('reaction:') for k in lots(engine, user['id']))
        ranking = other.get('/rewards/ranking').json()
        assert ranking['me']['rank'] is None and ranking['me']['xp'] == 0


# 24·26-5. 랭킹: 반응·공유 XP 제외, 동점 동순위, 주 경계(KST 월요일), 응답 필드는 rank·nickname·xp·is_me뿐.
@pytest.mark.parametrize('spent', [False, True])
def test_delete_post_reclaims_share_points_once(member, spent):
    from backend.app.models_rewards import RewardPointLot as Lot, RewardDebt as Debt
    client, engine, user, mp = member
    mp.setattr(settings, 'reward_community_xp_mode', True)
    day = on(mp, 0)
    posts = [client.post('/community/posts', json={'meal_id': save(client, t, day)['id']}).json()
             for t in ('lunch', 'dinner')]
    # 같은 날 두 번째 공유에는 보상이 없으므로 삭제 차감도 없어야 한다.
    assert client.get(f'/community/posts/{posts[1]["id"]}/delete-preview').json()['me'] == 0
    if spent:
        with Session(engine) as db:
            amount = sum(l.remaining for l in db.scalars(select(Lot).where(Lot.user_id == user['id'])))
            service.spend_points(db, user['id'], amount, 'item', 'test', 'test-spent')
            db.commit()
    before = client.get('/rewards/me').json()['balance']
    path = f'/community/posts/{posts[0]["id"]}'
    assert client.get(path + '/delete-preview').json()['me'] == -1
    assert client.delete(path).json()['deducted']['me'] == -1
    assert client.get('/rewards/me').json()['balance'] == max(0, before - 1)
    assert client.delete(path).status_code == 404
    with Session(engine) as db:
        service.community_post_deleted(db, user['id'], posts[0]['id'], 0)
        db.commit()
        debts = list(db.scalars(select(Debt).where(Debt.user_id == user['id'])))
        assert sum(d.amount for d in debts) == (1 if spent else 0)


def test_ranking(member):
    client, engine, user, mp = member
    day = on(mp, 0)
    with TestClient(app) as other:
        rival = account(other, 'rival@example.com')
        with Session(engine) as db:
            for uid in (user['id'], rival['id']):
                service.grant_xp(db, uid, 'meal', 30, 'w', day)
                service.grant_xp(db, uid, 'meal', 99, 'old', date(2026, 10, 18))
            service.grant_xp(db, rival['id'], 'reaction_received', 50, 'r', day, ranking=False)
            db.commit()
        data = client.get('/rewards/ranking').json()
    assert [i['rank'] for i in data['items']] == [1, 1] and {i['xp'] for i in data['items']} == {30}
    for item in data['items']:
        assert set(item) == {'rank', 'nickname', 'xp', 'is_me'} and item['nickname']
    assert data['me']['is_me'] and data['week_start'] == '2026-10-19'
    text = str(data)
    assert 'Tester' not in text and 'rival@example.com' not in text


# 성장 화면: 로드맵 5단계, 요일 7칸, 미션 문구는 API에서.
def test_growth_view(member):
    client, engine, user, mp = member
    save(client, 'lunch', on(mp, 0))
    data = client.get('/rewards/growth').json()
    assert [r['level'] for r in data['roadmap']] == [1, 2, 3, 4, 5]
    assert len(data['week']) == 7 and data['week'][2]['state'] == 'recorded'
    assert data['missions'][0]['text'] and data['today_xp'][0]['xp'] == 10


# 사용자 결정(2026-10-26): 가입한 날은 연속 기록 1일째. 미션 기록 일수에는 넣지 않는다.
def test_signup_day_counts_as_streak_day_one(member):
    client, engine, user, mp = member
    pin_signup(engine, user['id'], NOON)
    state = client.get('/rewards/me').json()['streak']
    assert (state['days'], state['today_recorded'], state['missed_yesterday']) == (1, False, False)
    week = {row['date']: row['state'] for row in client.get('/rewards/growth').json()['week']}
    assert week[str(NOON.date())] == 'joined'
    assert week[str(NOON.date() - timedelta(days=1))] == 'before_join'
    # 가입 다음 날 기록 → 2일째, 그다음 날 기록 → 3일째 보너스(가입일 포함).
    save(client, 'lunch', on(mp, 1))
    assert client.get('/rewards/me').json()['streak']['days'] == 2
    third = on(mp, 2)
    save(client, 'lunch', third)
    assert client.get('/rewards/me').json()['streak']['days'] == 3
    assert f'streak3:{third}' in lots(engine, user['id'])
    weekly = next(m for m in client.get('/rewards/growth').json()['missions'] if m['id'].startswith('weekly'))
    assert weekly['progress'] == 2


def test_signup_day_missed_next_day_breaks_streak(member):
    client, engine, user, mp = member
    pin_signup(engine, user['id'], NOON)
    on(mp, 2)
    state = client.get('/rewards/me').json()['streak']
    assert state['days'] == 0 and state['missed_yesterday']
