# 채팅 식사기록(A0) 신규 ORM 모델. 기존 모델 파일을 바꾸지 않도록 별도 파일에 둔다.
# MutationRequest는 쓰기 요청의 영속 멱등성 키이자 성공한 변경의 before/after 이력이다.
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .models import Base, uid, utcnow


# MutationRequest: mutation_requests 테이블. 성공한 쓰기만 기록하며 실패한 요청은 같은 request_id로 재시도할 수 있다.
class MutationRequest(Base):
    __tablename__ = 'mutation_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    # 요청한 회원. 멱등성 키는 회원·작업 종류 범위에서만 유일하다.
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    # 작업 종류. 예: meal_item.consumption
    operation: Mapped[str] = mapped_column(String(40))
    # 클라이언트가 만든 UUID 문자열.
    request_id: Mapped[str] = mapped_column(String(36))
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[str] = mapped_column(String(36))
    # 필드 순서·숫자 표현을 정규화한 명령 내용의 SHA-256. 같은 키에 다른 내용이면 충돌로 판정한다.
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default='succeeded')
    result_id: Mapped[str | None] = mapped_column(String(36))
    result_version: Mapped[int | None] = mapped_column(Integer)
    # 성공한 변경의 전·후 snapshot(섭취 비율·유효 배율·영양값).
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'operation', 'request_id', name='uq_mutation_requests_key'),)


# ---- A1: 대화·메시지·첨부·식사 초안 ----

# Conversation: 회원별 채팅 식사기록 대화. 저장 후 정정 대기 상태(pending_*)도 여기에 둔다.
class Conversation(Base):
    __tablename__ = 'chat_conversations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    status: Mapped[str] = mapped_column(String(16), default='active')
    # 다음 메시지 server sequence. 메시지 순서는 시간값이 아니라 이 값으로 정한다.
    next_sequence: Mapped[int] = mapped_column(Integer, default=1)
    # 저장된 식사의 섭취량 정정 확인 대기(예: {"item_id", "consumption_ratio", "version"}).
    pending_question: Mapped[str] = mapped_column(String(20), default='none')
    pending_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ChatMessage: 사용자 원문·봇 응답. 봇 카드는 당시 snapshot(payload)으로 보존해 이후 정정으로 바뀌지 않는다.
class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('chat_conversations.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    author_role: Mapped[str] = mapped_column(String(8))
    kind: Mapped[str] = mapped_column(String(20), default='text')
    text: Mapped[str] = mapped_column(String(1000), default='')
    payload: Mapped[dict | None] = mapped_column(JSON)
    # 사용자 메시지 멱등 키. 같은 키·같은 내용 재전송은 원 결과를 돌려준다.
    client_message_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default='processed')
    reply_to_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('conversation_id', 'sequence', name='uq_chat_messages_sequence'),
                      UniqueConstraint('user_id', 'conversation_id', 'client_message_id', name='uq_chat_messages_client'))


# ChatAttachment: 채팅 사진. 기존 ImageUpload를 수정하지 않고 참조한다. 분석 실패해도 사진은 보존한다.
class ChatAttachment(Base):
    __tablename__ = 'chat_attachments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('chat_conversations.id', ondelete='CASCADE'), index=True)
    message_id: Mapped[str | None] = mapped_column(String(36))
    image_upload_id: Mapped[str | None] = mapped_column(ForeignKey('image_uploads.id'))
    mime: Mapped[str] = mapped_column(String(40), default='image/jpeg')
    size: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64))
    # uploaded → analyzed | failed
    status: Mapped[str] = mapped_column(String(16), default='uploaded')
    upload_request_id: Mapped[str] = mapped_column(String(36))
    storage_key: Mapped[str] = mapped_column(String(255))
    analysis_error: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'upload_request_id', name='uq_chat_attachments_request'),)


# MealDraft: 확정 전 식사 초안. 집계·추천·관리자 QA는 읽지 않는다. 한 초안은 최대 한 Meal로 확정된다.
class MealDraft(Base):
    __tablename__ = 'meal_drafts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('chat_conversations.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    attachment_id: Mapped[str | None] = mapped_column(ForeignKey('chat_attachments.id'))
    # analyzing → needs_confirmation → confirmed | abandoned
    status: Mapped[str] = mapped_column(String(24), default='analyzing')
    version: Mapped[int] = mapped_column(Integer, default=1)
    meal_date: Mapped[date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(16))
    pending_question: Mapped[str] = mapped_column(String(20), default='none')
    pending_target_id: Mapped[str | None] = mapped_column(String(36))
    analysis_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_meal_id: Mapped[str | None] = mapped_column(ForeignKey('meals.id'), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    items: Mapped[list['DraftItem']] = relationship(cascade='all, delete-orphan', lazy='selectin',
                                                    order_by='DraftItem.position')
    __table_args__ = (CheckConstraint("meal_type IN ('breakfast','lunch','dinner','snack')", name='ck_meal_drafts_type'),)


# DraftItem: 초안 음식. 탐지 ID와 최종 음식 ID를 둘 다 보존한다(R12). 채팅 기록의 기준 배율은 1.0 고정(R17).
class DraftItem(Base):
    __tablename__ = 'meal_draft_items'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    draft_id: Mapped[str] = mapped_column(ForeignKey('meal_drafts.id', ondelete='CASCADE'), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    source_detection_id: Mapped[str | None] = mapped_column(ForeignKey('detection_logs.id'))
    food_id: Mapped[int] = mapped_column(ForeignKey('foods.id'))
    serving_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    consumption_ratio: Mapped[float] = mapped_column(Float, default=1.0)
    nutrition: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)
    bbox: Mapped[list | None] = mapped_column(JSON)
    __table_args__ = (CheckConstraint('consumption_ratio >= 0 AND consumption_ratio <= 1', name='ck_draft_items_ratio'),
                      CheckConstraint('serving_multiplier = 1', name='ck_draft_items_base'))
