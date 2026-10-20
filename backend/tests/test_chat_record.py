# 채팅 식사기록 A1 검사(지시서 v9 14장 A1). 사진 분석은 mock(detect_image 대체)이며 실제 YOLO 시연과 구분한다.
import io
from uuid import uuid4
import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.chat_api import router as chat_router
from backend.app.models import Meal, MealItem, Detection
from backend.app.models_chat import ChatMessage, MealDraft, ChatAttachment
from backend.app.services import chat_record
from backend.app.services.chat_interpret import interpret_chat, chips_for_meal_types
from backend.app.services.nutrition import food_catalog
from backend.tests.test_consumption import build_env, teardown_env, account

FOODS = [(f['class_id'], f['food_name']) for f in food_catalog()]
NAMES = {cid: name for cid, name in FOODS}
GALBI, RICE = 2, next(cid for cid, name in FOODS if name == '쌀밥') if any(n == '쌀밥' for _, n in FOODS) else 0


@pytest.fixture
def env(monkeypatch, tmp_path):
    engine, schema, base_engine, routes = build_env(monkeypatch, tmp_path, True)
    app.include_router(chat_router)
    detections = {'value': [(GALBI, 0.9)]}

    def fake_detect(path):
        if detections['value'] is None:
            raise RuntimeError('boom')
        return {'model_version': 'test', 'detections': [
            {'class_id': cid, 'predicted_label': NAMES[cid], 'confidence': conf, 'bbox': [0, 0, 50, 50]}
            for cid, conf in detections['value']]}
    monkeypatch.setattr(chat_record, 'detect_image', fake_detect)
    with TestClient(app) as client:
        yield client, engine, detections
    teardown_env(engine, schema, base_engine, routes)


def png():
    data = io.BytesIO(); Image.new('RGB', (100, 100), 'white').save(data, format='PNG')
    return data.getvalue()


def start(client):
    state = client.get('/chat/conversation').json()
    return state['conversation_id']


def photo(client, conversation_id, request_id=None):
    up = client.post('/chat/attachments', data={'conversation_id': conversation_id,
                     'upload_request_id': request_id or str(uuid4())}, files={'file': ('a.png', png(), 'image/png')})
    assert up.status_code == 200, up.text
    analyzed = client.post(f'/chat/attachments/{up.json()["attachment_id"]}/analysis')
    assert analyzed.status_code == 200, analyzed.text
    return analyzed.json()


def say(client, conversation_id, text, message_id=None):
    response = client.post('/chat/messages', json={'conversation_id': conversation_id,
                           'client_message_id': message_id or str(uuid4()), 'text': text})
    assert response.status_code == 200, response.text
    return response.json()


def meals(engine):
    with Session(engine) as db:
        return db.scalars(select(Meal)).all()


def last_bot(result):
    return [m for m in result['messages'] if m['role'] == 'bot'][-1]


# T42: 분석 후 한 문장 "절반만 먹었어 올려줘" → 자동 저장.
def test_t42_one_sentence_saves(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    analyzed = photo(client, conversation)
    assert analyzed['draft']['pending_question'] == 'amount'
    assert analyzed['messages'][-1]['kind'] == 'analysis'
    result = say(client, conversation, '절반만 먹었어 올려줘')
    assert last_bot(result)['kind'] == 'saved'
    saved = meals(engine)
    assert len(saved) == 1 and saved[0].chat_attachment_id
    item = saved[0].items[0]
    assert (item.consumption_ratio, item.serving_multiplier, item.nutrition['cal']) == (0.5, 1.0, 361.5)
    assert client.get('/analytics/today').json()['totals']['cal'] == 361.5
    history = client.get('/meals/history').json()['items'][0]
    assert history['image_urls'] and history['items'][0]['consumption_ratio'] == 0.5


# T43: 비율만 → 저장 안 됨, 이어서 "올려줘" / "맞아 올려줘"는 100%.
def test_t43_ratio_then_confirm(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    photo(client, conversation)
    asked = say(client, conversation, '절반만 먹었어')
    assert last_bot(asked)['kind'] == 'confirm' and '기록할까요' in last_bot(asked)['text']
    assert '오늘' in last_bot(asked)['text']
    assert meals(engine) == []
    say(client, conversation, '올려줘')
    assert meals(engine)[0].items[0].consumption_ratio == 0.5
    photo(client, conversation)
    say(client, conversation, '맞아 올려줘')
    assert sorted(m.items[0].consumption_ratio for m in meals(engine)) == [0.5, 1.0]


# T44: 초안 없이 "응"·"올려줘", 취소, 불명확 표현.
def test_t44_no_save_without_intent(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    for text in ['응', '올려줘']:
        assert '사진' in last_bot(say(client, conversation, text))['text']
    photo(client, conversation)
    assert '멈췄' in last_bot(say(client, conversation, '취소'))['text']
    assert last_bot(say(client, conversation, '조금 먹었어 올려줘'))['kind'] == 'text'
    assert meals(engine) == []
    say(client, conversation, '절반만 먹었어 올려줘')
    assert len(meals(engine)) == 1


# T45: 여러 음식.
def test_t45_multiple_foods(env):
    client, engine, detections = env
    account(client)
    detections['value'] = [(GALBI, 0.9), (0, 0.8)]
    conversation = start(client)
    photo(client, conversation)
    vague = say(client, conversation, '절반만 먹었어')
    assert '어떤 음식' in last_bot(vague)['text'] and len(last_bot(vague)['payload']['chips']) == 2
    bad = say(client, conversation, f'{NAMES[GALBI]}는 절반, {NAMES[0]}은 조금 먹었어 올려줘')
    assert meals(engine) == [] and last_bot(bad)['kind'] == 'text'
    say(client, conversation, f'{NAMES[GALBI]}는 절반, {NAMES[0]}은 다 먹었어 올려줘')
    ratios = {i.food_id: i.consumption_ratio for i in meals(engine)[0].items}
    assert ratios == {GALBI: 0.5, 0: 1.0}


# T60: 단순 긍정의 상태 의존.
def test_t60_affirm_depends_on_question(env):
    client, engine, detections = env
    account(client)
    detections['value'] = [(GALBI, 0.1)]
    conversation = start(client)
    checked = photo(client, conversation)
    assert checked['draft']['pending_question'] == 'food_check'
    say(client, conversation, '맞아')
    assert meals(engine) == []
    say(client, conversation, '응')
    assert meals(engine) == []
    say(client, conversation, '절반')
    say(client, conversation, '응')
    assert len(meals(engine)) == 1


# T61·T62: 명시적 저장 동사, 식사 종류 칩·결합 문장·없는 값.
def test_t61_t62_save_verb_and_meal_info(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    photo(client, conversation)
    changed = say(client, conversation, '점심으로 바꿔줘')
    assert '점심' in last_bot(changed)['text'] and changed['draft']['meal_type'] == 'lunch'
    assert last_bot(say(client, conversation, '브런치로 바꿔줘'))['text'].startswith('식사 종류')
    assert meals(engine) == []
    say(client, conversation, '어제 저녁으로 올려줘')
    meal = meals(engine)[0]
    assert meal.meal_type == 'dinner' and meal.items[0].consumption_ratio == 1.0
    assert (chat_record.korean_date(chat_record.datetime.now(chat_record.timezone.utc)) - meal.meal_date).days == 1


@pytest.mark.parametrize('hour,expected', [(5, 'breakfast'), (10, 'breakfast'), (11, 'lunch'), (15, 'lunch'),
                                           (16, 'dinner'), (21, 'dinner'), (22, 'snack'), (4, 'snack')])
def test_t62_default_meal_type(hour, expected):
    from datetime import datetime
    assert chat_record.default_meal_type(datetime(2026, 10, 15, hour, 30, tzinfo=chat_record.KST)) == expected


# T63: 음식 정정.
def test_t63_food_change(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    photo(client, conversation)
    target = NAMES[0]
    changed = say(client, conversation, f'{NAMES[GALBI]}가 아니라 {target}야')
    assert changed['draft']['items'][0]['food_id'] == 0
    assert changed['draft']['items'][0]['source_detection_id']
    assert '목록에 없어요' in last_bot(say(client, conversation, f'{target}가 아니라 없는음식야'))['text']
    say(client, conversation, '다 먹었어 올려줘')
    after = say(client, conversation, f'{target}가 아니라 {NAMES[GALBI]}야')
    assert '바꿀 수 없어요' in last_bot(after)['text']


def test_t63_underscore_name_matches():
    name = next((n for _, n in FOODS if '_' in n), None)
    if not name:
        pytest.skip('밑줄 음식명 없음')
    spoken = name.replace('_', ' ')
    result = interpret_chat(spoken + '이야', 'food_name', [], None, FOODS)
    assert result['intent'] == 'add_food' and result['food']['name'] == name


# T64: 기준 배율 표현.
def test_t64_serving_expressions(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    photo(client, conversation)
    for text in ['2인분 먹었어', '두 그릇 먹었어 올려줘']:
        assert '1인분 기준' in last_bot(say(client, conversation, text))['text']
    assert meals(engine) == []
    say(client, conversation, '다 먹었어 올려줘')
    assert all(i.serving_multiplier == 1.0 for m in meals(engine) for i in m.items)


# T65: "아니야" 단독 / 정정 / 취소 후 이어서.
def test_t65_cancel_and_correction(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    photo(client, conversation)
    say(client, conversation, '절반만 먹었어')
    assert '멈췄' in last_bot(say(client, conversation, '아니야'))['text']
    corrected = say(client, conversation, '아니, 4분의 1')
    assert corrected['draft']['items'][0]['consumption_ratio'] == 0.25
    say(client, conversation, '취소')
    say(client, conversation, '절반만 먹었어 올려줘')
    assert meals(engine)[0].items[0].consumption_ratio == 0.5


# T66: 대상 칩과 전체 적용.
def test_t66_target_chip(env):
    client, engine, detections = env
    account(client)
    detections['value'] = [(GALBI, 0.9), (0, 0.8)]
    conversation = start(client)
    photo(client, conversation)
    chip = last_bot(say(client, conversation, '절반만 먹었어'))['payload']['chips'][0]['text']
    say(client, conversation, chip)
    result = say(client, conversation, '절반만 먹었어')
    ratios = {i['food_id']: i['consumption_ratio'] for i in result['draft']['items']}
    assert ratios == {GALBI: 0.5, 0: 1.0}
    every = say(client, conversation, '전부 절반만 먹었어')
    assert {i['consumption_ratio'] for i in every['draft']['items']} == {0.5}


# T67: 5.3 표의 모든 칩 전송 문장이 의도대로 해석된다(clarify 0건).
def test_t67_chip_sentences():
    two = [{'id': 'a', 'food_name': NAMES[GALBI]}, {'id': 'b', 'food_name': NAMES[0]}]
    sentences = [(c['text'], 'amount') for c in chat_record.ANALYSIS_CHIPS + chat_record.AMOUNT_CHIPS]
    sentences += [(c['text'], 'save_confirm') for c in chat_record.YES_NO]
    sentences += [(c['text'], 'amount') for c in chips_for_meal_types()]
    sentences += [('맞아', 'food_check')]
    sentences += [(chat_record.topic(t['food_name']), 'target') for t in two]
    for text, pending in sentences:
        targets = two if pending == 'target' else two[:1]
        result = interpret_chat(text, pending, targets, None, FOODS)
        assert result['intent'] != 'clarify', (text, result)


# T24·T38·T50: 확정 시 탐지 ID 보존, 음식 수정은 기존 POST /meals와 같이 탐지 기록에만 남는다(재학습 폐기).
def test_t24_t38_t50_confirm_matches_post_meals(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    photo(client, conversation)
    say(client, conversation, f'{NAMES[GALBI]}가 아니라 {NAMES[0]}야')
    say(client, conversation, '다 먹었어 올려줘')
    with Session(engine) as db:
        item = db.scalars(select(MealItem)).one()
        assert item.detection_log_id and item.predicted_label == NAMES[GALBI] and item.food_id == 0
        assert db.get(Detection, item.detection_log_id).corrected_label == NAMES[0]
        chat_nutrition = item.nutrition
    # 같은 입력을 기존 POST /meals로 저장한 결과와 영양 snapshot 비교.
    direct = client.post('/meals', json={'meal_type': 'lunch', 'items': [{'class_id': 0, 'serving_multiplier': 1}]}).json()
    assert direct['items'][0]['nutrition'] == chat_nutrition


# T25: 같은 client_message_id 재전송·다른 내용, upload_request_id 재전송.
def test_t25_idempotency(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    upload_id = str(uuid4())
    photo(client, conversation, upload_id)
    again = client.post('/chat/attachments', data={'conversation_id': conversation, 'upload_request_id': upload_id},
                        files={'file': ('a.png', png(), 'image/png')})
    assert again.status_code == 200
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ChatAttachment)) == 1
    message_id = str(uuid4())
    first = say(client, conversation, '다 먹었어 올려줘', message_id)
    second = say(client, conversation, '다 먹었어 올려줘', message_id)
    assert second['replayed'] is True and [m['id'] for m in second['messages']] == [m['id'] for m in first['messages']]
    assert len(meals(engine)) == 1
    conflict = client.post('/chat/messages', json={'conversation_id': conversation, 'client_message_id': message_id,
                                                   'text': '절반'})
    assert conflict.status_code == 409


# T27: 타 사용자 대화·사진·메시지.
def test_t27_other_user(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    analyzed = photo(client, conversation)
    account(client, 'two@example.com')
    assert client.post('/chat/messages', json={'conversation_id': conversation, 'client_message_id': str(uuid4()),
                                               'text': '올려줘'}).status_code == 404
    assert client.post(f'/chat/attachments/{analyzed["attachment_id"]}/analysis').status_code == 404
    assert client.get(analyzed['image_url'].replace('/api', '')).status_code == 404
    assert client.get('/chat/conversation').json()['conversation_id'] != conversation


# T32·T33·T35: 분석 결과 복원(재분석 없음), 분석 실패 후 음식 이름으로 완성.
def test_t32_t33_restore_and_failure(env):
    client, engine, detections = env
    account(client)
    conversation = start(client)
    analyzed = photo(client, conversation)
    restored = client.get('/chat/conversation').json()
    assert restored['draft']['id'] == analyzed['draft']['id']
    again = client.post(f'/chat/attachments/{analyzed["attachment_id"]}/analysis').json()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Detection)) == 1
    detections['value'] = None
    failed = photo(client, conversation)
    assert failed['draft']['pending_question'] == 'food_name' and failed['draft']['analysis_failed']
    assert failed['image_url']
    with Session(engine) as db:
        assert db.scalar(select(MealDraft).where(MealDraft.id == analyzed['draft']['id'])).status == 'abandoned'
    say(client, conversation, f'{NAMES[GALBI]}야')
    say(client, conversation, '다 먹었어 올려줘')
    meal = meals(engine)[0]
    assert meal.chat_attachment_id and meal.items[0].detection_log_id is None
    assert client.get('/meals/history').json()['items'][0]['image_urls']


# 저장 후 말로 정정(5.2-8).
def test_saved_meal_correction_by_chat(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    photo(client, conversation)
    say(client, conversation, '다 먹었어 올려줘')
    asked = say(client, conversation, '아니, 4분의 1')
    assert last_bot(asked)['kind'] == 'correction'
    assert meals(engine)[0].items[0].consumption_ratio == 1.0
    say(client, conversation, '응')
    with Session(engine) as db:
        item = db.scalars(select(MealItem)).one()
        assert (item.consumption_ratio, item.version, item.nutrition['cal']) == (0.25, 2, 180.75)


# T51: 초안·대화·첨부는 집계에 들어가지 않는다.
def test_t51_drafts_not_aggregated(env):
    client, engine, _ = env
    account(client)
    before = client.get('/analytics/today').json()['totals']
    conversation = start(client)
    photo(client, conversation)
    say(client, conversation, '절반만 먹었어')
    assert client.get('/analytics/today').json()['totals'] == before
    assert client.get('/meals/history').json()['items'] == []


# 업로드 검증: 비지원 형식은 성공 처리하지 않는다.
def test_t29_rejects_unsupported(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    gif = io.BytesIO(); Image.new('RGB', (10, 10)).save(gif, format='GIF')
    bad = client.post('/chat/attachments', data={'conversation_id': conversation, 'upload_request_id': str(uuid4())},
                      files={'file': ('a.gif', gif.getvalue(), 'image/gif')})
    assert bad.status_code == 422
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ChatAttachment)) == 0
