# 채팅 식사기록·섭취량 수정(A0) 요청 모델. 기존 RequestModel(extra 금지, NaN/inf 금지)을 상속한다.
# 일반 float는 "0.5"·true를 숫자로 바꾸므로(K09 확인) 비율은 strict 숫자만, version은 strict 정수만 받는다.
from typing import Annotated, Literal, Union
from uuid import UUID
from pydantic import Field, StrictFloat, StrictInt
from .schemas import RequestModel

# 0~1 섭취 비율. JSON 정수 0·1과 실수만 허용하고 bool·문자열·null·NaN은 거부한다.
Ratio = Annotated[Union[StrictFloat, StrictInt], Field(ge=0, le=1)]


class InterpretRequest(RequestModel):
    text: str = Field(min_length=1, max_length=200)
    item_id: str | None = Field(default=None, max_length=36)
    meal_id: str | None = Field(default=None, max_length=36)
    # A0 입력창은 보관한 미리보기가 있으면 save_confirm을 보낸다(단순 긍정 해석 기준).
    pending_question: Literal['none', 'amount', 'save_confirm'] = 'none'


class ConsumptionPreviewRequest(RequestModel):
    consumption_ratio: Ratio


class ConsumptionUpdateRequest(RequestModel):
    consumption_ratio: Ratio
    expected_version: StrictInt = Field(ge=1)
    request_id: UUID
