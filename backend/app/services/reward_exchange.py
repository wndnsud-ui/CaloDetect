"""리워드 Stage C: 건강상품 교환 신청·취소·쿠폰함·관리자 처리(지시서 v3 §2-5, §6-11).

- REWARD_EXCHANGE_ENABLED=false이거나 월 전체 상한이 없으면 모든 교환·쿠폰 API는 404.
- 조건: 가입 14일 이후(KST 날짜) + KST 달력월 1회. 본인인증 없음.
- 교환 제외 출처(온보딩·커뮤니티 계열) lot은 교환 차감에 쓰지 않는다.
- 회원의 첫 교환은 held(운영자 확인), 월 전체 활성 교환 수는 상한까지.
- 잠금 순서: reward_accounts → reward_point_lots → reward_exchange_month_counters → reward_exchanges.
  한 회원의 교환 상태 변경(신청·취소·발급·보류·실패)은 모두 그 회원의 계정 행을 먼저 잠가 직렬화한다.
- 쿠폰 번호는 AES-GCM으로 암호화해 저장하고 본인 응답에만 복호화한다. 로그에는 상품 ID·포인트만 남긴다.
"""
import base64
import hashlib
import logging
import re
import secrets
from datetime import timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from sqlalchemy import select, func
from ..config import settings
from ..models import Meal, User
from ..models_rewards import (RewardProduct as Product, RewardExchange as Exchange, RewardExchangeMonthCounter as Counter,
    RewardPointLot as Lot, RewardPointAllocation as Allocation, RewardNickname as Nickname)
from . import rewards, reward_rules as rules

log = logging.getLogger('calodetect')
ACTIVE = ('requested', 'held', 'issued', 'used')
PENDING = ('requested', 'held')
COUPON_AAD = b'calodetect-reward-coupon-v1'
CODE_PATTERN = re.compile(r'^[0-9A-Za-z-]{4,64}$')

# 개발용 상품(가격·제휴사·이미지는 운영 확정 전 자리표시자, TBD). (id, 이름, 종류, 가격, 판매, 설명)
PRODUCTS = (
    ('energy_bar', '에너지바', 'goods', 120, True, '곡물·견과 에너지바 1개'),
    ('energy_drink', '에너지 드링크', 'goods', 150, True, '무가당 에너지 드링크 1캔'),
    ('greek_yogurt', '그릭요거트', 'goods', 180, True, '플레인 그릭요거트 1개'),
    ('protein_bar', '프로틴바', 'goods', 200, True, '단백질 20g 프로틴바 1개'),
    ('chicken_sandwich', '닭가슴살 샌드위치', 'goods', 250, True, '통밀빵 닭가슴살 샌드위치 1개'),
    ('salad_box', '샐러드 박스', 'goods', 300, True, '채소·단백질 샐러드 1팩'),
    ('ai_report', 'AI 식단 리포트', 'ai', 300, False, '준비 중이에요'),
    ('pro_coaching', '영양사 1:1 코칭', 'pro', 1000, False, '준비 중이에요'),
)
MESSAGES = {
    'account_days': '실물 교환은 가입 14일 이후에 할 수 있어요.',
    'monthly': '이번 달 교환을 이미 신청했어요. 다음 달에 다시 신청할 수 있어요.',
    'global_cap': '이번 달 교환 수량이 모두 찼어요. 다음 달에 다시 신청해 주세요.',
    'restricted': '가입 보너스와 커뮤니티 포인트는 꾸미기에만 쓸 수 있어요.',
    'issued': '발급된 쿠폰은 취소할 수 없어요.',
    'first_hold': '첫 교환은 운영자가 확인한 뒤 발급돼요.',
    'unavailable': '준비 중인 상품이에요.',
}


def require_enabled():
    if not settings.reward_exchange_active:
        raise HTTPException(404, 'Not Found')


def startup_check():
    """플래그는 켰는데 월 전체 상한(또는 암호화 키)이 없으면 시작 때 1번 경고한다(교환 API는 404)."""
    if settings.reward_exchange_enabled and not settings.reward_exchange_active:
        log.warning('reward exchange disabled: global cap not set')


def ensure_products(db):
    existing = set(db.scalars(select(Product.id)))
    for order, (product_id, name, category, price, available, description) in enumerate(PRODUCTS):
        if product_id not in existing:
            rewards.savepoint(db, lambda: (db.add(Product(id=product_id, name=name, category=category, price=price,
                available=available, partner_label='[제휴사명]', description=description, image_key=None,
                active=True, sort_order=order)), db.flush()))


# ---- 쿠폰 번호 암호화 ----

def cipher():
    return AESGCM(hashlib.sha256(b'reward-coupon:' + settings.oauth_state_secret.encode()).digest())


def seal(code):
    nonce = secrets.token_bytes(12)
    return base64.urlsafe_b64encode(nonce + cipher().encrypt(nonce, code.encode(), COUPON_AAD)).decode()


def unseal(value):
    raw = base64.urlsafe_b64decode(value)
    return cipher().decrypt(raw[:12], raw[12:], COUPON_AAD).decode()


# ---- 조건 ----

def month_now():
    return rules.month_key(rewards.today())


def account_days(user):
    return (rewards.today() - rewards.signup_day(user)).days


def monthly_used(db, user_id, month):
    return db.scalar(select(func.count()).select_from(Exchange).where(
        Exchange.user_id == user_id, Exchange.month_key == month, Exchange.status.in_(ACTIVE)))


def conditions(db, user):
    balance = rewards.balance_info(db, user.id)
    days_left = max(0, settings.reward_exchange_min_account_days - account_days(user))
    return {'exchangeable': balance['exchangeable'], 'deco_only': balance['deco_only'], 'account_days_left': days_left,
            'monthly_used': monthly_used(db, user.id, month_now()), 'monthly_limit': settings.reward_exchange_monthly_limit,
            'first_hold': settings.reward_exchange_first_hold and not has_issued(db, user.id)}


def has_issued(db, user_id):
    return bool(db.scalar(select(func.count()).select_from(Exchange).where(
        Exchange.user_id == user_id, Exchange.status.in_(('issued', 'used')))))


def products(db, user):
    require_enabled()
    ensure_products(db)
    state = conditions(db, user)
    items = []
    for product in db.scalars(select(Product).where(Product.active.is_(True)).order_by(Product.sort_order)):
        shortfall = max(0, product.price - state['exchangeable'])
        reason = None
        if not product.available:
            reason = 'unavailable'
        elif state['account_days_left']:
            reason = 'account_days'
        elif state['monthly_used'] >= state['monthly_limit']:
            reason = 'monthly'
        elif shortfall:
            reason = 'restricted' if product.price <= state['exchangeable'] + state['deco_only'] else 'insufficient'
        items.append({'id': product.id, 'name': product.name, 'category': product.category, 'price': product.price,
            'available': product.available, 'partner_label': product.partner_label, 'description': product.description,
            'image_key': product.image_key, 'shortfall': shortfall, 'eta_days': rewards.eta_points(db, user, shortfall, exchange_only=True) if shortfall else 0,
            'can_exchange': reason is None, 'reason': reason,
            'message': f'포인트가 부족해요. {shortfall}P 더 모으면 돼요.' if reason == 'insufficient' else MESSAGES.get(reason)})
    db.commit()
    return {'items': items, 'conditions': state}


# ---- 신청 ----

def lock_counter(db, month):
    rewards.savepoint(db, lambda: (db.add(Counter(month_key=month, active_count=0)), db.flush()))
    return db.scalar(select(Counter).where(Counter.month_key == month).with_for_update().execution_options(populate_existing=True))


def reject(db, reason, status=409, message=None):
    db.rollback()
    log.info('reward exchange rejected %s', reason)
    raise HTTPException(status, message or MESSAGES[reason])


def request_exchange(db, user, product_id):
    require_enabled()
    ensure_products(db)
    product = db.get(Product, product_id)
    if product is None or not product.active:
        raise HTTPException(404, '상품을 찾을 수 없습니다.')
    if not product.available:
        raise HTTPException(409, MESSAGES['unavailable'])
    rewards.account(db, user.id, lock=True)                       # 1) 계정
    if account_days(user) < settings.reward_exchange_min_account_days:
        reject(db, 'account_days', 403)
    month = month_now()
    if monthly_used(db, user.id, month) >= settings.reward_exchange_monthly_limit:
        reject(db, 'monthly')
    try:                                                         # 2) 적립 건(교환 제외 출처 빼고)
        spend, _ = rewards.spend_points(db, user.id, product.price, 'exchange', 'product', product.id, order='exchange')
    except rewards.Insufficient as error:
        total = rewards.balance_info(db, user.id)['balance']
        if total >= product.price:
            reject(db, 'insufficient', 422, MESSAGES['restricted'])
        reject(db, 'insufficient', 422, f'포인트가 부족해요. {error.needed}P 더 모으면 돼요.')
    counter = lock_counter(db, month)                            # 3) 월 전체 카운터
    if counter.active_count >= settings.reward_exchange_global_monthly_cap:
        reject(db, 'global_cap')
    counter.active_count += 1
    first = settings.reward_exchange_first_hold and not has_issued(db, user.id)
    exchange = Exchange(user_id=user.id, product_id=product.id, points=product.price, status='held' if first else 'requested',
                        first_exchange=first, requested_at=rewards.now(), month_key=month, spend_id=spend.id)
    db.add(exchange)                                             # 4) 교환
    db.commit()
    log.info('reward exchange %s %s %d first=%s', exchange.status, product.id, product.price, first)
    return {**exchange_json(db, exchange, user), 'notice': MESSAGES['first_hold'] if first else '쿠폰함에서 확인할 수 있어요.'}


# ---- 환불·상태 변경 ----

def refund(db, exchange):
    """allocation을 거꾸로 따라 lot remaining을 복원. 만료된 lot이면 출처 제한을 이어받은 새 refund lot."""
    allocations = list(db.scalars(select(Allocation).where(Allocation.spend_id == exchange.spend_id)))
    lots = {lot.id: lot for lot in db.scalars(select(Lot).where(Lot.id.in_([a.lot_id for a in allocations]))
                                                  .order_by(Lot.expires_at, Lot.earned_at, Lot.id).with_for_update())}
    stamp = rewards.now()
    for allocation in allocations:
        lot = lots[allocation.lot_id]
        if rules.as_aware(lot.expires_at) > stamp:
            lot.remaining = min(lot.amount, lot.remaining + allocation.amount)
        else:
            rewards.grant_points(db, exchange.user_id, 'refund', allocation.amount, f'refund:{exchange.id}:{lot.id}',
                                 'exchange', exchange.id, restricted=rewards.is_restricted(lot))
    rewards.refresh_cache(db, exchange.user_id)


def locked_exchange(db, exchange_id, user_id=None):
    """대상 교환의 회원 계정을 먼저 잠그고(잠금 순서) 교환 행을 최신 상태로 다시 읽는다."""
    exchange = db.get(Exchange, exchange_id)
    if exchange is None or (user_id is not None and exchange.user_id != user_id):
        raise HTTPException(404, '교환 신청을 찾을 수 없습니다.')
    rewards.account(db, exchange.user_id, lock=True)
    return exchange


def close_with_refund(db, exchange, status):
    refund(db, exchange)
    counter = lock_counter(db, exchange.month_key)
    counter.active_count = max(0, counter.active_count - 1)
    row = db.scalar(select(Exchange).where(Exchange.id == exchange.id).with_for_update().execution_options(populate_existing=True))
    if row.status not in PENDING:
        db.rollback()
        raise HTTPException(409, MESSAGES['issued'])
    row.status, row.closed_at = status, rewards.now()
    db.commit()
    log.info('reward exchange %s %s %d first=%s', status, row.product_id, row.points, row.first_exchange)
    return row


def cancel(db, user, exchange_id):
    require_enabled()
    exchange = locked_exchange(db, exchange_id, user.id)
    db.refresh(exchange)
    if exchange.status not in PENDING:
        db.rollback()
        raise HTTPException(409, MESSAGES['issued'] if exchange.status in ('issued', 'used') else '이미 처리된 신청이에요.')
    row = close_with_refund(db, exchange, 'canceled')
    return {**exchange_json(db, row, user), 'notice': f'{row.points}P를 돌려드렸어요. 이번 달에 다시 신청할 수 있어요.'}


def mark_used(db, user, exchange_id):
    require_enabled()
    exchange = locked_exchange(db, exchange_id, user.id)
    db.refresh(exchange)
    if exchange.status != 'issued':
        db.rollback()
        raise HTTPException(409, '발급된 쿠폰만 사용 표시할 수 있어요.')
    exchange.status, exchange.used_marked_at = 'used', rewards.now()
    db.commit()
    log.info('reward exchange used %s %d first=%s', exchange.product_id, exchange.points, exchange.first_exchange)
    return exchange_json(db, exchange, user)


# ---- 쿠폰함 ----

def coupon_state(exchange):
    if exchange.status in PENDING:
        return 'pending'
    expires = rules.as_aware(exchange.coupon_expires_at)
    if exchange.status == 'issued' and (expires is None or expires > rewards.now()):
        return 'active'
    return 'closed'


def exchange_json(db, exchange, owner=None):
    """쿠폰 번호는 소유자(owner) 본인 응답에만 넣는다."""
    product = db.get(Product, exchange.product_id)
    expires = rules.as_aware(exchange.coupon_expires_at)
    code = None
    if owner is not None and owner.id == exchange.user_id and exchange.coupon_code_enc and exchange.status in ('issued', 'used'):
        code = unseal(exchange.coupon_code_enc)
    return {'id': exchange.id, 'product_id': exchange.product_id, 'product_name': product.name if product else None,
            'partner_label': product.partner_label if product else None, 'image_key': product.image_key if product else None,
            'points': exchange.points, 'status': exchange.status, 'state': coupon_state(exchange),
            'first_exchange': exchange.first_exchange, 'requested_at': rules.as_aware(exchange.requested_at),
            'issued_at': rules.as_aware(exchange.issued_at), 'coupon_code': code, 'coupon_expires_at': expires,
            'days_left': (rewards.korean_date(expires) - rewards.today()).days if expires else None,
            'used_marked_at': rules.as_aware(exchange.used_marked_at), 'cancelable': exchange.status in PENDING}


def coupons(db, user, state=None):
    require_enabled()
    rows = list(db.scalars(select(Exchange).where(Exchange.user_id == user.id).order_by(Exchange.requested_at.desc())))
    items = [exchange_json(db, row, user) for row in rows]
    summary = {'active': sum(i['state'] == 'active' for i in items), 'pending': sum(i['state'] == 'pending' for i in items),
               'expiring_soon': sum(i['state'] == 'active' and i['days_left'] is not None and i['days_left'] <= 7 for i in items),
               'monthly_used': monthly_used(db, user.id, month_now()), 'monthly_limit': settings.reward_exchange_monthly_limit}
    return {'items': [i for i in items if state is None or i['state'] == state], 'summary': summary}


# ---- 관리자 ----

def record_summary(db, user_id):
    """판단 보조: 최근 30일 기록 일수와 사진 기록 비율(자동 차단 없음)."""
    day = rewards.today()
    start = day - timedelta(days=29)
    meals = list(db.scalars(select(Meal).where(Meal.user_id == user_id, Meal.meal_date >= start)))
    return {'recorded_days_30': len(rewards.recorded_days(db, user_id, start, day)), 'meals_30': len(meals),
            'photo_ratio_30': round(sum(rewards.is_photo_meal(m) for m in meals) / len(meals), 2) if meals else 0}


def admin_list(db, status=None):
    require_enabled()
    query = select(Exchange).order_by(Exchange.requested_at.desc()).limit(200)
    if status:
        query = query.where(Exchange.status == status)
    nicknames = {n.user_id: n.nickname for n in db.scalars(select(Nickname))}
    return {'items': [{**exchange_json(db, row), 'user_id': row.user_id, 'nickname': nicknames.get(row.user_id),
                       'signup_days': account_days(db.get(User, row.user_id)), **record_summary(db, row.user_id)}
                      for row in db.scalars(query)]}


def admin_hold(db, exchange_id):
    require_enabled()
    exchange = locked_exchange(db, exchange_id)
    db.refresh(exchange)
    if exchange.status != 'requested':
        db.rollback()
        raise HTTPException(409, '대기 중인 신청만 보류할 수 있어요.')
    exchange.status = 'held'
    db.commit()
    log.info('reward exchange held %s %d first=%s', exchange.product_id, exchange.points, exchange.first_exchange)
    return exchange_json(db, exchange)


def admin_issue(db, exchange_id, code, expires_at):
    require_enabled()
    code = (code or '').strip()
    if not CODE_PATTERN.match(code):
        raise HTTPException(422, '쿠폰 번호는 영문·숫자·-로 4~64자예요.')
    if rules.as_aware(expires_at) <= rewards.now():
        raise HTTPException(422, '쿠폰 유효기간은 지금 이후여야 해요.')
    exchange = locked_exchange(db, exchange_id)
    db.refresh(exchange)
    if exchange.status not in PENDING:
        db.rollback()
        raise HTTPException(409, '대기·보류 중인 신청만 발급할 수 있어요.')
    exchange.status, exchange.issued_at = 'issued', rewards.now()
    exchange.coupon_code_enc, exchange.coupon_expires_at = seal(code), expires_at
    db.commit()
    log.info('reward exchange issued %s %d first=%s', exchange.product_id, exchange.points, exchange.first_exchange)
    return exchange_json(db, exchange)


def admin_fail(db, exchange_id):
    require_enabled()
    exchange = locked_exchange(db, exchange_id)
    db.refresh(exchange)
    if exchange.status not in PENDING:
        db.rollback()
        raise HTTPException(409, '대기·보류 중인 신청만 실패 처리할 수 있어요.')
    return exchange_json(db, close_with_refund(db, exchange, 'failed'))
