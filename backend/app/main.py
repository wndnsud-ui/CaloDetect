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
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI(title='CaloDetect API', version='0.1.0')
app.include_router(accounts_router)
app.include_router(meal_router)
app.include_router(social_router)
app.include_router(passwords_router)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                   allow_credentials=True, allow_methods=['GET', 'POST', 'PUT'],
                   allow_headers=['Content-Type', 'X-CSRF-Token', 'Authorization'])


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return JSONResponse(status_code=503, content={'error': {'code': 'DATABASE_UNAVAILABLE',
                        'message': '데이터베이스 실행 상태와 마이그레이션을 확인하세요.'}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {
        'code': 'VALIDATION_ERROR', 'message': '입력값을 확인하세요.',
        'fields': [{'location': list(e['loc']), 'message': e['msg']} for e in error.errors()]}})


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    return JSONResponse(status_code=error.status_code,
                        content={'error': {'code': str(error.status_code), 'message': str(error.detail)}})


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'CaloDetect', 'stage': 'p0-integration'}


@app.get('/system/status')
def system_status():
    return {'stage': 'p0-integration', 'nutrition_source': 'CaloDetect_nutrition_all_matched.csv',
            'food_count': len(food_catalog()), 'timezone': 'Asia/Seoul',
            'available': ['food_catalog', 'nutrition_calculation', 'calorie_calculation', 'auth', 'profile_persistence',
                          'meal_persistence', 'detection_api', 'recommendation', 'correction', 'admin_qa'],
            'pending': ['signup_policy', 'image_storage_policy', 'recommendation_policy'],
            'policy_tbd': ['service_consent_text', 'model_improvement_consent_text', 'image_storage', 'image_retention',
                           'recommendation_source', 'macro_targets', 'sugar_sodium_limits']}


@app.get('/health/database')
def database_health():
    try:
        check_database()
    except Exception:
        # Do not expose connection credentials or exception text.
        raise HTTPException(503, 'PostgreSQL 연결 설정 또는 실행 상태를 확인하세요.')
    return {'status': 'ok'}


@app.get('/foods')
def foods():
    return {'items': food_catalog()}


@app.post('/nutrition/calculate')
def nutrition(body: NutritionRequest):
    try:
        return calculate_nutrition(body.class_id, body.serving_multiplier)
    except ValueError as error:
        raise HTTPException(422, str(error))


@app.post('/profiles/calorie-preview')
def calorie_preview(body: CalorieRequest):
    # Calculation preview only; no registration policy or persisted profile.
    try:
        return calculate_calorie_range(body)
    except ValueError as error:
        raise HTTPException(422, str(error))


class NutritionPreview(RequestModel):
    items: list[NutritionRequest] = Field(min_length=1, max_length=100)


@app.post('/nutrition/preview')
def nutrition_preview(body: NutritionPreview):
    items = [calculate_nutrition(item.class_id, item.serving_multiplier) for item in body.items]
    keys = items[0]['nutrition'].keys()
    return {'items': items, 'totals': {key: round(sum(item['nutrition'][key] for item in items), 2)
                                       for key in keys}}
