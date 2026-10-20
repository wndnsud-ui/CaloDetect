# CaloPoint·Growth·Reward ORM 모델(리워드 지시서 v3 §5). 기존 테이블은 바꾸지 않고 새 테이블만 둔다.
# 포인트는 적립 건(lot) → 차감(spend) → 배분(allocation) 원장으로만 관리한다. 캐시는 원장에서 다시 계산할 수 있다.
# 모든 지급의 중복은 UNIQUE(user_id, idem_key)로 막는다. FK CASCADE는 쓰지 않는다.
from datetime import date, datetime
from sqlalchemy import String, Integer, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base, uid, utcnow


# 회원별 잠금 행과 캐시. 차감·구매·보호권은 항상 이 행을 먼저 FOR UPDATE로 잠근다(§6-0).
class RewardAccount(Base):
    __tablename__ = 'reward_accounts'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    balance_cache: Mapped[int] = mapped_column(Integer, default=0)
    xp_total_cache: Mapped[int] = mapped_column(Integer, default=0)
    # 지금 레벨. 내려가지 않는다.
    level: Mapped[int] = mapped_column(Integer, default=1)
    # 목표 리워드: item:<id> / product:<id>
    goal_ref: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# 지급 결과 묶음. 식단 저장 1회 = 1묶음이며 기록 직후 보상 패널이 조회한다(§6-1).
class RewardGrantBatch(Base):
    __tablename__ = 'reward_grant_batches'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    meal_id: Mapped[str | None] = mapped_column(ForeignKey('meals.id'), index=True)
    # 끼니 보상이 없을 때의 이유: date_window | duplicate_meal | photo_reused
    skip_reason: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# 적립 건. remaining은 0~amount, 만료일이 빠른 건부터 쓴다.
class RewardPointLot(Base):
    __tablename__ = 'reward_point_lots'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    # onboarding meal bonus mission community community_legacy levelup refund adjust
    source: Mapped[str] = mapped_column(String(24))
    amount: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ref_type: Mapped[str | None] = mapped_column(String(24))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    idem_key: Mapped[str] = mapped_column(String(120))
    # refund lot이 원래 lot의 교환 제외 출처 제한을 이어받는다(§5-3).
    restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey('reward_grant_batches.id'), index=True)
    __table_args__ = (UniqueConstraint('user_id', 'idem_key', name='uq_reward_lots_idem'),
                      CheckConstraint('amount > 0', name='ck_reward_lots_amount'),
                      CheckConstraint('remaining >= 0 AND remaining <= amount', name='ck_reward_lots_remaining'),
                      Index('ix_reward_lots_user_expiry', 'user_id', 'expires_at'))


# 차감 1건(item exchange expire revoke).
class RewardPointSpend(Base):
    __tablename__ = 'reward_point_spends'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    amount: Mapped[int] = mapped_column(Integer)
    ref_type: Mapped[str | None] = mapped_column(String(24))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint('amount > 0', name='ck_reward_spends_amount'),)


# 어느 적립 건에서 얼마를 썼는지. 환불은 이것을 거꾸로 따라간다.
class RewardPointAllocation(Base):
    __tablename__ = 'reward_point_allocations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    spend_id: Mapped[str] = mapped_column(ForeignKey('reward_point_spends.id'), index=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey('reward_point_lots.id'), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    __table_args__ = (CheckConstraint('amount > 0', name='ck_reward_allocations_amount'),)


# 잔액보다 큰 회수분. 다음 적립 때 같은 트랜잭션에서 먼저 상계한다. 잔액은 음수가 되지 않는다.
class RewardDebt(Base):
    __tablename__ = 'reward_debts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(16), default='revoke')
    ref_type: Mapped[str | None] = mapped_column(String(24))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint('amount > 0', name='ck_reward_debts_amount'),
                      CheckConstraint('remaining >= 0 AND remaining <= amount', name='ck_reward_debts_remaining'))


# XP 원장. 음수는 회수만. 레벨은 내려가지 않는다.
class RewardXpEvent(Base):
    __tablename__ = 'reward_xp_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    # meal snack three_meals mission balance streak share reaction_received reaction_given revoke
    source: Mapped[str] = mapped_column(String(24))
    counts_for_ranking: Mapped[bool] = mapped_column(Boolean, default=True)
    # KST 날짜. 일 상한·주간 집계 기준.
    event_date: Mapped[date] = mapped_column(Date, index=True)
    ref_type: Mapped[str | None] = mapped_column(String(24))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    idem_key: Mapped[str] = mapped_column(String(120))
    batch_id: Mapped[str | None] = mapped_column(ForeignKey('reward_grant_batches.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'idem_key', name='uq_reward_xp_idem'),)


# 아이템 카탈로그(시드). id는 slug.
class RewardItem(Base):
    __tablename__ = 'reward_items'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(16))
    slot: Mapped[str] = mapped_column(String(16))
    price: Mapped[int | None] = mapped_column(Integer)
    level_required: Mapped[int | None] = mapped_column(Integer)
    sellable: Mapped[bool] = mapped_column(Boolean, default=True)
    stage: Mapped[str] = mapped_column(String(1), default='A')
    asset_key: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class RewardUserItem(Base):
    __tablename__ = 'reward_user_items'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey('reward_items.id'), primary_key=True)
    # 보호권만 1보다 클 수 있다.
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    # purchase level default
    acquired_via: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint('quantity >= 0', name='ck_reward_user_items_quantity'),)


class RewardEquipment(Base):
    __tablename__ = 'reward_equipment'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    slot: Mapped[str] = mapped_column(String(16), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey('reward_items.id'))


# 보상에 쓰인 사진의 SHA-256. 원본 대신 해시만 저장하며 회원 구분 없이 재사용을 막는다.
class RewardPhotoHash(Base):
    __tablename__ = 'reward_photo_hashes'
    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    meal_id: Mapped[str] = mapped_column(ForeignKey('meals.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# 랭킹 공개 닉네임(§5-7). users 테이블은 건드리지 않는다.
class RewardNickname(Base):
    __tablename__ = 'reward_nicknames'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(40))
    # NFC + 소문자 + 공백 제거. 중복 검사 기준.
    nickname_key: Mapped[str] = mapped_column(String(40), unique=True)
    generated: Mapped[bool] = mapped_column(Boolean, default=True)
    # generated signup account ranking admin_reset
    set_via: Mapped[str] = mapped_column(String(16))
    # 직접 변경(account·ranking) 때만 갱신. null이면 다음 직접 변경은 주기 제한이 없다.
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prompt_dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---- Stage B ----

# 레벨업 이벤트. seen_at이 비어 있으면 프런트가 축하 창을 띄운다.
class RewardLevelEvent(Base):
    __tablename__ = 'reward_level_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    level: Mapped[int] = mapped_column(Integer)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'level', name='uq_reward_level_events'),)


# 보호권 사용 기록(월 상한 검사용).
class RewardStreakProtection(Base):
    __tablename__ = 'reward_streak_protections'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    protected_date: Mapped[date] = mapped_column(Date, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---- Stage C (REWARD_EXCHANGE_ENABLED 플래그 뒤) ----

# 건강상품·서비스 카탈로그(시드). ai·pro는 available=false("준비 중"). 이미지는 image_key로 나중에 교체한다.
class RewardProduct(Base):
    __tablename__ = 'reward_products'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    # goods ai pro
    category: Mapped[str] = mapped_column(String(16))
    price: Mapped[int] = mapped_column(Integer)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    partner_label: Mapped[str] = mapped_column(String(60), default='[제휴사명]')
    description: Mapped[str] = mapped_column(String(200), default='')
    image_key: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint('price > 0', name='ck_reward_products_price'),)


# 교환 신청 1건. 쿠폰 번호는 암호화해 저장하고 본인 응답에만 복호화해 넣는다.
class RewardExchange(Base):
    __tablename__ = 'reward_exchanges'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey('reward_products.id'))
    points: Mapped[int] = mapped_column(Integer)
    # requested held issued used canceled failed
    status: Mapped[str] = mapped_column(String(16))
    first_exchange: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coupon_code_enc: Mapped[str | None] = mapped_column(String(400))
    coupon_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # KST yyyy-mm. 월 1회·월 전체 상한 기준.
    month_key: Mapped[str] = mapped_column(String(7), index=True)
    spend_id: Mapped[str] = mapped_column(ForeignKey('reward_point_spends.id'))
    __table_args__ = (CheckConstraint("status IN ('requested','held','issued','used','canceled','failed')",
                                      name='ck_reward_exchanges_status'),
                      CheckConstraint('points > 0', name='ck_reward_exchanges_points'))


# KST 월별 활성 교환 수. 월 전체 상한 검사는 이 행을 FOR UPDATE로 잠가 처리한다.
class RewardExchangeMonthCounter(Base):
    __tablename__ = 'reward_exchange_month_counters'
    month_key: Mapped[str] = mapped_column(String(7), primary_key=True)
    active_count: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint('active_count >= 0', name='ck_reward_exchange_counter'),)
