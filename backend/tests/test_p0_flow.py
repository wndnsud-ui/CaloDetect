# 회귀 테스트: p0_flow 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
# 10월 15일 박근수 수정: 추천 점수 경계, 경고 fallback, 목표 검증과 추천 소유권을 회귀 검사한다.
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
from backend.app.models import Base, User, Meal, Detection, RecommendationLog
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


# 회귀 검사: 탐지 · 보정. 2026-10-20 모델 개선(재학습) 폐기 후 수정은 탐지 기록에만 남는다.
def test_detection_correction(env):
    client,engine,monkeypatch=env
    user=account(client)
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
    assert client.get(saved['image_urls'][0].replace('/api', '')).status_code == 200
    with Session(engine) as db:
        assert db.get(Detection, ids[0]).corrected_label == catalog[2]['food_name']
    assert client.post(f'/detections/{ids[0]}/correction',json={'class_id':3}).status_code==200
    with Session(engine) as db:
        assert db.get(Detection, ids[0]).corrected_label == catalog[3]['food_name']


# 회귀 검사: 모델 개선 동의·관리자 재학습 QA 경로는 폐기되어 없다(관리자도 404).
def test_model_improvement_retired(env):
    client, engine, _ = env
    user = account(client)
    with Session(engine) as db:
        db.get(User, user['id']).role = 'admin'; db.commit()
    assert client.get('/users/me/consent').status_code == 404
    assert client.put('/users/me/consent', json={'model_improvement_consent': True}).status_code in (404, 405)
    assert client.get('/admin/retraining/samples').status_code == 404
    assert 'model_improvement_consent_text' not in client.get('/auth/policy').json()
    assert not hasattr(User, 'model_improvement_consent')


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
    refreshed=client.post('/recommendations/meals',json={
        'exclude_foods':[item['class_id'] for item in data['items']],
    })
    assert refreshed.status_code==200,refreshed.text
    assert {item['class_id'] for item in data['items']}.isdisjoint(
        item['class_id'] for item in refreshed.json()['items']
    )
    with Session(engine) as db:
        assert db.get(RecommendationLog,data['id']).acted is False
    saved=client.post('/meals',json={'meal_type':'dinner','recommendation_id':data['id'],
        'items':[{'class_id':data['items'][0]['class_id'],'serving_multiplier':1}]})
    assert saved.status_code==201,saved.text
    duplicate=client.post('/meals',json={'meal_type':'dinner','recommendation_id':data['id'],
        'items':[{'class_id':data['items'][0]['class_id'],'serving_multiplier':1}]})
    assert duplicate.status_code==409
    with Session(engine) as db:
        log=db.get(RecommendationLog,data['id'])
        assert log.acted is True
        assert log.selected_item==data['items'][0]['class_id']


# 회귀 검사: 목표 칼로리의 None/0/음수 상태가 추천 계산을 시작하기 전에 422로 거부되는지 확인한다.
@pytest.mark.parametrize('target_calories',[None,0,-1])
def test_recommendation_requires_positive_target(env,target_calories):
    from backend.app.services import recommendation as recommendation_service
    assert recommendation_service.calorie_band(350)=='light'
    assert recommendation_service.calorie_band(351)=='medium'
    assert recommendation_service.calorie_band(700)=='medium'
    assert recommendation_service.calorie_band(701)=='high'

    client,_,monkeypatch=env
    account(client)
    monkeypatch.setattr(recommendation_service,'get_today_status',lambda db,user_id:{
        'target_calories':target_calories,
        'remaining_calories':0,
        'totals':{'cal':0,'sodium':0,'sugar':0},
    })
    response=client.post('/recommendations/meals',json={})
    assert response.status_code==422
    assert response.json()['detail']=='먼저 유효한 목표 칼로리를 저장해 주세요.'


# 회귀 검사: 80%/100%/120% 경계와 끼니별 목표 열량 계산식을 검증한다.
def test_recommendation_limit_and_meal_target_boundaries():
    from backend.app.services.recommendation import calculate_limit_fit,calculate_meal_target
    assert calculate_limit_fit(0,1600,2000)==1.0
    assert calculate_limit_fit(0,2000,2000)==0.5
    assert calculate_limit_fit(0,2400,2000) is None
    assert calculate_meal_target(2000,1200,'lunch')==600
    assert calculate_meal_target(2000,200,'lunch')==200
    assert calculate_meal_target(2000,0,'lunch')==1


# 회귀 검사: protein 테마가 입력 스키마/API를 거쳐 추천 순위에 반영되는지 검증한다.
def test_recommendation_theme_is_applied(env):
    from backend.app.services import recommendation as recommendation_service
    client,_,monkeypatch=env
    account(client);profile(client)
    foods=[
        {'class_id':0,'food_name':'가벼운 메뉴','category':'A','unit':'1회','cal':300,'carbs':50,'protein':5,'fat':10,'sugar':5,'sodium':300},
        {'class_id':1,'food_name':'단백질 낮은 메뉴','category':'B','unit':'1회','cal':600,'carbs':45,'protein':5,'fat':9,'sugar':4,'sodium':400},
        {'class_id':2,'food_name':'단백질 높은 메뉴','category':'C','unit':'1회','cal':600,'carbs':48,'protein':30,'fat':10,'sugar':5,'sodium':500},
        {'class_id':3,'food_name':'고열량 메뉴','category':'D','unit':'1회','cal':800,'carbs':48,'protein':15,'fat':10,'sugar':5,'sodium':500},
    ]
    monkeypatch.setattr(recommendation_service,'food_catalog',lambda:foods)
    for theme in ('balance','protein','light'):
        response=client.post('/recommendations/meals',json={'meal_type':'lunch','theme':theme})
        assert response.status_code==200,response.text
        items=response.json()['items']
        assert [item['calorie_band'] for item in items]==['light','medium','high']
        if theme=='protein':
            assert items[1]['class_id']==2


# 회귀 검사: 오늘 포함 최근 7일의 음식은 제외하고 7일 경계 밖 기록은 다시 추천할 수 있다.
def test_recommendation_excludes_foods_consumed_within_last_seven_days(env):
    from datetime import date,timedelta
    from backend.app.services import recommendation as recommendation_service
    client,_,monkeypatch=env
    account(client);profile(client)
    today=date(2026,10,15)
    monkeypatch.setattr(recommendation_service,'korean_date',lambda instant:today)
    monkeypatch.setattr(recommendation_service,'get_today_status',lambda db,user_id:{
        'date':str(today),'target_calories':2500,'remaining_calories':2000,
        'totals':{'cal':500,'sodium':0,'sugar':0},
    })
    foods=[
        {'class_id':0,'food_name':'최근 기록 가벼운 메뉴','category':'A','unit':'1회','cal':300,'carbs':40,'protein':10,'fat':8,'sugar':3,'sodium':250},
        {'class_id':1,'food_name':'새 가벼운 메뉴','category':'B','unit':'1회','cal':320,'carbs':42,'protein':12,'fat':8,'sugar':3,'sodium':260},
        {'class_id':2,'food_name':'최근 기록 보통 메뉴','category':'C','unit':'1회','cal':500,'carbs':50,'protein':20,'fat':10,'sugar':4,'sodium':350},
        {'class_id':3,'food_name':'새 보통 메뉴','category':'D','unit':'1회','cal':600,'carbs':55,'protein':22,'fat':12,'sugar':5,'sodium':400},
        {'class_id':4,'food_name':'7일 경계 밖 고열량 메뉴','category':'E','unit':'1회','cal':800,'carbs':60,'protein':25,'fat':15,'sugar':6,'sodium':450},
    ]
    monkeypatch.setattr(recommendation_service,'food_catalog',lambda:foods)
    for class_id,meal_date in ((0,today-timedelta(days=6)),(2,today-timedelta(days=1)),(4,today-timedelta(days=7))):
        saved=client.post('/meals',json={
            'meal_type':'lunch','meal_date':meal_date.isoformat(),
            'items':[{'class_id':class_id,'serving_multiplier':1}],
        })
        assert saved.status_code==201,saved.text

    response=client.post('/recommendations/meals',json={'meal_type':'lunch','theme':'balance'})
    assert response.status_code==200,response.text
    items=response.json()['items']
    assert [item['calorie_band'] for item in items]==['light','medium','high']
    assert [item['class_id'] for item in items]==[1,3,4]


# 회귀 검사: 일반 후보가 부족한 경우에만 경고 fallback을 사용한다.
def test_recommendation_fallback_is_limited_and_visible(env):
    from backend.app.services import recommendation as recommendation_service
    client,_,monkeypatch=env
    account(client);profile(client)
    foods=[
        {'class_id':0,'food_name':'일반 가벼운 메뉴','category':'A','unit':'1회','cal':300,'carbs':50,'protein':20,'fat':10,'sugar':5,'sodium':300},
        {'class_id':1,'food_name':'일반 보통 메뉴','category':'B','unit':'1회','cal':550,'carbs':45,'protein':18,'fat':9,'sugar':4,'sodium':400},
        {'class_id':2,'food_name':'한도 초과 고열량 메뉴','category':'C','unit':'1회','cal':800,'carbs':48,'protein':19,'fat':10,'sugar':5,'sodium':2400},
    ]
    monkeypatch.setattr(recommendation_service,'food_catalog',lambda:foods)
    response=client.post('/recommendations/meals',json={'meal_type':'lunch'})
    assert response.status_code==200,response.text
    data=response.json()
    assert len(data['items'])==3
    assert [item['calorie_band'] for item in data['items']]==['light','medium','high']
    fallback=next(item for item in data['items'] if item['class_id']==2)
    assert fallback.get('warning')
    assert '경고형 대체 메뉴' in data['notice']
    assert all('score' not in item and 'is_fallback' not in item for item in data['items'])


# 회귀 검사: 일반 후보 세 개가 있으면 fallback을 사용하지 않고 끼니 목표·결측 방어를 유지한다.
def test_recommendation_does_not_show_unused_fallback_warning(env):
    from backend.app.services import recommendation as recommendation_service
    client,_,monkeypatch=env
    account(client);profile(client)
    foods=[
        {'class_id':0,'food_name':'고열량 메뉴','category':'A','unit':'1회','cal':1100,'carbs':50,'protein':20,'fat':10,'sugar':5,'sodium':300},
        {'class_id':1,'food_name':'가벼운 메뉴','category':'B','unit':'1회','cal':300,'carbs':45,'protein':18,'fat':9,'sugar':4,'sodium':400},
        {'class_id':2,'food_name':'보통 열량 메뉴','category':'C','unit':'1회','cal':600,'carbs':48,'protein':19,'fat':10,'sugar':5,'sodium':500},
        {'class_id':3,'food_name':'한도 초과 보통 메뉴','category':'D','unit':'1회','cal':580,'carbs':48,'protein':19,'fat':10,'sugar':5,'sodium':2400},
        {'class_id':4,'food_name':'영양 결측 메뉴','category':'E','unit':'1회','cal':600,'carbs':48,'protein':19,'fat':10,'sugar':None,'sodium':500},
    ]
    monkeypatch.setattr(recommendation_service,'food_catalog',lambda:foods)
    monkeypatch.setattr(recommendation_service,'get_today_status',lambda db,user_id:{
        'date':'2026-10-15','target_calories':2000,'remaining_calories':1200,
        'totals':{'cal':800,'sodium':0,'sugar':0},
    })
    response=client.post('/recommendations/meals',json={'meal_type':'lunch'})
    assert response.status_code==200,response.text
    data=response.json()
    assert len(data['items'])==3
    assert [item['calorie_band'] for item in data['items']]==['light','medium','high']
    assert all(item['class_id'] not in (3,4) for item in data['items'])
    assert data['items'][0]['class_id']==1
    assert data['items'][1]['class_id']==2
    assert all(item['class_id']!=4 for item in data['items'])
    assert all(item.get('warning') is None for item in data['items'])
    assert '경고형 대체 메뉴' not in data['notice']


# 회귀 검사: 다른 회원이 recommendation_id를 제출해도 원 소유자의 로그 상태는 바뀌지 않는다.
def test_recommendation_log_rejects_other_user(env):
    client,engine,_=env
    account(client);profile(client)
    response=client.post('/recommendations/meals',json={})
    assert response.status_code==200,response.text
    recommendation=response.json()
    account(client,'two@example.com')
    saved=client.post('/meals',json={
        'meal_type':'dinner',
        'recommendation_id':recommendation['id'],
        'items':[{'class_id':recommendation['items'][0]['class_id'],'serving_multiplier':1}],
    })
    assert saved.status_code==404
    with Session(engine) as db:
        log=db.get(RecommendationLog,recommendation['id'])
        assert log.acted is False
        assert log.selected_item is None


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
