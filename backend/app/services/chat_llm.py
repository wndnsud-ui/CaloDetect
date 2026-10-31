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
           'select_target', 'clarify', 'general_chat', 'meal_recommend', 'restaurant_search', 'undo']
THEMES = ['balance', 'protein', 'light']
REASONS = ['none', 'ambiguous_target', 'vague_amount', 'unknown_food', 'unknown_meal_type', 'serving_unit',
           'unsupported_expression']
# 챗봇에 아직 없는 기능을 물으면 그 기능이 있는 화면으로 안내한다(서비스에 없는 기능을 있다고 하지 않는다).
PAGES = {'recommend': '식사 추천', 'analysis': '식단 분석', 'goal': '목표 설정', 'history': '히스토리',
         'rewards': '리워드', 'community': '커뮤니티'}
PAGE_LABELS = {'recommend': '오늘 뭐먹지? 열기', 'analysis': '식단 분석 열기', 'goal': '목표 설정 열기',
               'history': '식단 관리 열기', 'rewards': '리워드몰 열기', 'community': '커뮤니티 열기'}
QUESTIONS = {'none': '없음', 'amount': '드신 양', 'food_check': '인식한 음식이 맞는지', 'food_name': '음식 이름',
             'target': '어떤 음식의 양을 바꿀지', 'save_confirm': '이대로 저장할지'}

# Structured Outputs(strict): 모든 키 필수, 값이 없으면 null.
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['intent', 'updates', 'save', 'meal_date', 'meal_type', 'target_id', 'food_name',
                 'clarification_reason', 'candidate_ids', 'unknown_text', 'reply', 'suggest_page', 'out_of_scope',
                 'recommend_theme', 'preference', 'place_query', 'place_area'],
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
        'reply': {'type': ['string', 'null']},
        'suggest_page': {'type': ['string', 'null'], 'enum': [*PAGES, None]},
        'out_of_scope': {'type': 'boolean'},
        'recommend_theme': {'type': ['string', 'null'], 'enum': [*THEMES, None]},
        'preference': {'type': ['string', 'null']},
        'place_query': {'type': ['string', 'null']},
        'place_area': {'type': ['string', 'null']},
    },
}

# 추천 후보 중 조건에 맞는 메뉴 고르기(2단계 호출). 후보 목록에 없는 food_id는 서버가 버린다.
PICK_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['picks', 'answer'],
    'properties': {
        'picks': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False, 'required': ['food_id', 'reason'],
                                             'properties': {'food_id': {'type': 'integer'}, 'reason': {'type': 'string'}}}},
        'answer': {'type': 'string'},
    },
}
PICK_SYSTEM = """너는 식단 앱의 지방이다. 아래 후보 메뉴 중에서 사용자 조건에 가장 잘 맞는 메뉴를 최대 3개 고른다.
- 후보 목록의 food_id만 고른다. 조건(매운맛, 국물 없음, 한식 등)에 맞는 후보를 우선하고, 맞는 후보가 적으면 가까운 것을 고른다.
- reason은 메뉴마다 25자 이내 한 문장. answer는 고른 이유를 1~2문장(100자 이내) 다정한 말투로. 이모지는 쓰지 않는다."""

SYSTEM = """너는 식단 기록 앱 CaloDetect의 '칼로티 코치' 문장 해석기다. 사용자 한 문장을 읽고 JSON만 낸다.
기록을 바꾸는 의도에서는 해석만 하고 칼로리·영양 수치를 만들지 않는다(수치는 서버가 계산한다).

[판단 순서] 반드시 이 순서로 고른다.
1. 현재 질문이 '이대로 저장할지'이고 긍정(응·네·맞아·좋아·그래)이면 confirm_save. 부정·취소면 cancel.
   그 밖의 상황에서 "방금 거 취소해줘", "되돌려줘", "원래대로"는 undo.
2. 문장에 섭취 비율 표현(다·반·절반·4분의1·1/4·25%·안 먹음 등, 오탈자 포함)이 있고 대상 음식이 있으면 update_consumption.
   비율 표현만 있는 짧은 답("4분의 1", "절반만 머겄어")도 update_consumption이다. vague_amount가 아니다.
3. 날짜·식사 종류 변경, 음식 정정·추가, 대상 선택이면 그 의도.
4. 먹을 메뉴를 추천해 달라는 말("오늘 뭐 먹지", "점심 추천", "단백질 많은 메뉴", "가볍게 먹을 거")은 meal_recommend.
   주변 식당·맛집·가게를 찾는 말("근처 샐러드 가게", "강남역 맛집", "국밥집 어디 있어")은 restaurant_search.
5. 그 밖에 기록과 관계없는 말(인사, 기분, 음식 정보, 식단 평가, 목표·포인트 등 앱 기능 질문)은 general_chat.
   "목표 칼로리 바꿔줘"는 음식이 아니므로 unknown_food가 아니라 general_chat(suggest_page=goal, out_of_scope=true).

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
- general_chat: 식사 기록·양 수정·메뉴 추천·식당 찾기가 아닌 말(인사, 잡담, 기분, 질문, 식단 평가 등). reply에 답을 쓴다.
- meal_recommend: 메뉴 추천 요청. meal_type은 말한 끼니(없으면 null), recommend_theme은 단백질=protein,
  가볍게·다이어트·저칼로리=light, 그 밖=balance. preference에는 그 밖의 조건(예: "매운", "국물 없는", "한식", "다른 메뉴")을
  짧게 적고 없으면 null. reply에는 추천을 시작하는 짧은 한 문장을 쓸 수 있다.
- restaurant_search: 식당 찾기. place_query는 음식 종류 키워드(예: 샐러드, 국밥, 한식, 없으면 null),
  place_area는 사용자가 말한 지역·역 이름(예: 강남역, 없으면 null). "근처", "여기"는 지역명이 아니다.
- undo: 직전에 바꾼 기록을 되돌림.

[general_chat 답 reply] (사용자 결정 2026-10-31: 자유 추천·수치 언급 허용)
- 너는 지방이다. 동글동글한 지방 캐릭터로, 다정하고 짧게(2~4문장, 250자 이내) 반말 섞인 존댓말로 답한다. 이모지는 쓰지 않는다.
- 음식 칼로리·영양 질문, 식단 조언, 잡담 모두 직접 답한다. 칼로리·영양 수치는 일반적인 1인분 기준 대략값으로 말해도 된다.
- 아래 [사용자 기록](오늘 끼니와 최근 7일 하루 섭취량)이 있으면 그 기록과 목표 칼로리를 바탕으로 답한다.
  "요즘 왜 살이 안 빠지지", "이번 주 어땠어"처럼 기간을 물으면 최근 7일 기록으로 답한다. 기록에 없는 내용을 사용자가 먹었다고 지어내지 않는다.
  기록이 없으면 아직 오늘 기록이 없다고 말하고 일반적인 기준으로 답한다.
- 질병 진단·치료·약 복용은 지시하지 않고 필요하면 전문가 상담을 권한다. 극단적인 단식·과도한 제한은 권하지 않는다.
- 앱 화면이 더 도움이 되면 suggest_page로 버튼을 붙일 수 있다: 상세 추천=recommend, 기간별 분석=analysis, 목표 변경=goal,
  지난 기록=history, 포인트=rewards, 커뮤니티=community. 그래도 reply에서는 질문에 먼저 직접 답한다.
- out_of_scope는 이 챗봇이 직접 할 수 없는 앱 동작(목표 칼로리 저장, 포인트 사용, 글쓰기 등)을 요청받아 화면 안내만 할 때만 true.
- general_chat·meal_recommend가 아니면 reply=null. general_chat이 아니면 suggest_page=null, out_of_scope=false.
- meal_recommend가 아니면 recommend_theme=null, preference=null. restaurant_search가 아니면 place_query=null, place_area=null.

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


def build_prompt(text, pending_question, targets, pending_target_id, foods, context=None):
    target_lines = '\n'.join(f'- id={t["id"]} 이름={t["food_name"]}' + (f' ({t["label"]})' if t.get('label') else '')
                             for t in targets) or '- (없음)'
    selected = next((t['food_name'] for t in targets if t['id'] == pending_target_id), None)
    return (f'현재 질문: {QUESTIONS.get(pending_question, "없음")}\n'
            f'선택된 대상: {selected or "없음"}\n'
            f'대상 음식(지금 기록 중이거나 고칠 수 있는 음식, 괄호는 끼니):\n{target_lines}\n'
            f'음식 목록: {", ".join(name for _, name in foods)}\n'
            f'[사용자 기록]\n{context or "(없음)"}\n'
            f'사용자 문장: {text}')


def call_openai(messages, schema=None, name='chat_interpretation'):
    if not settings.openai_api_key:
        raise LlmUnavailable('missing key')
    body = {'model': settings.openai_model, 'temperature': 0, 'messages': messages,
            'response_format': {'type': 'json_schema', 'json_schema': {'name': name, 'strict': True, 'schema': schema or SCHEMA}}}
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

    if intent in ('cancel', 'confirm_save', 'affirm', 'undo'):
        return done(base(intent))
    if intent == 'meal_recommend':
        theme = raw.get('recommend_theme') if raw.get('recommend_theme') in THEMES else 'balance'
        meal_type = raw.get('meal_type') if raw.get('meal_type') in MEAL_LABELS else None
        return done(base('meal_recommend', theme=theme, meal_type=meal_type, reply=(raw.get('reply') or '').strip()[:200] or None,
                         preference=(raw.get('preference') or '').strip()[:60] or None))
    if intent == 'restaurant_search':
        return done(base('restaurant_search', place_query=(raw.get('place_query') or '').strip()[:30] or None,
                         place_area=(raw.get('place_area') or '').strip()[:30] or None))
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
    if intent == 'general_chat':
        reply = (raw.get('reply') or '').strip()[:500] or None
        page = raw.get('suggest_page') if raw.get('suggest_page') in PAGES else None
        return done(base('general_chat', reply=reply, suggest_page=page, out_of_scope=bool(raw.get('out_of_scope'))))
    return done(clarify('unsupported_expression'))


def interpret_with_llm(text, pending_question='none', targets=(), pending_target_id=None, foods=(), context=None):
    targets, foods = list(targets), list(foods)
    raw = call_openai([{'role': 'system', 'content': SYSTEM},
                       {'role': 'user', 'content': build_prompt(text, pending_question, targets, pending_target_id, foods, context)}])
    return to_result(raw, targets, pending_target_id, foods)


# 추천 후보에서 조건에 맞는 메뉴 최대 3개를 고른다. 실패하면 None(서버 점수순으로 대신 보여 준다).
def pick_recommendations(preference, candidates, request_text):
    lines = '\n'.join(f'- food_id={c["class_id"]} {c["food_name"]} ({c["category"]}, 약 {round(c["nutrition"]["cal"])}kcal, '
                      f'단백질 {round(c["nutrition"]["protein"])}g)' for c in candidates)
    try:
        raw = call_openai([{'role': 'system', 'content': PICK_SYSTEM},
                           {'role': 'user', 'content': f'사용자 요청: {request_text}\n조건: {preference}\n후보:\n{lines}'}],
                          PICK_SCHEMA, 'meal_picks')
    except LlmUnavailable:
        return None
    by_id = {c['class_id']: c for c in candidates}
    picks, seen = [], set()
    for pick in raw.get('picks') or []:
        if pick.get('food_id') in by_id and pick['food_id'] not in seen:
            seen.add(pick['food_id'])
            picks.append({'candidate': by_id[pick['food_id']], 'reason': (pick.get('reason') or '').strip()[:60]})
    return {'picks': picks[:3], 'answer': (raw.get('answer') or '').strip()[:200]} if picks else None


# 같은 음식이 여러 끼니에 있는데 끼니를 말하지 않고 한꺼번에 바꾸려 하면 되묻기로 바꾼다(CASE 9).
# "아침이랑 점심 둘 다"처럼 끼니를 모두 말했으면 그대로 둔다.
def ambiguous_meals(result, text, targets):
    if result['intent'] != 'update_consumption':
        return result
    by_id = {t['id']: t for t in targets}
    groups = {}
    for update in result['updates']:
        target = by_id.get(update['target_id'], {})
        if target.get('label'):
            groups.setdefault(target['food_name'], []).append(target)
    for same in groups.values():
        labels = {t['label'] for t in same}
        if len(labels) > 1 and not all(any(word in text for word in label.split()[-1:]) for label in labels):
            ambiguous = clarify('ambiguous_target', same)
            ambiguous['source'] = 'llm'
            return ambiguous
    return result


# 해석 진입점. LLM을 쓸 수 있으면 LLM, 장애 때만 규칙 해석기(비상용).
# 규칙 해석기도 알아듣지 못하면 llm_failed=True로 돌려 화면에 오류 문구를 보여 준다(기록 변경 없음).
def interpret(text, pending_question='none', targets=(), pending_target_id=None, foods=(), use_llm=True, context=None):
    if use_llm and available():
        try:
            result = interpret_with_llm(text, pending_question, targets, pending_target_id, foods, context)
            # LLM이 되묻기로 답했거나 확인 응답(응·저장해줘)을 고른 경우, 규칙 해석기가 정확히 아는 표현이면 규칙 결과를 쓴다.
            # 예: "4분의 1"을 되묻기로, 확인 질문이 아닌데 "응"을 저장 확인으로 고른 경우.
            if result['intent'] in ('clarify', 'confirm_save', 'affirm'):
                rule = interpret_chat(text, pending_question, targets, pending_target_id, foods)
                if rule['intent'] != 'clarify':
                    rule['source'] = 'llm'
                    return rule
            return ambiguous_meals(result, text, targets)
        except LlmUnavailable:
            result = interpret_chat(text, pending_question, targets, pending_target_id, foods)
            if result['intent'] == 'clarify' and result['clarification_reason'] == 'unsupported_expression':
                result['llm_failed'] = True
            return result
    return interpret_chat(text, pending_question, targets, pending_target_id, foods)
