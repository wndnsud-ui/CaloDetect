# 확정 식사 항목의 섭취량 해석·미리보기·수정 서비스(A0).
# 잠금 순서: 식사 항목 행 → MutationRequest 확인 → version 비교. 모든 판정은 행 잠금 이후에 한다.
# 기존 save_meal·correction·apply_correction은 호출하지 않으며 RetrainingSample을 만들지 않는다.
import hashlib
import json
import logging
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from ..models import Food, Meal, MealItem
from ..models_chat import MutationRequest
from .consumption import consumption_nutrition, interpret, matches_calculation

OPERATION = 'meal_item.consumption'
logger = logging.getLogger('calodetect')


# 상태 코드·오류 코드·사용자 문구를 함께 전달하는 서비스 오류. 내부 예외 문구는 노출하지 않는다.
class ChatRecordError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def not_found():
    return ChatRecordError(404, '404', '기록을 찾을 수 없습니다.')


# 소유한 식사 항목과 식사를 반환한다. 미존재·타 사용자는 모두 404.
def owned_item(db, user, item_id, lock=False):
    item = db.get(MealItem, item_id, with_for_update=lock) if item_id else None
    meal = db.get(Meal, item.meal_id) if item else None
    if not item or not meal or meal.user_id != user.id:
        raise not_found()
    return item, meal


def owned_meal(db, user, meal_id):
    meal = db.get(Meal, meal_id) if meal_id else None
    if not meal or meal.user_id != user.id:
        raise not_found()
    return meal


def snapshot(item, ratio=None, nutrition=None):
    ratio = item.consumption_ratio if ratio is None else ratio
    return {'consumption_ratio': ratio, 'effective_multiplier': item.serving_multiplier * ratio,
            'nutrition': dict(nutrition if nutrition is not None else item.nutrition)}


# 대화 문장을 해석한다. 확정 식사에는 아무것도 쓰지 않는다.
def interpret_for_meal(db, user, body):
    selected_id = None
    empty_meal = False
    if body.item_id:
        item, meal = owned_item(db, user, body.item_id)
        if body.meal_id and body.meal_id != meal.id:
            raise not_found()
        selected_id = item.id
        targets = [{'id': i.id, 'food_name': i.corrected_label} for i in meal.items]
    elif body.meal_id:
        meal = owned_meal(db, user, body.meal_id)
        targets = [{'id': i.id, 'food_name': i.corrected_label} for i in meal.items]
        empty_meal = not targets
    else:
        targets = []
    return interpret(body.text, body.pending_question, targets, selected_id, 'meal_item', empty_meal)


# 수정 전(저장값)·후(CSV × 기준 배율 × 새 비율) 영양값을 비교해 보여 준다. 쓰기 없음.
def preview_item(db, user, item_id, ratio):
    item, meal = owned_item(db, user, item_id)
    food = db.get(Food, item.food_id)
    _, current = consumption_nutrition(item.food_id, item.serving_multiplier, item.consumption_ratio)
    effective, after = consumption_nutrition(item.food_id, item.serving_multiplier, float(ratio))
    return {'item_id': item.id, 'meal_id': meal.id, 'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type,
            'food_name': item.corrected_label, 'unit': food.serving_unit if food else None,
            'serving_multiplier': item.serving_multiplier, 'version': item.version,
            # 저장된 값이 현재 계산과 다르면 화면이 원인을 단정하지 않고 "값 불일치"를 안내한다.
            'stored_matches_calculation': matches_calculation(item.nutrition, current),
            'before': snapshot(item),
            'after': {'consumption_ratio': float(ratio), 'effective_multiplier': effective, 'nutrition': after}}


# 필드 순서·숫자 표현을 정규화한 명령 내용의 해시.
def payload_hash(item_id, ratio, expected_version):
    payload = {'item_id': item_id, 'consumption_ratio': float(ratio), 'expected_version': int(expected_version)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def replay(record):
    return {'item_id': record.result_id, 'version': record.result_version, 'before': record.before,
            'after': record.after, 'replayed': True}


def existing_request(db, user, request_id):
    return db.scalar(select(MutationRequest).where(MutationRequest.user_id == user.id,
        MutationRequest.operation == OPERATION, MutationRequest.request_id == request_id))


def check_replay(record, digest):
    if record.payload_hash != digest:
        raise ChatRecordError(409, 'request_id_conflict', '같은 요청 ID로 다른 내용을 저장할 수 없어요.')
    return replay(record)


# 섭취 비율을 수정한다. 같은 request_id·같은 내용은 원 결과를 쓰기 없이 반환한다(R2·R10).
def update_item_consumption(db, user, item_id, body):
    request_id = str(body.request_id)
    item, meal = owned_item(db, user, item_id, lock=True)
    digest = payload_hash(item.id, body.consumption_ratio, body.expected_version)
    record = existing_request(db, user, request_id)
    if record:
        return check_replay(record, digest)
    if item.version != body.expected_version:
        raise ChatRecordError(409, 'version_conflict', '기록이 변경됐어요. 최신 내용을 확인해 주세요.')
    before = snapshot(item)
    ratio = float(body.consumption_ratio)
    _, nutrition = consumption_nutrition(item.food_id, item.serving_multiplier, ratio)
    item.consumption_ratio = ratio
    # JSON 컬럼은 제자리 수정하지 않고 새 dict를 대입한다.
    item.nutrition = dict(nutrition)
    item.version = item.version + 1
    after = snapshot(item, ratio, nutrition)
    db.add(MutationRequest(user_id=user.id, operation=OPERATION, request_id=request_id, target_type='meal_item',
                           target_id=item.id, payload_hash=digest, status='succeeded', result_id=item.id,
                           result_version=item.version, before=before, after=after))
    try:
        db.commit()
    except IntegrityError:
        # 같은 request_id가 동시에 저장된 경우: 먼저 성공한 결과를 돌려주거나 충돌로 판정한다.
        db.rollback()
        record = existing_request(db, user, request_id)
        if record:
            return check_replay(record, digest)
        raise ChatRecordError(409, 'version_conflict', '기록이 변경됐어요. 최신 내용을 확인해 주세요.')
    except Exception:
        db.rollback()
        logger.exception('consumption update failed')
        raise ChatRecordError(503, 'save_failed', '아직 저장되지 않았어요. 다시 시도해 주세요.')
    logger.info('meal item consumption update')
    return {'item_id': item.id, 'meal_id': meal.id, 'version': item.version, 'before': before, 'after': after,
            'replayed': False}
