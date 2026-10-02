from sqlalchemy.orm import Session
from backend.app.db import get_engine
from backend.app.models import Food
from backend.app.services.nutrition import food_catalog


def seed(db):
    for row in food_catalog():
        if db.get(Food, row['class_id']) is None:
            db.add(Food(id=row['class_id'], canonical_name=row['food_name'], display_name=row['food_name'],
                model_class=row['class_id'], category=row['category'], serving_unit=row['unit'],
                nutrition_source='CaloDetect_nutrition_all_matched.csv', active=True,
                nutrition={k:row[k] for k in ['cal','carbs','protein','fat','sugar','sodium']}))
    db.commit()


if __name__ == '__main__':
    with Session(get_engine()) as db:
        seed(db)
    print('Food seed complete: existing 150 classes')
