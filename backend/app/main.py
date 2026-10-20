# FastAPI 앱 진입점. 기능별 라우터, CORS와 공통 오류 응답을 등록한다.
# 비회원 음식 조회·계산 미리보기와 상태 점검을 제공하며 DB 연결 오류에서 접속 정보는 반환하지 않는다.
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import check_database
from .schemas import NutritionRequest, CalorieRequest
from .services.nutrition import food_catalog, calculate_nutrition
from .services.profile import calculate_calorie_range
from .schemas import RequestModel
from pydantic import Field
from .accounts import router as accounts_router
from .api import router as meal_router
from .social_auth import router as social_router
from .passwords import router as passwords_router
from .kakao_auth import router as kakao_router
from .community import router as community_router
from .rewards import router as rewards_router
from sqlalchemy.exc import SQLAlchemyError

# 앱 객체를 Uvicorn이 backend.app.main:app으로 불러온다. 라우터 등록 순서를 그대로 유지한다.
app = FastAPI(title='CaloDetect API', version='0.1.0')
app.include_router(accounts_router)
app.include_router(meal_router)
app.include_router(social_router)
app.include_router(passwords_router)
app.include_router(kakao_router)
app.include_router(community_router)
app.include_router(rewards_router)
from .admin_rewards import router as admin_rewards_router
from .services.reward_exchange import startup_check as reward_exchange_startup_check
app.include_router(admin_rewards_router)
reward_exchange_startup_check()
# 개발용 테스트 페이지(리워드 더미). 로컬 개발·테스트 가입 설정일 때만 경로가 생긴다.
from backend.scripts.seed_local_test_account import local_test_account_enabled
if local_test_account_enabled():
    from .dev_demo import router as dev_demo_router
    app.include_router(dev_demo_router)
# 채팅 식사기록(섭취량 수정) 라우트는 기능 플래그가 켜졌을 때만 등록한다. 기본 false.
if settings.chat_record_enabled:
    from .consumption_api import router as consumption_router
    from .chat_api import router as chat_router
    app.include_router(consumption_router)
    app.include_router(chat_router)
# 쿠키 인증을 허용하되 CORS 원본은 설정된 프런트엔드로 제한한다. 실제 변경 권한은 인증/CSRF가 검사한다.
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                   allow_credentials=True, allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
                   allow_headers=['Content-Type', 'X-CSRF-Token', 'Authorization'])


# DB 예외를 자격정보가 없는 공통 503 응답으로 변환한다.
@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return JSONResponse(status_code=503, content={'error': {'code': 'DATABASE_UNAVAILABLE',
                        'message': '데이터베이스 실행 상태와 마이그레이션을 확인하세요.'}})


# Pydantic 요청 오류를 필드 위치와 메시지가 포함된 422 공통 응답으로 변환한다.
@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {
        'code': 'VALIDATION_ERROR', 'message': '입력값을 확인하세요.',
        'fields': [{'location': list(e['loc']), 'message': e['msg']} for e in error.errors()]}})


# 명시적으로 발생한 HTTPException의 상태 코드와 안내 문구를 공통 error 구조로 반환한다.
@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    return JSONResponse(status_code=error.status_code,
                        content={'error': {'code': str(error.status_code), 'message': str(error.detail)}})


# 앱 프로세스의 기본 상태를 반환한다. DB 상태는 별도 health/database에서 확인한다.
# HTTP GET /health: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'CaloDetect', 'stage': 'p0-integration'}


# 구현된 기능·데이터 출처·한국 시간 기준과 아직 확정되지 않은 정책을 구분해 반환한다.
# HTTP GET /system/status: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@app.get('/system/status')
def system_status():
    return _with_exchange({'stage': 'p0-integration', 'nutrition_source': 'CaloDetect_nutrition_all_matched.csv',
            'food_count': len(food_catalog()), 'timezone': 'Asia/Seoul',
            'available': ['food_catalog', 'nutrition_calculation', 'calorie_calculation', 'auth', 'profile_persistence',
                          'meal_persistence', 'detection_api', 'recommendation', 'correction', 'community_feed', 'community_points',
                          'reward_points', 'reward_items', 'reward_nickname', 'reward_growth', 'reward_ranking'],
            'pending': ['signup_policy', 'image_storage_policy', 'recommendation_policy'],
            'policy_tbd': ['service_consent_text', 'image_storage', 'image_retention',
                           'recommendation_source', 'macro_targets', 'sugar_sodium_limits', 'community_photo_consent_text',
                           'community_point_values', 'community_point_usage', 'community_multi_account_abuse', 'community_photo_copy_retention',
                           'reward_point_values', 'reward_missions', 'reward_goal_calorie_floor', 'reward_nickname_blocklist',
                           'reward_character_sheet', 'reward_character_name', 'reward_photo_capture_time',
                           'reward_exchange_partner', 'reward_exchange_global_cap', 'reward_abuse_detection']})


# 리워드 Stage C: REWARD_EXCHANGE_ENABLED와 월 전체 상한이 모두 설정됐을 때만 available에 reward_exchange를 넣는다.
def _with_exchange(status):
    if settings.reward_exchange_active:
        status['available'].append('reward_exchange')
    return status


# 실제 DB 연결을 검사하고 실패 시 내부 예외 대신 일반 연결 안내를 반환한다.
# HTTP GET /health/database: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@app.get('/health/database')
def database_health():
    try:
        check_database()
    except Exception:
        # Do not expose connection credentials or exception text.
        raise HTTPException(503, 'PostgreSQL 연결 설정 또는 실행 상태를 확인하세요.')
    return {'status': 'ok'}


# 검증된 기존 CSV의 음식 카탈로그를 반환한다.
# HTTP GET /foods: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@app.get('/foods')
def foods():
    return {'items': food_catalog()}


# 검증된 음식 클래스와 섭취량 배율로 서버 영양 계산을 수행한다.
# HTTP POST /nutrition/calculate: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@app.post('/nutrition/calculate')
def nutrition(body: NutritionRequest):
    try:
        return calculate_nutrition(body.class_id, body.serving_multiplier)
    except ValueError as error:
        raise HTTPException(422, str(error))


# 회원가입/DB 저장 없이 입력된 신체 정보의 목표 칼로리 범위를 계산한다.
# HTTP POST /profiles/calorie-preview: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@app.post('/profiles/calorie-preview')
def calorie_preview(body: CalorieRequest):
    # Calculation preview only; no registration policy or persisted profile.
    try:
        return calculate_calorie_range(body)
    except ValueError as error:
        raise HTTPException(422, str(error))


# NutritionPreview: RequestModel를 확장한 입력 모델. Field의 길이·수치 범위와 validator가 API 진입 전에 적용된다.
class NutritionPreview(RequestModel):
    items: list[NutritionRequest] = Field(min_length=1, max_length=100)


# 음식별 영양을 각각 계산하고 같은 영양 항목을 합산해 식단 미리보기를 반환한다.
# HTTP POST /nutrition/preview: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@app.post('/nutrition/preview')
def nutrition_preview(body: NutritionPreview):
    # 각 항목을 같은 영양 계산 서비스로 계산하므로 미리보기와 식단 저장의 수치 기준이 일치한다.
    items = [calculate_nutrition(item.class_id, item.serving_multiplier) for item in body.items]
    keys = items[0]['nutrition'].keys()
    return {'items': items, 'totals': {key: round(sum(item['nutrition'][key] for item in items), 2)
                                       for key in keys}}
