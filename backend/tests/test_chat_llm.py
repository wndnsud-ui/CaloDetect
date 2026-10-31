# 칼로티 코치 LLM(챗봇 업무지시서 v1.2 2단계) 검사. OpenAI 호출은 가짜 함수로 바꾸며 외부 네트워크를 쓰지 않는다.
# 실제 모델 응답 품질은 backend/scripts/check_chat_llm.py로 별도 확인한다.
from uuid import uuid4
import pytest
from backend.app.config import settings
from backend.app.services import chat_llm
from backend.tests.test_chat_record import FOODS, GALBI, NAMES, env, last_bot, meals, photo, start  # noqa: F401
from backend.tests.test_consumption import account

TARGETS = [{'id': 'a', 'food_name': '김치찌개'}, {'id': 'b', 'food_name': '쌀밥'}]


def raw(**values):
    data = {'intent': 'clarify', 'updates': [], 'save': False, 'meal_date': None, 'meal_type': None, 'target_id': None,
            'food_name': None, 'clarification_reason': 'none', 'candidate_ids': [], 'unknown_text': None,
            'reply': None, 'suggest_page': None, 'out_of_scope': False}
    data.update(values)
    return data


# ---- LLM 출력 검증(to_result): 목록에 없는 대상·음식, 범위를 벗어난 비율은 되묻기로 바꾼다 ----

def test_multiple_updates_keep_server_format():
    result = chat_llm.to_result(raw(intent='update_consumption', updates=[
        {'target_id': 'a', 'consumption_ratio': 1}, {'target_id': 'b', 'consumption_ratio': 0.5}]), TARGETS, None, FOODS)
    assert result['source'] == 'llm' and result['intent'] == 'update_consumption'
    assert result['updates'] == [{'target_id': 'a', 'consumption_ratio': 1.0}, {'target_id': 'b', 'consumption_ratio': 0.5}]
    assert result['save'] is False and result['meal_info'] is None


@pytest.mark.parametrize('update', [{'target_id': 'zzz', 'consumption_ratio': 0.5}])
def test_unknown_target_is_not_applied(update):
    result = chat_llm.to_result(raw(intent='update_consumption', updates=[update]), TARGETS, None, FOODS)
    assert result['intent'] == 'clarify' and result['updates'] == []


@pytest.mark.parametrize('ratio', [None, 1.5, -0.1, True])
def test_missing_or_invalid_ratio_asks_amount(ratio):
    result = chat_llm.to_result(raw(intent='update_consumption', updates=[{'target_id': 'b', 'consumption_ratio': ratio}]),
                                TARGETS, None, FOODS)
    assert result['intent'] == 'clarify' and result['clarification_reason'] == 'vague_amount'
    assert result['candidates'] == [{'id': 'b', 'food_name': '쌀밥'}]


def test_food_must_be_in_catalog():
    known = chat_llm.to_result(raw(intent='change_food', target_id='a', food_name=NAMES[GALBI]), TARGETS, None, FOODS)
    assert known['intent'] == 'change_food' and known['food']['id'] == GALBI
    unknown = chat_llm.to_result(raw(intent='add_food', food_name='우주비빔면'), TARGETS, None, FOODS)
    assert unknown['intent'] == 'clarify' and unknown['clarification_reason'] == 'unknown_food'
    assert unknown['unknown_text'] == '우주비빔면'


def test_meal_info_and_general_chat():
    info = chat_llm.to_result(raw(intent='set_meal_info', meal_date='yesterday', meal_type='dinner', save=True), TARGETS, None, FOODS)
    assert info['meal_info'] == {'date': 'yesterday', 'meal_type': 'dinner'} and info['save'] is True
    assert chat_llm.to_result(raw(intent='set_meal_info'), TARGETS, None, FOODS)['clarification_reason'] == 'unknown_meal_type'
    chat = chat_llm.to_result(raw(intent='general_chat', reply='오늘도 고생 많았어요.'), TARGETS, None, FOODS)
    assert (chat['intent'], chat['reply'], chat['out_of_scope']) == ('general_chat', '오늘도 고생 많았어요.', False)
    # 사용자 결정(2026-10-31): 자유 대화에서는 추천·대략 수치 언급을 허용한다. 화면 버튼은 붙여도 직접 답한 것으로 센다.
    numbers = chat_llm.to_result(raw(intent='general_chat', reply='닭가슴살 샐러드 어때요? 대략 300kcal예요.', suggest_page='recommend'), TARGETS, None, FOODS)
    assert numbers['reply'].endswith('300kcal예요.') and numbers['suggest_page'] == 'recommend' and numbers['out_of_scope'] is False


def test_failure_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(settings, 'chat_llm_enabled', True)
    monkeypatch.setattr(settings, 'openai_api_key', 'test-key')

    def broken(messages):
        raise chat_llm.LlmUnavailable('timeout')
    monkeypatch.setattr(chat_llm, 'call_openai', broken)
    understood = chat_llm.interpret('절반만 먹었어', 'amount', TARGETS[:1], None, FOODS)
    assert understood['source'] == 'rule' and understood['updates'][0]['consumption_ratio'] == 0.5
    lost = chat_llm.interpret('밥은 반 정도 남겼어', 'amount', TARGETS, None, FOODS)
    assert lost['llm_failed'] is True


# ---- API: 동의·하루 횟수·LLM 해석 결과 저장(CASE 7·15·17·18) ----

@pytest.fixture
def llm(env, monkeypatch):
    client, engine, detections = env
    monkeypatch.setattr(settings, 'chat_llm_enabled', True)
    monkeypatch.setattr(settings, 'openai_api_key', 'test-key')
    monkeypatch.setattr(settings, 'chat_daily_limit', 5)
    calls = {'count': 0, 'reply': None}

    def fake(messages):
        calls['count'] += 1
        calls['last'] = messages[-1]['content']
        if calls['reply'] is None:
            raise chat_llm.LlmUnavailable('down')
        reply = calls['reply']
        return reply(messages) if callable(reply) else reply
    monkeypatch.setattr(chat_llm, 'call_openai', fake)
    account(client)
    return client, engine, detections, calls


def send(client, conversation, text, chip=False):
    return client.post('/chat/messages', json={'conversation_id': conversation, 'client_message_id': str(uuid4()),
                                               'text': text, 'chip': chip})


def target_id(messages, name):
    prompt = messages[-1]['content']
    line = next(line for line in prompt.splitlines() if line.endswith(f'이름={name}'))
    return line.split('id=')[1].split(' ')[0]


def test_consent_required_once(llm):
    client, _, _, calls = llm
    status = client.get('/chat/status').json()
    assert status['llm'] is True and status['consent_required'] is True and status['usage']['remaining'] == 5
    conversation = start(client)
    assert send(client, conversation, '안녕').status_code == 403
    assert calls['count'] == 0
    agreed = client.post('/chat/consent').json()
    assert agreed['consent_required'] is False
    assert client.post('/chat/consent').json()['consent_required'] is False
    assert client.get('/chat/status').json()['consent_required'] is False


def test_case7_free_sentence_updates_two_foods(llm):
    client, engine, detections, calls = llm
    client.post('/chat/consent')
    detections['value'] = [(GALBI, 0.9), (0, 0.8)]
    conversation = start(client)
    photo(client, conversation)
    calls['reply'] = lambda messages: raw(intent='update_consumption', updates=[
        {'target_id': target_id(messages, NAMES[GALBI]), 'consumption_ratio': 1},
        {'target_id': target_id(messages, NAMES[0]), 'consumption_ratio': 0.5}])
    result = send(client, conversation, f'{NAMES[GALBI]}는 다 먹었는데 {NAMES[0]}은 반 정도 남겼어')
    assert result.status_code == 200, result.text
    body = result.json()
    assert last_bot(body)['kind'] == 'confirm' and meals(engine) == []
    assert sorted(i['consumption_ratio'] for i in body['draft']['items']) == [0.5, 1.0]
    assert body['usage'] == {'used': 1, 'limit': 5, 'remaining': 4}
    # 확인 칩("응")은 규칙 해석기로 저장하고 횟수에 넣지 않는다.
    chip = next(c for c in last_bot(body)['payload']['chips'] if c['label'] == '응')
    saved = send(client, conversation, chip['text'], chip=True).json()
    assert last_bot(saved)['kind'] == 'saved' and saved['usage']['used'] == 1 and calls['count'] == 1
    assert sorted(i.consumption_ratio for i in meals(engine)[0].items) == [0.5, 1.0]


def test_vague_amount_asks_with_choices(llm):
    client, engine, _, calls = llm
    client.post('/chat/consent')
    conversation = start(client)
    photo(client, conversation)
    calls['reply'] = lambda messages: raw(intent='clarify', clarification_reason='vague_amount',
                                          candidate_ids=[target_id(messages, NAMES[GALBI])])
    body = send(client, conversation, '조금 먹었어').json()
    bot = last_bot(body)
    assert '어느 정도' in bot['text'] and [c['label'] for c in bot['payload']['chips']] == ['1/4 정도', '절반 정도', '3/4 정도', '직접 입력']
    assert all(i['consumption_ratio'] == 1 for i in body['draft']['items']) and meals(engine) == []
    half = send(client, conversation, bot['payload']['chips'][1]['text'], chip=True).json()
    assert half['draft']['items'][0]['consumption_ratio'] == 0.5 and half['usage']['used'] == 1


def test_case15_llm_failure_changes_nothing(llm):
    client, engine, _, calls = llm
    client.post('/chat/consent')
    conversation = start(client)
    before = photo(client, conversation)['draft']
    calls['reply'] = None
    body = send(client, conversation, '밥은 반 정도 남겼어').json()
    assert last_bot(body)['text'] == '지금 답변을 만들지 못했어요. 다시 질문해주세요.'
    assert body['draft']['items'] == before['items'] and body['draft']['version'] == before['version']
    assert body['usage']['used'] == 0 and meals(engine) == []


def test_case18_daily_limit_blocks_without_llm_call(llm):
    client, _, _, calls = llm
    client.post('/chat/consent')
    conversation = start(client)
    photo(client, conversation)
    calls['reply'] = raw(intent='general_chat', reply='힘내요!')
    for _ in range(5):
        assert send(client, conversation, '오늘 힘들다').status_code == 200
    calls_before = calls['count']
    blocked = send(client, conversation, '하나 더')
    assert blocked.status_code == 429 and blocked.json()['error']['message'] == '오늘 질문을 다 썼어요. 내일 다시 만나요!'
    assert calls['count'] == calls_before
    assert client.get('/chat/status').json()['usage'] == {'used': 5, 'limit': 5, 'remaining': 0}


def test_chip_flag_needs_matching_chip_text(llm):
    client, _, _, calls = llm
    client.post('/chat/consent')
    conversation = start(client)
    photo(client, conversation)
    calls['reply'] = raw(intent='general_chat', reply='네!')
    # 직전 봇 메시지가 제시하지 않은 문장은 chip=true여도 LLM·횟수 대상이다.
    body = send(client, conversation, '아무 말이나', chip=True).json()
    assert body['usage']['used'] == 1 and calls['count'] == 1


def test_general_chat_and_out_of_scope_counting(llm, monkeypatch):
    client, _, _, calls = llm
    client.post('/chat/consent')
    conversation = start(client)
    calls['reply'] = raw(intent='general_chat', reply='안녕! 오늘도 같이 기록해요.')
    hello = send(client, conversation, '안녕').json()
    assert last_bot(hello)['text'] == '안녕! 오늘도 같이 기록해요.' and hello['usage']['used'] == 1
    # 오늘 기록 요약이 프롬프트에 들어간다.
    assert '[사용자 오늘 기록]' in calls['last'] and '오늘 기록 없음' in calls['last']
    calls['reply'] = raw(intent='general_chat', reply='목표 칼로리 저장은 목표 설정 화면에서 할 수 있어요.', suggest_page='goal', out_of_scope=True)
    ask = send(client, conversation, '목표 칼로리 1500으로 바꿔줘').json()
    chips = last_bot(ask)['payload']['chips']
    assert chips == [{'label': '목표 설정 열기', 'action': 'navigate', 'page': '목표 설정'}]
    assert ask['usage']['used'] == 1


def test_no_saved_meal_answer_is_free(llm):
    client, _, _, calls = llm
    client.post('/chat/consent')
    conversation = start(client)
    calls['reply'] = raw(intent='clarify', clarification_reason='vague_amount')
    body = send(client, conversation, '방금 기록한 양 바꾸고 싶어').json()
    assert '기록한 식사가 아직 없어요' in last_bot(body)['text'] or '사진' in last_bot(body)['text']
    assert body['usage']['used'] == 0


def test_rule_rescues_llm_clarify_on_exact_expression(monkeypatch):
    monkeypatch.setattr(settings, 'chat_llm_enabled', True)
    monkeypatch.setattr(settings, 'openai_api_key', 'test-key')
    monkeypatch.setattr(chat_llm, 'call_openai', lambda messages: raw(intent='clarify', clarification_reason='vague_amount', candidate_ids=['a']))
    rescued = chat_llm.interpret('4분의 1', 'amount', TARGETS[:1], None, FOODS)
    assert rescued['intent'] == 'update_consumption' and rescued['updates'][0]['consumption_ratio'] == 0.25
    vague = chat_llm.interpret('조금 먹었어', 'amount', TARGETS[:1], None, FOODS)
    assert vague['intent'] == 'clarify' and vague['clarification_reason'] == 'vague_amount'
