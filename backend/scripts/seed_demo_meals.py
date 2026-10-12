"""로컬 테스트 계정에 최근 30일 식단을 추가한다. 기존 기록은 보존한다.

실행: python -m backend.scripts.seed_demo_meals
개발 환경에서만 동작하며 날짜/계정/끼니별 UUID로 중복 생성을 방지한다.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid5, NAMESPACE_URL
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.db import get_engine
from backend.app.models import User, Meal, MealItem, Food
from backend.app.services.nutrition import calculate_nutrition
from backend.scripts.seed_local_test_account import local_test_account_enabled, TEST_ACCOUNT_EMAIL

if not local_test_account_enabled():
    raise SystemExit('Local development test settings required.')
today = datetime.now(ZoneInfo('Asia/Seoul')).date()
plans = {
    'breakfast': [(16, 0.8), (46, 0.5)],
    'lunch': [(28, 1.0), (11, 0.5)],
    'dinner': [(39, 1.0), (47, 1.0)],
    'snack': [(37, 0.5)],
}
added_meals = added_items = 0
with Session(get_engine()) as db:
    user = db.scalar(select(User).where(User.email == TEST_ACCOUNT_EMAIL).with_for_update())
    if user is None or user.role != 'user' or user.oauth_provider:
        raise SystemExit('Expected local email test user missing.')
    before = db.scalar(select(func.count()).select_from(Meal).where(Meal.user_id != user.id))
    for offset in range(30):
        day = today - timedelta(days=offset)
        for meal_type, template in plans.items():
            meal_id = str(uuid5(NAMESPACE_URL, f'calodetect-demo-v1:{user.id}:{day}:{meal_type}'))
            if db.get(Meal, meal_id) is not None:
                continue
            hour = {'breakfast': 8, 'lunch': 12, 'dinner': 18, 'snack': 9}[meal_type]
            stamp = datetime(day.year, day.month, day.day, hour, tzinfo=ZoneInfo('Asia/Seoul'))
            meal = Meal(id=meal_id, user_id=user.id, meal_date=day, meal_type=meal_type, created_at=stamp)
            for index, (food_id, base_multiplier) in enumerate(template):
                # Alternate familiar existing foods and portion sizes across days.
                if index == 0 and meal_type == 'lunch':
                    food_id = [28, 39, 56][offset % 3]
                multiplier = round(base_multiplier * [0.85, 1.0, 1.15, 0.95][offset % 4], 2)
                calculated = calculate_nutrition(food_id, multiplier)
                if db.get(Food, food_id) is None:
                    raise RuntimeError('Existing food catalog must be seeded first.')
                meal.items.append(MealItem(
                    id=str(uuid5(NAMESPACE_URL, f'{meal_id}:{index}')),
                    food_id=food_id, corrected_label=calculated['food_name'],
                    serving_multiplier=multiplier, nutrition=calculated['nutrition'], created_at=stamp))
                added_items += 1
            db.add(meal)
            added_meals += 1
    db.flush()
    after = db.scalar(select(func.count()).select_from(Meal).where(Meal.user_id != user.id))
    assert before == after, 'Other accounts must stay unchanged.'
    db.commit()
print(f'Added meals={added_meals}, food items={added_items}; range={today-timedelta(days=29)}..{today}')
