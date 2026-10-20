# 채팅 식사기록 A0(확정 식사 섭취량 수정) 검사. 지시서 v9 14장 T01~T19·T47·T49.
# test_p0_flow.py의 env·계정 생성 패턴을 복제했다. 기존 테스트 파일은 수정하지 않는다.
# 새 기능 테스트는 CHAT_RECORD_ENABLED를 켠 상태로 라우터를 임시 등록하고, 끝나면 원래 라우트 목록으로 되돌린다.
import os
import threading
from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db import get_db, get_engine
from backend.app.accounts import database
from backend.app.config import settings
from backend.app.models import Base, Meal, MealItem, Detection, User
from backend.app.models_chat import MutationRequest
from backend.app.consumption_api import router as consumption_router
from backend.app.services.consumption import interpret, consumption_nutrition
from backend.app.services.nutrition import calculate_nutrition
from backend.app.services.consumption_record import update_item_consumption, ChatRecordError
from backend.app.schemas_chat import ConsumptionUpdateRequest
from backend.scripts.seed_foods import seed

GALBI = 2  # CSV class_id 2 갈비구이, 인분 (약 200g), cal 723.0 / sodium 1206.0
LEGACY_ITEM_KEYS = {'id', 'class_id', 'food_name', 'detection_id', 'serving_multiplier', 'nutrition'}
NEW_ITEM_KEYS = {'consumption_ratio', 'version', 'effective_multiplier'}


def build_env(monkeypatch, tmp_path, enabled):
    monkeypatch.setattr(settings, 'local_test_image_analysis', False)
    schema = None
    if os.environ.get('RUN_POSTGRES_TESTS') == '1':
        schema = 'test_' + uuid4().hex
        base_engine = get_engine()
        with base_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = base_engine.execution_options(schema_translate_map={None: schema})
    else:
        base_engine = None
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed(db)

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
    monkeypatch.setattr(settings, 'chat_record_enabled', enabled)
    # 개인 .env에서 플래그를 켜 두었어도 테스트는 on/off 상태를 직접 만든다(앱 import 시점 등록과 무관).
    from backend.app.chat_api import router as chat_router
    routes = list(app.router.routes)
    new_paths = {route.path for route in consumption_router.routes + chat_router.routes}

    # FastAPI 버전에 따라 포함된 라우터가 개별 APIRoute 또는 _IncludedRouter(original_router)로 보관된다.
    def is_new(route):
        return (getattr(route, 'original_router', None) in (consumption_router, chat_router)
                or getattr(route, 'path', None) in new_paths)
    app.router.routes[:] = [route for route in routes if not is_new(route)]
    if enabled:
        app.include_router(consumption_router)
    return engine, schema, base_engine, routes


def teardown_env(engine, schema, base_engine, routes):
    app.router.routes[:] = routes
    app.openapi_schema = None
    app.dependency_overrides.clear()
    if schema:
        with base_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    else:
        engine.dispose()


@pytest.fixture
def env(monkeypatch, tmp_path):
    engine, schema, base_engine, routes = build_env(monkeypatch, tmp_path, True)
    with TestClient(app) as client:
        yield client, engine, monkeypatch
    teardown_env(engine, schema, base_engine, routes)


@pytest.fixture
def env_off(monkeypatch, tmp_path):
    engine, schema, base_engine, routes = build_env(monkeypatch, tmp_path, False)
    with TestClient(app) as client:
        yield client, engine, monkeypatch
    teardown_env(engine, schema, base_engine, routes)


def account(client, email='one@example.com'):
    response = client.post('/auth/signup', json={'email': email, 'password': 'test-password-123',
        'name': 'Tester', 'age': 30, 'service_consent': True, 'consent_text': 'TEST ONLY consent'})
    assert response.status_code == 201, response.text
    data = response.json()
    client.headers['X-CSRF-Token'] = data['csrf_token']
    return data['user']


def save(client, items, meal_type='dinner'):
    response = client.post('/meals', json={'meal_type': meal_type, 'items': items})
    assert response.status_code == 201, response.text
    return response.json()


def galbi_meal(client, multiplier=1):
    meal = save(client, [{'class_id': GALBI, 'serving_multiplier': multiplier}])
    return meal, meal['items'][0]


def put(client, item_id, ratio, version, request_id=None):
    return client.put(f'/meals/items/{item_id}/consumption', json={
        'consumption_ratio': ratio, 'expected_version': version, 'request_id': request_id or str(uuid4())})


def calc(ratio, base=1.0):
    return calculate_nutrition(GALBI, base * ratio)['nutrition']


ONE = [{'id': 'a', 'food_name': '갈비구이'}]
TWO = [{'id': 'a', 'food_name': '밥'}, {'id': 'b', 'food_name': '불고기'}]


# T01: 정규화·결합 표현.
@pytest.mark.parametrize('sentence,intent,ratio', [
    ('4분의1', 'update_consumption', 0.25), ('아니, 4분의 1', 'update_consumption', 0.25),
    ('반 먹었어', 'update_consumption', 0.5), ('다 먹음', 'update_consumption', 1.0),
    ('절반!', 'update_consumption', 0.5), ('3/4', 'update_consumption', 0.75),
    ('3/4 먹었어', 'update_consumption', 0.75), ('하나도 안 먹었어요', 'update_consumption', 0.0),
    ('절반만 먹었어 올려줘', 'update_and_confirm', 0.5), ('4분의 1, 저장해줘', 'update_and_confirm', 0.25),
    ('맞아 올려줘', 'confirm_save', None), ('저장해줘', 'confirm_save', None), ('기록해요', 'confirm_save', None),
])
def test_t01_rule_interpretation(sentence, intent, ratio):
    result = interpret(sentence, 'none', ONE)
    assert result['intent'] == intent
    assert result['consumption_ratio'] == ratio
    assert result['source'] == 'rule'


# T01 보충: 단순 긍정·취소의 상태 의존 해석(8.1).
def test_t01_affirm_and_cancel_depend_on_pending_question():
    assert interpret('응', 'none', ONE)['intent'] == 'affirm'
    assert interpret('응', 'amount', ONE)['intent'] == 'affirm'
    assert interpret('응', 'save_confirm', ONE)['intent'] == 'confirm_save'
    assert interpret('맞아요', 'save_confirm', ONE)['intent'] == 'confirm_save'
    for sentence in ['아니야', '아니', '아냐', '취소', '그만', '안할래']:
        assert interpret(sentence, 'save_confirm', ONE)['intent'] == 'cancel'


# T02: 확인 질문 예 전부 → clarify, ratio null.
@pytest.mark.parametrize('sentence', [
    '조금', '반쯤', '더 먹었어', '반 남겼어', '반찬만 먹었어', '반도 못 먹었어', '다 못 먹었어', '150%', '125%',
    '50%가 아니라 25%', '절반보다 적게 먹었어', '50%~75%', '1/4.5', '2인분 먹었어', '두 그릇', '응 절반',
    '조금 먹었어 올려줘', '두 그릇 먹었어 올려줘', '반', '다',
])
def test_t02_unsupported_expressions_clarify(sentence):
    result = interpret(sentence, 'save_confirm', ONE)
    assert result['intent'] == 'clarify'
    assert result['needs_clarification'] is True
    assert result['consumption_ratio'] is None


# 8.5: 여러 음식·전체 적용·대상 불명확.
def test_targets_multi_clause_and_all_prefix():
    multi = interpret('밥은 절반, 불고기는 다 먹었어 올려줘', 'none', TWO)
    assert multi['intent'] == 'update_and_confirm'
    assert {(u['target_id'], u['consumption_ratio']) for u in multi['updates']} == {('a', 0.5), ('b', 1.0)}
    assert interpret('밥은 절반, 불고기는 조금 먹었어', 'none', TWO)['intent'] == 'clarify'
    every = interpret('전부 절반만 먹었어', 'none', TWO)
    assert {u['consumption_ratio'] for u in every['updates']} == {0.5} and len(every['updates']) == 2
    assert len(interpret('다 먹었어', 'none', TWO)['updates']) == 2
    vague = interpret('절반만 먹었어', 'none', TWO)
    assert vague['clarification_reason'] == 'ambiguous_target'
    assert [c['food_name'] for c in vague['candidates']] == ['밥', '불고기']
    named = interpret('불고기는 4분의 1 먹었어', 'none', TWO)
    assert named['target_id'] == 'b' and named['consumption_ratio'] == 0.25
    # 카드로 고른 대상과 문장 속 음식명이 다르면 질문한다.
    assert interpret('불고기는 절반', 'none', TWO, selected_id='a')['intent'] == 'clarify'
    same = [{'id': 'a', 'food_name': '밥'}, {'id': 'b', 'food_name': '밥'}]
    assert interpret('밥은 절반', 'none', same)['clarification_reason'] == 'ambiguous_target'


# T03: 대상 결정 API.
def test_t03_target_resolution(env):
    client, _, _ = env
    account(client)
    two = save(client, [{'class_id': GALBI, 'serving_multiplier': 1}, {'class_id': 0, 'serving_multiplier': 1}])
    other, _ = galbi_meal(client)
    url = '/meals/consumption/interpret'
    ambiguous = client.post(url, json={'text': '절반만 먹었어', 'meal_id': two['id']}).json()
    assert ambiguous['clarification_reason'] == 'ambiguous_target' and len(ambiguous['candidates']) == 2
    assert client.post(url, json={'text': '절반만 먹었어'}).json()['clarification_reason'] == 'missing_target'
    single = client.post(url, json={'text': '절반만 먹었어', 'item_id': two['items'][0]['id']}).json()
    assert single['target_id'] == two['items'][0]['id'] and single['consumption_ratio'] == 0.5
    mismatch = client.post(url, json={'text': '절반', 'item_id': two['items'][0]['id'], 'meal_id': other['id']})
    assert mismatch.status_code == 404
    with Session(env[1]) as db:
        empty = Meal(user_id=db.scalar(select(User.id)), meal_date=date.today(), meal_type='lunch')
        db.add(empty); db.commit(); empty_id = empty.id
    assert client.post(url, json={'text': '절반', 'meal_id': empty_id}).json()['clarification_reason'] == 'empty_meal'


# T04: 입력 검증 422, 쓰기 없음.
def test_t04_invalid_inputs_rejected(env):
    client, engine, _ = env
    account(client)
    _, item = galbi_meal(client)
    url = f'/meals/items/{item["id"]}/consumption'
    good = {'consumption_ratio': 0.5, 'expected_version': 1, 'request_id': str(uuid4())}
    for field, bad in [('consumption_ratio', -1), ('consumption_ratio', 1.5), ('consumption_ratio', '0.5'),
                       ('consumption_ratio', True), ('consumption_ratio', None), ('expected_version', True),
                       ('expected_version', 0), ('expected_version', '1'), ('request_id', 'not-a-uuid')]:
        response = client.put(url, json={**good, field: bad})
        assert response.status_code == 422, (field, bad)
    raw = client.put(url, content=b'{"consumption_ratio": NaN, "expected_version": 1, "request_id": "%s"}'
                     % str(uuid4()).encode(), headers={'Content-Type': 'application/json'})
    assert raw.status_code == 422
    with Session(engine) as db:
        row = db.get(MealItem, item['id'])
        assert (row.consumption_ratio, row.version) == (1.0, 1)
        assert db.scalar(select(func.count()).select_from(MutationRequest)) == 0


# T05: 0.0 / 1.0 / JSON 정수 0·1 허용.
def test_t05_boundary_values_allowed(env):
    client, _, _ = env
    account(client)
    _, item = galbi_meal(client)
    version = 1
    for ratio in [0.0, 1.0, 0, 1]:
        response = put(client, item['id'], ratio, version)
        assert response.status_code == 200, response.text
        version = response.json()['version']
    assert version == 5


# T06: 계산. 현재 snapshot에 다시 곱하지 않는다.
def test_t06_calculation(env):
    client, _, _ = env
    account(client)
    _, item = galbi_meal(client)
    expected = {0.5: 361.5, 0.75: 542.25, 0.25: 180.75}
    version = 1
    for ratio, cal in expected.items():
        body = put(client, item['id'], ratio, version).json()
        version = body['version']
        assert body['after']['nutrition']['cal'] == cal
        assert body['after']['nutrition']['fat'] == calc(ratio)['fat']
    zero = put(client, item['id'], 0, version).json()
    assert set(zero['after']['nutrition'].values()) == {0.0}
    meal = client.get('/meals/history').json()['items'][0]
    assert meal['items'][0]['class_id'] == GALBI and meal['items'][0]['serving_multiplier'] == 1
    _, double = galbi_meal(client, 2)
    first = put(client, double['id'], 0.5, 1).json()
    second = put(client, double['id'], 0.25, first['version']).json()
    assert first['after']['nutrition']['cal'] == 723.0
    assert second['after']['nutrition']['cal'] == 361.5
    assert second['after']['effective_multiplier'] == 0.5


# T07: snapshot 키·단위.
def test_t07_snapshot_keys():
    effective, nutrition = consumption_nutrition(GALBI, 1.0, 0.5)
    assert effective == 0.5
    assert set(nutrition) == {'cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium'}
    assert nutrition['sodium'] == 603.0


# T08: 미리보기 → 확정 흐름(A0 클라이언트 규칙을 API 호출 순서로 재현).
def test_t08_preview_then_confirm(env):
    client, engine, _ = env
    account(client)
    meal, item = galbi_meal(client)
    url = '/meals/consumption/interpret'
    first = client.post(url, json={'text': '절반만 먹었어', 'item_id': item['id']}).json()
    assert first['intent'] == 'update_consumption'
    preview = client.post(f'/meals/items/{item["id"]}/consumption/preview',
                          json={'consumption_ratio': first['consumption_ratio']}).json()
    assert preview['before']['nutrition']['cal'] == 723.0 and preview['after']['nutrition']['cal'] == 361.5
    assert client.get('/analytics/today').json()['totals']['cal'] == 723.0
    # 미리보기 없이 "저장해줘"·"응": 해석은 되지만 클라이언트는 보관값이 없어 저장하지 않는다.
    assert client.post(url, json={'text': '응', 'item_id': item['id']}).json()['intent'] == 'affirm'
    # 새 비율 "4분의 1" → 새 미리보기 → "응"(save_confirm) → 마지막 미리보기로 저장.
    newer = client.post(url, json={'text': '4분의 1', 'item_id': item['id']}).json()
    confirm = client.post(url, json={'text': '응', 'item_id': item['id'], 'pending_question': 'save_confirm'}).json()
    assert confirm['intent'] == 'confirm_save'
    saved = put(client, item['id'], newer['consumption_ratio'], preview['version'])
    assert saved.status_code == 200 and saved.json()['version'] == 2
    history = client.get('/meals/history').json()['items']
    assert history[0]['id'] == meal['id'] and len(history[0]['items']) == 1
    assert history[0]['items'][0]['id'] == item['id']
    assert client.get('/analytics/today').json()['totals']['cal'] == 180.75
    # 한 문장 "절반만 먹었어 저장해줘".
    once = client.post(url, json={'text': '절반만 먹었어 저장해줘', 'item_id': item['id']}).json()
    assert once['intent'] == 'update_and_confirm'
    assert put(client, item['id'], once['consumption_ratio'], 2).json()['after']['nutrition']['cal'] == 361.5


# T09: 같은 request_id·같은 payload 재전송.
def test_t09_same_request_replays(env):
    client, engine, _ = env
    account(client)
    _, item = galbi_meal(client)
    request_id = str(uuid4())
    first = put(client, item['id'], 0.5, 1, request_id).json()
    again = put(client, item['id'], 0.5, 1, request_id)
    assert again.status_code == 200 and again.json()['replayed'] is True
    assert again.json()['version'] == first['version'] == 2
    with Session(engine) as db:
        assert db.get(MealItem, item['id']).version == 2
        assert db.scalar(select(func.count()).select_from(MutationRequest)) == 1


# T10: 같은 request_id·다른 payload.
def test_t10_request_id_conflict(env):
    client, engine, _ = env
    account(client)
    _, item = galbi_meal(client)
    request_id = str(uuid4())
    put(client, item['id'], 0.5, 1, request_id)
    conflict = put(client, item['id'], 0.25, 1, request_id)
    assert conflict.status_code == 409 and conflict.json()['error']['code'] == 'request_id_conflict'
    with Session(engine) as db:
        assert db.get(MealItem, item['id']).consumption_ratio == 0.5


# T11: A 저장 → B 저장 → A 지연 재시도.
def test_t11_delayed_retry_keeps_latest(env):
    client, engine, _ = env
    account(client)
    _, item = galbi_meal(client)
    a = str(uuid4())
    put(client, item['id'], 0.5, 1, a)
    put(client, item['id'], 0.25, 2)
    retry = put(client, item['id'], 0.5, 1, a).json()
    assert retry['replayed'] is True and retry['version'] == 2
    with Session(engine) as db:
        row = db.get(MealItem, item['id'])
        assert (row.consumption_ratio, row.version) == (0.25, 3)


# T12: 오래된 version.
def test_t12_version_conflict(env):
    client, engine, _ = env
    account(client)
    _, item = galbi_meal(client)
    put(client, item['id'], 0.5, 1)
    stale = put(client, item['id'], 0.25, 1)
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'version_conflict'
    with Session(engine) as db:
        assert db.get(MealItem, item['id']).consumption_ratio == 0.5


# T13(PG 전용): 같은 expected_version 동시 수정 2건 → 1건 성공.
@pytest.mark.skipif(os.environ.get('RUN_POSTGRES_TESTS') != '1', reason='PostgreSQL 전용(K13)')
def test_t13_concurrent_updates_postgres(env):
    client, engine, _ = env
    account(client)
    _, item = galbi_meal(client)
    with Session(engine) as db:
        user = db.scalar(select(User))
        user_id = user.id
    results = []
    barrier = threading.Barrier(2)

    def worker(ratio):
        with Session(engine) as db:
            owner = db.get(User, user_id)
            body = ConsumptionUpdateRequest(consumption_ratio=ratio, expected_version=1, request_id=uuid4())
            barrier.wait()
            try:
                results.append(update_item_consumption(db, owner, item['id'], body)['version'])
            except ChatRecordError as error:
                results.append(error.code)
    threads = [threading.Thread(target=worker, args=(r,)) for r in (0.5, 0.25)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(map(str, results)) == ['2', 'version_conflict']


# T14: commit 실패 주입 → rollback, 이력 없음, 같은 request_id 재시도 성공.
def test_t14_commit_failure_rolls_back(env):
    client, engine, monkeypatch = env
    account(client)
    _, item = galbi_meal(client)
    request_id = str(uuid4())
    original = Session.commit
    calls = {'n': 0}

    def failing(self):
        calls['n'] += 1
        raise RuntimeError('injected secret detail')
    monkeypatch.setattr(Session, 'commit', failing)
    failed = put(client, item['id'], 0.5, 1, request_id)
    monkeypatch.setattr(Session, 'commit', original)
    assert failed.status_code == 503 and 'secret' not in failed.text
    assert calls['n'] == 1
    with Session(engine) as db:
        assert db.get(MealItem, item['id']).version == 1
        assert db.scalar(select(func.count()).select_from(MutationRequest)) == 0
    retried = put(client, item['id'], 0.5, 1, request_id)
    assert retried.status_code == 200 and retried.json()['replayed'] is False


# T15: 타 사용자 항목·식사 → 404.
def test_t15_other_user_not_found(env):
    client, _, _ = env
    account(client)
    meal, item = galbi_meal(client)
    account(client, 'two@example.com')
    assert client.post('/meals/consumption/interpret', json={'text': '절반', 'item_id': item['id']}).status_code == 404
    assert client.post('/meals/consumption/interpret', json={'text': '절반', 'meal_id': meal['id']}).status_code == 404
    assert client.post(f'/meals/items/{item["id"]}/consumption/preview',
                       json={'consumption_ratio': 0.5}).status_code == 404
    assert put(client, item['id'], 0.5, 1).status_code == 404


# T16: 저장 후 재로그인 조회·과거 날짜 항목의 월 집계.
def test_t16_aggregates_follow_saved_ratio(env):
    client, engine, _ = env
    account(client)
    meal, item = galbi_meal(client)
    put(client, item['id'], 0.5, 1)
    client.post('/auth/logout', json={})
    login = client.post('/auth/login', json={'email': 'one@example.com', 'password': 'test-password-123'}).json()
    client.headers['X-CSRF-Token'] = login['csrf_token']
    assert client.get('/analytics/today').json()['totals']['cal'] == 361.5
    assert client.get('/meals/history').json()['items'][0]['items'][0]['nutrition']['cal'] == 361.5
    with Session(engine) as db:
        db.get(Meal, meal['id']).meal_date = date(2024, 2, 10); db.commit()
    put(client, item['id'], 0.25, 2)
    month = client.get('/analytics/month?year=2024&month=2').json()
    assert month['days'][9]['totals']['cal'] == 180.75


def add_detection(engine, user_id, label):
    with Session(engine) as db:
        record = Detection(user_id=user_id, image_path='x.jpg', image_group_id=str(uuid4()),
                           predicted_label=label, confidence=0.9, bbox=[0, 0, 1, 1], model_version='test')
        db.add(record); db.commit()
        return record.id


# T17: correction 보완 패치(R3, 2026-10-15 사용자 승인) — 음식 변경 시 섭취 비율을 유지해 재계산하고 version을 올린다.
def test_t17_correction_keeps_consumption_ratio(env):
    client, engine, _ = env
    user = account(client)
    detection_id = add_detection(engine, user['id'], '갈비구이')
    meal = save(client, [{'class_id': GALBI, 'serving_multiplier': 1, 'detection_id': detection_id}])
    item = meal['items'][0]
    put(client, item['id'], 0.5, 1)
    assert client.post(f'/detections/{detection_id}/correction', json={'class_id': 0}).status_code == 200
    with Session(engine) as db:
        row = db.get(MealItem, item['id'])
        assert (row.consumption_ratio, row.version, row.food_id) == (0.5, 3, 0)
        assert row.nutrition == calculate_nutrition(0, 0.5)['nutrition']
    entry = client.post(f'/meals/items/{item["id"]}/consumption/preview', json={'consumption_ratio': 0.5}).json()
    assert entry['stored_matches_calculation'] is True
    # 수정 전 version(2)으로 저장하던 화면은 충돌로 최신 값을 다시 불러온다.
    assert put(client, item['id'], 0.25, 2).status_code == 409


# T17 보충: 비율 1.0 항목의 correction 결과는 패치 전과 같다.
def test_t17_correction_unchanged_for_full_ratio(env):
    client, engine, _ = env
    user = account(client)
    detection_id = add_detection(engine, user['id'], '갈비구이')
    item = save(client, [{'class_id': GALBI, 'serving_multiplier': 1.5, 'detection_id': detection_id}])['items'][0]
    client.post(f'/detections/{detection_id}/correction', json={'class_id': 0})
    with Session(engine) as db:
        assert db.get(MealItem, item['id']).nutrition == calculate_nutrition(0, 1.5)['nutrition']


# T18: 저장값이 현재 계산과 다르면(기존 데이터 불일치 등) 진입 시 감지하고, 저장 시 CSV 기준으로 재계산한다.
def test_t18_mismatch_detected_and_fixed(env):
    client, engine, _ = env
    account(client)
    _, item = galbi_meal(client)
    with Session(engine) as db:
        db.get(MealItem, item['id']).nutrition = {**calc(1.0), 'cal': 1.0}; db.commit()
    entry = client.post(f'/meals/items/{item["id"]}/consumption/preview', json={'consumption_ratio': 1}).json()
    assert entry['stored_matches_calculation'] is False
    with Session(engine) as db:
        assert db.get(MealItem, item['id']).version == 1
    fixed = put(client, item['id'], 0.5, 1).json()
    assert fixed['after']['nutrition'] == calc(0.5)
    again = client.post(f'/meals/items/{item["id"]}/consumption/preview', json={'consumption_ratio': 0.5}).json()
    assert again['stored_matches_calculation'] is True


# P8 보완: 비율 0(안 먹음) 항목은 추천의 "최근 먹은 음식" 제외 목록에 들어가지 않는다.
def test_zero_ratio_not_counted_as_recently_eaten(env):
    from backend.app.services.recommendation import recently_consumed_food_ids
    client, engine, _ = env
    user = account(client)
    _, eaten = galbi_meal(client)
    skipped = save(client, [{'class_id': 0, 'serving_multiplier': 1}])['items'][0]
    put(client, skipped['id'], 0, 1)
    with Session(engine) as db:
        assert recently_consumed_food_ids(db, user['id']) == {GALBI}


def snapshot_responses(client):
    responses = {'today_meals': client.get('/meals/today').json(), 'history': client.get('/meals/history').json(),
                 'today': client.get('/analytics/today').json()}
    today = date.fromisoformat(responses['today']['date'])
    responses['month'] = client.get(f'/analytics/month?year={today.year}&month={today.month}').json()
    return responses


def item_dicts(value):
    if isinstance(value, dict):
        if 'serving_multiplier' in value and 'nutrition' in value and 'class_id' in value:
            yield value
        for child in value.values():
            yield from item_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from item_dicts(child)


# T47: 플래그 off → 새 라우트 404, 기존 응답 키는 변경 전과 같다.
def test_t47_flag_off_routes_absent_and_keys_unchanged(env_off):
    client, _, _ = env_off
    account(client)
    _, item = galbi_meal(client)
    assert client.post('/meals/consumption/interpret', json={'text': '절반'}).status_code == 404
    assert client.post(f'/meals/items/{item["id"]}/consumption/preview',
                       json={'consumption_ratio': 0.5}).status_code == 404
    assert put(client, item['id'], 0.5, 1).status_code in (404, 405)
    items = list(item_dicts(snapshot_responses(client)))
    assert items and all(set(entry) == LEGACY_ITEM_KEYS for entry in items)


# T49: 플래그 on → 기존 키·값 유지, 추가 키만 존재(비율 1.0 데이터).
def test_t49_flag_on_only_adds_keys(env, monkeypatch):
    client, _, _ = env
    account(client)
    save(client, [{'class_id': GALBI, 'serving_multiplier': 1.5}, {'class_id': 0, 'serving_multiplier': 1}])
    monkeypatch.setattr(settings, 'chat_record_enabled', False)
    off = snapshot_responses(client)
    monkeypatch.setattr(settings, 'chat_record_enabled', True)
    on = snapshot_responses(client)

    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in NEW_ITEM_KEYS}
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value
    assert strip(on) == off
    for entry in item_dicts(on):
        assert set(entry) == LEGACY_ITEM_KEYS | NEW_ITEM_KEYS
        assert entry['consumption_ratio'] == 1.0 and entry['version'] == 1
        assert entry['effective_multiplier'] == entry['serving_multiplier']
