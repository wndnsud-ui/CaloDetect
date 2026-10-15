# 섭취량 대화 해석과 섭취 비율 영양 계산. DB·네트워크에 의존하지 않는 순수 함수만 둔다.
# 규칙 기반 해석기이며 LLM을 사용하지 않는다. interpret()와 같은 입력·출력이면 다른 해석기로 교체할 수 있다.
# 허용 표현은 지시서 v9 8장 문법의 전체 일치만 인정하고, 부분 검색·유사도·별칭 추측은 하지 않는다.
import re
from .nutrition import calculate_nutrition

NUTRIENTS = ['cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium']

# 앞머리 정정 표현. 긴 것부터 정확히 한 번 제거한다.
CORRECTION_PREFIXES = ['아니야', '아니', '아냐', '정정']
SAVE_VERBS = ['저장해줘', '기록해줘', '올려줘', '저장해', '기록해', '올려']
AFFIRM_WORDS = ['맞아', '그래', '좋아', '응', '네', '어']
CANCEL_WORDS = ['안할래', '취소', '그만']
ENDINGS = ['먹었어요', '먹었어', '먹었음', '먹음']
# (핵심어, 비율, 어미 없이 단독 허용)
RATIO_CORES = [
    ('다', 1.0, False), ('전부', 1.0, False),
    ('절반만', 0.5, True), ('절반', 0.5, True), ('반만', 0.5, True), ('1/2', 0.5, True), ('50%', 0.5, True),
    ('반', 0.5, False),
    ('4분의1', 0.25, True), ('사분의일', 0.25, True), ('1/4', 0.25, True), ('25%', 0.25, True),
    ('4분의3', 0.75, True), ('사분의삼', 0.75, True), ('3/4', 0.75, True), ('75%', 0.75, True),
    ('하나도안', 0.0, False), ('안', 0.0, False),
]
ALL_PREFIXES = ['전부', '모두', '다']
TARGET_PARTICLES = ['은', '는', '을', '를']
CLAUSE_SPLIT = re.compile(r',|그리고')


# 공백을 모두 지우고 문장 끝 . ! ~ 를 제거한다.
def compact(text):
    value = re.sub(r'\s+', '', text or '')
    return value.rstrip('.!~')


# 정정 접두어를 한 번 제거한다. (남은 문자열, 접두어 제거 여부)를 반환한다.
def strip_correction(value):
    for prefix in CORRECTION_PREFIXES:
        if value.startswith(prefix):
            rest = value[len(prefix):]
            return (rest[1:] if rest.startswith(',') else rest), True
    return value, False


# 음식명 비교용 정규화. 공백·`_`·`/`를 같게 취급해 모두 지운다(정확 일치 비교에만 사용).
def food_key(name):
    return re.sub(r'[\s_/]+', '', name or '')


# 어휘 + 선택적 끝 `요` 전체 일치 여부.
def is_word(value, words):
    return any(value == word or value == word + '요' for word in words)


# 비율 문장 전체 일치. 일치하면 비율, 아니면 None.
def match_ratio(value):
    for core, ratio, standalone in RATIO_CORES:
        if value == core and standalone:
            return ratio
        if value.startswith(core) and value[len(core):] in ENDINGS:
            return ratio
    return None


# 끝의 저장 동사를 떼어 낸다. (남은 문자열, 저장 동사 여부).
def split_save_verb(value):
    for verb in SAVE_VERBS:
        for word in (verb + '요', verb):
            if value.endswith(word):
                rest = value[:-len(word)]
                return rest[:-1] if rest.endswith(',') else rest, True
    return value, False


# 결과 구조(8.4)를 만든다. 지정하지 않은 값은 null.
def result(intent, **values):
    data = {'intent': intent, 'meal_info': {'date': None, 'meal_type': None},
            'food_change': {'from_food_id': None, 'to_food_id': None},
            'target_type': None, 'target_id': None, 'consumption_ratio': None,
            'needs_clarification': False, 'clarification_reason': None,
            'candidates': [], 'updates': [], 'source': 'rule'}
    data.update(values)
    return data


def clarify(reason, candidates=()):
    return result('clarify', needs_clarification=True, clarification_reason=reason,
                  candidates=[{'id': c['id'], 'food_name': c['food_name']} for c in candidates])


# 절 앞의 대상 음식명(+조사)을 찾는다. 반환: ('none'|'one'|'many', 대상 목록, 남은 문자열).
def split_target(value, targets):
    for particle in TARGET_PARTICLES:
        matched = [t for t in targets if value.startswith(food_key(t['food_name']) + particle)]
        if matched:
            names = {food_key(t['food_name']) for t in matched}
            # 서로 다른 이름이 동시에 접두어로 맞으면 더 긴 이름만 남긴다.
            longest = max(names, key=len)
            matched = [t for t in matched if food_key(t['food_name']) == longest]
            rest = value[len(longest) + len(particle):]
            return ('one' if len(matched) == 1 else 'many'), matched, rest
    return 'none', [], value


# 비율 본문(저장 동사를 뗀 뒤)을 대상별 비율 목록으로 해석한다. 실패하면 clarify 결과를 반환한다.
def resolve_updates(body, targets, selected_id):
    clauses = [c for c in CLAUSE_SPLIT.split(body)]
    if len(clauses) > 1:
        # 여러 절은 각 절이 `음식명+조사+비율`로 모두 전체 일치해야 한다.
        updates = []
        for clause in clauses:
            kind, matched, rest = split_target(clause, targets)
            ratio = match_ratio(rest)
            if kind != 'one' or ratio is None or (selected_id and matched[0]['id'] != selected_id):
                return None, (clarify('ambiguous_target', targets) if kind == 'many' else clarify('unsupported_expression'))
            updates.append((matched[0], ratio))
        if len({t['id'] for t, _ in updates}) != len(updates):
            return None, clarify('unsupported_expression')
        return updates, None
    kind, matched, rest = split_target(body, targets)
    if kind == 'many':
        return None, clarify('ambiguous_target', matched)
    if kind == 'one':
        ratio = match_ratio(rest)
        if ratio is None:
            return None, clarify('unsupported_expression')
        if selected_id and matched[0]['id'] != selected_id:
            # 카드로 고른 대상과 문장 속 음식명이 다르면 추측하지 않고 묻는다.
            return None, clarify('ambiguous_target', targets)
        return [(matched[0], ratio)], None
    # 전체 적용 접두어: "전부 절반만 먹었어" → 모든 대상.
    for prefix in ALL_PREFIXES:
        if body.startswith(prefix):
            ratio = match_ratio(body[len(prefix):])
            if ratio is not None:
                if not targets:
                    return None, clarify('missing_target')
                return [(t, ratio) for t in targets], None
    ratio = match_ratio(body)
    if ratio is None:
        return None, clarify('unsupported_expression')
    if selected_id:
        chosen = [t for t in targets if t['id'] == selected_id]
        if chosen:
            return [(chosen[0], ratio)], None
    if not targets:
        return None, clarify('missing_target')
    if len(targets) == 1 or (ratio == 1.0 and body.startswith(('다', '전부'))):
        # 대상이 하나이거나 "다/전부 먹었어"(그 자체가 전체 1.0)면 모든 대상에 적용한다.
        return [(t, ratio) for t in targets], None
    return None, clarify('ambiguous_target', targets)


# 대화 한 문장을 섭취량·확정·취소 의도로 해석한다.
# pending_question: 봇의 직전 질문 상태(none|amount|food_check|food_name|target|save_confirm).
# targets: 현재 대상 목록 [{'id','food_name'}], selected_id: 카드로 고른 대상 ID(이미 소유권 검증됨).
# empty_meal: 식사 단위 진입인데 항목이 0개인 경우.
def interpret(text, pending_question='none', targets=(), selected_id=None, target_type='meal_item', empty_meal=False):
    targets = list(targets)
    value = compact(text)
    value, corrected = strip_correction(value)
    if corrected and value == '':
        return result('cancel')
    if is_word(value, CANCEL_WORDS):
        return result('cancel')
    body, save = split_save_verb(value)
    if save and body == '':
        return result('confirm_save')
    if save and is_word(body, AFFIRM_WORDS):
        # "맞아 올려줘": 단순 긍정 + 명시적 저장 동사 = 저장 확정.
        return result('confirm_save')
    if not save and is_word(body, AFFIRM_WORDS):
        if pending_question == 'save_confirm':
            return result('confirm_save')
        return result('affirm')
    if empty_meal:
        return clarify('empty_meal')
    updates, failure = resolve_updates(body, targets, selected_id)
    if failure:
        return failure
    intent = 'update_and_confirm' if save else 'update_consumption'
    single = updates[0] if len(updates) == 1 else None
    return result(intent, target_type=target_type,
                  target_id=single[0]['id'] if single else None,
                  consumption_ratio=single[1] if single else None,
                  updates=[{'target_id': t['id'], 'food_name': t['food_name'], 'consumption_ratio': r}
                           for t, r in updates])


# 기준 배율 × 섭취 비율로 CSV에서 다시 계산한다. 현재 snapshot에 비율을 다시 곱하지 않는다.
# calculate_nutrition은 배율 0을 거부하지 않으므로(K05) 비율 0도 같은 함수로 계산한다(모든 값 0.0).
def consumption_nutrition(class_id, base_multiplier, ratio):
    effective = base_multiplier * ratio
    return effective, calculate_nutrition(class_id, effective)['nutrition']


# 저장된 영양 snapshot이 현재 계산과 같은지 확인한다(키 집합과 소수 2자리 값).
def matches_calculation(stored, calculated):
    if not isinstance(stored, dict) or set(stored) != set(calculated):
        return False
    return all(abs(float(stored[key]) - float(calculated[key])) < 0.005 for key in calculated)
