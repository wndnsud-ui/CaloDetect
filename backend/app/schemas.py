# API 요청의 타입·허용 범위·필수 필드를 검증하는 Pydantic 모델.
# 입력 형식 검증과 별도로 서비스 함수가 소유권·현재 정책·계산 결과의 유효성을 확인한다.
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic import EmailStr
from datetime import date


# RequestModel: BaseModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class RequestModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class CommunityPostRequest(RequestModel):
    meal_id: str = Field(min_length=1, max_length=36)
    comment: str = Field(default='', max_length=300)
    show_photo: bool = Field(default=False, strict=True)


# 커뮤니티 댓글. 앞뒤 공백 제거 후 1~300자는 서비스가 확인한다.
class CommunityCommentRequest(RequestModel):
    body: str = Field(min_length=1, max_length=300)


# NutritionRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class NutritionRequest(RequestModel):
    # 기존 0~149 음식 클래스 번호. 모델·YAML·CSV에서 같은 음식 연결을 유지한다.
    class_id: int = Field(ge=0, le=149)
    # CSV 기준 섭취량에 곱하는 양의 배율. g 단위 절대량과 다르다.
    serving_multiplier: float = Field(gt=0, le=100)


# CalorieRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class CalorieRequest(RequestModel):
    # 키(cm). 계산에 전달하기 전에 유효한 양수 범위를 검사한다.
    height: float = Field(gt=0, le=300)
    # 체중(kg). 계산에 전달하기 전에 유효한 양수 범위를 검사한다.
    weight: float = Field(gt=0, le=500)
    # 만 나이. 타입/범위 검사 외에 가입·로그인 서비스가 최소 연령을 확인한다.
    age: int = Field(gt=0, le=120)
    # BMR 공식의 성별 상수를 고르는 기존 enum.
    sex: Literal['male', 'female']
    # TDEE 활동 계수를 고르는 기존 enum.
    activity_level: Literal['sedentary', 'light', 'moderate', 'active']
    # 감량·유지·증가 목표. TDEE에서 권장 범위 offset을 고른다.
    goal_type: Literal['weight_loss', 'maintain', 'muscle_gain']
    # 하루 목표(kcal). None은 미설정이며 상한 외 최소 허용값은 계산 서비스가 검사한다.
    target_calories: float | None = Field(default=None, gt=0, le=5000)


# LoginRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class LoginRequest(RequestModel):
    # 가입 이메일. 인증 경로에서 정규화하고 DB의 unique 제약으로 중복 가입을 막는다.
    email: EmailStr
    # 인증용 입력 비밀번호. 이 요청 필드는 DB 저장용 해시와 다르다.
    password: str = Field(min_length=10, max_length=128)


# SignupRequest: LoginRequest를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class SignupRequest(LoginRequest):
    # 만 나이. 타입/범위 검사 외에 가입·로그인 서비스가 최소 연령을 확인한다.
    age: int = Field(gt=0, le=120)
    # 현재 서비스 필수 동의의 수락 여부. 실제 허용은 정책 검사에서 판단한다.
    service_consent: Literal[True]


# MealItemRequest: NutritionRequest를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class MealNutrition(RequestModel):
    cal: float | None = Field(default=None, ge=0, le=100000)
    carbs: float | None = Field(default=None, ge=0, le=100000)
    protein: float | None = Field(default=None, ge=0, le=100000)
    fat: float | None = Field(default=None, ge=0, le=100000)
    sugar: float | None = Field(default=None, ge=0, le=100000)
    sodium: float | None = Field(default=None, ge=0, le=1000000)


class MealItemRequest(RequestModel):
    id: str | None = Field(default=None, max_length=36)
    version: int | None = Field(default=None, ge=1)
    class_id: int | None = Field(default=None, ge=0, le=149)
    reference_food_id: str | None = Field(default=None, max_length=80)
    food_name: str | None = Field(default=None, min_length=1, max_length=120)
    serving_multiplier: float = Field(default=1, gt=0, le=100)
    amount: float = Field(default=1, gt=0, le=100000)
    amount_unit: Literal['g', 'ml', 'serving'] = 'serving'
    nutrition: MealNutrition | None = None
    is_llm_estimated: bool = False
    # 연결할 탐지 ID. null이면 음식 직접 선택이며 서버에서 소유권/재사용을 확인한다.
    detection_id: str | None = None

    @model_validator(mode='after')
    def legacy_amount(self):
        if 'amount' not in self.model_fields_set:
            self.amount = self.serving_multiplier
        return self


# MealRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class MealRequest(RequestModel):
    # 아침·점심·저녁·간식 구분을 위한 API enum.
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack']
    # 식단을 기록한 날짜. 기본 날짜는 한국 시간 기준이며 생성 UTC 시각과 구분한다.
    meal_date: date | None = None
    items: list[MealItemRequest] = Field(default_factory=list, max_length=100)
    image_upload_id: str | None = Field(default=None, max_length=36)
    meal_time: str | None = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    analysis_status: Literal['pending', 'analyzed', 'skipped', 'failed'] = 'analyzed'
    expected_version: int | None = Field(default=None, ge=1)
    # 10월 15일 박근수 수정: 추천 선택 기록은 식단 저장과 같은 DB transaction에서 소유권을 검사한다.
    recommendation_id: str | None = None

    @model_validator(mode='after')
    def record_required(self):
        if not self.items and not self.image_upload_id:
            raise ValueError('사진 또는 음식을 추가해 주세요.')
        return self


# CorrectionRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class CorrectionRequest(RequestModel):
    # 기존 0~149 음식 클래스 번호. 모델·YAML·CSV에서 같은 음식 연결을 유지한다.
    class_id: int = Field(ge=0, le=149)


# RecommendationRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class RecommendationRequest(RequestModel):
    # 아침·점심·저녁·간식 구분을 위한 API enum.
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack'] = 'dinner'
    # 10월 15일 박근수 수정: API key는 유지하고 UI 명칭만 '기본 맞춤 추천'으로 안내한다.
    theme: Literal['balance', 'protein', 'light'] = 'balance'
    # 추천에서 제외할 기존 음식 class_id 목록.
    exclude_foods: list[int] = Field(default_factory=list, max_length=150)
    # 이전 API 요청과의 호환을 위해 유지하며 현재 UI/점수에서는 사용하지 않는다.
    preferred_categories: list[str] = Field(default_factory=list, max_length=30)


# 추천 카드의 [근처 맛집 찾기]: 메뉴명과 지역명 또는 브라우저 좌표 중 하나가 필요하다. 위치는 저장하지 않는다.
class RecommendationPlacesRequest(RequestModel):
    query: str = Field(min_length=1, max_length=30)
    area: str | None = Field(default=None, max_length=30)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode='after')
    def area_or_location(self):
        self.query = self.query.strip()
        self.area = (self.area or '').strip() or None
        if not self.query:
            raise ValueError('메뉴 이름이 필요합니다.')
        if (self.lat is None) != (self.lng is None):
            raise ValueError('위도와 경도를 함께 보내 주세요.')
        if not self.area and self.lat is None:
            raise ValueError('지역 이름 또는 현재 위치가 필요합니다.')
        return self
