"""개발용 테스트 페이지 API: 로컬 테스트 계정에 리워드 더미를 버튼 한 번으로 만든다.

main.py가 local_test_account_enabled()(APP_ENV=development, LOCAL_TEST_SIGNUP=true, 프런트 localhost)일 때만 등록한다.
Docker에서는 요청이 프록시를 거쳐 loopback 검사를 할 수 없으므로, 등록 조건 + 로그인 + 테스트 계정 본인만 허용한다.
"""
from typing import Literal
from datetime import timedelta
from fastapi import APIRouter, HTTPException
from pydantic import Field
from .api import CurrentUser, DB
from .schemas import RequestModel
from .services import reward_demo, rewards

router = APIRouter(prefix='/dev/demo', tags=['dev'])
TEST_ACCOUNT_EMAIL = 'test@calodetect.local'


class DemoRequest(RequestModel):
    points: int = Field(default=200, ge=0, le=5000)
    xp: int = Field(default=1200, ge=0, le=10000)
    streak: int = Field(default=5, ge=0, le=60)
    protectors: int = Field(default=1, ge=0, le=10)
    reset: bool = False
    account_days: int | None = Field(default=None, ge=0, le=3650)
    # 리워드몰 v1.3 시연 시나리오(지시서 §10): v13 = 교환 가능 320P·지난 쿠폰 2건, v13_coaching = 760P
    scenario: Literal['default', 'v13', 'v13_coaching'] = 'default'


def test_account_only(user):
    if user.email != TEST_ACCOUNT_EMAIL:
        raise HTTPException(403, f'테스트 페이지는 테스트 계정({TEST_ACCOUNT_EMAIL})으로만 쓸 수 있어요.')


@router.get('/status')
def status(user: CurrentUser):
    return {'enabled': True, 'test_account': user.email == TEST_ACCOUNT_EMAIL, 'account_email': TEST_ACCOUNT_EMAIL}


@router.post('/rewards')
def seed_rewards(body: DemoRequest, user: CurrentUser, db: DB):
    test_account_only(user)
    # 테스트 계정 본인의 가입일만 조정한다. 교환 정책·관리자 발급 절차는 유지한다.
    if body.account_days is not None:
        user.created_at = rewards.now() - timedelta(days=body.account_days)
    if body.scenario != 'default':
        result = reward_demo.seed_v13(db, user, coaching=body.scenario == 'v13_coaching')
        db.commit()
        return result
    if body.reset:
        reward_demo.reset(db, user)
    result = reward_demo.seed(db, user, body.points, body.xp, body.streak, body.protectors)
    db.commit()
    return result


@router.post('/rewards/reset')
def reset_rewards(user: CurrentUser, db: DB):
    test_account_only(user)
    result = reward_demo.reset(db, user)
    db.commit()
    return result
