"""로컬 커뮤니티 시연 데이터. 기존 기록 보존, 재실행 중복·취소된 반응 복원 없음.

실행: python -m backend.scripts.seed_community_demo
"""
import secrets
from datetime import timedelta
from uuid import uuid5, NAMESPACE_URL
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.app.accounts import hash_password, LOCAL_TEST_CONSENT
from backend.app.db import get_engine
from backend.app.models import User, Meal, MealItem, Food, CommunityPost, utcnow
from backend.app.schemas import CommunityPostRequest
from backend.app.services.community import create_post, react
from backend.app.services.nutrition import calculate_nutrition
from backend.app.services.community_rules import KST
from backend.scripts.seed_local_test_account import local_test_account_enabled, TEST_ACCOUNT_EMAIL

PLANS = [
    (0, 'lunch', ['잡곡밥', '된장찌개', '불고기', '배추김치', '시금치나물', '깍두기'], '밥·국·반찬을 골고루 담은 점심이에요. 오늘도 든든하게 먹고 기록 완료!'),
    (1, 'lunch', ['비빔밥'], '바쁜 날에는 비빔밥 한 그릇. 한 끼를 간편하게 챙겼어요.'),
    (2, 'dinner', ['배추김치', '시금치나물', '깍두기'], '집에 있는 반찬 구성부터 기록해 봤어요. 구성 보기를 누르면 음식별 섭취량을 볼 수 있어요.'),
    (3, 'dinner', ['삼계탕'], '따뜻한 삼계탕으로 저녁을 먹었어요. 오늘의 식단도 차곡차곡 기록 중이에요.'),
    (4, 'breakfast', ['잡곡밥', '된장찌개', '배추김치'], '아침도 거르지 않고 챙기기. 밥은 반 공기, 국과 반찬을 곁들였어요.'),
    (1, 'dinner', ['잡곡밥', '불고기', '배추김치'], '오늘 저녁은 집밥으로 마무리했어요.\n식사 전에 사진 찍는 습관보다 기록하는 습관부터 만들고 있어요.\n처음에는 양을 가늠하기 어려웠는데 조금씩 익숙해지네요.\n다음에는 채소 반찬도 더 챙겨 보려고 해요.\n여러분은 오늘 어떤 식사를 하셨나요?\n이 글에서는 더보기와 접기를 확인할 수 있어요.'),
    (2, 'lunch', ['잡곡밥', '된장찌개', '불고기', '비빔밥', '배추김치'], '여러 메뉴를 조금씩 나눠 먹었어요. 주메뉴가 많을 때는 요약에 외 n개로 표시돼요.'),
    (4, 'snack', ['잡곡밥', '시금치나물'], '남은 밥과 나물을 조금씩 먹고 간식으로 기록했어요.'),
]


def seed(db):
    if not local_test_account_enabled():
        raise RuntimeError('Local development test settings required')
    now = utcnow()
    foods = {f.canonical_name: f for f in db.scalars(select(Food))}
    required = {name for _, _, names, _ in PLANS for name in names}
    if required - foods.keys():
        raise RuntimeError('Existing food catalog is missing required Korean foods')
    users = []
    for index, name in enumerate(['지민', '서연', '민재', '혜진', '도윤']):
        email = f'community-demo-{index+1}@calodetect.local'
        display = f'{name} (예시)'
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and (user.name != display or user.role != 'user' or user.oauth_provider):
            raise RuntimeError('Demo account identity collision; no existing account is overwritten')
        if user is None:
            user = User(email=email, name=display, password_hash=hash_password(secrets.token_urlsafe(40)),
                        role='user', age=30, model_improvement_consent=False, service_consent_text=LOCAL_TEST_CONSENT)
            db.add(user)
        users.append(user)
    db.flush()
    local_user = db.scalar(select(User).where(User.email == TEST_ACCOUNT_EMAIL))
    # 내 게시물·내 포인트도 볼 수 있도록 기존 로컬 테스트 계정에 전용 예시 식단 2개만 추가한다.
    plans = list(PLANS)
    if local_user and local_user.role == 'user' and not local_user.oauth_provider:
        users.append(local_user)
        plans += [(5, 'lunch', ['잡곡밥', '된장찌개', '배추김치'], '내 게시물에서 확인할 수 있는 집밥 예시예요.'),
                  (5, 'dinner', ['비빔밥'], '공유·삭제·포인트 확인을 위한 비빔밥 예시예요.')]
    added = reactions = 0
    for index, (owner, kind, names, comment) in enumerate(plans):
        meal_id = str(uuid5(NAMESPACE_URL, f'calodetect-community-demo-v1:{index}'))
        existing = db.get(Meal, meal_id)
        if existing:
            if existing.user_id != users[owner].id:
                raise RuntimeError('Demo meal identity collision')
            continue  # 사용자가 삭제·수정·반응 취소한 예시는 복원하지 않는다.
        stamp = now - timedelta(hours=index*3, minutes=10)
        meal = Meal(id=meal_id, user_id=users[owner].id, meal_type=kind,
                    meal_date=stamp.astimezone(KST).date(), created_at=stamp)
        for position, name in enumerate(names):
            food = foods[name]
            multiplier = .5 if name == '잡곡밥' and kind == 'breakfast' else .3 if len(names)>4 else 1
            result = calculate_nutrition(food.id, multiplier)
            meal.items.append(MealItem(id=str(uuid5(NAMESPACE_URL, f'{meal_id}:{position}')),
                food_id=food.id, corrected_label=food.canonical_name, serving_multiplier=multiplier,
                consumption_ratio=1, nutrition=result['nutrition'], created_at=stamp+timedelta(microseconds=position)))
        db.add(meal);db.flush()
        post = create_post(db, users[owner], CommunityPostRequest(meal_id=meal.id, comment='[더미 예시] '+comment))
        db.get(CommunityPost, post['id']).created_at = stamp
        db.flush()
        for offset in range(1, min(4, len(users))):
            actor = users[(owner+offset) % len(users)]
            react(db, actor, post['id'], 'like');reactions += 1
            if (index+offset) % 2 == 0:
                react(db, actor, post['id'], 'recommend');reactions += 1
        added += 1
    db.commit()
    return {'added_posts': added, 'added_reactions': reactions}


def main():
    # 서비스의 commit도 savepoint 안에 두어 시드 전체를 한 번에 확정한다.
    with get_engine().begin() as connection:
        connection.execute(text('SELECT pg_advisory_xact_lock(20261016, 2)'))
        with Session(bind=connection, join_transaction_mode='create_savepoint') as db:
            print(seed(db))


if __name__ == '__main__':
    main()
