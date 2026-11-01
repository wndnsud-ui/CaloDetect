# '가벼운 식단' 추천에 더하는 다이어트형 한 끼 후보. 식약처 음식 DB(nutrition_foods)에서 고른 식품코드만 쓰고
# 영양값은 DB의 1회 제공량 값을 그대로 쓴다. 기존 150개 class_id 카탈로그와는 섞지 않는다(class_id 없음, food_ref 사용).
# 각 항목: (식품코드, 화면 표시 이름, 분류, 맛집 검색어)
from sqlalchemy import select

from ..models import NutritionFood

DIET_FOODS = (
    ('mfds:D214-640000000-0004', '그릴드치킨 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0023', '시저치킨 샐러드', '샐러드', '샐러드'),
    ('mfds:D114-640080000-0001', '닭가슴살 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0047', '콥샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0022', '스파이시쉬림프 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0010', '쉬림프에그 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0036', '머쉬룸불고기 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0034', '리코타그릴치킨 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0001', '과카몰리치킨 샐러드', '샐러드', '샐러드'),
    ('mfds:D114-640310000-0001', '참치 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0024', '오렌지 그릴치킨 샐러드', '샐러드', '샐러드'),
    ('mfds:D214-640000000-0006', '두부포케 샐러드', '포케', '포케'),
    ('mfds:D103-167000000-0001', '월남쌈', '쌈·말이', '월남쌈'),
    ('mfds:D106-287150000-0001', '버섯 샤브샤브', '샤브샤브', '샤브샤브'),
    ('mfds:D106-287180000-0001', '소고기 샤브샤브', '샤브샤브', '샤브샤브'),
    ('mfds:D103-152380000-0001', '메밀국수', '국수', '메밀국수'),
    ('mfds:D501-015000000-0001', '묵밥', '밥', '묵밥'),
    ('mfds:D601-018370000-0001', '열무 비빔밥', '밥', '비빔밥'),
    ('mfds:D101-007480000-0001', '채소김밥', '김밥', '김밥'),
    ('mfds:D406-276000000-0001', '두부전골', '전골·찌개', '두부전골'),
    ('mfds:D406-282180000-0001', '소고기 버섯전골', '전골·찌개', '버섯전골'),
    ('mfds:D406-310130000-0001', '바지락 순두부찌개', '전골·찌개', '순두부'),
    ('mfds:D705-213000000-0001', '닭곰탕', '국·탕', '닭곰탕'),
    ('mfds:D504-181090000-0001', '채소 닭죽', '죽', '죽'),
    ('mfds:D110-470000000-0001', '마파두부', '중식', '마파두부'),
)
NUTRIENTS = ('cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium')


# rank_candidates가 기존 카탈로그와 같은 형태로 평가할 수 있게 음식 dict로 만든다. DB에 없는 코드는 건너뛴다.
def diet_candidates(db):
    rows = {row.id: row for row in db.scalars(
        select(NutritionFood).where(NutritionFood.id.in_([code for code, *_ in DIET_FOODS]))).all()}
    foods = []
    for code, name, category, place_query in DIET_FOODS:
        row = rows.get(code)
        nutrition = (row.nutrition or {}) if row else {}
        if row is None or nutrition.get('cal') is None:
            continue
        foods.append({
            'class_id': None, 'food_ref': code, 'food_name': name, 'category': category,
            'unit': f'1인분 (약 {row.serving_amount:g}{row.serving_unit})', 'place_query': place_query,
            **{key: None if nutrition.get(key) is None else round(float(nutrition[key]), 1) for key in NUTRIENTS},
        })
    return foods
