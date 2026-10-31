# 칼로티 코치 LLM 해석기 실제 호출 점검(개발용). .env의 OPENAI_API_KEY로 OpenAI를 부르며 DB는 쓰지 않는다.
# 서비스와 같은 interpret()(LLM + 규칙 보완)를 부른다. 기존 규칙 해석기 검사 문장과 업무지시서 v1.2 CASE 문장을 LLM에 보내 의도·비율이 기대와 같은지 본다.
# 실행: .\.venv-backend\Scripts\python.exe -m backend.scripts.check_chat_llm
import sys
from backend.app.config import settings
from backend.app.services.chat_llm import LlmUnavailable, available, interpret
from backend.app.services.nutrition import food_catalog

FOODS = [(f['class_id'], f['food_name']) for f in food_catalog()]
NAMES = dict(FOODS)
GALBI, FIRST = NAMES[2], NAMES[0]
ONE = [{'id': 'g', 'food_name': GALBI}]
TWO = [{'id': 'g', 'food_name': GALBI}, {'id': 'f', 'food_name': FIRST}]


def ratios(*pairs):
    return lambda r: r['intent'] == 'update_consumption' and sorted((u['target_id'], u['consumption_ratio']) for u in r['updates']) == sorted(pairs)


def intent(name, **checks):
    return lambda r: r['intent'] == name and all(r.get(k) == v for k, v in checks.items())


def reason(name):
    return lambda r: r['intent'] == 'clarify' and r['clarification_reason'] == name


# (문장, 현재 질문, 대상, 기대 판정)
CASES = [
    ('절반만 먹었어 올려줘', 'amount', ONE, lambda r: ratios(('g', 0.5))(r) and r['save']),
    ('다 먹었어', 'amount', ONE, lambda r: ratios(('g', 1.0))(r) and not r['save']),
    ('4분의 1', 'amount', ONE, ratios(('g', 0.25))),
    ('하나도 안 먹었어', 'amount', ONE, ratios(('g', 0.0))),
    ('응', 'save_confirm', ONE, intent('confirm_save')),
    ('응', 'food_check', ONE, intent('affirm')),
    ('올려줘', 'save_confirm', ONE, intent('confirm_save')),
    ('취소', 'save_confirm', ONE, intent('cancel')),
    ('어제 저녁으로 바꿔줘', 'save_confirm', ONE, lambda r: r['intent'] == 'set_meal_info' and r['meal_info'] == {'date': 'yesterday', 'meal_type': 'dinner'}),
    ('야식으로 바꿔줘', 'save_confirm', ONE, reason('unknown_meal_type')),
    (f'{GALBI}가 아니라 불고기야', 'amount', ONE, lambda r: r['intent'] in ('change_food', 'clarify')),
    (f'{GALBI}는', 'amount', TWO, intent('select_target', target_id='g')),
    (f'{GALBI}는 절반, {FIRST}은 다 먹었어 올려줘', 'amount', TWO, lambda r: ratios(('g', 0.5), ('f', 1.0))(r) and r['save']),
    (f'{GALBI}는 다 먹었는데 {FIRST}은 반 정도 남겼어', 'amount', TWO, ratios(('g', 1.0), ('f', 0.5))),  # CASE 7
    ('조금 먹었어', 'amount', ONE, reason('vague_amount')),
    ('밥 조금 먹었어', 'amount', [{'id': 'r', 'food_name': '쌀밥'}], reason('vague_amount')),
    ('두 그릇 먹었어', 'amount', ONE, reason('serving_unit')),
    ('절반만 머겄어', 'amount', ONE, ratios(('g', 0.5))),  # 오탈자
    ('오늘 저녁 뭐 먹지?', 'none', ONE, lambda r: r['intent'] == 'general_chat' and bool(r['reply']) and not r['out_of_scope']),
    ('오늘 힘들다 ㅠㅠ', 'none', ONE, lambda r: r['intent'] == 'general_chat' and bool(r['reply']) and not r['out_of_scope']),
    ('안녕', 'none', [], lambda r: r['intent'] == 'general_chat' and bool(r['reply'])),
    ('오늘 식사 어땠어?', 'none', [], lambda r: r['intent'] == 'general_chat' and bool(r['reply'])),
    ('목표 칼로리 1500으로 바꿔줘', 'none', [], lambda r: r['intent'] == 'general_chat' and r['suggest_page'] == 'goal'),
]


def main():
    if not available():
        print('CHAT_LLM_ENABLED=true와 OPENAI_API_KEY가 필요합니다.'); return 1
    print(f'model={settings.openai_model}')
    failed = 0
    for text, question, targets, check in CASES:
        try:
            result = interpret(text, question, targets, None, FOODS)
        except LlmUnavailable as error:
            print(f'ERROR  {text} -> {error}'); failed += 1; continue
        ok = check(result)
        failed += not ok
        summary = {k: result[k] for k in ('intent', 'updates', 'save', 'meal_info', 'target_id', 'clarification_reason', 'reply', 'suggest_page') if result.get(k)}
        print(f'{"PASS" if ok else "FAIL"}  {text} -> {summary}')
    print(f'{len(CASES) - failed}/{len(CASES)} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
