# 회원별 식단 영양 합계와 한국 시간 기준 일간·월간 분석.
# 저장된 영양 스냅샷을 집계하며 월 평균은 실제 기록일만 포함하고 미기록일은 null로 구분한다.
from datetime import date, datetime, timezone
from calendar import monthrange
from sqlalchemy import select
from ..models import Meal, Profile, Detection
from sqlalchemy.orm import object_session
from .timezone import korean_date

NUTRIENTS = ['cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium']


# 한 달 전체 회원 식단을 조회해 날짜별 합계를 만들고 기록된 날만 분모로 월 평균을 계산한다.
def get_month_status(db, user_id, year, month):
    # 윤년과 월별 길이를 반영해 해당 월의 마지막 날짜를 얻는다.
    days = monthrange(year, month)[1]
    # 히스토리 API의 조회 개수 제한 없이 월 범위 전체를 조회해 집계 누락을 방지한다.
    meals = db.scalars(select(Meal).where(Meal.user_id == user_id,
        Meal.meal_date >= date(year, month, 1), Meal.meal_date <= date(year, month, days))).all()
    records = []
    for day in range(1, days + 1):
        current = date(year, month, day)
        entries = [meal for meal in meals if meal.meal_date == current]
        # 기록일은 영양 스냅샷을 합산하고 미기록일은 None으로 둬 0 섭취와 구분한다.
        totals = {key: round(sum(item.nutrition[key] for meal in entries for item in meal.items), 2)
                  for key in NUTRIENTS} if entries else None
        records.append({'date': str(current), 'totals': totals,
                        'meals': [meal_json(meal) for meal in entries]})
    # 평균 분모에는 식단이 하나 이상 기록된 날만 넣는다. 일부 식사만 기록한 날도 기록일이다.
    recorded = [record for record in records if record['totals'] is not None]
    averages = {key: round(sum(record['totals'][key] for record in recorded) / len(recorded), 2)
                for key in NUTRIENTS} if recorded else None
    return {'timezone': 'Asia/Seoul', 'days': records, 'recorded_days': len(recorded),
            'averages': averages}


# 식단 항목과 같은 소유자의 탐지 이미지를 응답으로 직렬화하며 동일 이미지 그룹은 한 번만 포함한다.
def meal_json(meal):
    db = object_session(meal)
    image_ids = []
    for item in meal.items:
        detection = db.get(Detection, item.detection_log_id) if db and item.detection_log_id else None
        # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
        # 연결된 탐지의 소유자가 식단 소유자와 같은 경우만 이미지 URL에 포함하고 중복 사진은 제거한다.
        if detection and detection.user_id == meal.user_id and detection.image_group_id not in image_ids:
            image_ids.append(detection.image_group_id)
    return {'id': meal.id, 'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type,
            'image_urls': [f'/api/meals/images/{image_id}' for image_id in image_ids],
            'items': [{'id': i.id, 'class_id': i.food_id, 'food_name': i.corrected_label,
                       'detection_id': i.detection_log_id, 'serving_multiplier': i.serving_multiplier,
                       'nutrition': i.nutrition} for i in meal.items]}


# 한국 날짜로 오늘 식단을 조회·합산하고 저장된 목표와 비교한다. 남은 칼로리는 0 미만으로 표시하지 않는다.
def get_today_status(db, user_id, instant=None):
    today = korean_date(instant or datetime.now(timezone.utc))
    # 히스토리 API의 조회 개수 제한 없이 월 범위 전체를 조회해 집계 누락을 방지한다.
    meals = db.scalars(select(Meal).where(Meal.user_id == user_id, Meal.meal_date == today)
                       .order_by(Meal.created_at.desc())).all()
    totals = {key: round(sum(item.nutrition[key] for meal in meals for item in meal.items), 2) for key in NUTRIENTS}
    profile = db.get(Profile, user_id)
    # 과거 CSV나 임의 기본값 대신 회원이 저장한 현재 프로필 목표를 읽는다.
    target = profile.calculation['target_calories'] if profile else None
    return {'date': str(today), 'timezone': 'Asia/Seoul', 'totals': totals,
            'target_calories': target,
            'remaining_calories': max(0, round(target - totals['cal'], 2)) if target else None,
            # 미확정 탄단지 목표와 당류/나트륨 제한은 숫자를 만들어 표시하지 않는다.
            'macro_targets': None, 'sugar_sodium_limits': None,
            'meals': [meal_json(m) for m in meals],
            'message': '목표를 설정해 주세요.' if not target else
                ('오늘 섭취량이 목표를 초과했습니다.' if totals['cal'] > target else '기록한 식단을 바탕으로 다음 식사를 선택해 보세요.')}
