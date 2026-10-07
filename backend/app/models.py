from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Float, Integer, Boolean, Date, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def uid():
    return str(uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CommunityPost(Base):
    __tablename__ = 'community_posts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(String(4000))
    category: Mapped[str] = mapped_column(String(20))
    visibility: Mapped[str] = mapped_column(String(20), default='private')
    image_name: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    __table_args__ = (CheckConstraint("visibility IN ('private', 'public')"),)


class CommunityReaction(Base):
    __tablename__ = 'community_reactions'
    post_id: Mapped[str] = mapped_column(ForeignKey('community_posts.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    __table_args__ = (CheckConstraint("kind IN ('like', 'recommend')"),)


class CommunityComment(Base):
    __tablename__ = 'community_comments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    post_id: Mapped[str] = mapped_column(ForeignKey('community_posts.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    text: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    service_consent_text: Mapped[str] = mapped_column(String(4000))
    service_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default='user', server_default='user')
    age: Mapped[int | None] = mapped_column(Integer)
    oauth_provider: Mapped[str | None] = mapped_column(String(32))
    oauth_subject: Mapped[str | None] = mapped_column(String(255))
    model_improvement_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    model_improvement_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (UniqueConstraint('oauth_provider', 'oauth_subject'), CheckConstraint("role IN ('user', 'admin')"))


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    csrf_token: Mapped[str] = mapped_column(String(64))


class Profile(Base):
    __tablename__ = 'user_profiles'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    # Team-defined macro/sugar/sodium targets are not fabricated.
    @property
    def calculation(self):
        return self.data
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Food(Base):
    __tablename__ = 'foods'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    canonical_name: Mapped[str] = mapped_column(String(120), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    model_class: Mapped[int] = mapped_column(Integer, unique=True)
    category: Mapped[str] = mapped_column(String(120))
    serving_unit: Mapped[str] = mapped_column(String(120))
    nutrition_source: Mapped[str] = mapped_column(String(255))
    nutrition: Mapped[dict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Detection(Base):
    __tablename__ = 'detection_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    image_path: Mapped[str] = mapped_column(String(255))
    image_group_id: Mapped[str] = mapped_column(String(36), index=True)
    predicted_label: Mapped[str] = mapped_column(String(120))
    corrected_label: Mapped[str | None] = mapped_column(String(120))
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[list] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImageUpload(Base):
    __tablename__ = 'image_uploads'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    image_path: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Meal(Base):
    __tablename__ = 'meals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    meal_date: Mapped[datetime] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    items: Mapped[list['MealItem']] = relationship(cascade='all, delete-orphan', lazy='selectin')


class MealItem(Base):
    __tablename__ = 'meal_items'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    meal_id: Mapped[str] = mapped_column(ForeignKey('meals.id'), index=True)
    food_id: Mapped[int] = mapped_column(ForeignKey('foods.id'))
    detection_log_id: Mapped[str | None] = mapped_column(ForeignKey('detection_logs.id'), unique=True)
    predicted_label: Mapped[str | None] = mapped_column(String(120))
    corrected_label: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float | None] = mapped_column(Float)
    serving_multiplier: Mapped[float] = mapped_column(Float)
    nutrition: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint('serving_multiplier > 0'),)


class RetrainingSample(Base):
    __tablename__ = 'retraining_samples'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    detection_log_id: Mapped[str] = mapped_column(ForeignKey('detection_logs.id'), index=True)
    image_path: Mapped[str] = mapped_column(String(255))
    predicted_label: Mapped[str] = mapped_column(String(120))
    corrected_label: Mapped[str] = mapped_column(String(120))
    qa_status: Mapped[str] = mapped_column(String(16), default='PENDING')
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("qa_status IN ('PENDING','APPROVED','REJECTED')"),)


class RecommendationLog(Base):
    __tablename__ = 'recommendation_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    nutrition_snapshot: Mapped[dict] = mapped_column(JSON)
    recommendation_json: Mapped[list] = mapped_column(JSON)
    selected_item: Mapped[int | None] = mapped_column(Integer)
    acted: Mapped[bool] = mapped_column(Boolean, default=False)
