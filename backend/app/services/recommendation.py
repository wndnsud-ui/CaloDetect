# 추천 후보와 점수는 승인된 기존 CSV 데이터 및 Python 규칙으로 계산한다.
# 10월 15일 박근수 수정: 끼니 목표 열량, 영양 한도 위험 패널티, 안전 fallback과 근거를 일관되게 처리한다.
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ..models import Meal, RecommendationLog
from .analytics import get_today_status
from .nutrition import food_catalog
from .timezone import korean_date


logger = logging.getLogger('calodetect')

# 아래 점수 기준은 이번 추천 고도화에 사용되는 개발 기본값이며 확정된 운영 영양 정책이 아니다.
HIGH_PROTEIN_G = 20.0
LIGHT_MEAL_KCAL = 350.0
HEAVY_MEAL_KCAL = 700.0
# 나트륨 개발 기준은 WHO 2,000mg/day, 당류는 KDRI 2025 총 에너지의 20% 기준을 사용한다.
SODIUM_DAILY_LIMIT_MG = 2000.0
SUGAR_ENERGY_RATIO = 0.20
SOFT_THRESHOLD = 0.80
HARD_THRESHOLD = 1.20
MEAL_FIT_WEIGHT = 1.0
MEAL_TARGET_RATIO = {
    'breakfast': 0.25,
    'lunch': 0.30,
    'dinner': 0.30,
    'snack': 0.15,
}
CALORIE_BANDS = (
    ('light', '가벼운 메뉴'),
    ('medium', '보통 열량'),
    ('high', '고열량 메뉴'),
)


# 일일 누적량과 후보 메뉴를 합산해 영양 한도 대비 위험 수준을 0~1 점수로 반환한다.
def calculate_limit_fit(
    today_total: float,
    menu_value: float,
    limit: float,
    soft: float = SOFT_THRESHOLD,
    hard: float = HARD_THRESHOLD,
) -> float | None:
    after = today_total + menu_value
    safe_limit = max(limit, 1.0)

    if after <= safe_limit * soft:
        return 1.0
    if after >= safe_limit * hard:
        return None

    denominator = max(safe_limit * (hard - soft), 1.0)
    score = 1.0 - (after - safe_limit * soft) / denominator
    return round(max(0.0, min(1.0, score)), 4)


# 일일 목표와 남은 열량에서 선택한 끼니에 사용할 비교 목표치를 계산한다.
def calculate_meal_target(
    target_calories: float,
    remaining_calories: float,
    meal_type: str,
) -> float:
    ratio = MEAL_TARGET_RATIO.get(meal_type, 0.30)
    base_target = target_calories * ratio
    return max(1.0, min(base_target, max(remaining_calories, 1.0)))


# 아침·간식에는 가벼운 메뉴를 우선하고 점심·저녁은 추가 감점을 적용하지 않는다.
def calculate_meal_fit(meal_type: str, food_calories: float) -> float:
    if meal_type not in ('breakfast', 'snack'):
        return 1.0
    if food_calories <= LIGHT_MEAL_KCAL:
        return 1.0
    if food_calories >= HEAVY_MEAL_KCAL:
        return 0.0
    return round(
        1.0 - (food_calories - LIGHT_MEAL_KCAL)
        / (HEAVY_MEAL_KCAL - LIGHT_MEAL_KCAL),
        4,
    )


def recently_consumed_food_ids(db, user_id: int, today=None) -> set[int]:
    """오늘을 포함한 최근 7일의 식단 기록에서 음식 class_id를 모은다."""
    today = today or korean_date(datetime.now(timezone.utc))
    start_date = today - timedelta(days=6)
    meals = db.scalars(
        select(Meal).where(
            Meal.user_id == user_id,
            Meal.meal_date >= start_date,
            Meal.meal_date <= today,
        )
    ).all()
    return {
        item.food_id
        for meal in meals
        for item in meal.items
        # 섭취 비율 0(안 먹음)으로 기록한 음식은 먹은 음식으로 보지 않는다. 기존 행은 비율 1.0이라 결과 동일.
        if item.consumption_ratio > 0
    }


def calorie_band(calories: float) -> str:
    if calories <= 350:
        return 'light'
    if calories <= 700:
        return 'medium'
    return 'high'


def fallback_item(food: dict, band: str) -> dict:
    return {
        'class_id': food['class_id'],
        'calorie_band': band,
        'food_name': food['food_name'],
        'category': food['category'],
        'unit': food['unit'],
        'nutrition': {
            key: food[key]
            for key in ('cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium')
        },
        'reasons': [
            '일반 추천 후보가 부족해 기준 초과 가능성이 있는 대체 메뉴로 표시했습니다.',
            '당류 또는 나트륨 기준을 초과할 수 있어 섭취량 조절이 필요합니다.',
        ],
        'score': -999.0,
        'is_fallback': True,
    }


# 오늘 상태와 메뉴 조건을 평가해 3개 후보를 만들고 추천 snapshot/log를 생성한다.
def recommend_meals(db, user, filters, window, theme='balance'):
    snapshot = get_today_status(db, user.id)
    target_calories = snapshot.get('target_calories')
    # None과 0 이하 목표를 모두 막아 당류 기준 계산과 추천 점수의 잘못된 분모를 방지한다.
    if target_calories is None or target_calories <= 0:
        raise ValueError('먼저 유효한 목표 칼로리를 저장해 주세요.')

    recent_meals = db.scalars(
        select(Meal)
        .where(Meal.user_id == user.id)
        .order_by(Meal.meal_date.desc(), Meal.created_at.desc())
        .limit(window)
    ).all()
    recent_food_ids = {
        item.food_id
        for meal in recent_meals
        for item in meal.items
        if item.consumption_ratio > 0
    }
    week_food_ids = recently_consumed_food_ids(db, user.id)

    totals = snapshot.get('totals') or {}
    current_eaten_sodium = float(totals.get('sodium') or 0)
    current_eaten_sugar = float(totals.get('sugar') or 0)
    remaining_calories = float(snapshot.get('remaining_calories') or 0)
    daily_sugar_limit = max(target_calories * SUGAR_ENERGY_RATIO / 4.0, 1.0)
    meal_type = getattr(filters, 'meal_type', 'lunch') or 'lunch'
    exclude_foods = set(getattr(filters, 'exclude_foods', [])) | week_food_ids
    meal_target = calculate_meal_target(
        target_calories,
        remaining_calories,
        meal_type,
    )

    ranked = []
    excluded_by_limits = []

    # 기존 CSV 외의 임의 음식이나 수치를 만들지 않고 각 후보의 현재 데이터만 평가한다.
    for food in food_catalog():
        if food['class_id'] in exclude_foods:
            continue

        # 결측 당류·나트륨은 0으로 간주하지 않는다. 안전한 메뉴로 오인하지 않도록 건너뛴다.
        if food.get('sodium') is None or food.get('sugar') is None:
            logger.warning(
                'recommendation skipped: nutrition missing',
                extra={'class_id': food.get('class_id')},
            )
            continue

        sodium_fit = calculate_limit_fit(
            current_eaten_sodium,
            food['sodium'],
            SODIUM_DAILY_LIMIT_MG,
        )
        sugar_fit = calculate_limit_fit(
            current_eaten_sugar,
            food['sugar'],
            daily_sugar_limit,
        )

        # 120% 이상인 메뉴는 우선 일반 후보에서 제외하고, 필요하면 경고 fallback으로만 검토한다.
        if sodium_fit is None or sugar_fit is None:
            excess_ratio = max(
                (current_eaten_sodium + food['sodium']) / SODIUM_DAILY_LIMIT_MG,
                (current_eaten_sugar + food['sugar']) / daily_sugar_limit,
            )
            excluded_by_limits.append({'food': food, 'excess_ratio': excess_ratio})
            continue

        if remaining_calories <= 0:
            calorie_fit = 1.0 - min(1.0, food['cal'] / 600.0)
        else:
            calorie_fit = 1.0 - (
                abs(food['cal'] - meal_target)
                / max(meal_target, food['cal'], 1.0)
            )

        repeat_penalty = 1.0 if food['class_id'] in recent_food_ids else 0.0
        meal_fit = calculate_meal_fit(meal_type, food['cal']) * MEAL_FIT_WEIGHT
        theme_bonus = 0.0
        if theme == 'protein':
            theme_bonus = min(1.0, food['protein'] / HIGH_PROTEIN_G)
        elif theme == 'light':
            theme_bonus = (
                1.0
                if food['cal'] <= LIGHT_MEAL_KCAL
                else max(0.0, 1.0 - (food['cal'] - LIGHT_MEAL_KCAL) / LIGHT_MEAL_KCAL)
            )

        # 건강 한도 위험은 선호도나 테마 보너스로 쉽게 상쇄되지 않도록 점수에서 직접 차감한다.
        nutrition_risk_penalty = (1.0 - sodium_fit) + (1.0 - sugar_fit)
        total_score = (
            calorie_fit
            - repeat_penalty
            + meal_fit
            + theme_bonus
            - nutrition_risk_penalty
        )

        if remaining_calories <= 0:
            reasons = ['오늘 목표 열량을 채워 추가 열량이 적은 메뉴를 우선 비교했습니다.']
        else:
            reasons = ['오늘 섭취량과 끼니 목표 열량을 반영했습니다.']
            reasons.append(
                '끼니 목표 열량에 가까운 메뉴입니다.'
                if abs(food['cal'] - meal_target) <= meal_target * 0.25
                else '끼니별 목표 열량에 맞춰 비교한 메뉴입니다.'
            )
        if sodium_fit < 1.0:
            reasons.append('오늘 나트륨 섭취량을 고려하면 이 메뉴는 섭취량 조절이 필요합니다.')
        if sugar_fit < 1.0:
            reasons.append('오늘 당류 섭취량을 고려하면 추가 당류 섭취에 주의가 필요합니다.')
        reasons.append(
            '최근 식사에 기록한 음식입니다.'
            if repeat_penalty
            else '최근 식사와 중복이 적습니다.'
        )
        if theme == 'protein':
            reasons.append('단백질 섭취를 보완하는 기준으로 선택했습니다.')
        elif theme == 'light':
            reasons.append('상대적으로 가벼운 열량의 메뉴를 우선했습니다.')

        ranked.append({
            'class_id': food['class_id'],
            'calorie_band': calorie_band(food['cal']),
            'food_name': food['food_name'],
            'category': food['category'],
            'unit': food['unit'],
            'nutrition': {
                key: food[key]
                for key in ('cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium')
            },
            'reasons': reasons,
            'score': round(total_score, 4),
            'is_fallback': False,
        })

    # 점수 동점은 class_id 오름차순으로 정렬해 동일한 입력에 재현 가능한 결과를 만든다.
    ranked.sort(key=lambda item: (-item['score'], item['class_id']))

    # 추천마다 저·중·고 열량 구간을 하나씩 반환하며, 구간 후보가 없을 때만 같은 구간 fallback을 쓴다.
    selected = []
    for band, label in CALORIE_BANDS:
        candidate = next(
            (item for item in ranked if item['calorie_band'] == band),
            None,
        )
        if candidate is None:
            fallback = next(
                (
                    entry
                    for entry in sorted(
                        excluded_by_limits,
                        key=lambda value: (value['excess_ratio'], value['food']['class_id']),
                    )
                    if calorie_band(entry['food']['cal']) == band
                ),
                None,
            )
            if fallback is not None:
                candidate = fallback_item(fallback['food'], band)
        if candidate is None:
            raise ValueError(
                f'현재 제외 조건을 적용한 {label} 추천 메뉴가 없습니다. '
                '다른 메뉴를 추천할 후보가 부족합니다.'
            )
        selected.append(candidate)

    # 사용자 경고는 실제 최종 후보에 fallback 메뉴가 포함됐을 때만 표시한다.
    used_fallback = any(item['is_fallback'] for item in selected)
    notice = (
        '오늘 나트륨 또는 당류 섭취량이 높아 경고형 대체 메뉴가 포함되었습니다. '
        '가능하면 양념과 국물 섭취량을 줄여 주세요.'
        if used_fallback
        else '최근 7일간 기록한 음식은 제외하고 현재 섭취 기록을 반영해 추천했습니다.'
    )

    # 추천 당시 snapshot과 내부 점수를 로그에 보존하되 내부 점수·flag는 응답에서 숨긴다.
    log = RecommendationLog(
        user_id=user.id,
        nutrition_snapshot=snapshot,
        recommendation_json=selected,
    )
    db.add(log)
    db.flush()
    response_items = [
        {
            **{
                key: value
                for key, value in item.items()
                if key not in ('score', 'is_fallback')
            },
            **(
                {'warning': '당류 또는 나트륨 기준 초과 가능'}
                if item['is_fallback']
                else {}
            ),
        }
        for item in selected
    ]
    return {
        'id': log.id,
        'items': response_items,
        'snapshot': snapshot,
        'mode': 'development_default',
        'notice': notice,
    }
