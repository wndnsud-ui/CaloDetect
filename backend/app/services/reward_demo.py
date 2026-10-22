"""로컬 테스트 계정 전용 리워드 더미 데이터(실행 가능성 확인용). 스크립트와 개발용 테스트 페이지가 같이 쓴다.

호출하는 쪽이 개발 환경(local_test_account_enabled)과 테스트 계정인지 먼저 확인한다. 운영 경로에서는 쓰지 않는다.
모든 지급은 'demo:' idem 키라 다시 실행해도 같은 값이면 중복되지 않는다.
"""
from datetime import timedelta
from sqlalchemy import delete, select
from ..models_rewards import (RewardAccount, RewardGrantBatch, RewardPointLot, RewardPointSpend, RewardPointAllocation,
    RewardDebt, RewardXpEvent, RewardUserItem, RewardEquipment, RewardPhotoHash, RewardLevelEvent, RewardStreakProtection,
    RewardExchange, RewardExchangeMonthCounter, RewardCoachPass)
from . import rewards, reward_rules as rules

SCENARIOS = ('default', 'v13', 'v13_coaching')

LIMITS = {'points': (0, 5000), 'xp': (0, 10000), 'streak': (0, 60), 'protectors': (0, 10)}


def seed(db, user, points=200, xp=1200, streak=5, protectors=1):
    """포인트(adjust)·XP·어제까지 n일 연속 기록·보호권을 넣고 레벨을 계산한다. commit은 호출 측."""
    for name, value in (('points', points), ('xp', xp), ('streak', streak), ('protectors', protectors)):
        low, high = LIMITS[name]
        if not low <= value <= high:
            raise ValueError(f'{name}은 {low}~{high} 사이로 정해 주세요.')
    rewards.ensure_items(db)
    rewards.account(db, user.id)
    today = rewards.today()
    for offset in range(1, streak + 1):
        day = today - timedelta(days=offset)
        rewards.grant_xp(db, user.id, 'meal', 10, f'demo:meal:{day.isoformat()}', day, 'demo', None)
    rewards.grant_xp(db, user.id, 'mission', max(0, xp - 10 * streak), f'demo:xp:{xp}:{today.isoformat()}', today, 'demo', None)
    rewards.grant_points(db, user.id, 'adjust', points, f'demo:points:{points}:{today.isoformat()}', 'demo', None)
    if protectors:
        row = db.get(RewardUserItem, (user.id, 'protector'))
        if row is None:
            db.add(RewardUserItem(user_id=user.id, item_id='protector', quantity=protectors, acquired_via='purchase'))
        else:
            row.quantity = max(row.quantity, protectors)
        db.flush()
    reached = rewards.check_level(db, user.id)
    return summary(db, user, reached)


def reset(db, user):
    """이 회원의 리워드 기록만 모두 지운다(식단·닉네임은 그대로). 다음 조회 때 LV.1·기본 배경으로 다시 시작한다.
    교환 신청도 지우고, 활성 교환이었으면 월 전체 카운터를 되돌려 같은 달에 다시 교환을 시험할 수 있게 한다."""
    for exchange in db.scalars(select(RewardExchange).where(RewardExchange.user_id == user.id,
                                                            RewardExchange.status.in_(('requested', 'held', 'issued', 'used')))):
        counter = db.get(RewardExchangeMonthCounter, exchange.month_key, with_for_update=True)
        if counter:
            counter.active_count = max(0, counter.active_count - 1)
    db.execute(delete(RewardExchange).where(RewardExchange.user_id == user.id))
    db.execute(delete(RewardCoachPass).where(RewardCoachPass.user_id == user.id))
    spends = select(RewardPointSpend.id).where(RewardPointSpend.user_id == user.id)
    lots = select(RewardPointLot.id).where(RewardPointLot.user_id == user.id)
    db.execute(delete(RewardPointAllocation).where(RewardPointAllocation.spend_id.in_(spends)))
    db.execute(delete(RewardPointAllocation).where(RewardPointAllocation.lot_id.in_(lots)))
    for model in (RewardPointSpend, RewardPointLot, RewardXpEvent, RewardDebt, RewardEquipment, RewardUserItem,
                  RewardPhotoHash, RewardLevelEvent, RewardStreakProtection, RewardGrantBatch, RewardAccount):
        db.execute(delete(model).where(model.user_id == user.id))
    db.flush()
    rewards.account(db, user.id)
    return summary(db, user, [])


def _spend(db, user, lot_source, amount, kind, ref_type, ref_id, at, idem):
    """지난 사용 내역 1건: 같은 금액의 적립 lot을 만들고 그 lot에서 바로 차감한다(잔액에는 영향 없음)."""
    lot = rewards.grant_points(db, user.id, lot_source, amount, idem, 'demo', None)
    lot.earned_at = at
    spend = RewardPointSpend(user_id=user.id, kind=kind, amount=amount, ref_type=ref_type, ref_id=ref_id, created_at=at)
    db.add(spend); db.flush()
    db.add(RewardPointAllocation(spend_id=spend.id, lot_id=lot.id, amount=amount))
    lot.remaining = 0
    db.flush()
    return spend


def seed_v13(db, user, coaching=False):
    """리워드몰 v1.3 시연 상태(지시서 §10). 교환 가능 포인트 320P(코칭 변형 760P), 이번 달 꾸미기 2건,
    지난달 교환 2건(used 프로틴바·issued 에너지 드링크), 이번 달 교환 0건, 목표 진한홍삼 프리미엄 30포.
    날짜는 생성 시점 기준 상대값. 가입일은 바꾸지 않는다. commit은 호출 측."""
    from fastapi import HTTPException
    from ..config import settings
    from . import reward_exchange
    if not settings.reward_exchange_active:
        raise HTTPException(409, 'v13 시나리오는 실물 교환 기능(REWARD_EXCHANGE_ENABLED·월 전체 상한)이 켜져 있어야 해요.')
    reset(db, user)
    reward_exchange.ensure_products(db)
    rewards.ensure_items(db)
    now = rewards.now()
    for source, amount in (('meal', 200), ('mission', 80), ('bonus', 40)) + ((('bonus', 440),) if coaching else ()):
        rewards.grant_points(db, user.id, source, amount, f'demo:v13:{source}:{amount}', 'demo', None)
    this_month = rewards.day_start(rewards.today().replace(day=1))
    deco_at = this_month + timedelta(days=2, hours=9)   # 이번 달 3일(시안 10.03), 아직 3일 전이면 1시간 전
    if deco_at > now:
        deco_at = now - timedelta(hours=1)
    for item_id, price, minute in (('prop_water', 40, 1), ('prop_heart', 60, 2)):
        _spend(db, user, 'meal', price, 'item', 'item', item_id, deco_at + timedelta(minutes=minute), f'demo:v13:item:{item_id}')
        if db.get(RewardUserItem, (user.id, item_id)) is None:
            db.add(RewardUserItem(user_id=user.id, item_id=item_id, quantity=1, acquired_via='purchase'))
    last_month = (rewards.today().replace(day=1) - timedelta(days=1)).replace(day=20)
    for product_id, option, price, status in (('protein_bar', '초코 크런치', 200, 'used'), ('energy_drink', '레몬 라임', 150, 'issued')):
        at = rewards.day_start(last_month) + timedelta(hours=12 if status == 'used' else 15)
        spend = _spend(db, user, 'meal', price, 'exchange', 'product', product_id, at, f'demo:v13:exchange:{product_id}')
        month = rules.month_key(last_month)
        exchange = RewardExchange(user_id=user.id, product_id=product_id, points=price, status=status, first_exchange=status == 'used',
                                  requested_at=at, issued_at=at + timedelta(hours=3), month_key=month, spend_id=spend.id,
                                  quantity=1, option_label=option, coupon_code_enc=reward_exchange.seal(f'DEMO-{product_id[:4].upper()}-0000'),
                                  coupon_expires_at=now + timedelta(days=40) if status == 'issued' else at + timedelta(days=30),
                                  used_marked_at=at + timedelta(days=4) if status == 'used' else None)
        db.add(exchange)
        counter = db.get(RewardExchangeMonthCounter, month)
        if counter is None:
            db.add(RewardExchangeMonthCounter(month_key=month, active_count=1))
        else:
            counter.active_count += 1
    db.flush()
    rewards.account(db, user.id).goal_ref = 'product:ginseng_premium30'
    return summary(db, user, [])


def summary(db, user, reached):
    row = rewards.refresh_cache(db, user.id)
    info = rewards.balance_info(db, user.id)
    protector = db.get(RewardUserItem, (user.id, 'protector'))
    return {'balance': info['balance'], 'deco_only': info['deco_only'], 'xp_total': row.xp_total_cache, 'level': row.level,
            'new_levels': reached, 'streak_days': rewards.streak_info(db, user)['days'],
            'protectors': protector.quantity if protector else 0}
