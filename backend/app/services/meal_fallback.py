"""Validated snapshots for catalog, detection, and free-form meal entries."""
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Food, NutritionFood, Detection, MealItem, ImageUpload
from .nutrition import calculate_nutrition
from .analytics import NUTRIENTS


def owned_photo(db, user, image_id):
    photo = db.get(ImageUpload, image_id) if image_id else None
    if image_id and (not photo or photo.user_id != user.id):
        raise HTTPException(404, '사진을 찾을 수 없습니다.')
    return photo


def fill_item(db, user, body, existing=None):
    item = existing or MealItem()
    if existing and body.detection_id != existing.detection_log_id:
        raise HTTPException(422, '기존 항목의 원본 탐지는 바꿀 수 없습니다. 새 항목으로 추가해 주세요.')
    detection = None
    if body.detection_id:
        detection = db.get(Detection, body.detection_id, with_for_update=True)
        if not detection or detection.user_id != user.id:
            raise HTTPException(404, '탐지 결과를 찾을 수 없습니다.')
        used = db.scalar(select(MealItem).where(MealItem.detection_log_id == detection.id))
        if used and (not existing or used.id != existing.id):
            raise HTTPException(409, '이미 저장한 탐지 결과입니다.')
    if body.class_id is not None and body.reference_food_id:
        raise HTTPException(422, '음식 출처는 하나만 선택해 주세요.')
    food = db.get(Food, body.class_id) if body.class_id is not None else None
    reference = db.get(NutritionFood, body.reference_food_id) if body.reference_food_id else None
    if body.class_id is not None and (not food or not food.active):
        raise HTTPException(422, '음식 데이터를 확인해 주세요.')
    if body.reference_food_id and not reference:
        raise HTTPException(422, '검색 음식을 찾을 수 없습니다.')
    name = (body.food_name or (food.canonical_name if food else reference.name if reference else '')).strip()
    if not name:
        raise HTTPException(422, '음식명을 입력해 주세요.')
    if detection and name != detection.predicted_label:
        from .correction import apply_correction
        apply_correction(db, detection, name, user)
    if reference:
        if body.amount_unit != 'serving' and body.amount_unit != reference.serving_unit:
            raise HTTPException(422, '원본 기준 단위와 같은 단위를 사용해 주세요. g과 ml를 임의 변환하지 않습니다.')
        multiplier = body.amount / reference.serving_amount if body.amount_unit != 'serving' else body.amount
        nutrition = {k: round(v * multiplier, 2) if v is not None else None for k, v in reference.nutrition.items()}
    elif food:
        if body.amount_unit != 'serving':
            raise HTTPException(422, '이 음식은 기준량 배수로 입력해 주세요.')
        nutrition = calculate_nutrition(food.id, body.serving_multiplier)['nutrition']
    else:
        nutrition = {k: None for k in NUTRIENTS}
    calculated = dict(nutrition)
    if body.nutrition is not None:
        nutrition = body.nutrition.model_dump()
    # Preserve the original provenance when editing an existing item.
    source = item.source if existing else 'ai' if detection else 'search' if food or reference else 'manual'
    old = (item.corrected_label, item.serving_multiplier, item.nutrition, item.food_id,
           item.reference_food_id, item.amount, item.amount_unit) if existing else None
    new = (name, body.serving_multiplier, nutrition, body.class_id,
           body.reference_food_id, body.amount, body.amount_unit)
    if existing and old != new:
        item.consumption_ratio = 1
    item.is_edited = bool((existing and (item.is_edited or old != new)) or
                          (detection and name != detection.predicted_label) or
                          ((food or reference) and body.nutrition is not None and calculated != nutrition))
    item.food_id = body.class_id
    item.reference_food_id = body.reference_food_id
    item.corrected_label = name
    item.serving_multiplier = body.serving_multiplier
    item.amount = body.amount
    item.amount_unit = body.amount_unit
    item.nutrition = {key: nutrition.get(key) for key in NUTRIENTS}
    item.source = source
    item.is_llm_estimated = bool(not food and not reference and body.is_llm_estimated) if not existing else item.is_llm_estimated or body.is_llm_estimated
    if not existing:
        item.detection_log_id = detection.id if detection else None
        item.predicted_label = detection.predicted_label if detection else None
        item.confidence = detection.confidence if detection else None
        item.ai_confidence = item.confidence
    else:
        item.version += 1
    return item
