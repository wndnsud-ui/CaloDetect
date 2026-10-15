# 채팅 식사기록(A1) 대화 해석기. 순수 함수이며 DB는 대화 서비스가 읽어 넘긴다(지시서 v9 8장).
# A0 해석기(consumption.py)의 정규화·비율·대상 규칙을 그대로 쓰고, 음식 정정·날짜/식사 종류·대상 칩을 더한다.
# 모든 표현은 전체 일치만 인정하며 유사도·별칭 추측을 하지 않는다. 규칙 기반(LLM 미사용).
import re
from .consumption import (AFFIRM_WORDS, CANCEL_WORDS, TARGET_PARTICLES, compact, food_key, is_word,
                          match_ratio, resolve_updates, split_save_verb, strip_correction)

# 기존 "식단 올리기" 화면과 같은 선택지·저장값·표시명·순서(K20: main.jsx meals).
MEAL_TYPES = [('breakfast', '아침'), ('lunch', '점심'), ('dinner', '저녁'), ('snack', '간식')]
MEAL_LABELS = dict(MEAL_TYPES)
MEAL_VALUES = {label: value for value, label in MEAL_TYPES}
NAME_ENDINGS = ['이에요', '예요', '이야', '야', '']
MEAL_INFO = re.compile(r'(오늘|어제)?(아침|점심|저녁|간식)(?:으로|로)(?:바꿔줘|바꿔|해줘|해)?요?$')
UNKNOWN_MEAL = re.compile(r'(?:오늘|어제)?(.+?)(?:으로|로)(?:바꿔줘|해줘)요?$')
FOOD_CHANGE = re.compile(r'^(.+?)(?:가|이)아니라(.+)$')
SERVING_WORDS = ('인분', '그릇', '두배', '2배', '세배', '3배')


def chips_for_meal_types():
    return [{'label': label, 'text': f'{label}으로 바꿔줘', 'value': value} for value, label in MEAL_TYPES]


# 정규화된 음식명 → (food_id, 원래 이름). 공백·`_`·`/`를 같게 취급한다.
def catalog_index(foods):
    return {food_key(name): (food_id, name) for food_id, name in foods}


# "불고기야"·"곰탕 설렁탕이야"처럼 이름 + 서술 어미. 카탈로그와 정확히 일치할 때만 반환.
def match_food_name(value, index):
    for ending in NAME_ENDINGS:
        if ending and not value.endswith(ending):
            continue
        name = value[:len(value) - len(ending)] if ending else value
        if name in index:
            return index[name]
    return None


def base(intent, **values):
    data = {'intent': intent, 'updates': [], 'save': False, 'meal_info': None, 'food_change': None,
            'target_id': None, 'food': None, 'clarification_reason': None, 'candidates': [], 'unknown_text': None,
            'source': 'rule'}
    data.update(values)
    return data


def clarify(reason, candidates=(), unknown_text=None):
    return base('clarify', clarification_reason=reason, unknown_text=unknown_text,
                candidates=[{'id': c['id'], 'food_name': c['food_name']} for c in candidates])


# 문장 끝의 날짜·식사 종류("어제 저녁으로", "점심으로 바꿔줘")를 떼어 낸다. (남은 문자열, 식사 정보 | None | 'unknown').
def split_meal_info(value):
    match = MEAL_INFO.search(value)
    if match:
        rest = value[:match.start()]
        return (rest[:-1] if rest.endswith(',') else rest), {'date': 'yesterday' if match.group(1) == '어제' else 'today',
                                                              'meal_type': MEAL_VALUES[match.group(2)]}
    unknown = UNKNOWN_MEAL.fullmatch(value)
    if unknown:
        return value, 'unknown'
    return value, None


# 채팅 한 문장 해석.
# pending_question: none|amount|food_check|food_name|target|save_confirm
# targets: 현재 초안 항목 [{'id','food_name'}], pending_target_id: 대상 칩으로 고른 항목, foods: [(food_id, name)] 150종.
def interpret_chat(text, pending_question='none', targets=(), pending_target_id=None, foods=()):
    targets = list(targets)
    index = catalog_index(foods)
    value = compact(text)
    value, corrected = strip_correction(value)
    if corrected and value == '':
        return base('cancel')
    if is_word(value, CANCEL_WORDS):
        return base('cancel')

    # 음식 정정: "A가 아니라 B야". A는 현재 초안 음식, B는 카탈로그 정확 일치.
    change = FOOD_CHANGE.match(value)
    if change:
        source = [t for t in targets if food_key(t['food_name']) == change.group(1)]
        if not source:
            return clarify('unsupported_expression')
        if len(source) > 1:
            return clarify('ambiguous_target', source)
        food = match_food_name(change.group(2), index)
        if not food:
            return clarify('unknown_food', unknown_text=change.group(2))
        return base('change_food', target_id=source[0]['id'], food={'id': food[0], 'name': food[1]})

    # 음식 이름만 말함: 인식 실패(food_name)면 추가, 대상 하나인 음식 확인(food_check)이면 교체.
    if pending_question in ('food_name', 'food_check'):
        food = match_food_name(value, index)
        if food:
            if pending_question == 'food_check' and len(targets) == 1:
                return base('change_food', target_id=targets[0]['id'], food={'id': food[0], 'name': food[1]})
            if pending_question == 'food_name':
                return base('add_food', food={'id': food[0], 'name': food[1]})

    body, save = split_save_verb(value)
    if not save and is_word(body, AFFIRM_WORDS):
        return base('confirm_save' if pending_question == 'save_confirm' else 'affirm')
    if save and (body == '' or is_word(body, AFFIRM_WORDS)):
        return base('confirm_save')

    body, meal_info = split_meal_info(body)
    if meal_info == 'unknown':
        return clarify('unknown_meal_type')
    if body == '' and meal_info:
        return base('set_meal_info', meal_info=meal_info, save=save)

    # 대상 칩: "갈비구이는"만 보내면 그 음식을 대상으로 고르고 비율을 기다린다.
    if not save and not meal_info:
        for particle in TARGET_PARTICLES:
            chosen = [t for t in targets if body == food_key(t['food_name']) + particle]
            if len(chosen) == 1:
                return base('select_target', target_id=chosen[0]['id'])
            if len(chosen) > 1:
                return clarify('ambiguous_target', chosen)

    if pending_question == 'food_name' and not targets:
        name = body.rstrip('야')
        return clarify('unknown_food', unknown_text=name) if name else clarify('unsupported_expression')

    selected = pending_target_id if any(t['id'] == pending_target_id for t in targets) else None
    updates, failure = resolve_updates(body, targets, selected)
    if failure:
        if failure['clarification_reason'] == 'unsupported_expression' and any(w in body for w in SERVING_WORDS):
            return clarify('serving_unit')
        reason = failure['clarification_reason']
        return clarify(reason, failure['candidates'])
    return base('update_consumption', save=save, meal_info=meal_info,
                updates=[{'target_id': t['id'], 'consumption_ratio': r} for t, r in updates])
