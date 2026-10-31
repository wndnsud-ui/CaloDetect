# 칼로티 코치 LLM 해석기(챗봇 업무지시서 v1.2 2단계). 공급자: OpenAI Chat Completions + Structured Outputs.
# LLM은 문장을 해석해 "무엇을 바꿀지"만 고른다. 비율 적용·음식 카탈로그 매칭·kcal 계산·저장은 기존 서버 코드가 한다.
# 결과는 규칙 해석기(chat_interpret.interpret_chat)와 같은 형식이며 source='llm'이다.
# LLM이 고른 대상·음식·비율은 여기서 다시 검증하고, 목록에 없거나 범위를 벗어나면 되묻기(clarify)로 바꾼다.
import json
import logging
import httpx
from ..config import settings
from .chat_interpret import MEAL_LABELS, base, catalog_index, clarify, interpret_chat
from .consumption import food_key

logger = logging.getLogger('calodetect')

INTENTS = ['update_consumption', 'confirm_save', 'affirm', 'cancel', 'set_meal_info', 'change_food', 'add_food',
           'select_target', 'clarify', 'unrelated']
REASONS = ['none', 'ambiguous_target', 'vague_amount', 'unknown_food', 'unknown_meal_type', 'serving_unit',
           'unsupported_expression']
QUESTIONS = {'none': '없음', 'amount': '드신 양', 'food_check': '인식한 음식이 맞는지', 'food_name': '음식 이름',
             'target': '어떤 음식의 양을 바꿀지', 'save_confirm': '이대로 저장할지'}

# Structured Outputs(strict): 모든 키 필수, 값이 없으면 null.
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['intent', 'updates', 'save', 'meal_date', 'meal_type', 'target_id', 'food_name',
                 'clarification_reason', 'candidate_ids', 'unknown_text'],
    'properties': {
        'intent': {'type': 'string', 'enum': INTENTS},
        'updates': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['target_id', 'consumption_ratio'],
            'properties': {'target_id': {'type': 'string'}, 'consumption_ratio': {'type': ['number', 'null']}}}},
        'save': {'type': 'boolean'},
        'meal_date': {'type': ['string', 'null'], 'enum': ['today', 'yesterday', None]},
        'meal_type': {'type': ['string', 'null'], 'enum': ['breakfast', 'lunch', 'dinner', 'snack', None]},
        'target_id': {'type': ['string', 'null']},
        'food_name': {'type': ['string', 'null']},
        'clarification_reason': {'type': 'string', 'enum': REASONS},
        'candidate_ids': {'type': 'array', 'items': {'type': 'string'}},
        'unknown_text': {'type': ['string', 'null']},
    },
}

SYSTEM = """너는 식단 기록 앱 CaloDetect의 '칼로티 코치' 문장 해석기다. 사용자 한 문장을 읽고 JSON만 낸다.
너는 해석만 한다. 칼로리·영양 수치는 절대 만들지 않는다.

[의도 intent]
- update_consumption: 대상 음식의 섭취 비율을 말함. updates에 대상마다 {target_id, consumption_ratio}.
- confirm_save: 저장 확인 질문(현재 질문=이대로 저장할지)에 긍정하거나, 양 없이 "저장해줘/올려줘/기록해줘"만 말함.
- affirm: 확인 질문이 아닌 상황의 단순 긍정("응", "맞아").
- cancel: 그만·취소·안 할래, 또는 "아니야"처럼 직전 제안을 거절함.
- set_meal_info: 날짜·식사 종류만 바꿈("어제 저녁으로 바꿔줘"). meal_date, meal_type을 채움.
- change_food: "A가 아니라 B야"처럼 대상 음식을 다른 음식으로 바꿈. target_id=A의 id, food_name=B.
  현재 질문이 '인식한 음식이 맞는지'이고 대상이 하나일 때 음식 이름만 말해도 change_food.
- add_food: 현재 질문이 '음식 이름'일 때 음식 이름을 말함. food_name을 채움.
- select_target: 비율 없이 대상 음식만 고름("갈비구이는"). target_id를 채움.
- clarify: 되물어야 함. clarification_reason을 고른다.
- unrelated: 식사 기록과 관계없는 말(메뉴 추천, 잡담, 질문 등).

[섭취 비율 규칙]
- 다/전부/싹/남김없이 = 1, 반/절반/반만/50% = 0.5, 4분의1/1/4/25% = 0.25, 4분의3/3/4/75% = 0.75,
  안 먹음/하나도 안 먹음 = 0, 3분의1 = 0.33, 3분의2 = 0.67. 그 밖의 명확한 숫자 비율은 0~1로 바꾼다.
- "반 정도 남겼어"는 남긴 양이 반이므로 0.5, "조금 남겼어"는 양이 불명확하다.
- 조금·좀·약간·많이·대부분·거의처럼 양이 불명확하면 비율을 정하지 말고 intent=clarify, clarification_reason=vague_amount,
  candidate_ids에 그 음식 id를 넣는다. 사용자가 말하지 않은 양을 절대 추측하지 않는다.
- 두 그릇·2인분·두 배처럼 1인분을 넘는 양은 clarify + serving_unit.
- 한 문장에 여러 음식이 있으면 updates에 모두 넣는다. "찌개는 다 먹고 밥은 반" → 찌개 1, 밥 0.5.
- "다 먹었어"처럼 음식을 지목하지 않으면 대상 음식 전체에 같은 비율을 적용한다.
- 음식을 지목했는데 대상 목록에서 둘 이상과 겹치면 clarify + ambiguous_target, candidate_ids에 후보 id.
- 지목한 음식이 대상 목록에 없으면 clarify + unsupported_expression.
- 선택된 대상이 있으면 음식을 지목하지 않은 비율은 그 대상에만 적용한다.

[저장 save]
- "올려줘/저장해줘/기록해줘/저장/올려"처럼 저장을 직접 말한 경우에만 true. 그 밖에는 false.

[음식 이름]
- food_name은 반드시 아래 음식 목록에 있는 이름을 그대로 쓴다. 오탈자·줄임말은 목록의 가장 가까운 이름으로 고친다.
  목록에 맞는 음식이 없으면 intent=clarify, clarification_reason=unknown_food, unknown_text=사용자가 말한 음식 이름.

[식사 종류]
- 아침=breakfast, 점심=lunch, 저녁=dinner, 간식=snack. 날짜는 오늘=today, 어제=yesterday. 말하지 않았으면 null.
- 식사 종류는 아침·점심·저녁·간식 네 가지뿐이다. 야식·브런치·새참·디저트처럼 다른 이름으로 바꾸라고 하면
  비슷한 종류로 바꾸지 말고 intent=clarify, clarification_reason=unknown_meal_type. 예: "야식으로 바꿔줘" → clarify + unknown_meal_type.

해당 없는 값은 null 또는 빈 배열로 둔다. clarify가 아니면 clarification_reason='none'."""


def available():
    return bool(settings.chat_llm_enabled and settings.openai_api_key)


class LlmUnavailable(Exception):
    pass


def build_prompt(text, pending_question, targets, pending_target_id, foods):
    target_lines = '\n'.join(f'- id={t["id"]} 이름={t["food_name"]}' for t in targets) or '- (없음)'
    selected = next((t['food_name'] for t in targets if t['id'] == pending_target_id), None)
    return (f'현재 질문: {QUESTIONS.get(pending_question, "없음")}\n'
            f'선택된 대상: {selected or "없음"}\n'
            f'대상 음식(지금 기록 중인 음식):\n{target_lines}\n'
            f'음식 목록: {", ".join(name for _, name in foods)}\n'
            f'사용자 문장: {text}')


def call_openai(messages):
    if not settings.openai_api_key:
        raise LlmUnavailable('missing key')
    body = {'model': settings.openai_model, 'temperature': 0, 'messages': messages,
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'chat_interpretation', 'strict': True, 'schema': SCHEMA}}}
    try:
        response = httpx.post(f'{settings.openai_base_url.rstrip("/")}/chat/completions', json=body,
                              headers={'Authorization': f'Bearer {settings.openai_api_key}'},
                              timeout=settings.chat_llm_timeout_seconds)
        response.raise_for_status()
        message = response.json()['choices'][0]['message']
        if message.get('refusal'):
            raise LlmUnavailable('refusal')
        return json.loads(message['content'])
    except LlmUnavailable:
        raise
    except Exception as error:
        # 키·문장이 로그에 남지 않도록 오류 종류만 기록한다.
        logger.warning('chat llm call failed: %s', type(error).__name__)
        raise LlmUnavailable(type(error).__name__) from error


# LLM 출력 → 규칙 해석기와 같은 결과 형식. 대상 id·음식 이름·비율·식사 종류를 서버 기준으로 다시 확인한다.
def to_result(raw, targets, pending_target_id, foods):
    by_id = {t['id']: t for t in targets}
    index = catalog_index(foods)
    intent = raw.get('intent')

    def done(result):
        result['source'] = 'llm'
        return result

    def meal_info():
        meal_type = raw.get('meal_type')
        if meal_type not in MEAL_LABELS:
            return None
        return {'date': 'yesterday' if raw.get('meal_date') == 'yesterday' else 'today', 'meal_type': meal_type}

    def food():
        name = raw.get('food_name') or ''
        match = index.get(food_key(name))
        return {'id': match[0], 'name': match[1]} if match else None

    if intent in ('cancel', 'confirm_save', 'affirm'):
        return done(base(intent))
    if intent == 'set_meal_info':
        info = meal_info()
        return done(base('set_meal_info', meal_info=info, save=bool(raw.get('save')))) if info else done(clarify('unknown_meal_type'))
    if intent in ('change_food', 'add_food'):
        chosen = food()
        if not chosen:
            return done(clarify('unknown_food', unknown_text=(raw.get('unknown_text') or raw.get('food_name') or '').strip()[:40] or '그 음식'))
        if intent == 'add_food':
            return done(base('add_food', food=chosen))
        target = raw.get('target_id') if raw.get('target_id') in by_id else (targets[0]['id'] if len(targets) == 1 else None)
        return done(base('change_food', target_id=target, food=chosen)) if target else done(clarify('ambiguous_target', targets))
    if intent == 'select_target':
        target = raw.get('target_id')
        return done(base('select_target', target_id=target)) if target in by_id else done(clarify('unsupported_expression'))
    if intent == 'update_consumption':
        updates = []
        for update in raw.get('updates') or []:
            ratio = update.get('consumption_ratio')
            if update.get('target_id') not in by_id:
                return done(clarify('unsupported_expression'))
            if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not 0 <= ratio <= 1:
                return done(clarify('vague_amount', [by_id[update['target_id']]]))
            updates.append({'target_id': update['target_id'], 'consumption_ratio': round(float(ratio), 2)})
        if not updates:
            return done(clarify('vague_amount', targets if len(targets) == 1 else []))
        return done(base('update_consumption', save=bool(raw.get('save')), meal_info=meal_info(), updates=updates))
    if intent == 'clarify':
        reason = raw.get('clarification_reason')
        reason = reason if reason in REASONS and reason != 'none' else 'unsupported_expression'
        candidates = [by_id[i] for i in raw.get('candidate_ids') or [] if i in by_id]
        if reason == 'vague_amount' and not candidates and pending_target_id in by_id:
            candidates = [by_id[pending_target_id]]
        if reason == 'unknown_food':
            return done(clarify('unknown_food', unknown_text=(raw.get('unknown_text') or '그 음식').strip()[:40]))
        return done(clarify(reason, candidates))
    return done(clarify('unrelated'))


def interpret_with_llm(text, pending_question='none', targets=(), pending_target_id=None, foods=()):
    targets, foods = list(targets), list(foods)
    raw = call_openai([{'role': 'system', 'content': SYSTEM},
                       {'role': 'user', 'content': build_prompt(text, pending_question, targets, pending_target_id, foods)}])
    return to_result(raw, targets, pending_target_id, foods)


# 해석 진입점. LLM을 쓸 수 있으면 LLM, 장애 때만 규칙 해석기(비상용).
# 규칙 해석기도 알아듣지 못하면 llm_failed=True로 돌려 화면에 오류 문구를 보여 준다(기록 변경 없음).
def interpret(text, pending_question='none', targets=(), pending_target_id=None, foods=(), use_llm=True):
    if use_llm and available():
        try:
            return interpret_with_llm(text, pending_question, targets, pending_target_id, foods)
        except LlmUnavailable:
            result = interpret_chat(text, pending_question, targets, pending_target_id, foods)
            if result['intent'] == 'clarify' and result['clarification_reason'] == 'unsupported_expression':
                result['llm_failed'] = True
            return result
    return interpret_chat(text, pending_question, targets, pending_target_id, foods)
