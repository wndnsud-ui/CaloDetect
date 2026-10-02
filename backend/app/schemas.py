from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic import EmailStr
from datetime import date


class RequestModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class NutritionRequest(RequestModel):
    class_id: int = Field(ge=0, le=149)
    serving_multiplier: float = Field(gt=0, le=100)


class CalorieRequest(RequestModel):
    height: float = Field(gt=0, le=300)
    weight: float = Field(gt=0, le=500)
    age: int = Field(gt=0, le=120)
    sex: Literal['male', 'female']
    activity_level: Literal['sedentary', 'light', 'moderate', 'active']
    goal_type: Literal['weight_loss', 'maintain', 'muscle_gain']
    target_calories: float | None = Field(default=None, gt=0, le=5000)


class LoginRequest(RequestModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class SignupRequest(LoginRequest):
    age: int = Field(gt=0, le=120)
    service_consent: Literal[True]
    model_improvement_consent: bool = False


class ConsentRequest(RequestModel):
    model_improvement_consent: bool


class MealItemRequest(NutritionRequest):
    detection_id: str | None = None


class MealRequest(RequestModel):
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack']
    meal_date: date | None = None
    items: list[MealItemRequest] = Field(min_length=1, max_length=100)
    recommendation_id: str | None = None


class CorrectionRequest(RequestModel):
    class_id: int = Field(ge=0, le=149)


class RecommendationRequest(RequestModel):
    meal_type: Literal['breakfast', 'lunch', 'dinner', 'snack'] = 'dinner'
    exclude_foods: list[int] = Field(default_factory=list, max_length=150)
    preferred_categories: list[str] = Field(default_factory=list, max_length=30)
