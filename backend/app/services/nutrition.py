# 승인된 기존 CSV를 조회하고 기준량 배율로 여섯 가지 영양 수치를 계산한다.
# 원본 class_id·food_name·unit을 유지하며 LLM 추정이나 새로운 음식 매핑을 사용하지 않는다.
from functools import lru_cache
from data_config import NUTRITION_PATH, NUMERIC_COLUMNS, load_nutrition_frame


# 검증된 기존 영양 DataFrame을 레코드 목록으로 바꾸고 한 번 읽은 결과를 캐시한다.
# 프로세스 안에서 CSV 검증/읽기 결과를 한 번 캐시한다. 원본 교체 후에는 프로세스 재시작 등이 필요하다.
@lru_cache(maxsize=1)
def food_catalog():
    # Existing class_id/food_name mapping, approved existing CSV, unchanged.
    return load_nutrition_frame().to_dict(orient='records')


# class_id로 기존 음식을 찾아 기준량 영양값에 배율을 곱하고 두 자리로 반올림한다.
def calculate_nutrition(class_id, multiplier):
    # 기존 class_id로만 조회한다. 비슷한 음식명 추정이나 신규 매핑은 수행하지 않는다.
    food = next((f for f in food_catalog() if f['class_id'] == class_id), None)
    if food is None:
        raise ValueError('음식 클래스를 찾을 수 없습니다.')
    return {'class_id': class_id, 'food_name': food['food_name'],
            'unit': food['unit'], 'serving_multiplier': multiplier,
            'nutrition_source': NUTRITION_PATH.name,
            # 각 CSV 수치에 배율을 곱한다. cal은 kcal, sodium은 mg, 나머지 영양소는 g 단위를 유지한다.
            'nutrition': {key: round(food[key] * multiplier, 2) for key in NUMERIC_COLUMNS}}
