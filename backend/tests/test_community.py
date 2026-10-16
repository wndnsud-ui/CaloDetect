"""커뮤니티 권한·원장·원본 반영·사진·커서 회귀. PostgreSQL은 별도 임시 schema 사용."""
import io
import os
import threading
from types import SimpleNamespace
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.main import app
from backend.app.models import (Meal, MealItem, User, Food, CommunityPost as Post,
    CommunityReaction as Reaction, PointTransaction as Tx, CommunityPostImage as Photo, ImageUpload, utcnow)
from backend.app.config import settings
from backend.app.services.community_rules import week_start
from backend.app.services import community as service
from backend.tests.test_p0_flow import env, account


@pytest.fixture
def users(env):
    _, engine, patch = env
    with TestClient(app) as a, TestClient(app) as b:
        a_user = account(a, f'a{uuid4().hex}@example.com')
        b_user = account(b, f'b{uuid4().hex}@example.com')
        yield a, b, a_user, b_user, engine, patch


def meal(client):
    r = client.post('/meals', json={'meal_type':'lunch', 'items':[{'class_id':0,'serving_multiplier':1}]})
    assert r.status_code == 201, r.text
    return r.json()


def post(client, saved=None, **extra):
    saved = saved or meal(client)
    r = client.post('/community/posts', json={'meal_id':saved['id'], **extra})
    assert r.status_code == 201, r.text
    return r.json()


def url(p, kind='like'):
    return f'/community/posts/{p["id"]}/reactions/{kind}'


def balance(client):
    return client.get('/community/points/me').json()['balance']


def test_sharing_privacy_catalog_live_and_eligible(users):
    a,b,au,bu,engine,_ = users
    saved = meal(a)
    choices = a.get('/community/eligible-meals').json()['items']
    choice = next(i for i in choices if i['meal_id']==saved['id'])
    assert set(choice)=={'meal_id','meal_date','meal_type','has_photo','items'}
    assert not choice['has_photo']
    assert b.get('/community/eligible-meals').json()['items']==[]
    assert b.post('/community/posts',json={'meal_id':saved['id']}).status_code==404
    p=post(a,saved,comment='  오늘의 한 끼  ')
    assert p['comment']=='오늘의 한 끼'
    assert a.get('/community/eligible-meals').json()['items']==[]
    assert a.post('/community/posts',json={'meal_id':saved['id']}).status_code==409
    public=b.get('/community/posts').json()['items'][0]
    assert public['meal_id'] is None and public['author']['is_me'] is False
    assert set(public['author'])=={'name','is_me'}
    assert b.get('/community/posts?mine=true').json()['items']==[]
    assert a.get('/community/posts?mine=true').json()['items'][0]['is_mine']
    assert not {'snapshot','snapshot_version','nutrition','items'} & set(Post.__table__.columns.keys())
    with Session(engine) as db:
        item=db.scalar(select(MealItem).where(MealItem.meal_id==saved['id']))
        food=db.get(Food,1)
        item.food_id=food.id;item.serving_multiplier=2;item.consumption_ratio=.25
        item.nutrition={k:12 for k in item.nutrition};db.commit()
        expected=(food.canonical_name,food.category,food.serving_unit)
    public=b.get('/community/posts').json()['items'][0]
    item=public['meal']['items'][0]
    assert (item['food_name'],item['category'],item['unit'])==expected
    assert item['serving_multiplier']==.5 and public['meal']['totals']['cal']==12
    assert 'detection_id' not in item
    assert a.post('/community/posts',json={'meal_id':saved['id'],'food_name':'fake'}).status_code==422


def test_reactions_original_amounts_revoke_and_repeat(users):
    a,b,_,_,engine,patch=users;p=post(a)
    assert a.post(url(p),json={}).status_code==403
    assert b.post(url(p),json={}).status_code==201
    assert b.post(url(p),json={}).status_code==409
    assert b.post(url(p,'recommend'),json={}).status_code==201
    assert (balance(a),balance(b))==(4,2)
    patch.setattr(settings,'community_recommend_received_points',99)
    patch.setattr(settings,'community_reaction_given_points',99)
    before=b.get(url(p,'recommend')+'/revoke-preview').json()
    assert before['me']==-1 and before['author']==-3
    assert (balance(a),balance(b))==(4,2)
    data=b.delete(url(p,'recommend')).json()
    assert data['deducted']=={'me':-1,'author':-3}
    assert b.delete(url(p,'recommend')).status_code==404
    assert (balance(a),balance(b))==(1,1)
    patch.setattr(settings,'community_reaction_given_points',1)
    for _ in range(3):
        assert b.delete(url(p)).status_code==200
        assert b.post(url(p),json={}).status_code==201
    assert (balance(a),balance(b))==(1,1)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Tx).where(Tx.reason=='like_received_revoked'))==3


def test_delete_net_once_reactors_unchanged_and_no_reshare(users):
    a,b,_,_,engine,_=users;saved=meal(a);p=post(a,saved)
    b.post(url(p),json={});b.delete(url(p));b.post(url(p,'recommend'),json={})
    assert b.get(f'/community/posts/{p["id"]}/delete-preview').status_code==403
    preview=a.get(f'/community/posts/{p["id"]}/delete-preview').json()
    assert preview=={'me':-3,'reactors_affected':False} and balance(a)==3
    assert a.delete(f'/community/posts/{p["id"]}').json()['deducted']=={'me':-3}
    assert (balance(a),balance(b))==(0,1)
    assert a.delete(f'/community/posts/{p["id"]}').status_code==404
    assert b.post(url(p),json={}).status_code==404
    assert b.delete(url(p,'recommend')).status_code==404
    assert a.get('/community/posts').json()['items']==[]
    assert a.get('/community/eligible-meals').json()['items']==[]
    r=a.post('/community/posts',json={'meal_id':saved['id']})
    assert r.status_code==409 and '다시 공유할 수 없어요' in r.text
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Tx).where(Tx.reason=='post_deleted_revoked'))==1


def test_cursor_same_time_invalid_and_csrf(users):
    a,b,_,_,engine,_=users
    posts=[post(a) for _ in range(5)]
    with Session(engine) as db:
        for p in db.scalars(select(Post)):p.created_at=utcnow().replace(microsecond=0)
        db.commit()
    ids=[];cursor=''
    while True:
        data=b.get('/community/posts',params={'limit':2,'cursor':cursor}).json()
        ids.extend(i['id'] for i in data['items']);cursor=data['next_cursor']
        if cursor is None:break
    assert len(ids)==len(set(ids))==5
    assert b.get('/community/posts?cursor=bad').status_code==422
    assert b.get('/community/posts?limit=0').status_code==422
    token=b.headers.pop('X-CSRF-Token')
    assert b.post(url(posts[0]),json={}).status_code==403
    assert b.delete(url(posts[0])).status_code==403
    b.headers['X-CSRF-Token']=token
    with TestClient(app) as anon:
        assert anon.get('/community/posts').status_code==401


def test_weekly_ranking_negative_current_week_and_ties(users):
    a,b,au,bu,engine,_=users;p=post(a)
    b.post(url(p,'recommend'),json={})
    with Session(engine) as db:
        for tx in db.scalars(select(Tx)):tx.created_at=week_start()-timedelta(days=1)
        db.add(Tx(user_id=au['id'],amount=5,reason='like_received'))
        db.add(Tx(user_id=bu['id'],amount=5,reason='like_received'));db.commit()
    data=a.get('/community/ranking/weekly').json()
    assert [i['rank'] for i in data['items']]==[1,1]
    assert all(set(i)=={'rank','name','points','is_me'} for i in data['items'])
    assert balance(a)==8
    b.delete(url(p,'recommend'))
    data=a.get('/community/ranking/weekly').json()
    assert data['me']['points']==2 and data['me']['deducted_this_week']==-3


def test_zero_amount_and_unique_ledger(users):
    a,b,au,bu,engine,patch=users;p=post(a)
    patch.setattr(settings,'community_like_received_points',0)
    patch.setattr(settings,'community_reaction_given_points',0)
    b.post(url(p),json={});b.delete(url(p))
    assert balance(a)==balance(b)==0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Tx))==0
        tx=dict(user_id=au['id'],amount=1,reason='like_received',reaction_id=str(uuid4()),post_id=p['id'])
        db.add(Tx(**tx));db.commit();db.add(Tx(**tx))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
        tx.update(reason='post_deleted_revoked',reaction_id=None)
        db.add(Tx(**tx));db.commit();db.add(Tx(**tx))
        with pytest.raises(IntegrityError):db.commit()


def test_public_photo_metadata_and_rollback(users,tmp_path,monkeypatch):
    from backend.app.models_chat import ChatAttachment
    a,b,au,bu,engine,patch=users
    saved=meal(a)
    root=tmp_path/'uploads';root.mkdir();patch.setattr(settings,'image_storage_dir',str(root))
    source=root/'original.jpg';exif=Image.Exif();exif[270]='private caption'
    Image.new('RGB',(10,10),'red').save(source,exif=exif)
    with Session(engine) as db:
        image=ImageUpload(user_id=au['id'],image_path=source.name);db.add(image);db.flush()
        # 탐지 ID와 원본 경로는 공개 응답에 포함하지 않는다.
        from backend.app.models import Detection
        d=Detection(user_id=au['id'],image_group_id=image.id,image_path=source.name,predicted_label='test',
            confidence=.9,bbox=[],model_version='test');db.add(d);db.flush()
        item=db.scalar(select(MealItem).where(MealItem.meal_id==saved['id']));item.detection_log_id=d.id
        image_id=image.id;db.commit()
    assert a.get('/community/eligible-meals').json()['items'][0]['has_photo']
    assert b.get('/meals/images/'+image_id).status_code==404
    p=post(a,saved,show_photo=True)
    r=b.get(p['image_urls'][0].removeprefix('/api'))
    assert r.status_code==200 and r.headers['cache-control']=='private, no-store'
    with Image.open(io.BytesIO(r.content)) as clean:assert not clean.getexif()
    assert b.get(p['image_urls'][0].removeprefix('/api').rsplit('/',1)[0]+'/wrong').status_code==404
    a.delete('/community/posts/'+p['id'])
    assert b.get(p['image_urls'][0].removeprefix('/api')).status_code==404
    assert source.exists()
    saved2=meal(a)
    assert a.post('/community/posts',json={'meal_id':saved2['id'],'show_photo':True}).status_code==422
    with Session(engine) as db:
        m=db.get(Meal,saved2['id']);item=m.items[0]
        d=Detection(user_id=au['id'],image_group_id=image_id,image_path=source.name,predicted_label='test',confidence=.9,bbox=[],model_version='test')
        db.add(d);db.flush();item.detection_log_id=d.id;db.commit()
    before=set((root/'community').iterdir())
    with Session(engine) as db:
        user=db.get(User,au['id'])
        from backend.app.schemas import CommunityPostRequest
        def fail():raise RuntimeError('injected commit failure')
        monkeypatch.setattr(db,'commit',fail)
        with pytest.raises(RuntimeError):service.create_post(db,user,CommunityPostRequest(meal_id=saved2['id'],show_photo=True))
    assert set((root/'community').iterdir())==before and source.exists()
    with Session(engine) as db:assert db.scalar(select(Post).where(Post.meal_id==saved2['id'])) is None


@pytest.mark.skipif(os.environ.get('RUN_POSTGRES_TESTS')!='1',reason='PostgreSQL 행 잠금 필수; SQLite 동시성 미검증')
@pytest.mark.parametrize('first_operation',['add','revoke','delete','same_revoke'])
def test_ordered_concurrent_mutations(users,first_operation):
    """A를 commit 직전에 멈추고 B가 실제 잠금 대기하는지 확인한다."""
    a,b,au,bu,engine,_=users;p=post(a)
    if first_operation in ('revoke','delete','same_revoke'):b.post(url(p,'recommend'),json={})
    ready,release,done=threading.Event(),threading.Event(),threading.Event()
    results,errors={},{}
    def first():
        try:
            with Session(engine) as db:
                real_commit=db.commit
                def paused_commit():
                    db.flush();ready.set()
                    if not release.wait(8):raise RuntimeError('commit barrier timeout')
                    real_commit()
                db.commit=paused_commit
                if first_operation=='delete':results['a']=service.delete_post(db,SimpleNamespace(id=au['id']),p['id'])
                else:results['a']=service.react(db,SimpleNamespace(id=bu['id']),p['id'],'recommend',first_operation!='add')
        except Exception as e:errors['a']=e;ready.set()
    def second():
        try:
            with Session(engine) as db:
                if first_operation=='same_revoke':results['b']=service.react(db,SimpleNamespace(id=bu['id']),p['id'],'recommend',True)
                else:results['b']=service.delete_post(db,SimpleNamespace(id=au['id']),p['id'])
        except Exception as e:errors['b']=e
        finally:done.set()
    t1=threading.Thread(target=first);t2=threading.Thread(target=second)
    t1.start()
    try:
        assert ready.wait(5) and 'a' not in errors
        t2.start()
        assert not done.wait(.5),'B must wait for A post lock'
    finally:
        release.set();t1.join(10)
        if t2.ident:t2.join(10)
    assert not t1.is_alive() and not t2.is_alive() and 'a' not in errors
    if first_operation in ('delete','same_revoke'):
        assert errors['b'].status_code==404
    else:
        assert not errors
        assert results['b']['deducted']['me']==(-3 if first_operation=='add' else 0)
    with Session(engine) as db:
        assert db.scalar(select(func.coalesce(func.sum(Tx.amount),0)).where(Tx.user_id==au['id']))==0
        assert db.scalar(select(func.count()).select_from(Tx).where(Tx.reason=='post_deleted_revoked'))<=1
        if first_operation in ('revoke','same_revoke'):
            assert db.scalar(select(func.count()).select_from(Tx).where(Tx.reason=='recommend_received_revoked'))==1


def test_migration_round_trip(env):
    import importlib
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    _,engine,_=env
    module=importlib.import_module('backend.migrations.versions.20261016_01_community')
    schema=engine.get_execution_options().get('schema_translate_map',{}).get(None)
    with engine.begin() as conn:
        ctx=MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.downgrade()
            before=set(inspect(conn).get_table_names(schema=schema))
            module.upgrade()
            after=set(inspect(conn).get_table_names(schema=schema))
            assert after-before=={'community_posts','community_post_images','community_reactions','point_transactions'}
            module.downgrade()
            assert set(inspect(conn).get_table_names(schema=schema))==before
            module.upgrade()
