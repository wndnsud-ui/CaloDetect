# SQLAlchemy ORM 테이블 정의. 회원, 세션, 프로필, 음식, 탐지, 식단과 QA 후보의 관계를 표현한다.
# ForeignKey는 참조 관계, UniqueConstraint/CheckConstraint는 DB 단계의 무결성 규칙이며 실제 스키마 변경은 Alembic이 담당한다.
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, Float, Integer, Boolean, Date, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# 탐지·식단·추천 등 레코드의 기본 식별자로 사용할 UUID 문자열을 생성한다.
def uid():
    return str(uuid4())


# 시간대 정보가 있는 현재 UTC 시각을 DB 시각 필드의 기본값으로 반환한다.
def utcnow():
    return datetime.now(timezone.utc)


# Base: DeclarativeBase 기반 구조. 아래 메서드는 이 객체의 인터페이스를 정의한다.
class Base(DeclarativeBase):
    pass


# User: users 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class User(Base):
    __tablename__ = 'users'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 사용자 표시 이름. 앞뒤 공백과 길이는 요청 모델에서 검증한다.
    name: Mapped[str] = mapped_column(String(80))
    # 가입 때 확인한 서비스 필수 동의 문구를 기록한다.
    service_consent_text: Mapped[str] = mapped_column(String(4000))
    # 서비스 필수 동의 시각. 시간대 정보가 있는 UTC로 저장한다.
    service_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # 가입 이메일. 인증 경로에서 정규화하고 DB의 unique 제약으로 중복 가입을 막는다.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    # salt를 포함한 비밀번호 해시. 원문 비밀번호를 저장하지 않는다.
    password_hash: Mapped[str] = mapped_column(String(256))
    # 사용자/관리자 권한. 일반 가입은 user이며 요청 입력으로 승격하지 않는다.
    role: Mapped[str] = mapped_column(String(20), default='user', server_default='user')
    # 만 나이. 타입/범위 검사 외에 가입·로그인 서비스가 최소 연령을 확인한다.
    age: Mapped[int | None] = mapped_column(Integer)
    # 소셜 제공자. oauth_subject와 함께 해당 제공자의 고유 계정을 식별한다.
    oauth_provider: Mapped[str | None] = mapped_column(String(32))
    # 제공자가 발급한 subject 식별자. 이메일 변경과 무관하게 같은 계정을 찾는다.
    oauth_subject: Mapped[str | None] = mapped_column(String(255))
    # 선택 모델 개선 동의. 서비스 필수 동의와 별도로 QA 후보 등록을 제어한다.
    model_improvement_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    # 모델 개선 동의의 최근 변경 시각.
    model_improvement_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 생성 시각. 기본값 함수는 새 레코드를 만들 때 호출된다.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # 최근 갱신 시각. ORM 갱신 시 onupdate 설정을 따른다.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (UniqueConstraint('oauth_provider', 'oauth_subject'), CheckConstraint("role IN ('user', 'admin')"))


# AuthSession: auth_sessions 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    # 세션 토큰 SHA-256. 브라우저 원문 토큰 대신 DB 조회 키로 저장한다.
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    # 소유 회원의 참조 키. 회원별 조회·권한 검사의 기준이다.
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    # 세션 만료 시각. 인증 시 현재 UTC 시각과 비교한다.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # 쿠키 기반 변경 요청에서 X-CSRF-Token과 대조하는 세션별 토큰.
    csrf_token: Mapped[str] = mapped_column(String(64))


# Profile: user_profiles 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class Profile(Base):
    __tablename__ = 'user_profiles'
    # 소유 회원의 참조 키. 회원별 조회·권한 검사의 기준이다.
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    # 입력 프로필과 서버 계산 결과를 함께 보관하는 JSON.
    data: Mapped[dict] = mapped_column(JSON)
    # Team-defined macro/sugar/sodium targets are not fabricated.
    # 저장된 프로필 JSON을 계산 결과 조회 인터페이스로 제공한다.
    @property
    def calculation(self):
        return self.data
    # 최근 갱신 시각. ORM 갱신 시 onupdate 설정을 따른다.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# Food: foods 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class Food(Base):
    __tablename__ = 'foods'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    # 기존 모델/CSV와 연결된 기준 음식명.
    canonical_name: Mapped[str] = mapped_column(String(120), unique=True)
    # 음식 목록과 화면에 사용할 표시 이름.
    display_name: Mapped[str] = mapped_column(String(120))
    # 기존 YOLO 클래스 번호. class_id 연결을 유지한다.
    model_class: Mapped[int] = mapped_column(Integer, unique=True)
    # 기존 CSV의 음식 분류. 추천의 선호·다양성 판정에 사용한다.
    category: Mapped[str] = mapped_column(String(120))
    # CSV 영양값의 기준량 문구. 임의의 새 g 기준으로 바꾸지 않는다.
    serving_unit: Mapped[str] = mapped_column(String(120))
    # 영양 수치의 원본 출처 파일 이름.
    nutrition_source: Mapped[str] = mapped_column(String(255))
    # cal(kcal), carbs/protein/fat/sugar(g), sodium(mg)의 영양 JSON.
    nutrition: Mapped[dict] = mapped_column(JSON)
    # 서비스에서 선택 가능한 음식인지 나타내는 활성 상태.
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# Detection: detection_logs 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class Detection(Base):
    __tablename__ = 'detection_logs'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    # 소유 회원의 참조 키. 회원별 조회·권한 검사의 기준이다.
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    # 저장 폴더 아래 서버가 정한 이미지 파일명. 사용자 원본 파일명을 저장 경로로 쓰지 않는다.
    image_path: Mapped[str] = mapped_column(String(255))
    # 한 업로드의 여러 탐지를 같은 사진으로 묶는 UUID.
    image_group_id: Mapped[str] = mapped_column(String(36), index=True)
    # 모델의 원래 탐지 음식명. 사용자 수정 후에도 비교용으로 보존한다.
    predicted_label: Mapped[str] = mapped_column(String(120))
    # 사용자가 확인·수정한 최종 음식명.
    corrected_label: Mapped[str | None] = mapped_column(String(120))
    # 모델 탐지 신뢰도. 정답 여부를 보장하는 값은 아니다.
    confidence: Mapped[float] = mapped_column(Float)
    # 모델의 탐지 영역 좌표 목록.
    bbox: Mapped[list] = mapped_column(JSON)
    # 탐지에 사용한 모델 버전/파일 식별 정보.
    model_version: Mapped[str] = mapped_column(String(120))
    # 생성 시각. 기본값 함수는 새 레코드를 만들 때 호출된다.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ImageUpload: image_uploads 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class ImageUpload(Base):
    __tablename__ = 'image_uploads'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    # 소유 회원의 참조 키. 회원별 조회·권한 검사의 기준이다.
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    # 저장 폴더 아래 서버가 정한 이미지 파일명. 사용자 원본 파일명을 저장 경로로 쓰지 않는다.
    image_path: Mapped[str] = mapped_column(String(255))
    # 생성 시각. 기본값 함수는 새 레코드를 만들 때 호출된다.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# Meal: meals 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class Meal(Base):
    __tablename__ = 'meals'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    # 소유 회원의 참조 키. 회원별 조회·권한 검사의 기준이다.
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    # 식단을 기록한 날짜. 기본 날짜는 한국 시간 기준이며 생성 UTC 시각과 구분한다.
    meal_date: Mapped[datetime] = mapped_column(Date, index=True)
    # 아침·점심·저녁·간식 구분을 위한 API enum.
    meal_type: Mapped[str] = mapped_column(String(16))
    # 생성 시각. 기본값 함수는 새 레코드를 만들 때 호출된다.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    items: Mapped[list['MealItem']] = relationship(cascade='all, delete-orphan', lazy='selectin')


# MealItem: meal_items 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class MealItem(Base):
    __tablename__ = 'meal_items'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    # 음식 항목이 속한 식단의 참조 키.
    meal_id: Mapped[str] = mapped_column(ForeignKey('meals.id'), index=True)
    # 음식 카탈로그의 기존 class_id와 연결되는 참조 키.
    food_id: Mapped[int] = mapped_column(ForeignKey('foods.id'))
    # 연결된 탐지 기록. 직접 선택한 음식은 없을 수 있으며 식단 항목의 unique 제약으로 중복 연결을 막는다.
    detection_log_id: Mapped[str | None] = mapped_column(ForeignKey('detection_logs.id'), unique=True)
    # 모델의 원래 탐지 음식명. 사용자 수정 후에도 비교용으로 보존한다.
    predicted_label: Mapped[str | None] = mapped_column(String(120))
    # 사용자가 확인·수정한 최종 음식명.
    corrected_label: Mapped[str] = mapped_column(String(120))
    # 모델 탐지 신뢰도. 정답 여부를 보장하는 값은 아니다.
    confidence: Mapped[float | None] = mapped_column(Float)
    # CSV 기준 섭취량에 곱하는 양의 배율. g 단위 절대량과 다르다.
    serving_multiplier: Mapped[float] = mapped_column(Float)
    # cal(kcal), carbs/protein/fat/sugar(g), sodium(mg)의 영양 JSON.
    nutrition: Mapped[dict] = mapped_column(JSON)
    # 생성 시각. 기본값 함수는 새 레코드를 만들 때 호출된다.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint('serving_multiplier > 0'),)


# RetrainingSample: retraining_samples 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class RetrainingSample(Base):
    __tablename__ = 'retraining_samples'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    # 연결된 탐지 기록. 직접 선택한 음식은 없을 수 있으며 식단 항목의 unique 제약으로 중복 연결을 막는다.
    detection_log_id: Mapped[str] = mapped_column(ForeignKey('detection_logs.id'), index=True)
    # 저장 폴더 아래 서버가 정한 이미지 파일명. 사용자 원본 파일명을 저장 경로로 쓰지 않는다.
    image_path: Mapped[str] = mapped_column(String(255))
    # 모델의 원래 탐지 음식명. 사용자 수정 후에도 비교용으로 보존한다.
    predicted_label: Mapped[str] = mapped_column(String(120))
    # 사용자가 확인·수정한 최종 음식명.
    corrected_label: Mapped[str] = mapped_column(String(120))
    # PENDING/APPROVED/REJECTED 검수 상태. 모델 재학습 완료 상태가 아니다.
    qa_status: Mapped[str] = mapped_column(String(16), default='PENDING')
    # 철회·재수정 등으로 후보 목록에서 제외됐는지 표시한다.
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    # 검수 결정을 기록한 관리자 ID. 승인과 거절 모두 공통 검수 함수에서 설정한다.
    approved_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    # 생성 시각. 기본값 함수는 새 레코드를 만들 때 호출된다.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("qa_status IN ('PENDING','APPROVED','REJECTED')"),)


# RecommendationLog: recommendation_logs 테이블의 ORM 모델. 아래 필드와 제약은 저장 형식과 참조 관계를 정의한다.
class RecommendationLog(Base):
    __tablename__ = 'recommendation_logs'
    # 레코드 기본 식별자. 테이블에 따라 정수 또는 UUID를 사용한다.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    # 소유 회원의 참조 키. 회원별 조회·권한 검사의 기준이다.
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    # 추천 생성 시각.
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # 추천 당시 오늘의 영양/목표 상태. 이후 식단 변화와 구분하기 위해 보관한다.
    nutrition_snapshot: Mapped[dict] = mapped_column(JSON)
    # 추천 당시 후보와 내부 정렬 정보를 보관한다. 공개 응답은 score를 제외한다.
    recommendation_json: Mapped[list] = mapped_column(JSON)
    # 회원이 식단으로 기록한 추천 음식 class_id.
    selected_item: Mapped[int | None] = mapped_column(Integer)
    # 이미 식단으로 기록한 추천인지 표시해 중복 사용을 막는다.
    acted: Mapped[bool] = mapped_column(Boolean, default=False)
