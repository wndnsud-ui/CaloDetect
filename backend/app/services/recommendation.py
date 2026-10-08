# 기존 음식 CSV와 오늘의 남은 칼로리·선호 분류·최근 음식 중복을 이용한 개발용 추천.
# 서로 다른 분류를 우선해 세 후보를 고르고 추천 당시 영양 상태와 결과를 기록한다. 미확정 영양 목표와 운영 가중치를 새로 정하지 않는다.
from sqlalchemy import select
from ..models import Meal, RecommendationLog
from .nutrition import food_catalog
from .analytics import get_today_status


# 남은 칼로리 적합도 + 선호 분류 - 최근 중복으로 순위를 정하고 분류 다양성을 우선한 세 후보를 기록한다.
# 동점은 class_id로 정렬해 결과를 재현하며 공개 응답에서는 내부 score를 제거한다.
def recommend_meals(db, user, filters, window):
    snapshot = get_today_status(db, user.id)
    # 남은 칼로리 추천을 계산할 근거가 없으면 먼저 목표 설정을 요청한다.
    if snapshot['target_calories'] is None:
        raise ValueError('먼저 목표 칼로리를 저장해 주세요.')
    recent = db.scalars(select(Meal).where(Meal.user_id == user.id)
                        .order_by(Meal.meal_date.desc(), Meal.created_at.desc()).limit(window)).all()
    # 최근 N개 식단의 모든 항목을 집합으로 만들어 음식별 중복 여부를 확인한다.
    recent_foods = {item.food_id for meal in recent for item in meal.items}
    remaining = snapshot['remaining_calories']
    ranked = []
    for food in food_catalog():
        if food['class_id'] in filters.exclude_foods:
            continue
        # 남은 칼로리와 음식 기준량의 차이를 큰 값으로 정규화한다. 분모는 최소 1로 두어 0 나눗셈을 피한다.
        fit = 1 - abs(food['cal'] - remaining) / max(remaining, food['cal'], 1)
        preference = 1 if food['category'] in filters.preferred_categories else 0
        repeat = 1 if food['class_id'] in recent_foods else 0
        # 현재 개발 기본식은 적합도 + 선호 - 중복이다. 운영 가중치를 확정한 공식으로 해석하지 않는다.
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
    # 높은 점수를 우선하고 동점은 class_id 오름차순으로 결정해 후보 순서를 재현한다.
    ranked.sort(key=lambda r: (-r['score'], r['class_id']))
    # 제외 조건으로 세 후보를 만들 수 없으면 빈 추천이나 임의 음식을 생성하지 않고 조건 수정을 요청한다.
    if len(ranked) < 3:
        raise ValueError('제외 조건 때문에 후보가 3개 미만입니다. 제외 음식을 줄여주세요.')
    # 첫 순회는 서로 다른 분류를 우선 선택하고 둘째 순회는 부족한 개수를 나머지 상위 후보로 채운다.
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
    # 추천 당시 상태와 후보를 저장해 회원 선택 기록이 어느 추천에서 왔는지 추적한다.
    log = RecommendationLog(user_id=user.id, nutrition_snapshot=snapshot, recommendation_json=selected)
                 # commit 전 SQL을 반영해 생성 ID·제약 오류를 확인한다. 아직 변경을 최종 확정한 것은 아니다.
    db.add(log); db.flush()
    # Internal ranking scores never appear in the public result.
    return {'id': log.id, 'items': [{k:v for k,v in item.items() if k != 'score'} for item in selected],
            'snapshot': snapshot, 'mode': 'development_default',
            'notice': '기존 CSV 기반 개발 추천입니다. 탄단지 목표·당류/나트륨 기준·끼니 적합성은 정책 미정으로 평가하지 않습니다.'}
