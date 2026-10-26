"""리워드 Stage C: 건강상품 교환 신청·취소·쿠폰함·관리자 처리(지시서 v3 §2-5, §6-11).

- REWARD_EXCHANGE_ENABLED=false이거나 월 전체 상한이 없으면 모든 교환·쿠폰 API는 404.
- 조건: 가입 14일 이후(KST 날짜) + KST 달력월 1회. 본인인증 없음.
- 교환 제외 출처(온보딩·커뮤니티 계열) lot은 교환 차감에 쓰지 않는다.
- 회원의 첫 교환은 held(운영자 확인), 월 전체 활성 교환 수는 상한까지.
- 잠금 순서: reward_accounts → reward_point_lots → reward_exchange_month_counters → reward_exchanges.
  한 회원의 교환 상태 변경(신청·취소·발급·보류·실패)은 모두 그 회원의 계정 행을 먼저 잠가 직렬화한다.
- 쿠폰 번호는 AES-GCM으로 암호화해 저장하고 본인 응답에만 복호화한다. 로그에는 상품 ID·포인트만 남긴다.
- 리워드몰 v1.3(M1·M3): 상품 상세·옵션·수량(차감 = 단가 × 수량, 월 1회는 교환 1건 기준), 프로모션 슬라이더,
  콜라보 기획전(REWARD_COLLAB_DEMO_ENABLED, 기본 꺼짐 — 꺼지면 콜라보 상품은 어디에도 내려가지 않음).
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
from . import rewards, reward_rules as rules, reward_catalog as catalog

log = logging.getLogger('calodetect')
ACTIVE = ('requested', 'held', 'issued', 'used')
PENDING = ('requested', 'held')
COUPON_AAD = b'calodetect-reward-coupon-v1'
CODE_PATTERN = re.compile(r'^[0-9A-Za-z-]{4,64}$')

MESSAGES = {
    'account_days': '실물 교환은 가입 14일 이후에 할 수 있어요.',
    'monthly': '이번 달 교환을 이미 신청했어요. 다음 달에 다시 신청할 수 있어요.',
    'global_cap': '이번 달 교환 수량이 모두 찼어요. 다음 달에 다시 신청해 주세요.',
    'restricted': '가입 보너스와 커뮤니티 포인트는 꾸미기에만 쓸 수 있어요.',
    'issued': '발급된 쿠폰은 취소할 수 없어요.',
    'first_hold': '첫 교환은 운영자가 확인한 뒤 발급돼요.',
    'unavailable': '준비 중인 상품이에요.',
}
CLOSED_REASON = {'used': 'used', 'canceled': 'canceled', 'failed': 'failed', 'issued': 'expired'}


def require_enabled():
    if not settings.reward_exchange_active:
        raise HTTPException(404, 'Not Found')


def startup_check():
    """플래그는 켰는데 월 전체 상한(또는 암호화 키)이 없으면 시작 때 1번 경고한다(교환 API는 404)."""
    if settings.reward_exchange_enabled and not settings.reward_exchange_active:
        log.warning('reward exchange disabled: global cap not set')


def ensure_products(db):
    """없으면 추가, 있으면 이름·하위분류·옵션·max_qty·listed·collab_brand·content만 갱신한다(§5-3).
    기존 행의 price·available·active는 덮어쓰지 않는다(운영자 변경 보호). 비활성 전환은 migration 20261022_01이 1회 처리한다."""
    rows = {p.id: p for p in db.scalars(select(Product))}
    for order, (product_id, name, category, price, available, description, sub, won, options, max_qty, listed, brand,
                content) in enumerate(catalog.PRODUCTS):
        row = rows.get(product_id)
        if row is None:
            rewards.savepoint(db, lambda: (db.add(Product(
                id=product_id, name=name, category=category, price=price, available=available, partner_label='[제휴사명]',
                description=description, image_key=None, active=product_id not in catalog.RETIRED, sort_order=order,
                subcategory=sub, list_price_won=won, options=list(options), max_qty=max_qty, listed=listed,
                collab_brand=brand, content=dict(content), is_mock=True)), db.flush()))
        elif (row.name, row.subcategory, row.options, row.max_qty, row.listed, row.collab_brand, row.content,
              row.list_price_won) != (name, sub, list(options), max_qty, listed, brand, dict(content), won):
            row.name, row.subcategory, row.options, row.max_qty = name, sub, list(options), max_qty
            row.listed, row.collab_brand, row.content, row.list_price_won = listed, brand, dict(content), won
    from .reward_coaching import ensure_coaches
    ensure_coaches(db)
    base = len(catalog.PRODUCTS)
    for offset, (product_id, coach_id, name) in enumerate(catalog.COACH_PRODUCTS):
        if product_id not in rows:
            rewards.savepoint(db, lambda: (db.add(Product(
                id=product_id, name=name, category='pro', price=catalog.COACH_PRICE, available=True,
                partner_label='[코치 채널]', description='7회 코칭 이용권', image_key=None, active=True,
                sort_order=base + offset, listed=True, coach_id=coach_id, options=[], max_qty=1, content={},
                is_mock=True)), db.flush()))


def visible(product):
    """서버에서 거르는 노출 규칙: 비활성·콜라보(기획전 플래그 off)·코칭(코칭 플래그 off) 상품은 어디에도 내려가지 않는다."""
    if product is None or not product.active:
        return False
    if product.collab_brand and not settings.reward_collab_demo_enabled:
        return False
    if product.coach_id and not settings.reward_coaching_enabled:
        return False
    return True


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


def goal_product_id(db, user_id):
    row = db.get(rewards.Account, user_id)
    return row.goal_ref[8:] if row and row.goal_ref and row.goal_ref.startswith('product:') else None


def availability(db, user, product, state, quantity=1):
    """교환 가능 여부·사유·부족분·예상 일수(서버 계산). 화면은 이 값만 쓴다."""
    total = product.price * quantity
    shortfall = max(0, total - state['exchangeable'])
    reason = None
    if not product.available:
        reason = 'unavailable'
    elif product.coach_id:
        # 코칭 이용권: 가입 14일·월 1회·월 상한을 적용하지 않는다(§6-4).
        reason = 'insufficient' if shortfall else None
    elif state['account_days_left']:
        reason = 'account_days'
    elif state['monthly_used'] >= state['monthly_limit']:
        reason = 'monthly'
    elif shortfall:
        reason = 'restricted' if total <= state['exchangeable'] + state['deco_only'] else 'insufficient'
    return {'shortfall': shortfall,
            'eta_days': rewards.eta_points(db, user, shortfall, exchange_only=True) if shortfall else 0,
            'can_exchange': reason is None, 'reason': reason,
            'message': f'포인트가 부족해요. {shortfall}P 더 모으면 돼요.' if reason == 'insufficient' else MESSAGES.get(reason)}


def card(db, user, product, state, goal_id):
    content = product.content or {}
    return {'id': product.id, 'name': product.name, 'category': product.category, 'price': product.price,
            'available': product.available, 'partner_label': product.partner_label, 'description': product.description,
            'image_key': product.image_key, 'subcategory': product.subcategory, 'list_price_won': product.list_price_won,
            'options': list(product.options or []), 'max_qty': product.max_qty, 'listed': product.listed,
            'collab_brand': product.collab_brand, 'coach_id': product.coach_id, 'is_mock': product.is_mock,
            'tags': content.get('tags', []), 'hero': content.get('hero'), 'line': content.get('line'),
            'is_goal': goal_id == product.id, **availability(db, user, product, state)}


def products(db, user, listed=True):
    require_enabled()
    ensure_products(db)
    state = conditions(db, user)
    goal_id = goal_product_id(db, user.id)
    query = select(Product).where(Product.active.is_(True)).order_by(Product.sort_order)
    items = [card(db, user, p, state, goal_id) for p in db.scalars(query) if visible(p) and (not listed or p.listed)]
    db.commit()
    return {'items': items, 'conditions': state}


def product_detail(db, user, product_id):
    """상품 상세 1건: 카드 필드 + content 전체 + related(카드 요약) + 교환 가능 여부(§6-1)."""
    require_enabled()
    ensure_products(db)
    product = db.get(Product, product_id)
    if not visible(product) or product.coach_id:
        raise HTTPException(404, '상품을 찾을 수 없습니다.')
    state = conditions(db, user)
    goal_id = goal_product_id(db, user.id)
    related = [db.get(Product, rid) for rid in (product.content or {}).get('related_ids', []) if rid != product.id]
    result = {**card(db, user, product, state, goal_id), 'content': product.content or {},
              'related': [card(db, user, r, state, goal_id) for r in related if visible(r)], 'conditions': state}
    db.commit()
    return result


def promotions(db, user):
    """프로모션 슬라이더 카드(M3). 포인트 칩은 사용자 기준으로 서버가 만든다. 기획전 플래그 off면 콜라보 카드는 뺀다."""
    require_enabled()
    ensure_products(db)
    state = conditions(db, user)
    collab_items = [p for p in db.scalars(select(Product).where(Product.active.is_(True), Product.collab_brand.is_not(None)))
                    if visible(p)]
    slides = []
    for promo in catalog.PROMOTIONS:
        if promo['target'] == 'collab':
            if collab_items:
                slides.append({**promo, 'product_id': None, 'chip': f'{min(p.price for p in collab_items):,}P부터 교환'})
            continue
        product = db.get(Product, promo['target'])
        if not visible(product):
            continue
        left = max(0, product.price - state['exchangeable'])
        slides.append({**promo, 'product_id': product.id, 'image': (product.content or {}).get('hero'),
                       'chip': f'{product.price:,}P · ' + ('지금 교환 가능' if not left else f'{left:,}P 남음')})
    db.commit()
    return {'items': slides}


def public_promotions(db):
    """공개 홈페이지 슬라이더(사용자 결정 2026-10-26). 회원 슬라이더와 같은 카드(콜라보는 기획전 플래그가 켜졌을 때만),
    가격은 회원별 잔액 없이 고정 문구. 교환 기능이 꺼져 있으면 빈 목록(홈은 기존 안내 표시).
    익명 요청이라 DB를 쓰지 않는다(ensure_products 미호출)."""
    if not settings.reward_exchange_active:
        return {'items': []}
    collab_items = [p for p in db.scalars(select(Product).where(Product.active.is_(True), Product.collab_brand.is_not(None)))
                    if visible(p)]
    slides = []
    for promo in catalog.PROMOTIONS:
        if promo['target'] == 'collab':
            if collab_items:
                slides.append({**promo, 'product_id': None, 'chip': f'{min(p.price for p in collab_items):,}P부터 교환'})
            continue
        product = db.get(Product, promo['target'])
        if not visible(product):
            continue
        slides.append({**promo, 'product_id': product.id, 'image': (product.content or {}).get('hero'),
                       'chip': f'{product.price:,}P로 교환'})
    return {'items': slides}


def collab(db, user):
    """콜라보 기획전(§7-6, M3). 플래그 off면 404. 전체 라인업은 교환 가능한 상품만(정과 2종 제외)."""
    require_enabled()
    if not settings.reward_collab_demo_enabled:
        raise HTTPException(404, 'Not Found')
    ensure_products(db)
    state = conditions(db, user)
    goal_id = goal_product_id(db, user.id)

    def find(pid):
        product = db.get(Product, pid)
        return card(db, user, product, state, goal_id) if visible(product) else None
    picks = [{**item, 'pick_desc': desc, 'pick_image': catalog.COLLAB_PICK_IMAGES.get(item['id'])}
             for item, desc in ((find(pid), desc) for pid, desc in catalog.COLLAB_PICKS) if item]
    lineup = [{**item, 'lineup_image': catalog.COLLAB_LINEUP_IMAGES.get(item['id'], item['hero'])}
              for item in (find(pid) for pid in catalog.COLLAB_LINEUP) if item]
    db.commit()
    return {'brand': catalog.COLLAB, 'picks': picks, 'lineup': lineup, 'conditions': state, 'images': catalog.COLLAB_IMAGES,
            'notice': '시연용 가상 기획전입니다. 실제 판매·제휴와 관계없어요.'}


# ---- 신청 ----

def lock_counter(db, month):
    rewards.savepoint(db, lambda: (db.add(Counter(month_key=month, active_count=0)), db.flush()))
    return db.scalar(select(Counter).where(Counter.month_key == month).with_for_update().execution_options(populate_existing=True))


def reject(db, reason, status=409, message=None):
    db.rollback()
    log.info('reward exchange rejected %s', reason)
    raise HTTPException(status, message or MESSAGES[reason])


def request_exchange(db, user, product_id, option=None, quantity=1):
    require_enabled()
    ensure_products(db)
    product = db.get(Product, product_id)
    if not visible(product) or product.coach_id:                 # 콜라보(기획전 off)·코칭 이용권은 이 경로에서 404
        raise HTTPException(404, '상품을 찾을 수 없습니다.')
    options = list(product.options or [])                        # 0) 입력 검사(잠금 전, §6-2)
    if options and option not in options:
        raise HTTPException(422, {'code': 'OPTION_REQUIRED', 'message': '맛을 선택해 주세요.'})
    if quantity < 1 or quantity > product.max_qty:
        raise HTTPException(422, {'code': 'QTY_LIMIT_EXCEEDED', 'message': f'수량은 1~{product.max_qty}개까지 고를 수 있어요.'})
    if not product.available:
        raise HTTPException(409, MESSAGES['unavailable'])
    total = product.price * quantity
    rewards.account(db, user.id, lock=True)                       # 1) 계정
    if account_days(user) < settings.reward_exchange_min_account_days:
        reject(db, 'account_days', 403)
    month = month_now()
    if monthly_used(db, user.id, month) >= settings.reward_exchange_monthly_limit:
        reject(db, 'monthly')
    try:                                                         # 2) 적립 건(교환 제외 출처 빼고)
        spend, _ = rewards.spend_points(db, user.id, total, 'exchange', 'product', product.id, order='exchange')
    except rewards.Insufficient as error:
        balance = rewards.balance_info(db, user.id)['balance']
        if balance >= total:
            reject(db, 'insufficient', 422, MESSAGES['restricted'])
        reject(db, 'insufficient', 422, f'포인트가 부족해요. {error.needed}P 더 모으면 돼요.')
    counter = lock_counter(db, month)                            # 3) 월 전체 카운터(수량과 무관하게 교환 1건)
    if counter.active_count >= settings.reward_exchange_global_monthly_cap:
        reject(db, 'global_cap')
    counter.active_count += 1
    first = settings.reward_exchange_first_hold and not has_issued(db, user.id)
    exchange = Exchange(user_id=user.id, product_id=product.id, points=total, status='held' if first else 'requested',
                        first_exchange=first, requested_at=rewards.now(), month_key=month, spend_id=spend.id,
                        quantity=quantity, option_label=option if options else None)
    db.add(exchange)                                             # 4) 교환
    db.commit()
    log.info('reward exchange %s %s %d qty=%d first=%s', exchange.status, product.id, total, quantity, first)
    return {**exchange_json(db, exchange, user), 'notice': MESSAGES['first_hold'] if first else '쿠폰함에서 확인할 수 있어요.'}


# ---- 환불·상태 변경 ----

def refund(db, exchange):
    refund_spend(db, exchange.user_id, exchange.spend_id, 'exchange', exchange.id)


def refund_spend(db, user_id, spend_id, ref_type, ref_id):
    """allocation을 거꾸로 따라 lot remaining을 복원. 만료된 lot이면 출처 제한을 이어받은 새 refund lot(교환·코칭 이용권 공용)."""
    allocations = list(db.scalars(select(Allocation).where(Allocation.spend_id == spend_id)))
    lots = {lot.id: lot for lot in db.scalars(select(Lot).where(Lot.id.in_([a.lot_id for a in allocations]))
                                                  .order_by(Lot.expires_at, Lot.earned_at, Lot.id).with_for_update())}
    stamp = rewards.now()
    for allocation in allocations:
        lot = lots[allocation.lot_id]
        if rules.as_aware(lot.expires_at) > stamp:
            lot.remaining = min(lot.amount, lot.remaining + allocation.amount)
        else:
            rewards.grant_points(db, user_id, 'refund', allocation.amount, f'refund:{ref_id}:{lot.id}',
                                 ref_type, ref_id, restricted=rewards.is_restricted(lot))
    rewards.refresh_cache(db, user_id)


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


def closed_reason(exchange):
    return CLOSED_REASON.get(exchange.status) if coupon_state(exchange) == 'closed' else None


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
            'used_marked_at': rules.as_aware(exchange.used_marked_at), 'cancelable': exchange.status in PENDING,
            'quantity': exchange.quantity or 1, 'option_label': exchange.option_label, 'closed_reason': closed_reason(exchange),
            'unit_points': exchange.points // (exchange.quantity or 1), 'subcategory': product.subcategory if product else None,
            'hero': (product.content or {}).get('hero') if product else None}


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
