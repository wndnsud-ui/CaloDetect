"""로컬 테스트 계정 전용 리워드 더미 데이터(실행 가능성 확인용). 스크립트와 개발용 테스트 페이지가 같이 쓴다.

호출하는 쪽이 개발 환경(local_test_account_enabled)과 테스트 계정인지 먼저 확인한다. 운영 경로에서는 쓰지 않는다.
모든 지급은 'demo:' idem 키라 다시 실행해도 같은 값이면 중복되지 않는다.
"""
from datetime import timedelta
from sqlalchemy import delete, select
from ..models_rewards import (RewardAccount, RewardGrantBatch, RewardPointLot, RewardPointSpend, RewardPointAllocation,
    RewardDebt, RewardXpEvent, RewardUserItem, RewardEquipment, RewardPhotoHash, RewardLevelEvent, RewardStreakProtection,
    RewardExchange, RewardExchangeMonthCounter)
from . import rewards

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


def summary(db, user, reached):
    row = rewards.refresh_cache(db, user.id)
    info = rewards.balance_info(db, user.id)
    protector = db.get(RewardUserItem, (user.id, 'protector'))
    return {'balance': info['balance'], 'deco_only': info['deco_only'], 'xp_total': row.xp_total_cache, 'level': row.level,
            'new_levels': reached, 'streak_days': rewards.streak_info(db, user)['days'],
            'protectors': protector.quantity if protector else 0}
