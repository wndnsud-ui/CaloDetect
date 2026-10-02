from sqlalchemy import select
from ..models import Meal, RecommendationLog
from .nutrition import food_catalog
from .analytics import get_today_status


def recommend_meals(db, user, filters, window):
    snapshot = get_today_status(db, user.id)
    if snapshot['target_calories'] is None:
        raise ValueError('먼저 목표 칼로리를 저장해 주세요.')
    recent = db.scalars(select(Meal).where(Meal.user_id == user.id)
                        .order_by(Meal.meal_date.desc(), Meal.created_at.desc()).limit(window)).all()
    recent_foods = {item.food_id for meal in recent for item in meal.items}
    remaining = snapshot['remaining_calories']
    ranked = []
    for food in food_catalog():
        if food['class_id'] in filters.exclude_foods:
            continue
        fit = 1 - abs(food['cal'] - remaining) / max(remaining, food['cal'], 1)
        preference = 1 if food['category'] in filters.preferred_categories else 0
        repeat = 1 if food['class_id'] in recent_foods else 0
        score = fit + preference - repeat
        reasons = ['기존 영양 데이터의 기준량으로 계산했습니다.']
        reasons.append('남은 칼로리 범위 안의 음식입니다.' if food['cal'] <= remaining
                       else '남은 칼로리를 초과하므로 섭취량을 조절해 주세요.')
        reasons.append('최근 식사와 중복이 적습니다.' if not repeat else '최근에 기록한 음식입니다.')
        if preference:
            reasons.append('선호한 음식 분류입니다.')
        ranked.append({'class_id': food['class_id'], 'food_name': food['food_name'],
            'category': food['category'], 'unit': food['unit'],
            'nutrition': {k: food[k] for k in ['cal','carbs','protein','fat','sugar','sodium']},
            'reasons': reasons, 'score': round(score, 4)})
    ranked.sort(key=lambda r: (-r['score'], r['class_id']))
    if len(ranked) < 3:
        raise ValueError('제외 조건 때문에 후보가 3개 미만입니다. 제외 음식을 줄여주세요.')
    selected, categories = [], set()
    for item in ranked:
        if item['category'] not in categories:
            selected.append(item); categories.add(item['category'])
        if len(selected) == 3:
            break
    for item in ranked:
        if len(selected) == 3:
            break
        if item not in selected:
            selected.append(item)
    log = RecommendationLog(user_id=user.id, nutrition_snapshot=snapshot, recommendation_json=selected)
    db.add(log); db.flush()
    # Internal ranking scores never appear in the public result.
    return {'id': log.id, 'items': [{k:v for k,v in item.items() if k != 'score'} for item in selected],
            'snapshot': snapshot, 'mode': 'development_default',
            'notice': '기존 CSV 기반 개발 추천입니다. 탄단지 목표·당류/나트륨 기준·끼니 적합성은 정책 미정으로 평가하지 않습니다.'}
