import pytest
import os
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.db import get_db
from backend.app.security import get_user
from backend.app.models import Base, User

@pytest.fixture
def board():
    schema=None
    if os.environ.get('RUN_POSTGRES_TESTS')=='1':
        from backend.app.db import get_engine
        base=get_engine();schema='test_'+uuid4().hex
        with base.begin() as connection: connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine=base.execution_options(schema_translate_map={None:schema})
    else:
        engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([User(id=i,name=f'Member {i}',email=f'{i}@example.com',password_hash='test',service_consent_text='test',age=25) for i in (1,2)])
        db.commit()
    actor=[1]
    def connection():
        with Session(engine) as db: yield db
    def member():
        with Session(engine) as db: return db.get(User,actor[0])
    app.dependency_overrides[get_db]=connection
    app.dependency_overrides[get_user]=member
    with TestClient(app) as client: yield client,actor
    app.dependency_overrides.clear()
    if schema:
        with base.begin() as connection: connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    else: engine.dispose()

def create(client,visibility='public',title='Lunch'):
    response=client.post('/community/posts',data={'title':title,'text':'Fresh lunch','category':'meal','visibility':visibility})
    assert response.status_code==200,response.text
    return response.json()['id']

def test_privacy_reactions_sort_and_persistence(board):
    client,actor=board
    private=create(client,'private')
    public=create(client)
    newer=create(client,title='Newer')
    actor[0]=2
    assert client.get(f'/community/posts/{private}').status_code==404
    assert client.put(f'/community/posts/{private}/reactions/like',json={'active':True}).status_code==404
    assert len(client.get('/community/posts').json()['items'])==2
    assert len(client.get('/community/posts?scope=others').json()['items'])==2
    assert client.get('/community/posts?scope=mine').json()['items']==[]
    for _ in range(2):
        assert client.put(f'/community/posts/{public}/reactions/like',json={'active':True}).json()['likes']==1
    client.put(f'/community/posts/{public}/reactions/recommend',json={'active':True})
    for sort in ('best','recommended'):
        assert client.get('/community/posts',params={'sort':sort}).json()['items'][0]['id']==public
    assert client.get('/community/posts',params={'sort':'latest'}).json()['items'][0]['id']==newer
    actor[0]=1
    post=client.get(f'/community/posts/{public}').json()
    assert post['likes']==1 and not post['liked']
    assert len(client.get('/community/posts').json()['items'])==3
    assert client.get('/community/posts?scope=others').json()['items']==[]
    assert len(client.get('/community/posts?scope=mine').json()['items'])==3
    actor[0]=2
    assert client.put(f'/community/posts/{public}/reactions/like',json={'active':False}).json()['likes']==0

def test_comments_ownership_and_delete(board):
    client,actor=board
    post=create(client)
    actor[0]=2
    assert client.post(f'/community/posts/{post}/comments',json={'text':'   '}).status_code==422
    result=client.post(f'/community/posts/{post}/comments',json={'text':'Nice!'}).json()
    comment=result['comment_items'][0]['id']
    assert result['comments']==1
    assert client.put(f'/community/posts/{post}/comments/{comment}',json={'text':'Updated'}).json()['comment_items'][0]['text']=='Updated'
    assert client.post(f'/community/posts/{post}/delete').status_code==403
    actor[0]=1
    assert client.put(f'/community/posts/{post}/comments/{comment}',json={'text':'Wrong'}).status_code==403
    assert client.post(f'/community/posts/{post}/comments/{comment}/delete').status_code==403
    actor[0]=2
    assert client.post(f'/community/posts/{post}/comments/{comment}/delete').json()['comments']==0
    actor[0]=1
    assert client.post(f'/community/posts/{post}/delete').status_code==200
    assert client.get(f'/community/posts/{post}').status_code==404

def test_photo_normalized_and_private(board,monkeypatch,tmp_path):
    from io import BytesIO
    from PIL import Image
    from backend.app import community
    monkeypatch.setattr(community,'image_root',lambda:tmp_path)
    client,actor=board
    data={'title':'Photo','text':'My meal','category':'meal'}
    assert client.post('/community/posts',data=data,files={'file':('bad.png',b'bad','image/png')}).status_code==422
    image=BytesIO();Image.new('RGB',(32,32),'green').save(image,'PNG')
    post=client.post('/community/posts',data=data,files={'file':('meal.png',image.getvalue(),'image/png')}).json()
    assert post['visibility']=='private'
    image_url=post['image_url'].removeprefix('/api')
    assert client.get(image_url).headers['content-type']=='image/jpeg'
    actor[0]=2
    assert client.get(image_url).status_code==404
    actor[0]=1
    client.post(f"/community/posts/{post['id']}/delete")
    assert not list(tmp_path.iterdir())
