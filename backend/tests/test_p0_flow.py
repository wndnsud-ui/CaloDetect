# 회귀 테스트: p0_flow 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
import io
import os
from uuid import uuid4
import pytest
from PIL import Image
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db import get_db
from backend.app.db import get_engine
from backend.app.accounts import database
from backend.app.config import settings
from backend.app.models import Base, User, Meal, Detection, RetrainingSample, RecommendationLog
from backend.scripts.seed_foods import seed


# env: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'local_test_image_analysis', False)
    schema = None
    if os.environ.get('RUN_POSTGRES_TESTS') == '1':
        schema = 'test_' + uuid4().hex
        base_engine = get_engine()
        with base_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = base_engine.execution_options(schema_translate_map={None: schema})
    else:
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)
    # session: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[database] = session
    monkeypatch.setattr(settings, 'age_min', 19)
    monkeypatch.setattr(settings, 'service_consent_text', 'TEST ONLY consent')
    monkeypatch.setattr(settings, 'model_improvement_consent_text', 'TEST ONLY model consent')
    monkeypatch.setattr(settings, 'image_storage_dir', str(tmp_path))
    monkeypatch.setattr(settings, 'recommendation_enabled', True)
    monkeypatch.setattr(settings, 'recent_meal_window', 3)
    with TestClient(app) as client:
        yield client, engine, monkeypatch
    app.dependency_overrides.clear()
    if schema:
        with base_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    else:
        engine.dispose()


# account: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
def account(client, email='one@example.com'):
    response = client.post('/auth/signup', json={'email':email,'password':'test-password-123',
        'name':'Tester','age':30,'service_consent':True,'consent_text':'TEST ONLY consent'})
    assert response.status_code == 201, response.text
    data = response.json()
    client.headers['X-CSRF-Token'] = data['csrf_token']
    return data['user']


# 회귀 검사: 월간 · 분석.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_month_analysis(env):
    from datetime import date
    client, engine, _ = env
    first = account(client)
    saved = client.post('/meals', json={'meal_type':'lunch', 'items':[
        {'class_id':0, 'serving_multiplier':1}]}).json()
    with Session(engine) as db:
        db.get(Meal, saved['id']).meal_date = date(2024, 2, 29)
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit()
    result = client.get('/analytics/month?year=2024&month=2')
    assert result.status_code == 200
    data = result.json()
    assert len(data['days']) == 29
    assert data['recorded_days'] == 1
    assert data['days'][0]['totals'] is None
    assert data['averages'] == data['days'][-1]['totals']
    assert data['averages']['cal'] == saved['items'][0]['nutrition']['cal']
    assert client.get('/analytics/month?year=2024&month=13').status_code == 422
    account(client, 'two@example.com')
    empty = client.get('/analytics/month?year=2024&month=2').json()
    assert empty['recorded_days'] == 0
    assert empty['averages'] is None


# 현재 회원의 저장된 프로필을 반환하고 아직 없으면 null로 표시한다.
def profile(client):
    response = client.put('/users/me/profile', json={'height':175,'weight':70,'age':30,'sex':'male',
        'activity_level':'moderate','goal_type':'maintain','target_calories':2500})
    assert response.status_code == 200, response.text


# png: 이 파일의 테스트용 환경·입력 또는 대체 클라이언트를 준비한다. 외부 기능과 분리된 검사에 사용한다.
def png():
    data=io.BytesIO(); Image.new('RGB',(100,100),'white').save(data,format='PNG')
    return data.getvalue()


# 회귀 검사: 가입 · 프로필 · 식단 · 로그아웃 · 재로그인.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_register_profile_meal_logout_and_relogin(env):
    client,engine,_=env
    user=account(client); profile(client)
    assert client.post('/auth/signup',json={'email':'one@example.com','password':'test-password-123','name':'T',
        'age':30,'service_consent':True,'consent_text':'TEST ONLY consent'}).status_code==409
    saved=client.post('/meals',json={'meal_type':'lunch','items':[{'class_id':0,'serving_multiplier':1.5}]} )
    assert saved.status_code==201,saved.text
    assert saved.json()['items'][0]['detection_id'] is None
    assert client.get('/analytics/today').json()['totals']['cal']>0
    assert client.post('/auth/logout',json={}).status_code==200
    assert client.get('/meals/history').status_code==401
    assert client.post('/auth/login',json={'email':'one@example.com','password':'wrong-password'}).status_code==401
    login=client.post('/auth/login',json={'email':'one@example.com','password':'test-password-123'}).json()
    client.headers['X-CSRF-Token']=login['csrf_token']
    assert len(client.get('/meals/history').json()['items'])==1
    with Session(engine) as db:
        assert db.get(User,user['id']).password_hash!='test-password-123'
    assert client.post('/users/1/make-admin',json={}).status_code==404


# 회귀 검사: 회원 · 분리 · 원자적 · 저장.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_user_isolation_and_atomic_save(env):
    client,engine,_=env
    first=account(client)
    with Session(engine) as db:
        d=Detection(user_id=first['id'],image_path='test.jpg',image_group_id='group',predicted_label='a',confidence=.9,bbox=[0,0,10,10],model_version='test')
                  # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.add(d);db.commit();detection_id=d.id
    client.post('/auth/logout',json={}); account(client,'two@example.com')
    response=client.post('/meals',json={'meal_type':'lunch','items':[{'class_id':0,'serving_multiplier':1},{'class_id':1,'serving_multiplier':1,'detection_id':detection_id}]})
    assert response.status_code==404,response.text
    assert client.get('/meals/history').json()['items']==[]
    with Session(engine) as db:
        assert db.scalars(select(Meal)).all()==[]
    assert client.get('/admin/retraining/samples').status_code==403


# 회귀 검사: 탐지 · 보정 · QA · 동의.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_detection_correction_qa_consent(env):
    client,engine,monkeypatch=env
    user=account(client)
    assert client.put('/users/me/consent',json={'model_improvement_consent':True}).status_code==200
    catalog=client.get('/foods').json()['items']
    monkeypatch.setattr('backend.app.api.detect_image',lambda path:{'model_version':'test', 'detections':[
        {'class_id':0,'predicted_label':catalog[0]['food_name'],'confidence':.9,'bbox':[0,0,10,10]},
        {'class_id':1,'predicted_label':catalog[1]['food_name'],'confidence':.8,'bbox':[20,20,40,40]}]})
    scan=client.post('/meals/detect',files={'file':('test.png',png(),'image/png')})
    assert scan.status_code==200,scan.text
    ids=scan.json()['detection_ids'];assert len(ids)==2
    response=client.post('/meals',json={'meal_type':'dinner','items':[{'class_id':2,'serving_multiplier':1,'detection_id':ids[0]}, {'class_id':1,'serving_multiplier':1,'detection_id':ids[1]}]})
    assert response.status_code==201,response.text
    assert response.json()['image_urls'] == [scan.json()['image_url']]
    saved = next(meal for meal in client.get('/analytics/today').json()['meals'] if meal['id'] == response.json()['id'])
    assert saved['image_urls'] == [scan.json()['image_url']]
    image_path = saved['image_urls'][0].replace('/api', '')
    assert client.get(image_path).status_code == 200
    with Session(engine) as db:
        assert len(db.scalars(select(RetrainingSample)).all())==1
                                             # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.get(User,user['id']).role='admin';db.commit()
    samples=client.get('/admin/retraining/samples').json()['items'];sample_id=samples[0]['id']
    assert client.post(f'/admin/retraining/samples/{sample_id}/approve',json={}).status_code==200
    assert client.post(f'/detections/{ids[0]}/correction',json={'class_id':3}).status_code==200
    with Session(engine) as db:
        samples=db.scalars(select(RetrainingSample)).all()
        assert {s.qa_status for s in samples}=={'APPROVED','PENDING'}
    assert client.put('/users/me/consent',json={'model_improvement_consent':False}).status_code==200
    with Session(engine) as db:
        samples=db.scalars(select(RetrainingSample)).all()
        assert next(s for s in samples if s.qa_status=='APPROVED').excluded is False
        assert next(s for s in samples if s.qa_status=='PENDING').excluded is True


# 회귀 검사: 모델 · 동의 · 승인 · 문구.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_model_consent_requires_approved_wording(env):
    client, _, monkeypatch = env
    account(client)
    monkeypatch.setattr(settings, 'model_improvement_consent_text', None)
    assert client.put('/users/me/consent', json={'model_improvement_consent': True}).status_code == 503
    assert client.get('/users/me/consent').json()['model_improvement_consent'] is False
    assert client.put('/users/me/consent', json={'model_improvement_consent': False}).status_code == 200


# 회귀 검사: 추천 · 세 후보 · 선택 기록.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_recommendations_three_and_acted(env):
    client,engine,_=env
    account(client);profile(client)
    response=client.post('/recommendations/meals',json={'exclude_foods':[0]})
    assert response.status_code==200,response.text
    data=response.json();assert len(data['items'])==3
    assert len({i['class_id'] for i in data['items']})==3
    assert all('score' not in i and i['class_id']!=0 for i in data['items'])
    with Session(engine) as db:
        assert db.get(RecommendationLog,data['id']).acted is False
    saved=client.post('/meals',json={'meal_type':'dinner','recommendation_id':data['id'],
        'items':[{'class_id':data['items'][0]['class_id'],'serving_multiplier':1}]})
    assert saved.status_code==201,saved.text
    with Session(engine) as db:
        assert db.get(RecommendationLog,data['id']).acted is True


# 회귀 검사: 이미지 · 연령 · CSRF.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_bad_image_age_and_csrf(env):
    client,_,_=env
    denied=client.post('/auth/signup',json={'email':'minor@example.com','password':'test-password-123',
        'name':'T','age':18,'service_consent':True,'consent_text':'TEST ONLY consent'})
    assert denied.status_code==422
    account(client)
    assert client.post('/meals/detect',files={'file':('bad.jpg',b'not image','image/jpeg')}).status_code==422
    client.headers.pop('X-CSRF-Token')
    assert client.post('/meals',json={'meal_type':'lunch','items':[{'class_id':0,'serving_multiplier':1}]}).status_code==403


# 회귀 검사: 실제 · YOLO · 빈 · 이미지.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
@pytest.mark.skipif(os.environ.get('RUN_VISION_TEST') != '1', reason='Explicit actual YOLO smoke check')
def test_actual_yolo_blank_image(env):
    client,_,_=env
    account(client)
    result=client.post('/meals/detect',files={'file':('blank.png',png(),'image/png')})
    assert result.status_code==200,result.text
    assert result.json()['manual_selection_available'] is True
    assert client.get(result.json()['image_url'].replace('/api','')).status_code==200


# 회귀 검사: 로컬 · 이미지 · 분석 · 운영 · or · 원격 · 클라이언트.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_local_image_analysis_is_not_enabled_for_production_or_remote_clients(env):
    remote, _, monkeypatch = env
    monkeypatch.setattr(settings, 'local_test_image_analysis', True)
    monkeypatch.setattr(settings, 'app_env', 'development')
    monkeypatch.setattr(settings, 'frontend_origin', 'http://localhost:5173')
    monkeypatch.setattr('backend.app.api.detect_image', lambda path: {'model_version': 'test', 'detections': []})
    account(remote)
    assert remote.post('/meals/detect', files={'file': ('test.png', png(), 'image/png')}).status_code == 503
    with TestClient(app, base_url='http://localhost:8000', client=('127.0.0.1', 50000)) as local:
        account(local, 'local-image@example.com')
        scan = local.post('/meals/detect', files={'file': ('test.png', png(), 'image/png')})
        assert scan.status_code == 200
        image_url = scan.json()['image_url'].replace('/api', '')
        assert local.get(image_url).status_code == 200
        monkeypatch.setattr(settings, 'app_env', 'production')
        assert local.post('/meals/detect', files={'file': ('test.png', png(), 'image/png')}).status_code == 503
        assert local.get(image_url).status_code == 503
