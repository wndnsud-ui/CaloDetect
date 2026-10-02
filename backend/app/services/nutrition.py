from functools import lru_cache
from data_config import NUTRITION_PATH, NUMERIC_COLUMNS, load_nutrition_frame


@lru_cache(maxsize=1)
def food_catalog():
    # Existing class_id/food_name mapping, approved existing CSV, unchanged.
    return load_nutrition_frame().to_dict(orient='records')


def calculate_nutrition(class_id, multiplier):
    food = next((f for f in food_catalog() if f['class_id'] == class_id), None)
    if food is None:
        raise ValueError('음식 클래스를 찾을 수 없습니다.')
    return {'class_id': class_id, 'food_name': food['food_name'],
            'unit': food['unit'], 'serving_multiplier': multiplier,
            'nutrition_source': NUTRITION_PATH.name,
            'nutrition': {key: round(food[key] * multiplier, 2) for key in NUMERIC_COLUMNS}}
