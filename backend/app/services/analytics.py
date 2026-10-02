from datetime import datetime, timezone
from sqlalchemy import select
from ..models import Meal, Profile
from .timezone import korean_date

NUTRIENTS = ['cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium']


def meal_json(meal):
    return {'id': meal.id, 'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type,
            'items': [{'id': i.id, 'class_id': i.food_id, 'food_name': i.corrected_label,
                       'detection_id': i.detection_log_id, 'serving_multiplier': i.serving_multiplier,
                       'nutrition': i.nutrition} for i in meal.items]}


def get_today_status(db, user_id, instant=None):
    today = korean_date(instant or datetime.now(timezone.utc))
    meals = db.scalars(select(Meal).where(Meal.user_id == user_id, Meal.meal_date == today)
                       .order_by(Meal.created_at.desc())).all()
    totals = {key: round(sum(item.nutrition[key] for meal in meals for item in meal.items), 2) for key in NUTRIENTS}
    profile = db.get(Profile, user_id)
    target = profile.calculation['target_calories'] if profile else None
    return {'date': str(today), 'timezone': 'Asia/Seoul', 'totals': totals,
            'target_calories': target,
            'remaining_calories': max(0, round(target - totals['cal'], 2)) if target else None,
            'macro_targets': None, 'sugar_sodium_limits': None,
            'meals': [meal_json(m) for m in meals],
            'message': '목표를 설정해 주세요.' if not target else
                ('오늘 섭취량이 목표를 초과했습니다.' if totals['cal'] > target else '기록한 식단을 바탕으로 다음 식사를 선택해 보세요.')}
