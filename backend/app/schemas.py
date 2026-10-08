# API 요청의 타입·허용 범위·필수 필드를 검증하는 Pydantic 모델.
# 입력 형식 검증과 별도로 서비스 함수가 소유권·현재 정책·계산 결과의 유효성을 확인한다.
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic import EmailStr
from datetime import date


# RequestModel: BaseModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class RequestModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


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
    # 선택 모델 개선 동의. 서비스 필수 동의와 별도로 QA 후보 등록을 제어한다.
    model_improvement_consent: bool = False


# ConsentRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class ConsentRequest(RequestModel):
    # 선택 모델 개선 동의. 서비스 필수 동의와 별도로 QA 후보 등록을 제어한다.
    model_improvement_consent: bool


# MealItemRequest: NutritionRequest를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class MealItemRequest(NutritionRequest):
    # 연결할 탐지 ID. null이면 음식 직접 선택이며 서버에서 소유권/재사용을 확인한다.
    detection_id: str | None = None


# MealRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class MealRequest(RequestModel):
    # 아침·점심·저녁·간식 구분을 위한 API enum.
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack']
    # 식단을 기록한 날짜. 기본 날짜는 한국 시간 기준이며 생성 UTC 시각과 구분한다.
    meal_date: date | None = None
    items: list[MealItemRequest] = Field(min_length=1, max_length=100)
    # 선택한 추천 기록 ID. 서버에서 소유권·후보 포함 여부·사용 상태를 확인한다.
    recommendation_id: str | None = None


# CorrectionRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class CorrectionRequest(RequestModel):
    # 기존 0~149 음식 클래스 번호. 모델·YAML·CSV에서 같은 음식 연결을 유지한다.
    class_id: int = Field(ge=0, le=149)


# RecommendationRequest: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class RecommendationRequest(RequestModel):
    # 아침·점심·저녁·간식 구분을 위한 API enum.
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack'] = 'dinner'
    # 추천에서 제외할 기존 음식 class_id 목록.
    exclude_foods: list[int] = Field(default_factory=list, max_length=150)
    # 추천에서 우선할 기존 음식 분류 목록.
    preferred_categories: list[str] = Field(default_factory=list, max_length=30)
