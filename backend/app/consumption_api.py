# 확정 식사 섭취량 수정(A0) 라우트. main.py가 CHAT_RECORD_ENABLED=true일 때만 등록한다.
# 인증·CSRF는 기존 get_user 의존성을 재사용하고, 오류는 기존과 같은 {'error': {code, message}} 구조로 반환한다.
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .db import get_db
from .models import User
from .security import get_user
from .schemas_chat import InterpretRequest, ConsumptionPreviewRequest, ConsumptionUpdateRequest
from .services.consumption_record import (ChatRecordError, interpret_for_meal, preview_item,
                                          update_item_consumption)

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_user)]


def failure(error: ChatRecordError):
    return JSONResponse(status_code=error.status, content={'error': {'code': error.code, 'message': error.message}})


# 대화 문장을 비율·확정·취소 의도로 해석한다. 확정 식사 쓰기 없음.
@router.post('/meals/consumption/interpret')
def interpret_consumption(body: InterpretRequest, user: CurrentUser, db: DB):
    try:
        return interpret_for_meal(db, user, body)
    except ChatRecordError as error:
        return failure(error)


# 새 비율의 수정 전·후 영양값을 계산한다. 확정 식사 불변.
@router.post('/meals/items/{item_id}/consumption/preview')
def preview_consumption(item_id: str, body: ConsumptionPreviewRequest, user: CurrentUser, db: DB):
    try:
        return preview_item(db, user, item_id, body.consumption_ratio)
    except ChatRecordError as error:
        return failure(error)


# 섭취 비율을 저장한다. expected_version·request_id로 동시성·멱등성을 보장한다.
@router.put('/meals/items/{item_id}/consumption')
def update_consumption(item_id: str, body: ConsumptionUpdateRequest, user: CurrentUser, db: DB):
    try:
        return update_item_consumption(db, user, item_id, body)
    except ChatRecordError as error:
        return failure(error)
