"""CaloPoint·Growth·Reward API(리워드 지시서 v3 §9, Stage A·B). 로그인 필수, 변경 요청은 기존 CSRF 검사를 따른다.

Stage C(교환·쿠폰)는 REWARD_EXCHANGE_ENABLED와 월 전체 상한이 설정됐을 때만 동작하고, 아니면 404다.
"""
from typing import Literal
from fastapi import APIRouter, Query
from pydantic import Field
from .api import CurrentUser, Admin, DB
from .schemas import RequestModel
from .services import rewards as service, reward_exchange as exchange, reward_coaching as coaching

router = APIRouter(tags=['rewards'])


class EquipRequest(RequestModel):
    slot: str = Field(min_length=1, max_length=16)
    item_id: str | None = Field(default=None, max_length=40)


class GoalRequest(RequestModel):
    ref: str | None = Field(default=None, max_length=80)


class NicknameRequest(RequestModel):
    nickname: str = Field(min_length=1, max_length=40)
    via: Literal['signup', 'account', 'ranking']


@router.get('/rewards/me')
def me(user: CurrentUser, db: DB):
    return service.me(db, user)


@router.get('/rewards/grants')
def grants(user: CurrentUser, db: DB, meal_id: str = Query(min_length=1, max_length=36)):
    return service.grants(db, user, meal_id)


@router.get('/rewards/ledger')
def ledger(user: CurrentUser, db: DB, cursor: str | None = Query(default=None, max_length=120),
           kind: Literal['earn', 'spend'] | None = None):
    return service.ledger(db, user, cursor, kind=kind)


@router.get('/rewards/items')
def items(user: CurrentUser, db: DB):
    return service.items_view(db, user)


@router.post('/rewards/items/{item_id}/purchase')
def purchase(item_id: str, user: CurrentUser, db: DB):
    return service.purchase(db, user, item_id)


@router.put('/rewards/equipment')
def equipment(body: EquipRequest, user: CurrentUser, db: DB):
    return service.equip(db, user, body.slot, body.item_id)


# ---- Stage B ----

@router.get('/rewards/growth')
def growth(user: CurrentUser, db: DB):
    return service.growth(db, user)


@router.post('/rewards/levelups/{event_id}/seen')
def levelup_seen(event_id: str, user: CurrentUser, db: DB):
    return service.seen_levelup(db, user, event_id)


@router.post('/rewards/streak/protect')
def protect(user: CurrentUser, db: DB):
    return service.protect_streak(db, user)


@router.put('/rewards/goal')
def goal(body: GoalRequest, user: CurrentUser, db: DB):
    return service.set_goal(db, user, body.ref)


@router.get('/rewards/ranking')
def ranking(user: CurrentUser, db: DB, metric: Literal['points', 'xp'] = 'points'):
    return service.ranking(db, user, metric=metric)


# ---- 닉네임 (Stage A) ----

@router.get('/rewards/nickname')
def nickname(user: CurrentUser, db: DB):
    row = service.ensure_member_nickname(db, user)
    result = service.nickname_json(db, user, row)
    db.commit()
    return result


@router.get('/rewards/nickname/suggestion')
def nickname_suggestion(user: CurrentUser, db: DB):
    return service.suggest_nickname(db, user)


@router.get('/rewards/nickname/check')
def nickname_check(user: CurrentUser, db: DB, nickname: str = Query(max_length=40)):
    return service.check_nickname(db, user, nickname)


@router.put('/rewards/nickname')
def nickname_save(body: NicknameRequest, user: CurrentUser, db: DB):
    return service.save_nickname(db, user, body.nickname, body.via)


@router.post('/rewards/nickname/prompt/dismiss')
def nickname_dismiss(user: CurrentUser, db: DB):
    return service.dismiss_prompt(db, user)


@router.get('/admin/rewards/nicknames')
def nickname_search(admin: Admin, db: DB, q: str | None = Query(default=None, max_length=40)):
    return service.admin_find_nicknames(db, q)


@router.post('/admin/rewards/nicknames/{user_id}/reset')
def nickname_reset(user_id: int, admin: Admin, db: DB):
    return service.admin_reset_nickname(db, user_id)


# ---- Stage C: 건강상품 교환·쿠폰함 (플래그 off → 404) ----

class ExchangeRequest(RequestModel):
    product_id: str = Field(min_length=1, max_length=40)
    # 리워드몰 v1.3: 옵션 있는 상품은 option 필수, quantity는 1~max_qty(서버 검사)
    option: str | None = Field(default=None, max_length=40)
    quantity: int = Field(default=1)


@router.get('/rewards/products')
def products(user: CurrentUser, db: DB, listed: bool = True):
    return exchange.products(db, user, listed)


@router.get('/rewards/products/{product_id}')
def product_detail(product_id: str, user: CurrentUser, db: DB):
    return exchange.product_detail(db, user, product_id)


# 공개 홈페이지용(로그인 불필요). 회원 슬라이더와 같은 카드(콜라보는 기획전 플래그 on일 때), 고정 가격 문구.
@router.get('/rewards/promotions/public')
def public_promotions(db: DB):
    return exchange.public_promotions(db)


@router.get('/rewards/promotions')
def promotions(user: CurrentUser, db: DB):
    return exchange.promotions(db, user)


@router.get('/rewards/collab')
def collab(user: CurrentUser, db: DB):
    return exchange.collab(db, user)


@router.post('/rewards/exchanges', status_code=201)
def request_exchange(body: ExchangeRequest, user: CurrentUser, db: DB):
    return exchange.request_exchange(db, user, body.product_id, body.option, body.quantity)


@router.post('/rewards/exchanges/{exchange_id}/cancel')
def cancel_exchange(exchange_id: str, user: CurrentUser, db: DB):
    return exchange.cancel(db, user, exchange_id)


@router.get('/rewards/coupons')
def coupons(user: CurrentUser, db: DB, status: Literal['active', 'pending', 'closed'] | None = None):
    return exchange.coupons(db, user, status)


@router.post('/rewards/coupons/{exchange_id}/used')
def coupon_used(exchange_id: str, user: CurrentUser, db: DB):
    return exchange.mark_used(db, user, exchange_id)


# ---- 리워드몰 v1.3 M4: 전문 코칭 이용권 (REWARD_COACHING_ENABLED=false → 404) ----

class PassRequest(RequestModel):
    idem_key: str = Field(min_length=8, max_length=120)


@router.get('/rewards/coaches')
def coach_list(user: CurrentUser, db: DB, specialty: str | None = Query(default=None, max_length=20)):
    return coaching.coaches(db, user, specialty)


@router.get('/rewards/coaches/feed')
def coach_feed(user: CurrentUser, db: DB):
    return coaching.feed(db, user)


@router.get('/rewards/coaches/{coach_id}')
def coach_detail(coach_id: str, user: CurrentUser, db: DB):
    return coaching.coach_detail(db, user, coach_id)


@router.post('/rewards/coaches/{coach_id}/passes')
def coach_buy(coach_id: str, body: PassRequest, user: CurrentUser, db: DB):
    return coaching.buy(db, user, coach_id, body.idem_key)


@router.get('/rewards/coach-passes')
def coach_passes(user: CurrentUser, db: DB):
    return coaching.my_passes(db, user)


@router.get('/admin/rewards/coach-passes')
def admin_coach_passes(admin: Admin, db: DB):
    return coaching.admin_list(db)


@router.post('/admin/rewards/coach-passes/{pass_id}/refund')
def admin_coach_refund(pass_id: str, admin: Admin, db: DB):
    return coaching.admin_refund(db, pass_id)
