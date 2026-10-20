# 리워드 아이템 카탈로그(지시서 v3 §5-5)를 DB에 준비하는 seed 도구. 이미 있는 행은 덮어쓰지 않아 반복 실행할 수 있다.
from sqlalchemy.orm import Session
from backend.app.db import get_engine
from backend.app.services.rewards import ensure_items
from backend.app.services.reward_exchange import ensure_products


def seed(db):
    ensure_items(db)
    ensure_products(db)  # Stage C 건강상품(자리표시자 가격·이미지). 플래그가 꺼져 있으면 화면·API에 나오지 않는다.
    db.commit()


if __name__ == '__main__':
    with Session(get_engine()) as db:
        seed(db)
    print('Reward item seed complete')
