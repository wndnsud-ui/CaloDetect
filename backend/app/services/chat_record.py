# 채팅 식사기록(A1) 서비스: 대화·사진 업로드·분석·식사 초안·말로 자동 확정·저장 후 정정.
# 저장은 사용자가 확정 의사를 말했을 때만 서버가 한다(R14·R15). 클라이언트는 영양값·확정 요청을 보내지 않는다.
# 잠금 순서: 대화 → 초안 → 식사 → 항목. 초안·대화·첨부는 집계·추천·관리자 QA가 읽지 않는다(P7).
import hashlib
import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from ..models import Detection, Food, ImageUpload, Meal, MealItem
from ..models_chat import ChatAttachment, ChatMessage, Conversation, DraftItem, MealDraft, MutationRequest
from .chat_interpret import MEAL_LABELS, chips_for_meal_types, interpret_chat
from .consumption_record import ChatRecordError, preview_item, update_item_consumption
from .correction import apply_correction
from .nutrition import calculate_nutrition
from .timezone import KST, korean_date
from .vision import detect_image
from . import rewards
from .. import storage

logger = logging.getLogger('calodetect')
NUTRIENTS = ['cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium']
ACTIVE = ('analyzing', 'needs_confirmation')
LOW_CONFIDENCE = 0.3
AMOUNT_CHIPS = [{'label': '다 먹었어', 'text': '다 먹었어'}, {'label': '절반', 'text': '절반만 먹었어'},
                {'label': '4분의 1', 'text': '4분의 1 먹었어'}, {'label': '안 먹었어', 'text': '안 먹었어'}]
ANALYSIS_CHIPS = [{'label': '다 먹었어', 'text': '다 먹었어 올려줘'}, {'label': '절반', 'text': '절반만 먹었어'}]
YES_NO = [{'label': '응', 'text': '응'}, {'label': '아니야', 'text': '아니야'}]
NAV_CHIPS = [{'label': '다른 사진도 기록하기', 'action': 'new_photo'}, {'label': '오늘의 식사 보기', 'action': 'today'}]
FAILED_TEXT = '음식을 확인하기 어려워요. 다시 찍거나 음식 이름을 말씀해 주세요.'
NO_DRAFT_TEXT = '먼저 사진을 찍거나 앨범에서 선택해 주세요.'


def not_found():
    return ChatRecordError(404, '404', '기록을 찾을 수 없습니다.')


def now_kst():
    return datetime.now(timezone.utc).astimezone(KST)


# 식사 종류 기본값. 기존 화면에 시각 규칙이 없어(K20) 지시서 5.0 기본 구간을 쓴다(Asia/Seoul).
def default_meal_type(instant=None):
    hour = (instant or now_kst()).hour
    if 5 <= hour < 11:
        return 'breakfast'
    if 11 <= hour < 16:
        return 'lunch'
    if 16 <= hour < 22:
        return 'dinner'
    return 'snack'


def has_batchim(word):
    last = word[-1:] if word else ''
    return '가' <= last <= '힣' and (ord(last) - 0xAC00) % 28 != 0


def topic(word):
    return word + ('은' if has_batchim(word) else '는')


def object_(word):
    return word + ('을' if has_batchim(word) else '를')


def to_(word):
    last = word[-1:] if word else ''
    rieul = '가' <= last <= '힣' and (ord(last) - 0xAC00) % 28 == 8
    return word + ('으로' if has_batchim(word) and not rieul else '로')


def percent(ratio):
    return f'{round(ratio * 100)}%'


def amount_word(ratio):
    return {1.0: '다', 0.5: '절반', 0.25: '4분의 1', 0.75: '4분의 3', 0.0: '안 먹음'}.get(ratio, percent(ratio))


def fmt(value):
    return f'{value:,.2f}'.rstrip('0').rstrip('.')


def require_storage():
    if not storage.configured():
        raise ChatRecordError(503, '503', '업로드 이미지 저장 정책을 설정해 주세요.')


def food_rows(db):
    return {food.id: food for food in db.scalars(select(Food).where(Food.active == True))}


def date_label(day):
    today = korean_date(datetime.now(timezone.utc))
    if day == today:
        return '오늘'
    if day == today - timedelta(days=1):
        return '어제'
    return f'{day.month}월 {day.day}일'


def meal_label(draft):
    return f'{date_label(draft.meal_date)} {MEAL_LABELS[draft.meal_type]}'


# ---- 직렬화 ----

def image_url(attachment):
    return f'/api/meals/images/{attachment.image_upload_id}' if attachment and attachment.image_upload_id else None


def draft_json(db, draft):
    if not draft:
        return None
    foods = food_rows(db)
    attachment = db.get(ChatAttachment, draft.attachment_id) if draft.attachment_id else None
    items = [{'id': i.id, 'food_id': i.food_id, 'food_name': foods[i.food_id].canonical_name if i.food_id in foods else '',
              'unit': foods[i.food_id].serving_unit if i.food_id in foods else '', 'consumption_ratio': i.consumption_ratio,
              'serving_multiplier': i.serving_multiplier, 'effective_multiplier': i.serving_multiplier * i.consumption_ratio,
              'nutrition': dict(i.nutrition), 'bbox': i.bbox, 'confidence': i.confidence,
              'source_detection_id': i.source_detection_id} for i in draft.items]
    return {'id': draft.id, 'status': draft.status, 'version': draft.version, 'meal_date': str(draft.meal_date),
            'meal_type': draft.meal_type, 'meal_label': meal_label(draft), 'pending_question': draft.pending_question,
            'pending_target_id': draft.pending_target_id, 'analysis_failed': draft.analysis_failed,
            'image_url': image_url(attachment), 'items': items,
            'totals': {k: round(sum(i['nutrition'][k] for i in items), 2) for k in NUTRIENTS}}


def message_json(message):
    return {'id': message.id, 'sequence': message.sequence, 'role': message.author_role, 'kind': message.kind,
            'text': message.text, 'payload': message.payload, 'client_message_id': message.client_message_id,
            'status': message.status, 'reply_to_id': message.reply_to_id, 'created_at': message.created_at.isoformat()}


# ---- 대화·메시지 ----

def get_conversation(db, user, conversation_id=None, lock=False):
    if conversation_id:
        conversation = db.get(Conversation, conversation_id, with_for_update=lock)
        if not conversation or conversation.user_id != user.id:
            raise not_found()
        return conversation
    conversation = db.scalar(select(Conversation).where(Conversation.user_id == user.id, Conversation.status == 'active')
                             .order_by(Conversation.created_at.desc()))
    if conversation:
        return conversation
    conversation = Conversation(user_id=user.id, status='active', next_sequence=1, pending_question='none')
    db.add(conversation); db.flush()
    add_message(db, conversation, 'bot', 'text', '사진을 찍거나 선택해 식사를 기록해 보세요.')
    db.commit()
    return conversation


def add_message(db, conversation, role, kind, text, payload=None, client_message_id=None, reply_to=None, status='processed'):
    message = ChatMessage(conversation_id=conversation.id, user_id=conversation.user_id, sequence=conversation.next_sequence,
                          author_role=role, kind=kind, text=text[:1000], payload=payload,
                          client_message_id=client_message_id, status=status, reply_to_id=reply_to)
    conversation.next_sequence = conversation.next_sequence + 1
    db.add(message); db.flush()
    return message


def bot(db, conversation, text, reply_to, kind='text', **payload):
    return add_message(db, conversation, 'bot', kind, text, payload or None, reply_to=reply_to)


def active_draft(db, conversation, lock=False):
    query = (select(MealDraft).where(MealDraft.conversation_id == conversation.id, MealDraft.status.in_(ACTIVE))
             .order_by(MealDraft.created_at.desc()))
    if lock:
        query = query.with_for_update()
    return db.scalars(query).first()


def conversation_state(db, user, before=None, limit=50):
    conversation = get_conversation(db, user)
    query = select(ChatMessage).where(ChatMessage.conversation_id == conversation.id)
    if before:
        query = query.where(ChatMessage.sequence < before)
    rows = db.scalars(query.order_by(ChatMessage.sequence.desc()).limit(limit + 1)).all()
    has_more = len(rows) > limit
    rows = list(reversed(rows[:limit]))
    return {'conversation_id': conversation.id, 'messages': [message_json(m) for m in rows], 'has_more': has_more,
            'draft': draft_json(db, active_draft(db, conversation)), 'meal_types': chips_for_meal_types(),
            'pending_question': conversation.pending_question}


# ---- 사진 업로드·분석 ----

# 기존 /meals/detect와 같은 기준(실제 디코딩, JPG/PNG, 10MB, 2500만 화소). 기존 검증은 라우트 본문에 있어 호출할 수 없다(K16).
def decode_image(content):
    if len(content) > 10 * 1024 * 1024:
        raise ChatRecordError(413, '413', '이미지는 10MB 이하로 업로드해 주세요.')
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in ('JPEG', 'PNG'):
                raise ValueError('format')
            if source.width * source.height > 25_000_000:
                raise ValueError('dimensions')
            return ImageOps.exif_transpose(source).convert('RGB')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ChatRecordError(422, '422', '정상 JPG/PNG 이미지를 선택해 주세요. 최대 2500만 화소입니다.')


def attachment_state(db, attachment):
    messages = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == attachment.conversation_id,
        ChatMessage.sequence >= db.get(ChatMessage, attachment.message_id).sequence).order_by(ChatMessage.sequence)).all()
    draft = db.scalar(select(MealDraft).where(MealDraft.attachment_id == attachment.id))
    return {'attachment_id': attachment.id, 'image_url': image_url(attachment), 'status': attachment.status,
            'messages': [message_json(m) for m in messages], 'draft': draft_json(db, draft)}


def upload_photo(db, user, conversation_id, upload_request_id, content):
    conversation = get_conversation(db, user, conversation_id, lock=True)
    checksum = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(ChatAttachment).where(ChatAttachment.user_id == user.id,
                                                      ChatAttachment.upload_request_id == upload_request_id))
    if existing:
        if existing.checksum != checksum:
            raise ChatRecordError(409, 'request_id_conflict', '같은 업로드 ID로 다른 사진을 보낼 수 없어요.')
        return attachment_state(db, existing)
    image = decode_image(content)
    require_storage()
    upload_id = str(uuid.uuid4())
    filename = upload_id + '.jpg'
    buffer = io.BytesIO(); image.save(buffer, format='JPEG', quality=90); data = buffer.getvalue()
    # 저장소 기록 → DB 기록 순서. DB 실패 시 이 요청이 만든 사진만 지운다(참조되지 않음).
    try:
        storage.put(filename, data)
    except OSError:
        logger.exception('chat photo storage failed')
        raise ChatRecordError(503, 'upload_failed', '사진을 저장하지 못했어요. 다시 시도해 주세요.')
    try:
        db.add(ImageUpload(id=upload_id, user_id=user.id, image_path=filename))
        attachment = ChatAttachment(user_id=user.id, conversation_id=conversation.id, image_upload_id=upload_id,
                                    mime='image/jpeg', size=len(data), checksum=checksum, status='uploaded',
                                    upload_request_id=upload_request_id, storage_key=filename)
        db.add(attachment); db.flush()
        message = add_message(db, conversation, 'user', 'photo', '사진', {'image_url': f'/api/meals/images/{upload_id}',
                                                                          'attachment_id': attachment.id})
        attachment.message_id = message.id
        # 새 사진은 새 식사 초안을 시작한다. 확정 전 이전 초안은 abandoned로 보존하고 저장된 식사는 덮어쓰지 않는다.
        for old in db.scalars(select(MealDraft).where(MealDraft.conversation_id == conversation.id,
                                                      MealDraft.status.in_(ACTIVE))).all():
            old.status = 'abandoned'
        conversation.pending_question = 'none'; conversation.pending_payload = None
        db.add(MealDraft(conversation_id=conversation.id, user_id=user.id, attachment_id=attachment.id,
                         status='analyzing', version=1, meal_date=korean_date(datetime.now(timezone.utc)),
                         meal_type=default_meal_type(), pending_question='none', analysis_failed=False))
        bot(db, conversation, '사진 속 음식을 확인하고 있어요.', message.id, kind='status')
        db.commit()
    except IntegrityError:
        db.rollback(); storage.delete(filename)
        existing = db.scalar(select(ChatAttachment).where(ChatAttachment.user_id == user.id,
                                                          ChatAttachment.upload_request_id == upload_request_id))
        if existing and existing.checksum == checksum:
            return attachment_state(db, existing)
        raise ChatRecordError(409, 'request_id_conflict', '같은 업로드 ID로 다른 사진을 보낼 수 없어요.')
    except Exception:
        db.rollback(); storage.delete(filename)
        logger.exception('chat photo upload failed')
        raise ChatRecordError(503, 'upload_failed', '사진을 저장하지 못했어요. 다시 시도해 주세요.')
    logger.info('chat photo uploaded')
    return attachment_state(db, attachment)


def analysis_text(draft, foods):
    names = ', '.join(foods[i.food_id].canonical_name for i in draft.items)
    total = sum(i.nutrition['cal'] for i in draft.items)
    return (f'{to_(names)} 분석됐어요(합계 약 {fmt(total)} kcal) · {meal_label(draft)}. 얼마나 드셨는지 말씀해 주세요. '
            '다 드셨으면 "올려줘"라고 하시면 바로 기록해요.')


def ask_amount(db, conversation, draft, reply_to, prefix=''):
    foods = food_rows(db)
    draft.pending_question = 'amount'
    return bot(db, conversation, prefix + analysis_text(draft, foods), reply_to, kind='analysis',
               draft=draft_json(db, draft), chips=ANALYSIS_CHIPS, meal_chips=True)


def analyze_attachment(db, user, attachment_id):
    attachment = db.get(ChatAttachment, attachment_id)
    if not attachment or attachment.user_id != user.id:
        raise not_found()
    conversation = get_conversation(db, user, attachment.conversation_id, lock=True)
    draft = db.scalar(select(MealDraft).where(MealDraft.attachment_id == attachment.id).with_for_update())
    # 분석 결과는 DB에 남기고 새로고침마다 재분석하지 않는다.
    if not draft or draft.status != 'analyzing':
        return attachment_state(db, attachment)
    require_storage()
    try:
        with storage.local_file(attachment.storage_key) as path:
            result = detect_image(path)
    except Exception:
        logger.exception('chat photo analysis failed')
        result = None
    foods = food_rows(db)
    if result:
        for position, item in enumerate(result['detections']):
            if item['class_id'] not in foods:
                continue
            record = Detection(user_id=user.id, image_path=attachment.storage_key, image_group_id=attachment.image_upload_id,
                               predicted_label=item['predicted_label'], confidence=item['confidence'],
                               bbox=item['bbox'], model_version=result['model_version'])
            db.add(record); db.flush()
            draft.items.append(DraftItem(position=position, source_detection_id=record.id, food_id=item['class_id'],
                                         serving_multiplier=1.0, consumption_ratio=1.0,
                                         nutrition=calculate_nutrition(item['class_id'], 1.0)['nutrition'],
                                         confidence=item['confidence'], bbox=item['bbox']))
        db.flush()
    attachment.status = 'analyzed' if result else 'failed'
    attachment.analysis_error = None if result else 'analysis_failed'
    draft.status = 'needs_confirmation'
    draft.version = draft.version + 1
    if not draft.items:
        # 분석 실패·인식 0건: 사진은 보존하고 음식 이름을 묻는다.
        draft.analysis_failed = not result
        draft.pending_question = 'food_name'
        bot(db, conversation, FAILED_TEXT, attachment.message_id, kind='status', draft=draft_json(db, draft))
    elif len(draft.items) == 1 and (draft.items[0].confidence or 0) < LOW_CONFIDENCE:
        draft.pending_question = 'food_check'
        name = foods[draft.items[0].food_id].canonical_name
        bot(db, conversation, f'{to_(name)} 보여요. 음식이 맞나요? 다른 음식이면 이름을 말씀해 주세요.',
            attachment.message_id, kind='analysis', draft=draft_json(db, draft), chips=[{'label': '맞아', 'text': '맞아'}])
    else:
        ask_amount(db, conversation, draft, attachment.message_id)
    db.commit()
    logger.info('chat photo analyzed')
    return attachment_state(db, attachment)


# ---- 메시지 처리 ----

def recalc(item):
    item.nutrition = dict(calculate_nutrition(item.food_id, item.serving_multiplier * item.consumption_ratio)['nutrition'])


def apply_meal_info(draft, meal_info):
    today = korean_date(datetime.now(timezone.utc))
    draft.meal_date = today - timedelta(days=1) if meal_info['date'] == 'yesterday' else today
    if meal_info['meal_type']:
        draft.meal_type = meal_info['meal_type']


def summary(draft, foods):
    parts = [f'{foods[i.food_id].canonical_name} {amount_word(i.consumption_ratio)}' for i in draft.items]
    total = sum(i.nutrition['cal'] for i in draft.items)
    return f'{meal_label(draft)}, {", ".join(parts)}(약 {fmt(total)} kcal)'


def ask_save(db, conversation, draft, reply_to, prefix=''):
    draft.pending_question = 'save_confirm'
    foods = food_rows(db)
    return bot(db, conversation, f'{prefix}{summary(draft, foods)}으로 기록할까요?', reply_to, kind='confirm',
               draft=draft_json(db, draft), chips=YES_NO, meal_chips=True)


# 초안을 식사로 확정한다. 커밋하지 않는다(호출 측 트랜잭션). 음식 수정은 기존 POST /meals와 같이 탐지 기록에만 남긴다.
def confirm_draft(db, user, conversation, draft, request_id, reply_to):
    if not draft.items:
        draft.pending_question = 'food_name'
        return bot(db, conversation, '기록할 음식이 없어요. 음식 이름을 말씀해 주세요.', reply_to)
    foods = food_rows(db)
    meal = Meal(user_id=user.id, meal_date=draft.meal_date, meal_type=draft.meal_type,
                chat_attachment_id=draft.attachment_id)
    db.add(meal); db.flush()
    for item in draft.items:
        food = foods.get(item.food_id)
        if not food:
            raise ChatRecordError(422, '422', '음식 데이터를 확인해 주세요.')
        detection = None
        if item.source_detection_id:
            detection = db.get(Detection, item.source_detection_id, with_for_update=True)
            if not detection or detection.user_id != user.id:
                raise not_found()
            if db.scalar(select(MealItem).where(MealItem.detection_log_id == detection.id)):
                raise ChatRecordError(409, 'invalid_state', '이미 저장한 탐지 결과입니다.')
            # apply_correction은 내부에서 commit하지 않는다(K17) → 같은 트랜잭션에서 호출한다.
            if food.canonical_name != detection.predicted_label:
                apply_correction(db, detection, food.canonical_name, user)
        nutrition = calculate_nutrition(food.id, 1.0 * item.consumption_ratio)['nutrition']
        meal.items.append(MealItem(food_id=food.id, detection_log_id=detection.id if detection else None,
                                   predicted_label=detection.predicted_label if detection else None,
                                   corrected_label=food.canonical_name, confidence=detection.confidence if detection else None,
                                   serving_multiplier=1.0, consumption_ratio=item.consumption_ratio, nutrition=nutrition))
    db.flush()
    rewards.meal_hook(db, user, meal)  # 리워드 보상 훅(SAVEPOINT 격리)
    draft.status = 'confirmed'; draft.confirmed_meal_id = meal.id; draft.pending_question = 'none'
    draft.version = draft.version + 1
    conversation.pending_question = 'none'; conversation.pending_payload = None
    db.add(MutationRequest(user_id=user.id, operation='draft.confirm', request_id=request_id, target_type='meal_draft',
                           target_id=draft.id, payload_hash=hashlib.sha256(draft.id.encode()).hexdigest(),
                           status='succeeded', result_id=meal.id, result_version=1))
    items = [{'food_name': i.corrected_label, 'consumption_ratio': i.consumption_ratio, 'cal': i.nutrition['cal']}
             for i in meal.items]
    snapshot = {'meal_id': meal.id, 'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type,
                'meal_label': meal_label(draft), 'items': items, 'image_url': draft_json(db, draft)['image_url'],
                'totals': {k: round(sum(i.nutrition[k] for i in meal.items), 2) for k in NUTRIENTS}}
    return bot(db, conversation, '식사 기록이 저장되었어요!', reply_to, kind='saved', meal=snapshot, chips=NAV_CHIPS)


def clarify_reply(db, conversation, draft, result, reply_to):
    reason = result['clarification_reason']
    if reason == 'ambiguous_target':
        if draft:
            draft.pending_question = 'target'
        chips = [{'label': c['food_name'], 'text': topic(c['food_name'])} for c in result['candidates']]
        return bot(db, conversation, '어떤 음식의 양을 바꿀까요?', reply_to, chips=chips)
    if reason == 'serving_unit':
        if draft:
            draft.pending_question = 'amount'
        return bot(db, conversation, '지금은 한 번에 1인분 기준으로만 기록할 수 있어요. 드신 비율로 말씀해 주세요.',
                   reply_to, chips=AMOUNT_CHIPS)
    if reason == 'unknown_food':
        return bot(db, conversation, f'"{result["unknown_text"]}"은(는) 목록에 없어요. 정확한 음식 이름으로 말씀해 주세요.', reply_to)
    if reason == 'unknown_meal_type':
        return bot(db, conversation, '식사 종류는 아침·점심·저녁·간식 중에서 골라 주세요.', reply_to, meal_chips=True)
    if reason in ('missing_target', 'empty_meal') and draft and not draft.items:
        draft.pending_question = 'food_name'
        return bot(db, conversation, '음식 이름을 말씀해 주세요.', reply_to)
    if draft and draft.pending_question not in ('food_name',):
        draft.pending_question = 'amount'
    return bot(db, conversation, '"절반", "4분의 1"처럼 말씀해 주시겠어요?', reply_to, chips=AMOUNT_CHIPS)


def handle_draft(db, user, conversation, draft, message, request_id):
    foods = food_rows(db)
    targets = [{'id': i.id, 'food_name': foods[i.food_id].canonical_name} for i in draft.items]
    result = interpret_chat(message.text, draft.pending_question, targets, draft.pending_target_id,
                            [(f.id, f.canonical_name) for f in foods.values()])
    intent = result['intent']
    reply_to = message.id
    by_id = {i.id: i for i in draft.items}
    if intent != 'clarify':
        draft.version = draft.version + 1
    if intent == 'cancel':
        draft.pending_question = 'none'; draft.pending_target_id = None
        return bot(db, conversation, '기록을 멈췄어요. 사진은 남겨 둘게요. 새 사진을 보내거나 양을 다시 말씀해 주세요.', reply_to)
    if intent == 'affirm':
        if draft.pending_question == 'food_check':
            return ask_amount(db, conversation, draft, reply_to)
        if draft.pending_question == 'amount':
            return bot(db, conversation, '다 드셨으면 "다 먹었어 올려줘"라고 말씀해 주세요. 일부만 드셨으면 "절반만 먹었어"처럼 말씀해 주세요.',
                       reply_to, chips=ANALYSIS_CHIPS)
        if draft.pending_question == 'food_name' or not draft.items:
            return bot(db, conversation, '음식 이름을 말씀해 주세요.', reply_to)
        return ask_amount(db, conversation, draft, reply_to)
    if intent == 'confirm_save':
        return confirm_draft(db, user, conversation, draft, request_id, reply_to)
    if intent == 'set_meal_info':
        apply_meal_info(draft, result['meal_info'])
        if result['save']:
            return confirm_draft(db, user, conversation, draft, request_id, reply_to)
        return ask_save(db, conversation, draft, reply_to, prefix=f'{meal_label(draft)}으로 바꿨어요. ')
    if intent in ('change_food', 'add_food'):
        food = result['food']
        if intent == 'add_food':
            draft.items.append(DraftItem(position=len(draft.items), food_id=food['id'], serving_multiplier=1.0,
                                         consumption_ratio=1.0, nutrition=calculate_nutrition(food['id'], 1.0)['nutrition']))
            db.flush()
            return ask_amount(db, conversation, draft, reply_to, prefix=f'{object_(food["name"])} 추가했어요. ')
        item = by_id[result['target_id']]
        # 탐지 ID(source_detection_id)는 유지하고 최종 음식만 바꾼다(R12). 탐지 원본은 확정 전까지 바꾸지 않는다.
        item.food_id = food['id']; recalc(item)
        db.flush()
        return ask_amount(db, conversation, draft, reply_to, prefix=f'{to_(food["name"])} 바꿨어요. ')
    if intent == 'select_target':
        draft.pending_target_id = result['target_id']; draft.pending_question = 'amount'
        name = foods[by_id[result['target_id']].food_id].canonical_name
        return bot(db, conversation, f'{object_(name)} 얼마나 드셨어요?', reply_to, chips=AMOUNT_CHIPS)
    if intent == 'update_consumption':
        for update in result['updates']:
            item = by_id[update['target_id']]
            item.consumption_ratio = update['consumption_ratio']; recalc(item)
        draft.pending_target_id = None
        if result['meal_info']:
            apply_meal_info(draft, result['meal_info'])
        db.flush()
        if result['save']:
            return confirm_draft(db, user, conversation, draft, request_id, reply_to)
        return ask_save(db, conversation, draft, reply_to)
    return clarify_reply(db, conversation, draft, result, reply_to)


def last_saved_meal(db, conversation):
    draft = db.scalar(select(MealDraft).where(MealDraft.conversation_id == conversation.id, MealDraft.status == 'confirmed')
                      .order_by(MealDraft.updated_at.desc()))
    return db.get(Meal, draft.confirmed_meal_id) if draft and draft.confirmed_meal_id else None


# 저장된 식사의 섭취량 정정(5.1과 같은 방식). A0 미리보기·수정 서비스를 재사용한다.
def handle_saved(db, user, conversation, message):
    meal = last_saved_meal(db, conversation)
    reply_to = message.id
    if not meal:
        return bot(db, conversation, NO_DRAFT_TEXT, reply_to)
    targets = [{'id': i.id, 'food_name': i.corrected_label} for i in meal.items]
    foods = [(f.id, f.canonical_name) for f in food_rows(db).values()]
    result = interpret_chat(message.text, conversation.pending_question, targets, None, foods)
    intent = result['intent']
    if intent in ('set_meal_info', 'change_food', 'add_food') or (intent == 'update_consumption' and result['meal_info']):
        return bot(db, conversation, '저장된 식사의 날짜·식사 종류·음식은 아직 여기서 바꿀 수 없어요. 드신 양만 바꿀 수 있어요.', reply_to)
    if intent == 'cancel':
        conversation.pending_question = 'none'; conversation.pending_payload = None
        return bot(db, conversation, '수정을 멈췄어요. 기록은 그대로예요.', reply_to)
    if intent == 'confirm_save' and conversation.pending_payload:
        return apply_saved_updates(db, user, conversation, conversation.pending_payload['updates'], message)
    if intent in ('confirm_save', 'affirm'):
        return bot(db, conversation, '바꾸실 양을 먼저 말씀해 주세요. 예: "아니, 4분의 1"', reply_to, chips=AMOUNT_CHIPS)
    if intent == 'update_consumption':
        updates, cards = [], []
        for update in result['updates']:
            preview = preview_item(db, user, update['target_id'], update['consumption_ratio'])
            updates.append({'item_id': preview['item_id'], 'consumption_ratio': update['consumption_ratio'],
                            'version': preview['version']})
            cards.append({'food_name': preview['food_name'], 'before': preview['before'], 'after': preview['after'],
                          'unit': preview['unit'], 'matches': preview['stored_matches_calculation']})
        if result['save']:
            return apply_saved_updates(db, user, conversation, updates, message)
        conversation.pending_question = 'save_confirm'; conversation.pending_payload = {'updates': updates}
        warn = '' if all(c['matches'] for c in cards) else '저장된 값이 현재 계산과 달라요. 저장하면 현재 기준으로 다시 계산돼요. '
        return bot(db, conversation, f'{warn}저장된 기록을 이렇게 바꿀까요?', reply_to, kind='correction', cards=cards, chips=YES_NO)
    return clarify_reply(db, conversation, None, result, reply_to)


def apply_saved_updates(db, user, conversation, updates, message):
    from ..schemas_chat import ConsumptionUpdateRequest
    results = []
    # 메시지 client_message_id에서 항목별 request_id를 유도한다. 같은 메시지 재시도는 같은 결과를 돌려준다.
    for update in updates:
        request_id = uuid.uuid5(uuid.UUID(message.client_message_id), update['item_id'])
        body = ConsumptionUpdateRequest(consumption_ratio=update['consumption_ratio'],
                                        expected_version=update['version'], request_id=request_id)
        results.append(update_item_consumption(db, user, update['item_id'], body))
    conversation = db.get(Conversation, conversation.id)
    conversation.pending_question = 'none'; conversation.pending_payload = None
    cards = [{'food_name': next(i.corrected_label for i in db.get(Meal, db.get(MealItem, r['item_id']).meal_id).items
                                if i.id == r['item_id']), 'before': r['before'], 'after': r['after']} for r in results]
    return bot(db, conversation, '저장된 기록을 바꿨어요.', message.id, kind='corrected', cards=cards, chips=NAV_CHIPS)


def post_message(db, user, conversation_id, client_message_id, text):
    conversation = get_conversation(db, user, conversation_id, lock=True)
    client_message_id = str(client_message_id)
    message = db.scalar(select(ChatMessage).where(ChatMessage.user_id == user.id,
        ChatMessage.conversation_id == conversation.id, ChatMessage.client_message_id == client_message_id))
    if message:
        if message.text != text:
            raise ChatRecordError(409, 'request_id_conflict', '같은 메시지 ID로 다른 내용을 보낼 수 없어요.')
        if message.status == 'processed':
            replies = db.scalars(select(ChatMessage).where(ChatMessage.reply_to_id == message.id)
                                 .order_by(ChatMessage.sequence)).all()
            return {'messages': [message_json(message)] + [message_json(m) for m in replies],
                    'draft': draft_json(db, active_draft(db, conversation)), 'replayed': True}
    else:
        # 수신한 사용자 메시지를 먼저 커밋한다. 이후 처리가 실패해도 원문은 남고 상태만 failed가 된다.
        message = add_message(db, conversation, 'user', 'text', text, client_message_id=client_message_id, status='received')
        db.commit()
        conversation = get_conversation(db, user, conversation.id, lock=True)
    try:
        draft = active_draft(db, conversation, lock=True)
        if draft and draft.status == 'analyzing':
            reply = bot(db, conversation, '사진 속 음식을 확인하고 있어요. 잠시만 기다려 주세요.', message.id)
        elif draft:
            reply = handle_draft(db, user, conversation, draft, message, client_message_id)
        else:
            reply = handle_saved(db, user, conversation, message)
        message = db.get(ChatMessage, message.id)
        message.status = 'processed'
        db.commit()
    except ChatRecordError as error:
        db.rollback()
        if error.status != 409:
            mark_failed(db, user, message.id)
            raise
        conversation = get_conversation(db, user, conversation.id, lock=True)
        message = db.get(ChatMessage, message.id)
        message.status = 'processed'
        reply = bot(db, conversation, '기록이 변경됐어요. 최신 내용을 확인해 주세요.', message.id)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception('chat message failed')
        mark_failed(db, user, message.id)
        raise ChatRecordError(503, 'save_failed', '아직 저장되지 않았어요. 다시 시도해 주세요.')
    replies = db.scalars(select(ChatMessage).where(ChatMessage.reply_to_id == message.id).order_by(ChatMessage.sequence)).all()
    return {'messages': [message_json(message)] + [message_json(m) for m in replies],
            'draft': draft_json(db, active_draft(db, get_conversation(db, user, conversation.id))), 'replayed': False}


def mark_failed(db, user, message_id):
    message = db.get(ChatMessage, message_id)
    if message:
        message.status = 'failed'
        db.commit()
