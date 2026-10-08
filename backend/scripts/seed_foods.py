# 기존 CSV의 음식과 영양정보를 DB 음식 카탈로그로 준비하는 seed 도구.
# 원본 class_id·food_name을 그대로 사용하고 기존 데이터 파일은 변경하지 않는다.
from sqlalchemy.orm import Session
from backend.app.db import get_engine
from backend.app.models import Food
from backend.app.services.nutrition import food_catalog


# 검증된 기존 음식 데이터를 DB에 반영하고 seed 결과를 확정한다.
def seed(db):
    for row in food_catalog():
        # 이미 있는 음식 행은 덮어쓰지 않고 누락된 기존 클래스만 채우므로 반복 실행할 수 있다.
        if db.get(Food, row['class_id']) is None:
            db.add(Food(id=row['class_id'], canonical_name=row['food_name'], display_name=row['food_name'],
                model_class=row['class_id'], category=row['category'], serving_unit=row['unit'],
                nutrition_source='CaloDetect_nutrition_all_matched.csv', active=True,
                nutrition={k:row[k] for k in ['cal','carbs','protein','fat','sugar','sodium']}))
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit()


if __name__ == '__main__':
    with Session(get_engine()) as db:
        seed(db)
    print('Food seed complete: existing 150 classes')
