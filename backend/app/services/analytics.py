# 회원별 식단 영양 합계와 한국 시간 기준 일간·월간 분석.
# 저장된 영양 스냅샷을 집계하며 월 평균은 실제 기록일만 포함하고 미기록일은 null로 구분한다.
from datetime import date, datetime, timezone
from calendar import monthrange
from sqlalchemy import select
from ..models import Meal, Profile, Detection, ImageUpload, NutritionFood
from sqlalchemy.orm import object_session
from .timezone import korean_date
from ..config import settings
from .profile import calculate_macro_targets
from .nutrition_limits import daily_limits

NUTRIENTS = ['cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium']


# 한 달 전체 회원 식단을 조회해 날짜별 합계를 만들고 기록된 날만 분모로 월 평균을 계산한다.
def get_month_status(db, user_id, year, month):
    # 윤년과 월별 길이를 반영해 해당 월의 마지막 날짜를 얻는다.
    days = monthrange(year, month)[1]
    # 히스토리 API의 조회 개수 제한 없이 월 범위 전체를 조회해 집계 누락을 방지한다.
    meals = db.scalars(select(Meal).where(Meal.user_id == user_id, Meal.deleted_at.is_(None),
        Meal.meal_date >= date(year, month, 1), Meal.meal_date <= date(year, month, days))).all()
    keep = prefetch(db, meals)  # noqa: F841 (identity map 유지용)
    records = []
    for day in range(1, days + 1):
        current = date(year, month, day)
        entries = [meal for meal in meals if meal.meal_date == current]
        # 기록일은 영양 스냅샷을 합산하고 미기록일은 None으로 둬 0 섭취와 구분한다.
        totals = {key: round(sum((item.nutrition.get(key) or 0) for meal in entries for item in meal.items), 2)
                  for key in NUTRIENTS} if entries else None
        records.append({'date': str(current), 'totals': totals,
                        'meals': [meal_json(meal) for meal in entries]})
    # 평균 분모에는 식단이 하나 이상 기록된 날만 넣는다. 일부 식사만 기록한 날도 기록일이다.
    recorded = [record for record in records if record['totals'] is not None]
    averages = {key: round(sum(record['totals'][key] for record in recorded) / len(recorded), 2)
                for key in NUTRIENTS} if recorded else None
    return {'timezone': 'Asia/Seoul', 'days': records, 'recorded_days': len(recorded),
            'averages': averages}


def prefetch(db, meals):
    """meal_json이 식단·항목마다 하던 단건 조회(음식 DB·탐지·사진)를 종류별 1번으로 묶어 미리 읽는다.
    운영 서버와 DB가 멀어 왕복 수가 곧 응답 시간이라서다. 세션 identity map은 약참조라 반환값을 쥐고 있어야 한다."""
    items = [i for m in meals for i in m.items]
    wanted = ((NutritionFood, {i.reference_food_id for i in items if i.reference_food_id}),
              (Detection, {i.detection_log_id for i in items if i.detection_log_id}),
              (ImageUpload, {m.image_upload_id for m in meals if m.image_upload_id}))
    return [db.scalars(select(model).where(model.id.in_(ids))).all() for model, ids in wanted if ids]


def meals_json(db, meals):
    keep = prefetch(db, meals)  # noqa: F841 (identity map 유지용)
    return [meal_json(m) for m in meals]


# 식단 항목과 같은 소유자의 탐지 이미지를 응답으로 직렬화하며 동일 이미지 그룹은 한 번만 포함한다.
def meal_json(meal):
    db = object_session(meal)
    references = {i.reference_food_id: db.get(NutritionFood, i.reference_food_id)
                  for i in meal.items if db and i.reference_food_id}
    image_ids = []
    if db and meal.image_upload_id:
        image = db.get(ImageUpload, meal.image_upload_id)
        if image and image.user_id == meal.user_id:
            image_ids.append(image.id)
    for item in meal.items:
        detection = db.get(Detection, item.detection_log_id) if db and item.detection_log_id else None
        # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
        # 연결된 탐지의 소유자가 식단 소유자와 같은 경우만 이미지 URL에 포함하고 중복 사진은 제거한다.
        if not meal.photo_override and detection and detection.user_id == meal.user_id and detection.image_group_id not in image_ids:
            image_ids.append(detection.image_group_id)
    data = {'id': meal.id, 'analysis_status': meal.analysis_status, 'image_upload_id': meal.image_upload_id,
            'meal_time': meal.meal_time, 'version': meal.version,
            'nutrition_pending': not meal.items or any(any(i.nutrition.get(k) is None for k in ('cal','carbs','protein','fat')) for i in meal.items), 'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type,
            'image_urls': [f'/api/meals/images/{image_id}' for image_id in image_ids],
            'items': [{'id': i.id, 'class_id': i.food_id, 'food_name': i.corrected_label,
                       'detection_id': i.detection_log_id, 'serving_multiplier': i.serving_multiplier,
                       'nutrition': i.nutrition, 'version': i.version, 'source': i.source, 'ai_confidence': i.ai_confidence,
                       'is_edited': i.is_edited, 'is_llm_estimated': i.is_llm_estimated,
                       'reference_food_id': i.reference_food_id,
                       'reference_unit': references[i.reference_food_id].serving_unit if references.get(i.reference_food_id) else None,
                       'reference_serving_amount': references[i.reference_food_id].serving_amount if references.get(i.reference_food_id) else None,
                       'amount': i.amount, 'amount_unit': i.amount_unit} for i in meal.items]}
    # 채팅 식사기록 플래그가 켜졌을 때만 섭취 비율 키를 추가한다. 기존 키·값은 그대로 둔다.
    if settings.chat_record_enabled:
        from .consumption_record import supports_consumption_edit
        # 채팅으로 기록한 식사는 탐지가 없어도(수동 선택·분석 실패) 첨부 사진을 추가로 보여 준다.
        if db and meal.chat_attachment_id and not meal.photo_override:
            from ..models_chat import ChatAttachment
            attachment = db.get(ChatAttachment, meal.chat_attachment_id)
            if attachment and attachment.user_id == meal.user_id and attachment.image_upload_id \
                    and attachment.image_upload_id not in image_ids:
                data['image_urls'].append(f'/api/meals/images/{attachment.image_upload_id}')
        for entry, item in zip(data['items'], meal.items):
            entry.update(consumption_ratio=item.consumption_ratio, version=item.version,
                         chat_editable=True,
                         consumption_editable=supports_consumption_edit(item),
                         effective_multiplier=item.serving_multiplier * item.consumption_ratio)
    return data


# 한국 날짜로 오늘 식단을 조회·합산하고 저장된 목표와 비교한다. 남은 칼로리는 0 미만으로 표시하지 않는다.
def get_today_status(db, user_id, instant=None):
    today = korean_date(instant or datetime.now(timezone.utc))
    # 히스토리 API의 조회 개수 제한 없이 월 범위 전체를 조회해 집계 누락을 방지한다.
    meals = db.scalars(select(Meal).where(Meal.user_id == user_id, Meal.deleted_at.is_(None), Meal.meal_date == today)
                       .order_by(Meal.created_at.desc())).all()
    totals = {key: round(sum((item.nutrition.get(key) or 0) for meal in meals for item in meal.items), 2) for key in NUTRIENTS}
    profile = db.get(Profile, user_id)
    # 과거 CSV나 임의 기본값 대신 회원이 저장한 현재 프로필 목표를 읽는다.
    target = profile.calculation['target_calories'] if profile else None
    return {'date': str(today), 'timezone': 'Asia/Seoul', 'totals': totals,
            'target_calories': target,
            'remaining_calories': max(0, round(target - totals['cal'], 2)) if target else None,
            # 탄단지는 승인된 비율, 당류·나트륨은 추천 엔진과 같은 개발 상한 기준.
            'macro_targets': calculate_macro_targets(target), 'sugar_sodium_limits': daily_limits(target),
            'meals': meals_json(db, meals),
            'message': '목표를 설정해 주세요.' if not target else
                ('오늘 섭취량이 목표를 초과했습니다.' if totals['cal'] > target else '기록한 식단을 바탕으로 다음 식사를 선택해 보세요.')}
