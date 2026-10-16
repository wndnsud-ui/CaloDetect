from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models import CommunityPost, Meal, User, PointTransaction
from backend.scripts.seed_community_demo import seed
from backend.scripts.seed_local_test_account import TEST_ACCOUNT_EMAIL
from backend.app.services.community import delete_post
from backend.tests.test_p0_flow import env, account


def test_demo_repeat_preserves_existing_and_deleted_content(env):
    client, engine, patch = env
    patch.setattr(settings, 'app_env', 'development')
    patch.setattr(settings, 'local_test_signup', True)
    patch.setattr(settings, 'frontend_origin', 'http://localhost:5174')
    user = account(client, TEST_ACCOUNT_EMAIL)
    original = client.post('/meals', json={'meal_type':'lunch','items':[{'class_id':0,'serving_multiplier':1}]}).json()
    with Session(engine) as db:
        assert seed(db)=={'added_posts':10,'added_reactions':45}
        assert seed(db)=={'added_posts':0,'added_reactions':0}
        assert db.scalar(select(func.count()).select_from(CommunityPost))==10
        assert db.scalar(select(func.count()).select_from(Meal))==11
        assert db.get(Meal,original['id']).items[0].nutrition==original['items'][0]['nutrition']
        current=db.get(User,user['id'])
        own=db.scalar(select(CommunityPost).where(CommunityPost.user_id==current.id))
        delete_post(db,current,own.id)
        balance=db.scalar(select(func.sum(PointTransaction.amount)).where(PointTransaction.user_id==current.id))
        assert seed(db)=={'added_posts':0,'added_reactions':0}
        assert db.get(CommunityPost,own.id).deleted_at is not None
        assert db.scalar(select(func.sum(PointTransaction.amount)).where(PointTransaction.user_id==current.id))==balance
