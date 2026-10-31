from .services.vision import mobile_request
# 채팅 식사기록(A1) 라우트. main.py가 CHAT_RECORD_ENABLED=true일 때만 등록한다.
# 식사 확정은 별도 공개 경로가 없고 메시지 처리 안에서 서버가 수행한다(지시서 11장).
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.orm import Session
from .api import require_image_environment
from .db import get_db
from .models import User
from .schemas import RequestModel
from .security import get_user
from .services.consumption_record import ChatRecordError
from .services import chat_record

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_user)]


class ChatMessageRequest(RequestModel):
    conversation_id: str = Field(min_length=1, max_length=36)
    client_message_id: UUID
    text: str = Field(min_length=1, max_length=200)
    # 답장 칩을 눌러 보낸 문장. 서버가 직전 칩 문장과 같은지 확인한 뒤에만 LLM·횟수에서 뺀다.
    chip: bool = False


def failure(error: ChatRecordError):
    return JSONResponse(status_code=error.status, content={'error': {'code': error.code, 'message': error.message}})


# 기능 사용 가능 여부. 플래그가 꺼지면 라우트 자체가 없어 404가 되고 프론트는 메뉴를 숨긴다. 쓰기 없음.
@router.get('/chat/status')
def status(user: CurrentUser, db: DB):
    return {'enabled': True, 'meal_types': chat_record.chips_for_meal_types(), **chat_record.llm_state(db, user)}


# 외부 AI(LLM) 전송 고지 동의(업무지시서 v1.2). 처음 한 번만 받고 시각을 계정에 남긴다. 재요청은 같은 결과.
@router.post('/chat/consent')
def consent(user: CurrentUser, db: DB):
    return chat_record.save_consent(db, user)


# 진행 중 대화를 복원하거나 새로 만든다. 프론트는 이 경로의 404로 기능 꺼짐을 판단한다.
@router.get('/chat/conversation')
def conversation(user: CurrentUser, db: DB, before: int | None = Query(default=None, ge=1),
                 limit: int = Query(default=50, ge=1, le=100)):
    try:
        return chat_record.conversation_state(db, user, before, limit)
    except ChatRecordError as error:
        return failure(error)


# 사진 업로드: 파일 저장·첨부·사진 메시지를 커밋한다. 분석은 별도 요청으로 이어서 한다.
@router.post('/chat/attachments')
def upload(request: Request, user: CurrentUser, db: DB, file: UploadFile, conversation_id: str = Form(max_length=36),
           upload_request_id: UUID = Form()):
    require_image_environment(request)
    try:
        content = file.file.read(10 * 1024 * 1024 + 1)
        return chat_record.upload_photo(db, user, conversation_id, str(upload_request_id), content)
    except ChatRecordError as error:
        return failure(error)


# 업로드한 사진을 기존 YOLO 분석(detect_image)으로 분석해 초안을 만든다. 이미 분석했으면 결과만 돌려준다.
@router.post('/chat/attachments/{attachment_id}/analysis')
def analyze(attachment_id: str, request: Request, user: CurrentUser, db: DB):
    require_image_environment(request)
    try:
        return chat_record.analyze_attachment(db, user, attachment_id, mobile=mobile_request(request))
    except ChatRecordError as error:
        return failure(error)


# 사용자 메시지(직접 입력·답장 칩)를 저장하고 해석해 초안 갱신·확정·정정을 처리한다.
@router.post('/chat/messages')
def message(body: ChatMessageRequest, user: CurrentUser, db: DB):
    try:
        return chat_record.post_message(db, user, body.conversation_id, body.client_message_id, body.text, body.chip)
    except ChatRecordError as error:
        return failure(error)
