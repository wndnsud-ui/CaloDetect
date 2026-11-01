"""Confirmed edits of saved meals. Caller commits with the processed chat message."""
import hashlib
import json
from datetime import timedelta
from sqlalchemy import select
from ..models import Meal, MealItem, Food, NutritionFood, Detection
from ..models_chat import MutationRequest
from .consumption_record import ChatRecordError
from .nutrition import calculate_nutrition
from .correction import apply_correction


def owned_saved_item(db, user, item_id):
    item = db.get(MealItem, item_id)
    meal = db.get(Meal, item.meal_id) if item else None
    if not item or not meal or meal.user_id != user.id:
        raise ChatRecordError(404, '404', '기록을 찾을 수 없습니다.')
    return item, meal


def preview_edit(db, user, item_id, result, text, today):
    item, meal = owned_saved_item(db, user, item_id)
    payload = {'item_id': item.id, 'meal_id': meal.id, 'meal_version': meal.version,
               'item_version': item.version, 'kind': result['intent']}
    if result['intent'] == 'set_meal_info':
        info = result['meal_info']
        if info['meal_type'] not in ('breakfast', 'lunch', 'dinner', 'snack'):
            raise ChatRecordError(422, '422', '아침·점심·저녁·간식 중에서 골라 주세요.')
        day = meal.meal_date
        if '어제' in text:
            day = today - timedelta(days=1)
        elif '오늘' in text:
            day = today
        payload.update(meal_type=info['meal_type'], meal_date=str(day))
    else:
        food = db.get(Food, result['food']['id'])
        if not food or not food.active:
            raise ChatRecordError(422, '422', '음식을 찾을 수 없습니다.')
        payload.update(food_id=food.id, food_name=food.canonical_name)
    return payload


def apply_edit(db, user, payload, request_id):
    # Match the meal editor lock order and check versions after taking locks.
    meal = db.get(Meal, payload['meal_id'], with_for_update=True, populate_existing=True)
    item = db.get(MealItem, payload['item_id'], with_for_update=True, populate_existing=True)
    if not meal or meal.user_id != user.id or not item or item.meal_id != meal.id:
        raise ChatRecordError(404, '404', '기록을 찾을 수 없습니다.')
    if meal.version != payload['meal_version'] or item.version != payload['item_version']:
        raise ChatRecordError(409, 'version_conflict', '기록이 변경됐어요. 다시 확인해 주세요.')
    before = {'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type,
              'food_name': item.corrected_label, 'nutrition': dict(item.nutrition)}
    if payload['kind'] == 'set_meal_info':
        from datetime import date
        meal.meal_type = payload['meal_type']
        meal.meal_date = date.fromisoformat(payload['meal_date'])
    else:
        food = db.get(Food, payload['food_id'])
        if not food or not food.active:
            raise ChatRecordError(422, '422', '음식을 찾을 수 없습니다.')
        servings = item.serving_multiplier
        if item.reference_food_id:
            reference = db.get(NutritionFood, item.reference_food_id)
            servings = item.amount if item.amount_unit == 'serving' else item.amount / reference.serving_amount
        item.food_id = food.id
        item.reference_food_id = None
        item.corrected_label = food.canonical_name
        item.serving_multiplier = servings
        item.amount, item.amount_unit = servings, 'serving'
        item.nutrition = calculate_nutrition(food.id, servings * item.consumption_ratio)['nutrition']
        item.is_edited, item.is_llm_estimated = True, False
        detection = db.get(Detection, item.detection_log_id) if item.detection_log_id else None
        if detection and detection.user_id == user.id:
            apply_correction(db, detection, food.canonical_name, user)
        item.version += 1
    meal.version += 1
    after = {'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type,
             'food_name': item.corrected_label, 'nutrition': dict(item.nutrition)}
    db.add(MutationRequest(user_id=user.id, operation='meal.details', request_id=request_id,
        target_type='meal', target_id=meal.id, payload_hash=hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()).hexdigest(), status='succeeded',
        result_id=meal.id, result_version=meal.version, before=before, after=after))
    return meal, item
