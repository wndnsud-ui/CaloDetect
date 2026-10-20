"""리워드 Stage C 관리자 API: 교환 신청 목록·보류·쿠폰 발급·실패(지시서 v3 §6-11). get_admin 필요, 플래그 off → 404."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter
from pydantic import Field
from .api import Admin, DB
from .schemas import RequestModel
from .services import reward_exchange as exchange

router = APIRouter(prefix='/admin/rewards/exchanges', tags=['admin-rewards'])
Status = Literal['requested', 'held', 'issued', 'used', 'canceled', 'failed']


class IssueRequest(RequestModel):
    coupon_code: str = Field(min_length=4, max_length=64)
    coupon_expires_at: datetime


@router.get('')
def exchanges(admin: Admin, db: DB, status: Status | None = None):
    return exchange.admin_list(db, status)


@router.post('/{exchange_id}/hold')
def hold(exchange_id: str, admin: Admin, db: DB):
    return exchange.admin_hold(db, exchange_id)


@router.post('/{exchange_id}/issue')
def issue(exchange_id: str, body: IssueRequest, admin: Admin, db: DB):
    return exchange.admin_issue(db, exchange_id, body.coupon_code, body.coupon_expires_at)


@router.post('/{exchange_id}/fail')
def fail(exchange_id: str, admin: Admin, db: DB):
    return exchange.admin_fail(db, exchange_id)
