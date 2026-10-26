"""CaloPoint·Growth·Reward 원장·지급·차감·구매·연속 기록·레벨·닉네임(리워드 지시서 v3 Stage A·B).

규칙(§6-0):
- 지급은 lot/xp 행 INSERT 하나. 중복은 UNIQUE(user_id, idem_key)로만 막고 IntegrityError는 SAVEPOINT로 그 지급만 건너뛴다.
- 차감(구매·만료·회수)은 reward_accounts 행 FOR UPDATE → lots(expires_at, earned_at, id 순) FOR UPDATE → allocation.
  잔액 부족 판정은 잠금 이후에 한다. 잔액은 원장(remaining 합계)에서 계산하고 balance_cache는 재계산용 캐시다.
- 식단 저장 경로의 훅은 SAVEPOINT 안에서 실행하고 실패해도 식단 저장은 계속한다.
- 로그에는 금액·출처만 남긴다. 회원·식단 ID, 이름·이메일·닉네임·사진 경로는 남기지 않는다.
"""
import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime, time as dtime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from ..config import settings
from ..models import Meal, Detection, Profile, User, PointTransaction
from ..models_chat import ChatAttachment
from ..models_rewards import (RewardAccount as Account, RewardGrantBatch as Batch, RewardPointLot as Lot,
    RewardPointSpend as Spend, RewardPointAllocation as Allocation, RewardDebt as Debt, RewardXpEvent as Xp,
    RewardItem as Item, RewardUserItem as UserItem, RewardEquipment as Equipment, RewardPhotoHash as PhotoHash,
    RewardNickname as Nickname, RewardLevelEvent as LevelEvent, RewardStreakProtection as Protection)
from . import reward_rules as rules
from .. import storage
from .timezone import KST, korean_date

log = logging.getLogger('calodetect')

# 시드 아이템(§5-5). (id, 이름, kind, slot, 가격, 필요 레벨, 판매, stage, active)
ITEMS = (
    ('starter_sticker', '기본 스티커', 'deco', 'sticker', 10, None, True, 'A', True),
    ('starter_glasses', '기본 안경', 'deco', 'glasses', 10, None, True, 'A', True),
    ('starter_ribbon', '리본', 'deco', 'ribbon', 10, None, True, 'A', True),
    ('starter_hat', '기본 모자', 'deco', 'hat', 20, None, True, 'A', True),
    ('starter_shoes', '운동화', 'deco', 'shoes', 20, None, True, 'A', True),
    ('starter_bg', '기본 배경', 'background', 'background', 30, None, True, 'A', True),
    ('prop_water', '물병 소품', 'deco', 'prop', 4, None, True, 'B', True),
    ('prop_salad', '샐러드 볼 소품', 'deco', 'prop', 5, None, True, 'B', True),
    ('prop_heart', '하트 쿠션', 'deco', 'prop', 6, None, True, 'B', True),
    ('outfit_workout', '운동복 세트', 'deco', 'prop', 8, None, True, 'B', True),
    ('season_set', '한정판 시즌 세트', 'deco', 'prop', 15, None, True, 'B', False),
    ('protector', '연속 기록 보호권', 'protector', 'none', 3, None, True, 'B', True),
    ('bg_lv1', '포근한 아침 방', 'background', 'background', None, 1, False, 'B', True),
    ('bg_lv2', '새싹 정원', 'background', 'background', None, 2, False, 'B', True),
    ('bg_lv3', '산책 공원', 'background', 'background', None, 3, False, 'B', True),
    ('bg_lv4', '텃밭 피크닉', 'background', 'background', None, 4, False, 'B', True),
    ('bg_lv5', '햇살 언덕', 'background', 'background', None, 5, False, 'B', True),
    ('outfit_lv3', '전용 의상', 'deco', 'outfit', 15, None, True, 'B', True),
    ('costume_lv4', '전용 코스튬', 'deco', 'outfit', 25, None, True, 'B', True),
    ('costume_explorer', '탐험가 코스튬', 'deco', 'outfit', 20, None, True, 'B', True),
    ('title_lv5', '건강 습관 칭호', 'deco', 'title', None, 5, False, 'B', True),
)
SLOTS = frozenset({'hat', 'glasses', 'ribbon', 'shoes', 'sticker', 'background', 'prop', 'outfit', 'title'})
DEFAULT_ITEMS = frozenset({'starter_sticker', 'starter_glasses', 'starter_ribbon', 'starter_hat', 'starter_shoes', 'starter_bg', 'bg_lv1'})
# 예상 일수 계산에서 빼는 일회성 출처(§6-12).
ETA_EXCLUDED = frozenset({'onboarding', 'levelup', 'refund', 'adjust', 'community_legacy'})
SKIP_MESSAGES = {'date_window': '어제 이전 날짜의 기록은 포인트 지급 대상이 아니에요.',
                 'duplicate_meal': '이 끼니는 이미 보상을 받았어요. 같은 끼니는 하루 한 번 지급돼요.',
                 'photo_reused': '이미 보상에 쓰인 사진이라 끼니 보상은 없어요.'}


class Insufficient(Exception):
    def __init__(self, needed):
        super().__init__(needed)
        self.needed = needed


# 테스트가 고정 시계를 주입할 수 있도록 현재 시각은 이 함수 하나에서만 읽는다.
def now():
    return datetime.now(timezone.utc)


def today():
    return korean_date(now())


def day_start(day):
    """KST 날짜 00:00을 UTC aware datetime으로."""
    return datetime.combine(day, dtime(0), KST).astimezone(timezone.utc)


def signup_day(user):
    return korean_date(rules.as_aware(user.created_at))


def is_new_member(user):
    """출시(REWARD_ONBOARDING_START_AT) 이후 가입자. 설정이 없으면 모두 출시 이전 회원으로 본다."""
    start = settings.reward_onboarding_start_at
    if start is None:
        return False
    return rules.as_aware(user.created_at) >= rules.as_aware(start)


def savepoint(db, work):
    """work를 SAVEPOINT에서 실행. 중복(IntegrityError)이면 None."""
    try:
        with db.begin_nested():
            return work()
    except IntegrityError:
        return None


# ---- 계정·아이템 ----

def ensure_items(db):
    existing = set(db.scalars(select(Item.id)))
    missing = [row for row in ITEMS if row[0] not in existing]
    for order, row in enumerate(ITEMS):
        if row in missing:
            item_id, name, kind, slot, price, level, sellable, stage, active = row
            savepoint(db, lambda: (db.add(Item(id=item_id, name=name, kind=kind, slot=slot, price=price,
                level_required=level, sellable=sellable, stage=stage, asset_key=item_id, active=active,
                sort_order=order)), db.flush()))
    # 코스튬 판매 전환을 기존 DB에도 반영하되 기존 소유권·구매 원장은 유지한다.
    for item_id, name, price in [('outfit_lv3', '전용 의상', 15), ('costume_lv4', '전용 코스튬', 25)]:
        item = db.get(Item, item_id)
        item.name, item.price, item.level_required, item.sellable = name, price, None, True
    # 기존 DB에도 승인된 가격을 동기화하며 과거 구매 원장은 보존한다.
    for item_id, _, kind, _, price, _, sellable, _, _ in ITEMS:
        if sellable and kind in {'deco', 'protector'} and item_id not in DEFAULT_ITEMS:
            db.get(Item, item_id).price = price
    # 기존 DB에도 기본 제공 정책을 적용하며 구매·포인트 원장은 보존한다.
    for item_id in DEFAULT_ITEMS:
        item = db.get(Item, item_id)
        item.price = None
        item.sellable = False
        if item_id == 'bg_lv1':
            item.name = '기본 배경 · 포근한 아침 방'
        elif item_id == 'starter_bg':
            item.name = '깔끔한 민트 방'


def account(db, user_id, lock=False):
    """회원 리워드 계정. 없으면 만들고 LV.1 배경을 기본 지급·장착한다."""
    row = db.get(Account, user_id, with_for_update=lock or None)
    if row:
        ensure_items(db)
        for item_id in DEFAULT_ITEMS:
            if db.get(UserItem, (user_id, item_id)) is None:
                give_item(db, user_id, item_id, 'default')
        return row
    ensure_items(db)

    def create():
        db.add(Account(user_id=user_id, level=1, balance_cache=0, xp_total_cache=0)); db.flush()
        db.add(UserItem(user_id=user_id, item_id='bg_lv1', quantity=1, acquired_via='default'))
        db.add(Equipment(user_id=user_id, slot='background', item_id='bg_lv1')); db.flush()
    savepoint(db, create)
    for item_id in DEFAULT_ITEMS - {'bg_lv1'}:
        give_item(db, user_id, item_id, 'default')
    return db.get(Account, user_id, with_for_update=lock or None, populate_existing=True)


def give_item(db, user_id, item_id, via):
    return savepoint(db, lambda: (db.add(UserItem(user_id=user_id, item_id=item_id, quantity=1, acquired_via=via)),
                                  db.flush(), True)[-1])


# ---- 잔액 ----

def live_lots(db, user_id, lock=False):
    query = (select(Lot).where(Lot.user_id == user_id, Lot.remaining > 0, Lot.expires_at > now())
             .order_by(Lot.expires_at, Lot.earned_at, Lot.id))
    return list(db.scalars(query.with_for_update() if lock else query))


def is_restricted(lot):
    return lot.source in settings.reward_excluded_sources or lot.restricted


def balance_info(db, user_id):
    lots = live_lots(db, user_id)
    total = sum(l.remaining for l in lots)
    restricted = sum(l.remaining for l in lots if is_restricted(l))
    soon = now() + timedelta(days=30)
    return {'balance': total, 'exchangeable': total - restricted, 'deco_only': restricted,
            'expiring_soon': sum(l.remaining for l in lots if rules.as_aware(l.expires_at) <= soon)}


def refresh_cache(db, user_id):
    row = account(db, user_id)
    row.balance_cache = sum(l.remaining for l in live_lots(db, user_id))
    row.xp_total_cache = db.scalar(select(func.coalesce(func.sum(Xp.amount), 0)).where(Xp.user_id == user_id))
    return row


# ---- 지급 ----

def grant_points(db, user_id, source, amount, idem, ref_type=None, ref_id=None, batch=None, restricted=False):
    """적립 1건. 금액 0이면 None, 이미 지급됐으면 False, 성공하면 lot."""
    if amount <= 0:
        return None
    stamp = now()
    lot = Lot(user_id=user_id, source=source, amount=amount, remaining=amount, earned_at=stamp,
              expires_at=stamp + timedelta(days=settings.reward_point_valid_days), ref_type=ref_type,
              ref_id=str(ref_id) if ref_id is not None else None, idem_key=idem, restricted=restricted,
              batch_id=batch.id if batch else None)
    if savepoint(db, lambda: (db.add(lot), db.flush(), True)[-1]) is None:
        log.info('reward grant skipped idem')
        return False
    settle_debts(db, user_id)
    refresh_cache(db, user_id)
    log.info('reward granted %s %d', source, amount)
    return lot


def grant_xp(db, user_id, source, amount, idem, day, ref_type=None, ref_id=None, batch=None, ranking=True):
    if amount == 0:
        return None
    event = Xp(user_id=user_id, source=source, amount=amount, counts_for_ranking=ranking, event_date=day,
               ref_type=ref_type, ref_id=str(ref_id) if ref_id is not None else None, idem_key=idem,
               batch_id=batch.id if batch else None)
    if savepoint(db, lambda: (db.add(event), db.flush(), True)[-1]) is None:
        return False
    refresh_cache(db, user_id)
    return event


def grant_capped_xp(db, user_id, source, amount, cap, idem, day, ref_type=None, ref_id=None):
    """일 상한이 있는 XP(커뮤니티 반응). 상한까지만 지급한다."""
    used = db.scalar(select(func.coalesce(func.sum(Xp.amount), 0)).where(
        Xp.user_id == user_id, Xp.source == source, Xp.event_date == day, Xp.amount > 0))
    give = min(amount, max(0, cap - used))
    if give <= 0:
        log.info('reward grant skipped daily_cap')
        return None
    return grant_xp(db, user_id, source, give, idem, day, ref_type, ref_id, ranking=False)


# ---- 차감 ----

def allocate(db, spend, lots, amount):
    """잠긴 lots에서 순서대로 amount만큼 배분한다. 실제 배분액을 반환."""
    left = amount
    used = []
    for lot in lots:
        if left <= 0:
            break
        take = min(lot.remaining, left)
        if take <= 0:
            continue
        lot.remaining -= take
        left -= take
        db.add(Allocation(spend_id=spend.id, lot_id=lot.id, amount=take))
        used.append((lot, take))
    return used


def expire_locked(db, user_id):
    """계정 잠금 후 호출. 유효기간 지난 lot을 expire spend로 0 처리한다(지연 처리)."""
    stamp = now()
    lots = list(db.scalars(select(Lot).where(Lot.user_id == user_id, Lot.remaining > 0, Lot.expires_at <= stamp)
                           .order_by(Lot.expires_at, Lot.earned_at, Lot.id).with_for_update()))
    total = sum(l.remaining for l in lots)
    if total:
        spend = Spend(user_id=user_id, kind='expire', amount=total, ref_type='expire')
        db.add(spend); db.flush()
        allocate(db, spend, lots, total)
        log.info('reward points expired %d', total)
    return total


def expire_lots(db, user_id):
    if db.scalar(select(func.count()).select_from(Lot).where(
            Lot.user_id == user_id, Lot.remaining > 0, Lot.expires_at <= now())):
        account(db, user_id, lock=True)
        expire_locked(db, user_id)
        refresh_cache(db, user_id)


def spend_points(db, user_id, amount, kind, ref_type, ref_id, order='restricted_first'):
    """구매 차감. 꾸미기·보호권은 교환 제외 출처(온보딩 → 커뮤니티 계열)를 먼저 쓴다(§6-9)."""
    account(db, user_id, lock=True)
    expire_locked(db, user_id)
    lots = live_lots(db, user_id, lock=True)
    if order == 'restricted_first':
        rank = lambda l: 0 if l.source == 'onboarding' else 1 if is_restricted(l) else 2
        lots = sorted(lots, key=rank)  # 안정 정렬이라 같은 순위 안에서는 만료일 순이 유지된다.
    elif order == 'exchange':
        # 실물·서비스 교환은 교환 제외 출처(온보딩·커뮤니티 계열, 그 제한을 이어받은 refund) lot을 쓰지 않는다(§2-5).
        lots = [l for l in lots if not is_restricted(l)]
    available = sum(l.remaining for l in lots)
    if available < amount:
        raise Insufficient(amount - available)
    spend = Spend(user_id=user_id, kind=kind, amount=amount, ref_type=ref_type, ref_id=ref_id)
    db.add(spend); db.flush()
    used = allocate(db, spend, lots, amount)
    refresh_cache(db, user_id)
    return spend, sum(take for lot, take in used if is_restricted(lot))


def take_for_revoke(db, user_id, amount, ref_type, ref_id, first=()):
    """회수: first lot들부터, 그다음 만료일 순으로 차감. 모자라면 reward_debts에 남긴다(잔액 음수 없음)."""
    lots = live_lots(db, user_id, lock=True)
    ordered = [l for l in first if l.remaining > 0] + [l for l in lots if l not in first]
    covered = min(amount, sum(l.remaining for l in ordered))
    if covered:
        spend = Spend(user_id=user_id, kind='revoke', amount=covered, ref_type=ref_type, ref_id=ref_id)
        db.add(spend); db.flush()
        allocate(db, spend, ordered, covered)
    if amount > covered:
        db.add(Debt(user_id=user_id, amount=amount - covered, remaining=amount - covered, reason='revoke',
                    ref_type=ref_type, ref_id=ref_id))
    refresh_cache(db, user_id)


def revoke_lot(db, user_id, idem):
    """idem으로 지급한 lot을 회수(커뮤니티 반응 취소·식단 삭제). 같은 lot은 한 번만 회수한다."""
    account(db, user_id, lock=True)
    lot = db.scalar(select(Lot).where(Lot.user_id == user_id, Lot.idem_key == idem).with_for_update())
    if lot is None:
        return 0
    done = db.scalar(select(func.count()).select_from(Spend).where(Spend.ref_type == 'lot', Spend.ref_id == lot.id))
    done = done or db.scalar(select(func.count()).select_from(Debt).where(Debt.ref_type == 'lot', Debt.ref_id == lot.id))
    if done:
        return 0
    take_for_revoke(db, user_id, lot.amount, 'lot', lot.id, first=[lot])
    log.info('reward revoked %d', lot.amount)
    return lot.amount


def settle_debts(db, user_id):
    """다음 적립 때 같은 트랜잭션에서 회수 미납분을 먼저 상계한다."""
    if not db.scalar(select(func.count()).select_from(Debt).where(Debt.user_id == user_id, Debt.remaining > 0)):
        return
    account(db, user_id, lock=True)
    for debt in db.scalars(select(Debt).where(Debt.user_id == user_id, Debt.remaining > 0)
                           .order_by(Debt.created_at, Debt.id).with_for_update()):
        lots = live_lots(db, user_id, lock=True)
        take = min(debt.remaining, sum(l.remaining for l in lots))
        if take <= 0:
            break
        spend = Spend(user_id=user_id, kind='revoke', amount=take, ref_type='debt', ref_id=debt.id)
        db.add(spend); db.flush()
        allocate(db, spend, lots, take)
        debt.remaining -= take


# ---- 식단 보상 훅 (§6-1) ----

def meal_hook(db, user, meal):
    """식단 생성 경로의 보상 훅. 식단 자체의 flush 오류는 호출 측이 기존대로 처리하고, 보상 오류는 격리한다."""
    if not settings.reward_enabled:
        return
    db.flush()
    try:
        with db.begin_nested():
            grant_for_meal(db, user, meal)
    except Exception:
        log.warning('reward grant failed')


def is_photo_meal(meal):
    return bool(meal.chat_attachment_id) or any(item.detection_log_id for item in meal.items)




def photo_hashes(db, meal):
    """식단 사진 원본의 SHA-256. 저장 비활성·파일 없음이면 검사를 건너뛴다(C6, 지급은 정상)."""
    if not storage.configured():
        log.info('photo_hash_unavailable')
        return []
    names = set(db.scalars(select(Detection.image_path).where(
        Detection.id.in_([i.detection_log_id for i in meal.items if i.detection_log_id]))))
    if meal.chat_attachment_id:
        attachment = db.get(ChatAttachment, meal.chat_attachment_id)
        if attachment:
            names.add(attachment.storage_key)
    digests = []
    for name in sorted(names):
        data = storage.get(name)
        if data is not None:
            digests.append(hashlib.sha256(data).hexdigest())
        else:
            log.info('photo_hash_unavailable')
    return digests


def meal_idem(meal_type, day):
    return f'snack:{day.isoformat()}' if meal_type == 'snack' else f'meal:{day.isoformat()}:{meal_type}'


def granted_meals(db, user_id, day):
    """그 날짜에 끼니 보상을 받은 식단 {idem: meal_id}. XP·포인트 어느 쪽이든 지급 기록이 있으면 인정."""
    keys = [meal_idem(t, day) for t in (*rules.MEAL_TYPES, 'snack')]
    found = {}
    for model in (Xp, Lot):
        for idem, ref in db.execute(select(model.idem_key, model.ref_id).where(
                model.user_id == user_id, model.idem_key.in_(keys))):
            found.setdefault(idem, ref)
    return found


def recorded_days(db, user_id, start, end):
    """'기록한 날': 보상 지급된 끼니 기록이 1개 이상인 KST 날짜."""
    return set(db.scalars(select(Xp.event_date).where(Xp.user_id == user_id, Xp.source.in_(('meal', 'snack')),
        Xp.amount > 0, Xp.event_date >= start, Xp.event_date <= end).distinct()))


def protected_days(db, user_id, start, end):
    return set(db.scalars(select(Protection.protected_date).where(Protection.user_id == user_id,
        Protection.protected_date >= start, Protection.protected_date <= end)))


def active_days(db, user_id, end, span=400):
    """연속 기록에 쓰는 날: 기록한 날 + 보호된 날 + 가입한 날(사용자 결정 2026-10-26, 가입일 = 1일째).
    미션·주간 기록 수에는 가입일을 넣지 않는다(recorded_days를 따로 쓴다)."""
    start = end - timedelta(days=span)
    days = recorded_days(db, user_id, start, end) | protected_days(db, user_id, start, end)
    owner = db.get(User, user_id)
    joined = signup_day(owner) if owner else None
    if joined and start <= joined <= end:
        days.add(joined)
    return days


def grant_for_meal(db, user, meal):
    day = today()
    batch = Batch(user_id=user.id, meal_id=meal.id)
    db.add(batch); db.flush()
    account(db, user.id)
    if not rules.in_grant_window(meal.meal_date, day):
        batch.skip_reason = 'date_window'
        log.info('reward grant skipped date_window')
        return batch
    hashes = photo_hashes(db, meal) if is_photo_meal(meal) else []
    reused = bool(hashes) and db.scalar(select(func.count()).select_from(PhotoHash).where(PhotoHash.sha256.in_(hashes)))
    if reused:
        batch.skip_reason = 'photo_reused'
        log.info('reward grant skipped photo_reused')
    else:
        idem = meal_idem(meal.meal_type, meal.meal_date)
        if meal.meal_type == 'snack':
            points, xp, source = settings.reward_snack_points, settings.reward_snack_xp, 'snack'
        else:
            points = settings.reward_meal_photo_points if is_photo_meal(meal) else settings.reward_meal_text_points
            xp, source = settings.reward_meal_xp, 'meal'
        lot = grant_points(db, user.id, 'meal', points, idem, 'meal', meal.id, batch)
        event = grant_xp(db, user.id, source, xp, idem, meal.meal_date, 'meal', meal.id, batch)
        if lot is False or event is False:
            batch.skip_reason = 'duplicate_meal'
            log.info('reward grant skipped duplicate_meal')
        else:
            for digest in hashes:
                savepoint(db, lambda: (db.add(PhotoHash(sha256=digest, user_id=user.id, meal_id=meal.id)), db.flush()))
    first_meal_onboarding(db, user, meal, batch)
    check_three_meals(db, user.id, meal.meal_date, batch)
    check_streak(db, user.id, meal.meal_date, batch)
    if meal.meal_date < day and day in recorded_days(db, user.id, day, day):
        check_streak(db, user.id, day, batch)
    check_missions(db, user, meal.meal_date, batch)
    check_level(db, user.id, batch)
    return batch


def first_meal_onboarding(db, user, meal, batch):
    """입력 경로·보상 이력과 무관하게 실제 첫 식단에만 지급한다."""
    if db.scalar(select(Meal.id).where(Meal.user_id == user.id, Meal.id != meal.id).limit(1)):
        return
    grant_points(db, user.id, 'onboarding', settings.reward_onboarding_first_meal, 'onboarding:first_meal',
                 'meal', meal.id, batch)


def check_three_meals(db, user_id, day, batch):
    granted = granted_meals(db, user_id, day)
    refs = [granted.get(meal_idem(t, day)) for t in rules.MEAL_TYPES]
    if not all(refs):
        return
    times = [rules.as_aware(t) for t in db.scalars(select(Meal.created_at).where(Meal.id.in_(refs)))]
    if not rules.three_meal_gap_ok(times):
        log.info('reward grant skipped three_meal_gap')
        return
    idem = f'three:{day.isoformat()}'
    grant_points(db, user_id, 'bonus', settings.reward_three_meals_points, idem, 'day', day.isoformat(), batch)
    grant_xp(db, user_id, 'three_meals', settings.reward_three_meals_xp, idem, day, 'day', day.isoformat(), batch)


def check_streak(db, user_id, end, batch=None):
    days = active_days(db, user_id, end)
    if end not in days:
        return
    kind = rules.streak_bonus(rules.streak_days(days, end))
    if not kind:
        return
    idem = f'{kind}:{end.isoformat()}'
    points = settings.reward_streak3_points if kind == 'streak3' else settings.reward_streak7_points
    xp = settings.reward_streak3_xp if kind == 'streak3' else settings.reward_streak7_xp
    grant_points(db, user_id, 'bonus', points, idem, 'day', end.isoformat(), batch)
    grant_xp(db, user_id, 'streak', xp, idem, end, 'day', end.isoformat(), batch)


def photo_meal_count(db, user_id, day):
    refs = [r for r in granted_meals(db, user_id, day).values() if r]
    return sum(1 for m in db.scalars(select(Meal).where(Meal.id.in_(refs))) if is_photo_meal(m))


def check_missions(db, user, day, batch):
    """§6-5 대체 미션: 오늘의(사진 2끼) · 주간(기록 5일) · 월간(기록 20일)."""
    if photo_meal_count(db, user.id, day) >= 2:
        idem = f'mission:{day.isoformat()}'
        grant_points(db, user.id, 'mission', settings.reward_daily_mission_points, idem, 'day', day.isoformat(), batch)
        grant_xp(db, user.id, 'mission', settings.reward_daily_mission_xp, idem, day, 'day', day.isoformat(), batch)
    monday = rules.week_monday(day)
    week_days = recorded_days(db, user.id, monday, monday + timedelta(days=6))
    if len(week_days) >= rules.weekly_required_days(signup_day(user), monday):
        grant_points(db, user.id, 'mission', settings.reward_weekly_mission_points,
                     f'weekly:{rules.iso_week_key(day)}', 'week', rules.iso_week_key(day), batch)
    first = day.replace(day=1)
    month_days = recorded_days(db, user.id, first, rules.month_end(day))
    if len(month_days) >= rules.monthly_required_days(signup_day(user), day):
        grant_points(db, user.id, 'mission', settings.reward_monthly_goal_points,
                     f'monthly:{rules.month_key(day)}', 'month', rules.month_key(day), batch)


# ---- 레벨 (§6-4) ----

def check_level(db, user_id, batch=None):
    """XP 합계로 레벨을 올린다(내려가지 않음). 여러 단계가 한 번에 오르면 가장 높은 레벨의 축하 창 1건만 남긴다."""
    row = refresh_cache(db, user_id)
    target = rules.level_for(row.xp_total_cache)
    if target <= row.level:
        return []
    reached = list(range(row.level + 1, target + 1))
    for level in reached:
        grant_points(db, user_id, 'levelup', rules.levelup_points(level), f'level:{level}', 'level', level, batch)
        for item_id in rules.LEVEL_ITEMS.get(level, ()):
            give_item(db, user_id, item_id, 'level')
        savepoint(db, lambda: (db.add(LevelEvent(user_id=user_id, level=level)), db.flush()))
        log.info('reward level up %d', level)
    row.level = target
    for event in db.scalars(select(LevelEvent).where(LevelEvent.user_id == user_id, LevelEvent.seen_at.is_(None),
                                                     LevelEvent.level < target)):
        event.seen_at = now()
    return reached


# ---- 회원가입·목표 온보딩 (§6-2) ----

def isolated(work, *args, conflict=None):
    """가입·목표·커뮤니티 경로의 보상 훅. 실패해도 기존 동작은 계속한다.

    기존 경로가 추가한 행의 flush 오류(중복)는 보상 오류가 아니므로 기존 처리로 돌려준다.
    conflict가 있으면 그 경로가 commit 때 내던 응답(예: 404 이미 처리된 요청)을 그대로 낸다.
    """
    if not settings.reward_enabled:
        return
    db = args[0]
    try:
        db.flush()
    except IntegrityError:
        if conflict:
            db.rollback()
            raise HTTPException(*conflict) from None
        raise
    try:
        with db.begin_nested():
            work(*args)
    except Exception:
        log.warning('reward grant failed')


def _signup(db, user):
    account(db, user.id)
    if is_new_member(user):
        grant_points(db, user.id, 'onboarding', settings.reward_onboarding_signup, 'onboarding:signup', 'user', None)


def signup_hook(db, user):
    isolated(_signup, db, user)


def _goal(db, user_id):
    grant_points(db, user_id, 'onboarding', settings.reward_onboarding_goal, 'onboarding:goal', 'profile', None)


def goal_hook(db, user_id):
    """PUT /users/me/profile 첫 저장 때만 호출된다."""
    isolated(_goal, db, user_id)


# ---- 커뮤니티 연결 (§6-7) ----

def _reaction(db, reaction_id, post_user_id, reactor_id, kind):
    # Stage A: 기존 point_transactions 지급과 같은 트랜잭션에 community lot을 미러링한다.
    for tx in db.scalars(select(PointTransaction).where(PointTransaction.reaction_id == reaction_id,
                                                        PointTransaction.amount > 0)):
        grant_points(db, tx.user_id, 'community', tx.amount, f'reaction:{reaction_id}:{tx.reason}', 'reaction', reaction_id)
    # Stage B: XP 모드에서는 반응 보상을 XP로(일 상한, 랭킹 제외).
    if settings.reward_community_xp_mode:
        day = today()
        received = (settings.reward_reaction_received_like_xp if kind == 'like'
                    else settings.reward_reaction_received_recommend_xp)
        grant_capped_xp(db, post_user_id, 'reaction_received', received, settings.reward_reaction_received_daily_cap,
                        f'reaction:{reaction_id}:received', day, 'reaction', reaction_id)
        grant_capped_xp(db, reactor_id, 'reaction_given', settings.reward_reaction_given_xp,
                        settings.reward_reaction_given_daily_cap, f'reaction:{reaction_id}:given', day, 'reaction', reaction_id)
        check_level(db, post_user_id)
        check_level(db, reactor_id)


def community_reaction(db, reaction_id, post_user_id, reactor_id, kind):
    isolated(_reaction, db, reaction_id, post_user_id, reactor_id, kind)


def _reaction_revoked(db, reaction_id):
    for lot in list(db.scalars(select(Lot).where(Lot.idem_key.like(f'reaction:{reaction_id}:%')))):
        revoke_lot(db, lot.user_id, lot.idem_key)
    for event in list(db.scalars(select(Xp).where(Xp.idem_key.like(f'reaction:{reaction_id}:%'), Xp.amount > 0))):
        grant_xp(db, event.user_id, 'revoke', -event.amount, f'revoke:{event.idem_key}', today(),
                 'reaction', reaction_id, ranking=False)


def community_reaction_revoked(db, reaction_id):
    isolated(_reaction_revoked, db, reaction_id, conflict=(404, '이미 처리된 요청입니다.'))


def post_share_lots(db, user_id, post_id):
    return list(db.scalars(select(Lot).where(
        Lot.user_id == user_id, Lot.ref_type == 'post', Lot.ref_id == post_id,
        Lot.idem_key.startswith('share:'))))


def _post_deleted(db, user_id, post_id, amount):
    account(db, user_id, lock=True)
    for lot in post_share_lots(db, user_id, post_id):
        revoke_lot(db, user_id, lot.idem_key)
    if amount <= 0:
        return
    if (db.scalar(select(func.count()).select_from(Spend).where(Spend.ref_type == 'post', Spend.ref_id == post_id))
            or db.scalar(select(func.count()).select_from(Debt).where(Debt.ref_type == 'post', Debt.ref_id == post_id))):
        return
    take_for_revoke(db, user_id, amount, 'post', post_id)


def community_post_deleted(db, user_id, post_id, amount):
    """해당 게시물 공유 lot과 기존 반응 포인트를 각각 한 번만 회수한다."""
    isolated(_post_deleted, db, user_id, post_id, amount, conflict=(404, '이미 처리된 요청입니다.'))


def _share(db, user_id, post_id):
    if not settings.reward_community_xp_mode:
        return
    day = today()
    grant_points(db, user_id, 'community', settings.reward_share_points, f'share:{day.isoformat()}', 'post', post_id)
    grant_xp(db, user_id, 'share', settings.reward_share_xp, f'share:{day.isoformat()}', day, 'post', post_id, ranking=False)
    check_level(db, user_id)


def community_share(db, user_id, post_id):
    isolated(_share, db, user_id, post_id)


# ---- 화면 문구 ----

def grant_label(idem, meal=None):
    head = idem.split(':')[0]
    if head == 'meal':
        meal_type = idem.split(':')[-1]
        photo = ' · 사진' if meal is not None and is_photo_meal(meal) else ''
        return f'{rules.MEAL_LABELS.get(meal_type, "")} 기록{photo}'
    if head == 'snack':
        return '간식 기록'
    if head == 'onboarding':
        return rules.GRANT_LABELS.get(idem, '온보딩')
    if head == 'level':
        return f'LV.{idem.split(":")[1]} 달성 보상'
    if head == 'revoke':
        return '반응 취소 회수'
    if head == 'demo':
        return '시연용 적립'
    if head == 'reaction':
        return '받은 반응' if idem.endswith('received') else '누른 반응' if idem.endswith('given') else '커뮤니티 반응'
    return rules.GRANT_LABELS.get(head, '보상')


def combine(lots, events, meals=None):
    """같은 idem의 포인트·XP를 한 줄로 합친다."""
    meals = meals or {}
    rows = {}
    for lot in lots:
        rows.setdefault(lot.idem_key, {'key': lot.idem_key, 'points': 0, 'xp': 0, 'ranking': True,
                                       'at': rules.as_aware(lot.earned_at)})['points'] += lot.amount
    for event in events:
        row = rows.setdefault(event.idem_key, {'key': event.idem_key, 'points': 0, 'xp': 0, 'ranking': True,
                                               'at': rules.as_aware(event.created_at)})
        row['xp'] += event.amount
        row['ranking'] = row['ranking'] and event.counts_for_ranking
    for row in rows.values():
        ref = meals.get(row['key'])
        row['label'] = grant_label(row['key'], ref)
    return sorted(rows.values(), key=lambda r: r['at'])


def public_rows(rows):
    return [{'key': r['key'], 'label': r['label'], 'points': r['points'], 'xp': r['xp'],
             'counts_for_ranking': r['ranking']} for r in rows]


def meal_status(db, user_id, day):
    granted = granted_meals(db, user_id, day)
    meals = list(db.scalars(select(Meal).where(Meal.user_id == user_id, Meal.meal_date == day)))
    result = {}
    for meal_type in (*rules.MEAL_TYPES, 'snack'):
        ref = granted.get(meal_idem(meal_type, day))
        recorded = [meal for meal in meals if meal.meal_type == meal_type]
        result[meal_type] = {'label': rules.MEAL_LABELS[meal_type], 'done': bool(recorded),
                             'rewarded': bool(ref), 'photo': any(is_photo_meal(meal) for meal in recorded)}
    return result


# ---- 조회 ----

def level_info(db, user_id, row):
    xp = row.xp_total_cache
    floor = settings.reward_levels[row.level - 1]
    nxt = rules.next_level_xp(row.level)
    info = {'level': row.level, 'level_name': rules.LEVEL_NAMES.get(row.level, ''), 'xp_total': xp,
            'level_floor_xp': floor, 'next_level': row.level + 1 if nxt is not None else None,
            'next_level_xp': nxt, 'xp_to_next': max(0, nxt - xp) if nxt is not None else 0,
            'level_progress': 1.0 if nxt is None else round(min(1, max(0, (xp - floor) / (nxt - floor))), 4)}
    return info


def eta_points(db, user, remaining, exchange_only=False):
    day = today()
    window = rules.eta_window(signup_day(user), day)
    start = day_start(day - timedelta(days=window - 1))
    lots = db.scalars(select(Lot).where(Lot.user_id == user.id, Lot.earned_at >= start))
    recent = sum(l.amount for l in lots if l.source not in ETA_EXCLUDED and not (exchange_only and is_restricted(l)))
    return rules.eta_days(remaining, recent, window)


def eta_xp(db, user, remaining):
    day = today()
    window = rules.eta_window(signup_day(user), day)
    recent = db.scalar(select(func.coalesce(func.sum(Xp.amount), 0)).where(
        Xp.user_id == user.id, Xp.event_date >= day - timedelta(days=window - 1), Xp.amount > 0, Xp.source != 'revoke'))
    return rules.eta_days(remaining, recent, window)


def owned_items(db, user_id):
    return {u.item_id: u for u in db.scalars(select(UserItem).where(UserItem.user_id == user_id)) if u.quantity > 0}


def goal_info(db, user, row, balance):
    """§6-12 목표 진행률. 아이템 목표는 총 잔액, 상품 목표는 교환 가능 포인트(Stage C 전에는 상품 없음)."""
    owned = owned_items(db, user.id)
    item, chosen = None, False
    if row.goal_ref and row.goal_ref.startswith('item:'):
        item = db.get(Item, row.goal_ref[5:])
        if item and not item.sellable:
            item = None
        chosen = item is not None
    if item is None:
        candidates = [i for i in db.scalars(select(Item).where(Item.active.is_(True), Item.sellable.is_(True),
                      Item.kind != 'protector').order_by(Item.price, Item.sort_order)) if i.id not in owned]
        item = candidates[0] if candidates else None
    product = None
    if settings.reward_exchange_active:
        from ..models_rewards import RewardProduct as Product
        from .reward_exchange import visible
        if row.goal_ref and row.goal_ref.startswith('product:'):
            product = db.get(Product, row.goal_ref[8:])
            product = product if visible(product) else None
            chosen = product is not None
            item = None if product else item
        elif item is None:
            # 목표 없음 + 살 아이템이 없으면 몰에 보이는 가장 싼 건강상품(교환 가능 포인트 기준).
            product = next((p for p in db.scalars(select(Product).where(
                Product.active.is_(True), Product.available.is_(True), Product.category == 'goods',
                Product.listed.is_(True)).order_by(Product.price, Product.sort_order)) if visible(p)), None)
    if product is not None:
        base = balance['exchangeable']
        remaining = max(0, product.price - base)
        return {'ref': f'product:{product.id}', 'chosen': chosen, 'product_id': product.id, 'name': product.name,
                'category': product.category, 'coach_id': product.coach_id, 'hero': (product.content or {}).get('hero'),
                'price': product.price, 'basis': 'exchangeable', 'base_points': base, 'remaining': remaining,
                'progress': round(min(1, base / product.price), 4), 'eta_days': eta_points(db, user, remaining, exchange_only=True)}
    if item is None:
        return None
    base = balance['balance']
    remaining = max(0, item.price - base)
    return {'ref': f'item:{item.id}', 'chosen': chosen, 'item_id': item.id, 'name': item.name, 'price': item.price,
            'basis': 'balance', 'base_points': base, 'remaining': remaining,
            'progress': round(min(1, base / item.price), 4) if item.price else 1,
            'eta_days': eta_points(db, user, remaining)}


def equipment_of(db, user_id):
    return {e.slot: e.item_id for e in db.scalars(select(Equipment).where(Equipment.user_id == user_id))}


def streak_info(db, user, row=None):
    day = today()
    days = active_days(db, user.id, day)
    yesterday = day - timedelta(days=1)
    streak = rules.current_streak(days, day)
    protectors = owned_items(db, user.id).get('protector')
    used = protections_this_month(db, user.id, day)
    can_protect = (yesterday not in days and (yesterday - timedelta(days=1)) in days
                   and bool(protectors) and used < settings.reward_protector_monthly_limit)
    resumed = rules.streak_days(days | {yesterday}, day if day in days else yesterday) if can_protect else None
    step, kind = rules.next_streak_bonus(streak)
    joined = signup_day(user)
    # 오늘 기록 여부는 실제 끼니 기록만 본다. 가입 전 날짜(어제가 가입 전)는 '놓친 날'이 아니다.
    return {'days': streak, 'today_recorded': bool(recorded_days(db, user.id, day, day)),
            'missed_yesterday': yesterday not in days and not (joined and yesterday < joined),
            'protectors': protectors.quantity if protectors else 0, 'protect_available': can_protect,
            'protected_this_month': used, 'protect_monthly_limit': settings.reward_protector_monthly_limit,
            'streak_if_protected': resumed, 'next_bonus_in_days': step,
            'next_bonus_points': settings.reward_streak3_points if kind == 'streak3' else settings.reward_streak7_points}


def protections_this_month(db, user_id, day):
    first = day.replace(day=1)
    return db.scalar(select(func.count()).select_from(Protection).where(
        Protection.user_id == user_id, Protection.created_at >= day_start(first)))


def available_actions(db, user, status, day):
    actions = []
    for meal_type in rules.MEAL_TYPES:
        if not status[meal_type]['rewarded']:
            actions.append({'id': meal_type, 'label': f'{rules.MEAL_LABELS[meal_type]} 기록',
                            'detail': f'사진 +{settings.reward_meal_photo_points}P · 사진 없이 +{settings.reward_meal_text_points}P',
                            'points': settings.reward_meal_photo_points, 'xp': settings.reward_meal_xp})
    if not status['snack']['rewarded']:
        actions.append({'id': 'snack', 'label': '간식 기록', 'detail': '하루 한 번',
                        'points': settings.reward_snack_points, 'xp': settings.reward_snack_xp})
    lots = {l.idem_key for l in db.scalars(select(Lot).where(Lot.user_id == user.id, Lot.idem_key.in_(
        [f'three:{day.isoformat()}', f'mission:{day.isoformat()}'])))}
    if f'three:{day.isoformat()}' not in lots:
        actions.append({'id': 'three', 'label': '하루 3끼 완료',
                        'detail': f'아침·점심·저녁을 {settings.reward_three_meal_min_gap_minutes // 60}시간 이상 간격으로 기록',
                        'points': settings.reward_three_meals_points, 'xp': settings.reward_three_meals_xp})
    if f'mission:{day.isoformat()}' not in lots:
        mission = rules.MISSIONS[0]
        actions.append({'id': 'mission', 'label': mission['title'], 'detail': mission['text'],
                        'progress': min(photo_meal_count(db, user.id, day), mission['goal']), 'goal': mission['goal'],
                        'points': settings.reward_daily_mission_points, 'xp': settings.reward_daily_mission_xp})
    return actions


def pending_levelup(db, user_id):
    event = db.scalar(select(LevelEvent).where(LevelEvent.user_id == user_id, LevelEvent.seen_at.is_(None))
                      .order_by(LevelEvent.level.desc()))
    if not event:
        return None
    items = [{'id': i.id, 'name': i.name, 'kind': i.kind, 'slot': i.slot}
             for i in db.scalars(select(Item).where(Item.id.in_(rules.LEVEL_ITEMS.get(event.level, ()))))]
    nxt = event.level + 1 if event.level < len(settings.reward_levels) else None
    return {'id': event.id, 'level': event.level, 'level_name': rules.LEVEL_NAMES.get(event.level, ''),
            'points': rules.levelup_points(event.level), 'items': items,
            'next': {'level': nxt, 'level_name': rules.LEVEL_NAMES.get(nxt, ''),
                     'xp': settings.reward_levels[nxt - 1], 'points': rules.levelup_points(nxt),
                     'items': [i for i in rules.LEVEL_ITEMS.get(nxt, ())]} if nxt else None}


def me(db, user):
    row = account(db, user.id)
    expire_lots(db, user.id)
    check_level(db, user.id)
    nickname = ensure_member_nickname(db, user)
    row = refresh_cache(db, user.id)
    balance = balance_info(db, user.id)
    day = today()
    start = day_start(day)
    lots = list(db.scalars(select(Lot).where(Lot.user_id == user.id, Lot.earned_at >= start)))
    events = list(db.scalars(select(Xp).where(Xp.user_id == user.id, Xp.event_date == day, Xp.amount > 0)))
    meals = {m.id: m for m in db.scalars(select(Meal).where(Meal.id.in_([l.ref_id for l in lots if l.ref_type == 'meal'])))}
    rows = combine(lots, events, {l.idem_key: meals.get(l.ref_id) for l in lots})
    status = meal_status(db, user.id, day)
    result = {**balance, 'today_points': sum(l.amount for l in lots), 'today_xp': sum(e.amount for e in events),
              'today_items': public_rows(rows), 'today_meals': status,
              'actions': available_actions(db, user, status, day), 'goal': goal_info(db, user, row, balance),
              'equipment': equipment_of(db, user.id), 'nickname': nickname_json(db, user, nickname),
              'nickname_prompt': nickname_prompt(user, nickname),
              # Stage B
              **level_info(db, user.id, row), 'streak': streak_info(db, user),
              'pending_levelup': pending_levelup(db, user.id)}
    result['xp_eta_days'] = eta_xp(db, user, result['xp_to_next']) if result['next_level_xp'] else None
    result['earn_rules'] = earn_rules()
    if settings.reward_exchange_active:
        # Stage C: 플래그가 켜졌을 때만 교환 조건을 넣는다(꺼진 기능의 필드는 응답에 넣지 않음).
        from .reward_exchange import conditions
        result['exchange'] = conditions(db, user)
    db.commit()
    return result


def earn_rules():
    """화면의 '포인트 모으는 법'. 수치를 하드코딩하지 않고 현재 설정값으로 만든다(리워드몰 v1.3 §3-2)."""
    rows = [('meal_photo', '사진으로 식단 기록', settings.reward_meal_photo_points, '끼니당 1회'),
            ('meal_text', '사진 없이 식단 기록', settings.reward_meal_text_points, '끼니당 1회'),
            ('snack', '간식 기록', settings.reward_snack_points, '하루 1회'),
            ('three_meals', '하루 3끼 기록 완료', settings.reward_three_meals_points,
             f'끼니 사이 {settings.reward_three_meal_min_gap_minutes // 60}시간 이상'),
            ('daily_mission', '오늘의 미션 완료', settings.reward_daily_mission_points, '하루 1회'),
            ('streak3', '3일 연속 기록', settings.reward_streak3_points, '7일마다 반복'),
            ('streak7', '7일 연속 기록', settings.reward_streak7_points, '7일마다 반복')]
    return [{'id': key, 'label': label, 'points': points, 'condition': condition} for key, label, points, condition in rows if points > 0]


def target_date(lot):
    """idem 키의 날짜가 적립일(KST)과 다르면 그 날짜가 정산 대상일이다(예: 전날 기록이 오늘 정산)."""
    for part in lot.idem_key.split(':'):
        try:
            day = date.fromisoformat(part)
        except ValueError:
            continue
        return day.isoformat() if day != korean_date(rules.as_aware(lot.earned_at)) else None
    return None


def grants(db, user, meal_id):
    meal = db.get(Meal, meal_id)
    if meal is None or meal.user_id != user.id:
        raise HTTPException(404, '식단을 찾을 수 없습니다.')
    batch = db.scalar(select(Batch).where(Batch.meal_id == meal.id, Batch.user_id == user.id))
    lots = list(db.scalars(select(Lot).where(Lot.batch_id == batch.id))) if batch else []
    events = list(db.scalars(select(Xp).where(Xp.batch_id == batch.id))) if batch else []
    rows = combine(lots, events, {l.idem_key: meal for l in lots if l.ref_id == meal.id})
    row = refresh_cache(db, user.id)
    reason = batch.skip_reason if batch else None
    has_meal_grant = any(r['key'].startswith(('meal:', 'snack:')) for r in rows)
    return {'meal_id': meal.id, 'meal_date': meal.meal_date.isoformat(), 'meal_type': meal.meal_type,
            'photo': is_photo_meal(meal), 'items': public_rows(rows),
            'total_points': sum(r['points'] for r in rows), 'total_xp': sum(r['xp'] for r in rows),
            'skip_reason': None if has_meal_grant else reason,
            'skip_message': None if has_meal_grant else SKIP_MESSAGES.get(reason),
            'photo_points': settings.reward_meal_photo_points, 'text_points': settings.reward_meal_text_points,
            'today_meals': meal_status(db, user.id, meal.meal_date), 'balance': balance_info(db, user.id)['balance'],
            'first_meal': any(r['key'] == 'onboarding:first_meal' for r in rows),
            **level_info(db, user.id, row)}


def spend_label(db, spend, names, products):
    if spend.kind == 'item':
        return f'{names.get(spend.ref_id, "아이템")} 구매'
    if spend.kind == 'exchange':
        return f'{products.get(spend.ref_id, "건강상품")} 교환 신청'
    if spend.kind == 'coach_pass':
        from .reward_coaching import spend_label as coach_label
        return coach_label(db, spend)
    return {'expire': '유효기간 만료', 'revoke': '포인트 회수'}.get(spend.kind, spend.kind)


def ledger(db, user, cursor=None, limit=30, kind=None):
    """적립·사용 내역. 커서는 마지막 줄의 '시각|ID'. kind: earn | spend(사용·회수 모두) | None."""
    before = None
    if cursor:
        try:
            stamp, ident = cursor.split('|', 1)
            before = (datetime.fromisoformat(stamp), ident)
        except ValueError:
            raise HTTPException(422, '입력값을 확인하세요.')
    rows = []
    for lot in db.scalars(select(Lot).where(Lot.user_id == user.id).order_by(Lot.earned_at.desc()).limit(500)):
        rows.append({'id': lot.id, 'type': 'earn', 'kind': 'earn', 'source': lot.source, 'label': grant_label(lot.idem_key),
                     'amount': lot.amount, 'at': rules.as_aware(lot.earned_at),
                     'expires_at': rules.as_aware(lot.expires_at), 'target_date': target_date(lot)})
    names = {i.id: i.name for i in db.scalars(select(Item))}
    from ..models_rewards import RewardProduct as Product
    products = {p.id: p.name for p in db.scalars(select(Product))}
    for spend in db.scalars(select(Spend).where(Spend.user_id == user.id).order_by(Spend.created_at.desc()).limit(500)):
        rows.append({'id': spend.id, 'type': spend.kind, 'kind': 'revoke' if spend.kind in ('revoke', 'expire') else 'spend',
                     'source': spend.kind, 'label': spend_label(db, spend, names, products),
                     'amount': -spend.amount, 'at': rules.as_aware(spend.created_at), 'expires_at': None, 'target_date': None})
    rows.sort(key=lambda r: (r['at'], r['id']), reverse=True)
    month_start = day_start(today().replace(day=1))
    summary = {'balance': balance_info(db, user.id)['balance'], 'expiring_soon': balance_info(db, user.id)['expiring_soon'],
               'month_earned': sum(r['amount'] for r in rows if r['kind'] == 'earn' and r['at'] >= month_start),
               'month_spent': -sum(r['amount'] for r in rows if r['kind'] != 'earn' and r['at'] >= month_start),
               'month': today().month}
    if kind == 'earn':
        rows = [r for r in rows if r['kind'] == 'earn']
    elif kind == 'spend':
        rows = [r for r in rows if r['kind'] != 'earn']
    if before:
        rows = [r for r in rows if (r['at'], r['id']) < (rules.as_aware(before[0]), before[1])]
    page = rows[:limit]
    nxt = f'{page[-1]["at"].isoformat()}|{page[-1]["id"]}' if len(rows) > limit else None
    return {'items': page, 'next_cursor': nxt, 'summary': summary}


def items_view(db, user):
    row = account(db, user.id)
    db.flush()
    owned = owned_items(db, user.id)
    equipped = equipment_of(db, user.id)
    balance = balance_info(db, user.id)['balance']
    result = []
    for item in db.scalars(select(Item).where(Item.active.is_(True)).order_by(Item.sort_order)):
        mine = owned.get(item.id)
        lock = None
        if not item.sellable:
            lock = None if mine else f'LV.{item.level_required}에서 열려요.'
        elif item.level_required and row.level < item.level_required:
            lock = f'LV.{item.level_required}에서 열려요.'
        shortfall = max(0, (item.price or 0) - balance) if item.sellable else None
        result.append({'id': item.id, 'name': item.name, 'kind': item.kind, 'slot': item.slot, 'price': item.price,
            'level_required': item.level_required, 'sellable': item.sellable, 'stage': item.stage,
            'default_provided': item.id in DEFAULT_ITEMS,
            'asset_key': item.asset_key, 'owned': bool(mine), 'quantity': mine.quantity if mine else 0,
            'equipped': equipped.get(item.slot) == item.id,
            'purchasable': item.sellable and lock is None and (not mine or item.kind == 'protector') and shortfall == 0,
            'shortfall': shortfall, 'lock_reason': lock,
            'eta_days': eta_points(db, user, shortfall) if shortfall else None})
    db.commit()
    return {'items': result, 'balance': balance, 'level': row.level}


def purchase(db, user, item_id):
    item = db.get(Item, item_id)
    if item is None or not item.active:
        raise HTTPException(404, '아이템을 찾을 수 없습니다.')
    row = account(db, user.id, lock=True)
    if not item.sellable or item.price is None:
        log.info('reward purchase rejected level_item')
        raise HTTPException(403, f'LV.{item.level_required}에서 열려요.' if item.level_required else '구매할 수 없는 아이템이에요.')
    if item.level_required and row.level < item.level_required:
        log.info('reward purchase rejected level')
        raise HTTPException(403, f'LV.{item.level_required}에서 열려요.')
    mine = db.get(UserItem, (user.id, item.id))
    if mine and mine.quantity > 0 and item.kind != 'protector':
        log.info('reward purchase rejected owned')
        raise HTTPException(409, '이미 가지고 있는 아이템이에요.')
    try:
        _, restricted_used = spend_points(db, user.id, item.price, 'item', 'item', item.id)
    except Insufficient as error:
        db.rollback()
        log.info('reward purchase rejected insufficient')
        raise HTTPException(422, f'포인트가 부족해요. {error.needed}P 더 모으면 돼요.')
    if mine:
        mine.quantity += 1
    else:
        db.add(UserItem(user_id=user.id, item_id=item.id, quantity=1, acquired_via='purchase'))
    db.flush()
    balance = balance_info(db, user.id)['balance']
    db.commit()
    log.info('reward purchase %s', item.id)
    return {'item_id': item.id, 'spent': item.price, 'restricted_used': restricted_used, 'balance': balance,
            'notice': f'가입 보너스·커뮤니티 포인트 {restricted_used}P가 먼저 사용됐어요.' if restricted_used else None}


def equip(db, user, slot, item_id):
    account(db, user.id, lock=True)
    if slot not in SLOTS:
        raise HTTPException(422, '입력값을 확인하세요.')
    row = db.get(Equipment, (user.id, slot))
    if item_id is None:
        if row:
            db.delete(row)
        db.commit()
        return {'equipment': equipment_of(db, user.id)}
    item = db.get(Item, item_id)
    if item is None or item.slot != slot:
        raise HTTPException(422, '이 자리에 착용할 수 없는 아이템이에요.')
    mine = db.get(UserItem, (user.id, item_id))
    if not mine or mine.quantity <= 0:
        raise HTTPException(403, '가지고 있지 않은 아이템이에요.')
    # 운동복은 기존 prop 슬롯을 유지하되 몸통 의상은 한 벌씩만 착용한다.
    # 소유권은 보존하고 검증 성공 후 같은 트랜잭션에서 기존 옷만 벗긴다.
    other_slot = 'outfit' if item_id == 'outfit_workout' else 'prop' if slot == 'outfit' else None
    if other_slot:
        other = db.get(Equipment, (user.id, other_slot))
        if other and other.item_id in {'outfit_workout', 'outfit_lv3', 'costume_lv4', 'costume_explorer'}:
            db.delete(other)
    if row:
        row.item_id = item_id
    else:
        db.add(Equipment(user_id=user.id, slot=slot, item_id=item_id))
    db.commit()
    return {'equipment': equipment_of(db, user.id)}


def set_goal(db, user, ref):
    row = account(db, user.id, lock=True)
    if ref is None:
        row.goal_ref = None
    elif ref.startswith('item:'):
        item = db.get(Item, ref[5:])
        if not item or not item.active or not item.sellable:
            raise HTTPException(404, '목표로 정할 수 없는 리워드예요.')
        row.goal_ref = ref
    elif ref.startswith('product:') and settings.reward_exchange_active:
        from ..models_rewards import RewardProduct as Product
        from .reward_exchange import visible
        product = db.get(Product, ref[8:])
        if product is not None and product.coach_id and not settings.reward_coaching_enabled:
            raise HTTPException(400, '전문 코칭은 아직 열리지 않았어요.')
        if not visible(product) or not product.available:
            raise HTTPException(404, '목표로 정할 수 없는 리워드예요.')
        row.goal_ref = ref
    else:
        # 건강상품(product:)은 Stage C 플래그가 켜졌을 때만 고를 수 있다.
        raise HTTPException(404, '목표로 정할 수 없는 리워드예요.')
    db.commit()
    return {'goal': goal_info(db, user, row, balance_info(db, user.id))}


def protect_streak(db, user):
    """어제를 보호권으로 보호(§6-3). 수량 차감과 보호 기록을 한 트랜잭션에서, 계정 잠금 먼저."""
    account(db, user.id, lock=True)
    day = today()
    yesterday = day - timedelta(days=1)
    days = active_days(db, user.id, day)
    if yesterday in days:
        raise HTTPException(409, '어제는 이미 기록이 이어져 있어요.')
    mine = db.scalar(select(UserItem).where(UserItem.user_id == user.id, UserItem.item_id == 'protector').with_for_update())
    if not mine or mine.quantity <= 0:
        raise HTTPException(422, '보호권이 없어요. 리워드 몰에서 받을 수 있어요.')
    if protections_this_month(db, user.id, day) >= settings.reward_protector_monthly_limit:
        raise HTTPException(409, f'보호권은 한 달에 {settings.reward_protector_monthly_limit}번까지 쓸 수 있어요.')
    mine.quantity -= 1
    db.add(Protection(user_id=user.id, protected_date=yesterday, created_at=now()))
    db.flush()
    if day in days:
        check_streak(db, user.id, day)
    check_level(db, user.id)
    db.commit()
    log.info('reward streak protected')
    return {'streak': streak_info(db, user)}


def seen_levelup(db, user, event_id):
    event = db.get(LevelEvent, event_id)
    if not event or event.user_id != user.id:
        raise HTTPException(404, '레벨업 기록을 찾을 수 없습니다.')
    event.seen_at = event.seen_at or now()
    db.commit()
    return {'seen': True}


def growth(db, user):
    row = account(db, user.id)
    check_level(db, user.id)
    row = refresh_cache(db, user.id)
    day = today()
    monday = rules.week_monday(day)
    sunday = monday + timedelta(days=6)
    recorded = recorded_days(db, user.id, monday - timedelta(days=30), sunday)
    protected = protected_days(db, user.id, monday - timedelta(days=30), sunday)
    days = active_days(db, user.id, day)
    joined = signup_day(user)
    base = day if day in days else day - timedelta(days=1)
    streak = rules.streak_days(days, base)
    xp_by_day = dict(db.execute(select(Xp.event_date, func.sum(Xp.amount)).where(
        Xp.user_id == user.id, Xp.event_date >= monday, Xp.event_date <= sunday).group_by(Xp.event_date)).all())
    week = []
    for offset in range(7):
        d = monday + timedelta(days=offset)
        if d in recorded:
            state = 'recorded'
        elif d in protected:
            state = 'protected'
        elif d == joined:
            state = 'joined'
        elif joined and d < joined:
            state = 'before_join'
        elif d < day:
            state = 'missed'
        elif d == day:
            state = 'today'
        else:
            state = 'future'
        bonus = None
        if d > base and streak:
            kind = rules.streak_bonus(streak + (d - base).days)
            if kind:
                bonus = settings.reward_streak3_points if kind == 'streak3' else settings.reward_streak7_points
        elif d in days:
            kind = rules.streak_bonus(rules.streak_days(days, d))
            if kind:
                bonus = settings.reward_streak3_points if kind == 'streak3' else settings.reward_streak7_points
        week.append({'date': d.isoformat(), 'weekday': '월화수목금토일'[offset], 'state': state,
                     'xp': int(xp_by_day.get(d, 0) or 0), 'bonus_points': bonus})
    events = list(db.scalars(select(Xp).where(Xp.user_id == user.id, Xp.event_date == day).order_by(Xp.created_at)))
    roadmap = []
    for level, needed in enumerate(settings.reward_levels, start=1):
        items = [i.name for i in db.scalars(select(Item).where(Item.id.in_(rules.LEVEL_ITEMS.get(level, ()))))]
        roadmap.append({'level': level, 'name': rules.LEVEL_NAMES.get(level, ''), 'xp': needed,
                        'points': rules.levelup_points(level), 'items': items, 'reached': row.level >= level})
    info = level_info(db, user.id, row)
    db.commit()
    return {**info, 'xp_eta_days': eta_xp(db, user, info['xp_to_next']) if info['next_level_xp'] else None,
            'roadmap': roadmap, 'week': week, 'streak': streak_info(db, user),
            'today_xp': public_rows(combine([], events)), 'missions': missions_view(db, user, day)}


def missions_view(db, user, day):
    monday = rules.week_monday(day)
    week_count = len(recorded_days(db, user.id, monday, monday + timedelta(days=6)))
    month_count = len(recorded_days(db, user.id, day.replace(day=1), rules.month_end(day)))
    week_goal = rules.weekly_required_days(signup_day(user), monday)
    month_goal = rules.monthly_required_days(signup_day(user), day)
    keys = {l.idem_key for l in db.scalars(select(Lot).where(Lot.user_id == user.id, Lot.idem_key.in_([
        f'mission:{day.isoformat()}', f'weekly:{rules.iso_week_key(day)}', f'monthly:{rules.month_key(day)}'])))}
    daily, weekly, monthly = rules.MISSIONS
    return [
        {'id': 'daily', 'title': daily['title'], 'text': daily['text'], 'progress': min(photo_meal_count(db, user.id, day), 2),
         'goal': daily['goal'], 'points': settings.reward_daily_mission_points, 'xp': settings.reward_daily_mission_xp,
         'done': f'mission:{day.isoformat()}' in keys},
        {'id': 'weekly', 'title': weekly['title'], 'text': weekly['text'].format(goal=week_goal),
         'progress': min(week_count, week_goal), 'goal': week_goal, 'points': settings.reward_weekly_mission_points,
         'xp': 0, 'done': f'weekly:{rules.iso_week_key(day)}' in keys},
        {'id': 'monthly', 'title': monthly['title'], 'text': monthly['text'].format(goal=month_goal),
         'progress': min(month_count, month_goal), 'goal': month_goal, 'points': settings.reward_monthly_goal_points,
         'xp': 0, 'done': f'monthly:{rules.month_key(day)}' in keys},
    ]


def ranking(db, user):
    """§6-10 주간 랭킹: 이번 주 랭킹 대상 XP 합계, 동점 동순위. 응답은 rank·nickname·xp·is_me만."""
    monday = rules.week_monday(today())
    score = func.sum(Xp.amount)
    rows = db.execute(select(Xp.user_id, score.label('xp')).where(Xp.counts_for_ranking.is_(True),
        Xp.event_date >= monday).group_by(Xp.user_id).having(score > 0).order_by(score.desc(), Xp.user_id)).all()
    items, mine, previous, rank = [], None, None, 0
    shown = {}
    for index, row in enumerate(rows):
        if row.xp != previous:
            rank = index + 1
        previous = row.xp
        if index < settings.reward_ranking_size or row.user_id == user.id:
            shown[row.user_id] = (rank, int(row.xp))
    nicknames = {n.user_id: n.nickname for n in db.scalars(select(Nickname).where(Nickname.user_id.in_(list(shown))))}
    for user_id in shown:
        if user_id not in nicknames:
            owner = db.get(User, user_id)
            nicknames[user_id] = create_generated(db, owner).nickname
    for index, (user_id, (rank, xp)) in enumerate(shown.items()):
        entry = {'rank': rank, 'nickname': nicknames[user_id], 'xp': xp, 'is_me': user_id == user.id}
        if index < settings.reward_ranking_size:
            items.append(entry)
        if user_id == user.id:
            mine = entry
    own = db.get(Nickname, user.id) or create_generated(db, user)
    db.commit()
    return {'timezone': 'Asia/Seoul', 'week_start': monday.isoformat(), 'items': items,
            'me': mine or {'rank': None, 'nickname': own.nickname, 'xp': 0, 'is_me': True},
            'notice': '이번 주 기록 XP 기준 · 반응·공유 XP 제외 · 닉네임으로만 표시돼요'}


# ---- 닉네임 (§6-13) ----

_rate = defaultdict(deque)
_rate_lock = threading.Lock()


def rate_limit(user_id, kind, per_minute):
    """회원당 분당 호출 수 제한(프로세스 메모리). 초과 시 429."""
    stamp = time.monotonic()
    with _rate_lock:
        calls = _rate[(user_id, kind)]
        while calls and stamp - calls[0] > 60:
            calls.popleft()
        if len(calls) >= per_minute:
            raise HTTPException(429, '잠시 후 다시 시도해 주세요.')
        calls.append(stamp)


def unused_nickname(db, exclude_user=None):
    for attempt in range(6):
        value = rules.generate_nickname(digits=4 if attempt < 5 else 6)
        taken = db.scalar(select(Nickname.user_id).where(Nickname.nickname_key == rules.nickname_key(value)))
        if taken is None or taken == exclude_user:
            return value
    return rules.generate_nickname(digits=6)


def display_names(db, user_ids):
    """공개 표시 이름: 닉네임 우선, 아직 닉네임이 없는 회원만 계정 이름."""
    ids = list(set(user_ids))
    names = {u.id: u.name for u in db.scalars(select(User).where(User.id.in_(ids)))}
    names.update({n.user_id: n.nickname for n in db.scalars(select(Nickname).where(Nickname.user_id.in_(ids)))})
    return names


def create_generated(db, user):
    existing = db.get(Nickname, user.id)
    if existing:
        return existing
    for _ in range(3):
        value = unused_nickname(db)
        row = Nickname(user_id=user.id, nickname=value, nickname_key=rules.nickname_key(value), generated=True,
                       set_via='generated')
        if savepoint(db, lambda: (db.add(row), db.flush(), True)[-1]):
            log.info('reward nickname generated')
            return row
        existing = db.get(Nickname, user.id)
        if existing:
            return existing
    raise HTTPException(503, '잠시 후 다시 시도해 주세요.')


def ensure_member_nickname(db, user):
    """출시 이전 회원은 처음 /rewards/me에 올 때 자동 생성. 신규 가입자는 가입 단계에서 정한다."""
    row = db.get(Nickname, user.id)
    if row is None and not is_new_member(user):
        row = create_generated(db, user)
    return row


def nickname_prompt(user, row):
    if row is None:
        return 'signup' if is_new_member(user) else None
    if row.generated and row.prompt_dismissed_at is None:
        return 'card'
    return None


def next_change_at(row):
    # 2026-10-20: nickname changes have no waiting period.
    return None


def nickname_json(db, user, row):
    nxt = next_change_at(row)
    return {'nickname': row.nickname if row else None, 'generated': row.generated if row else None,
            'set_via': row.set_via if row else None, 'next_change_at': nxt.isoformat() if nxt else None,
            'next_change_date': korean_date(nxt).isoformat() if nxt else None,
            'free_change': row is not None and row.changed_at is None,
            'signup_required': nickname_prompt(user, row) == 'signup'}


def nickname_problem(db, user, value):
    reason = rules.nickname_problem(value, user.name, None if user.email.endswith('.invalid') else user.email)
    if reason:
        return reason, None
    row = db.get(Nickname, user.id)
    key = rules.nickname_key(value)
    if row and row.nickname_key == key:
        return None, None
    other = db.scalar(select(Nickname.user_id).where(Nickname.nickname_key == key))
    if other is not None and other != user.id:
        return 'taken', None
    nxt = next_change_at(row)
    if nxt:
        return 'cooldown', korean_date(nxt)
    return None, None


def check_nickname(db, user, value):
    rate_limit(user.id, 'check', settings.reward_nickname_check_per_min)
    reason, nxt = nickname_problem(db, user, value)
    return {'ok': reason is None, 'reason': reason,
            'message': rules.nickname_message(reason, nxt) if reason else '쓸 수 있는 닉네임이에요.'}


def suggest_nickname(db, user):
    rate_limit(user.id, 'suggest', settings.reward_nickname_suggest_per_min)
    return {'nickname': unused_nickname(db, exclude_user=user.id)}


def save_nickname(db, user, value, via):
    row = db.get(Nickname, user.id)
    if via == 'signup' and nickname_prompt(user, row) != 'signup':
        raise HTTPException(409, '이미 닉네임을 정했어요. 마이페이지에서 바꿀 수 있어요.')
    nickname = rules.normalize_nickname(value)
    key = rules.nickname_key(nickname)
    if row and row.nickname_key == key:
        return {'nickname': nickname_json(db, user, row), 'changed': False}
    reason, nxt = nickname_problem(db, user, nickname)
    if reason:
        log.info('reward nickname rejected:%s', reason)
        raise HTTPException(409 if reason in ('taken', 'cooldown') else 422, rules.nickname_message(reason, nxt))
    stamp = now()
    if row is None:
        row = Nickname(user_id=user.id, nickname=nickname, nickname_key=key, generated=False, set_via=via,
                       changed_at=None if via == 'signup' else stamp)
        db.add(row)
    else:
        row.nickname, row.nickname_key, row.generated, row.set_via = nickname, key, False, via
        row.changed_at = stamp
    try:
        db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        log.info('reward nickname rejected:taken')
        raise HTTPException(409, rules.nickname_message('taken'))
    log.info('reward nickname changed')
    return {'nickname': nickname_json(db, user, row), 'changed': True}


def dismiss_prompt(db, user):
    """안내 카드 닫기. 가입 단계를 두 번째로 닫으면 자동 생성 닉네임을 유지한다(§6-13)."""
    row = db.get(Nickname, user.id)
    if row is None:
        create_generated(db, user)
    else:
        row.prompt_dismissed_at = row.prompt_dismissed_at or now()
    db.commit()
    return {'nickname_prompt': nickname_prompt(user, db.get(Nickname, user.id))}


def admin_find_nicknames(db, query=None):
    """관리자 닉네임 검색(부적절 닉네임 초기화용). 닉네임 정규화 키 부분 일치, 최근 변경 순 최대 50명."""
    stmt = select(Nickname).order_by(Nickname.updated_at.desc()).limit(50)
    if query:
        stmt = stmt.where(Nickname.nickname_key.contains(rules.nickname_key(query)))
    return {'items': [{'user_id': n.user_id, 'nickname': n.nickname, 'generated': n.generated, 'set_via': n.set_via,
                       'changed_at': rules.as_aware(n.changed_at), 'updated_at': rules.as_aware(n.updated_at)}
                      for n in db.scalars(stmt)]}


def admin_reset_nickname(db, user_id):
    owner = db.get(User, user_id)
    if owner is None:
        raise HTTPException(404, '회원을 찾을 수 없습니다.')
    row = db.get(Nickname, user_id)
    value = unused_nickname(db)
    if row is None:
        row = Nickname(user_id=user_id, nickname=value, nickname_key=rules.nickname_key(value), generated=True,
                       set_via='admin_reset')
        db.add(row)
    else:
        row.nickname, row.nickname_key, row.generated, row.set_via, row.changed_at = (
            value, rules.nickname_key(value), True, 'admin_reset', None)
    db.commit()
    log.info('reward nickname admin_reset')
    return {'reset': True}
