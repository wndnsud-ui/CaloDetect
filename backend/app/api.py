# 회원 식단·사진 탐지·영양 분석·추천 라우트. 2026-10-20 모델 개선(재학습)·관리자 QA 폐기.
# CurrentUser/Admin 의존성이 인증·역할을 검사하며, 개별 조회와 저장에서도 소유자와 중복 기록을 확인한다.
import io
import logging
import secrets
from datetime import date, datetime, timezone
from uuid import uuid4
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, Query
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import User, AuthSession, Profile, Food, Meal, MealItem, Detection, ImageUpload, RecommendationLog, utcnow
from .schemas import SignupRequest, LoginRequest, CalorieRequest, MealRequest, CorrectionRequest, RecommendationRequest, RecommendationPlacesRequest
from .security import password_hash, password_matches, new_session, get_user, get_admin, hash_token
from .services.profile import calculate_calorie_range
from .services.nutrition import food_catalog, calculate_nutrition
from .services.analytics import get_today_status, get_month_status, meal_json
from .services.timezone import korean_date
from .services.correction import apply_correction
from .services.recommendation import recommend_meals
from .services import places
from .services.vision import detect_image, mobile_request
from .accounts import local_development_environment, local_test_request
from .services import rewards
from . import storage

# 라우터를 main.py에 등록하면 아래 경로가 앱에 연결된다. DB/회원/관리자 타입 별칭은 FastAPI Depends를 포함한다.
router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_user)]
Admin = Annotated[User, Depends(get_admin)]
logger = logging.getLogger('calodetect')


@router.get('/foods/search')
def search_foods(user: CurrentUser, db: DB, q: str = Query(min_length=1, max_length=120)):
    from .models import NutritionFood
    needle = q.strip()
    if not needle:
        return {'items': []}
    legacy = db.scalars(select(Food).where(Food.active.is_(True),
        Food.display_name.contains(needle, autoescape=True)).order_by(Food.display_name).limit(30)).all()
    external = db.scalars(select(NutritionFood).where(NutritionFood.name.contains(needle, autoescape=True))
        .order_by(NutritionFood.name, NutritionFood.id).limit(30)).all()
    return {'items': [dict(class_id=f.id, food_name=f.display_name, unit=f.serving_unit,
        nutrition=f.nutrition, nutrition_source=f.nutrition_source, serving_grams=None) for f in legacy] +
        [dict(reference_food_id=f.id, food_name=f.name, unit='기준 제공량',
        nutrition=f.nutrition, nutrition_source=f.source, serving_amount=f.serving_amount,
        serving_unit=f.serving_unit, serving_grams=f.serving_amount if f.serving_unit == 'g' else None) for f in external]}


@router.post('/foods/portion')
def preview_food_portion(body: dict, user: CurrentUser, db: DB):
    from .schemas import MealItemRequest
    from .services.meal_fallback import fill_item
    from pydantic import ValidationError
    try:
        item = MealItemRequest.model_validate(body)
    except ValidationError:
        raise HTTPException(422, '음식과 양을 확인해 주세요.')
    if (item.class_id is None and not item.reference_food_id) or item.detection_id or item.nutrition is not None:
        raise HTTPException(422, '검색에서 선택한 음식과 양만 보내 주세요.')
    record = fill_item(db, user, item)
    return {'nutrition': record.nutrition}


@router.patch('/meals/{meal_id}')
def edit_meal(meal_id: str, body: dict, user: CurrentUser, db: DB):
    from .services.meal_fallback import owned_photo, fill_item, photo_ids, unused_photos
    from .schemas import MealItemRequest
    from pydantic import ValidationError
    meal = db.get(Meal, meal_id, with_for_update=True)
    if not meal or meal.user_id != user.id or meal.deleted_at is not None:
        raise HTTPException(404, '식단을 찾을 수 없습니다.')
    shown = photo_ids(meal_json(meal)) if 'image_upload_id' in body else set()
    if body.get('expected_version') != meal.version:
        raise HTTPException(409, '다른 곳에서 수정한 기록입니다. 다시 열어 주세요.')
    if 'meal_date' in body and body['meal_date'] is None:
        raise HTTPException(422, '식사 날짜를 입력해 주세요.')
    # Validate the complete merged record so PATCH omissions retain previous values.
    merged = {key: getattr(meal, key) for key in
              ('meal_type', 'meal_date', 'meal_time', 'analysis_status', 'image_upload_id')}
    merged['items'] = [dict(id=i.id, class_id=i.food_id, reference_food_id=i.reference_food_id,
        food_name=i.corrected_label, serving_multiplier=i.serving_multiplier, amount=i.amount,
        amount_unit=i.amount_unit, nutrition=i.nutrition, detection_id=i.detection_log_id,
        is_llm_estimated=i.is_llm_estimated) for i in meal.items]
    merged.update(body)
    try:
        validated = MealRequest.model_validate(merged)
    except ValidationError:
        raise HTTPException(422, '식단 입력값을 확인해 주세요.')
    if validated.recommendation_id is not None:
        raise HTTPException(422, '수정 중 추천을 다시 채택할 수 없습니다.')
    owned_photo(db, user, validated.image_upload_id)
    if 'items' in body:
        existing = {i.id: i for i in meal.items}
        ids = [i.id for i in validated.items if i.id]
        detections = [i.detection_id for i in validated.items if i.detection_id]
        if len(ids) != len(set(ids)) or any(i not in existing for i in ids) or len(detections) != len(set(detections)):
            raise HTTPException(422, '중복되거나 다른 식단의 항목입니다.')
        for entry in validated.items:
            if entry.id:
                current = db.get(MealItem, entry.id, with_for_update=True, populate_existing=True)
                if entry.version != current.version:
                    raise HTTPException(409, '음식 항목이 변경되었습니다. 다시 열어 주세요.')
        meal.items = [fill_item(db, user, entry, existing.get(entry.id)) for entry in validated.items]
    for key in ('meal_type', 'meal_date', 'meal_time', 'analysis_status', 'image_upload_id'):
        if key in body:
            setattr(meal, key, getattr(validated, key))
    if 'image_upload_id' in body:
        meal.photo_override = True
    meal.version += 1
    db.flush()
    result = meal_json(meal)
    keys = []
    if shown and not result['image_urls']:
        # 사진 삭제(2026-11-02 사용자 결정). 사진 교체는 기존처럼 참조만 바꾼다.
        # 다른 기록이 쓰지 않는 사진은 파일까지 지우고, 이 식단을 올린 게시물(사진 사본 포함)을 지워 공유·반응 포인트를,
        # 이 식단의 기록 포인트·XP를 회수한다.
        from .services import community
        keys = unused_photos(db, user.id, shown) + community.remove_meal_post(db, user, meal.id)
        rewards.meal_photo_removed(db, user.id, meal)
    db.commit()
    for key in keys:
        storage.delete(key)
    return result


# 식단 전체 삭제(2026-11-02 사용자 요청). 행은 남기고 deleted_at으로 모든 조회에서 뺀다.
# 다른 기록이 쓰지 않는 사진은 파일까지 지우고, 이 식단을 올린 게시물을 지우며, 받은 포인트·XP를 무조건 회수한다.
@router.delete('/meals/{meal_id}')
def delete_meal(meal_id: str, user: CurrentUser, db: DB, expected_version: int = Query(ge=1)):
    from .services.meal_fallback import photo_ids, unused_photos
    from .services import community
    meal = db.get(Meal, meal_id, with_for_update=True)
    if not meal or meal.user_id != user.id or meal.deleted_at is not None:
        raise HTTPException(404, '식단을 찾을 수 없습니다.')
    if expected_version != meal.version:
        raise HTTPException(409, '다른 곳에서 수정한 기록입니다. 다시 열어 주세요.')
    shown = photo_ids(meal_json(meal))
    meal.deleted_at, meal.version = utcnow(), meal.version + 1
    db.flush()
    keys = unused_photos(db, user.id, shown) + community.remove_meal_post(db, user, meal.id)
    rewards.meal_deleted(db, user.id, meal)
    db.commit()
    for key in keys:
        storage.delete(key)
    logger.info('meal deleted')
    return {'deleted': True, 'id': meal.id}


# 로컬 사진 분석 테스트가 활성화된 경우 개발 환경/loopback 접속인지 검사한다.
def require_image_environment(request):
    if settings.local_test_image_analysis and (not local_development_environment() or not local_test_request(request)):
        raise HTTPException(503, '사진 분석 테스트는 로컬 개발 환경에서만 사용할 수 있습니다.')


# 업로드 크기·이미지 형식·화소 수를 확인하고 회전을 보정해 UUID JPEG로 저장한 뒤 YOLO를 호출한다.
# 탐지 기록과 업로드 정보를 함께 확정하고 DB/추론 실패 시 rollback과 저장 파일 정리를 수행한다.
# HTTP POST /meals/detect: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/meals/detect')
def detect(file: UploadFile, request: Request, user: CurrentUser, db: DB, analyze: bool = True):
    require_image_environment(request)
    if not storage.configured():
        raise HTTPException(503, '업로드 이미지 저장 정책을 설정해 주세요.')
    # 최대 허용량보다 1바이트 더 읽어 큰 파일을 전부 메모리에 올리지 않고 10MB 초과를 감지한다.
    content = file.file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, '이미지는 10MB 이하로 업로드해 주세요.')
    try:
        # 파일 확장자/MIME 대신 실제 이미지 디코딩 결과를 검사해 JPEG/PNG 여부를 판단한다.
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in ('JPEG', 'PNG'):
                raise ValueError('format')
            # 압축 파일은 작아도 디코딩 후 메모리를 많이 사용할 수 있어 전체 화소 수를 제한한다.
            if source.width * source.height > 25_000_000:
                raise ValueError('dimensions')
            # 휴대폰 EXIF 회전을 픽셀에 반영하고 모델 입력/저장에 맞춰 RGB로 통일한다.
            image = ImageOps.exif_transpose(source).convert('RGB')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, '정상 JPG/PNG 이미지를 선택해 주세요. 최대 2500만 화소입니다.')
    # 서버 UUID를 사진 그룹과 파일명(저장소 키)에 함께 사용한다. 같은 사진의 여러 탐지는 같은 group_id를 공유한다.
    group_id = str(uuid4()); filename = group_id + '.jpg'
    buffer = io.BytesIO(); image.save(buffer, format='JPEG', quality=90); data = buffer.getvalue()
    try:
        storage.put(filename, data)
    except OSError:
        logger.warning('meal photo storage failed')
        raise HTTPException(503, '사진을 저장하지 못했습니다. 다시 시도해 주세요.')
    try:
        result = {'detections': [], 'model_version': 'skipped'}
        analysis_status = 'skipped'
        if analyze:
            try:
                with storage.local_file(filename, data) as path:
                    result = detect_image(path, mobile=True) if mobile_request(request) else detect_image(path)
                analysis_status = 'analyzed' if result['detections'] else 'failed'
            except Exception:
                logger.warning('Inference unavailable; photo retained for manual record')
                analysis_status = 'failed'
        db.add(ImageUpload(id=group_id, user_id=user.id, image_path=filename))
        detections = []
        # 모델이 반환한 각 음식 박스를 별도 탐지 행으로 저장해 나중에 개별 음식 수정/식단 연결이 가능하게 한다.
        for item in result['detections']:
            record = Detection(user_id=user.id, image_path=filename, image_group_id=group_id,
                predicted_label=item['predicted_label'], confidence=item['confidence'],
                bbox=item['bbox'], model_version=result['model_version'])
                            # commit 전 SQL을 반영해 생성 ID·제약 오류를 확인한다. 아직 변경을 최종 확정한 것은 아니다.
            db.add(record); db.flush()
            detections.append({'id': record.id, **item})
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit(); logger.info('YOLO inference complete')
    except Exception:
        # 실패한 트랜잭션을 되돌려 부분 변경이 확정되지 않도록 한다.
        logger.exception('Meal photo inference or detection persistence failed')
        db.rollback(); storage.delete(filename)
        raise HTTPException(503, '사진 분석에 실패했습니다. 직접 음식을 선택하거나 다시 시도해 주세요.')
    return {'analysis_status': analysis_status, 'low_confidence_threshold': settings.meal_low_confidence_threshold, 'image_group_id': group_id, 'image_url': f'/api/meals/images/{group_id}',
            'detections': detections, 'detection_ids': [d['id'] for d in detections],
            'manual_selection_available': True}


# 업로드 이미지의 소유자와 실제 파일 존재를 확인한 뒤 private/no-store 응답으로 전달한다.
# HTTP GET /meals/images/{image_id}: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/meals/images/{image_id}')
def meal_image(image_id: str, request: Request, user: CurrentUser, db: DB):
    require_image_environment(request)
    image = db.get(ImageUpload, image_id)
    # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
    if not image or image.user_id != user.id:
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    data = storage.get(image.image_path) if storage.configured() else None
    if data is None:
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    return Response(data, media_type='image/jpeg', headers={'Cache-Control': 'private, no-store'})


# 회원·음식·탐지·추천의 소유권과 중복 사용을 검사하고 서버 계산 영양값으로 식단을 저장한다.
# 탐지 행 잠금과 DB 제약으로 중복 기록을 방지하며 식단·보정·추천 선택 상태를 같은 트랜잭션에 반영한다.
# HTTP POST /meals: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/meals', status_code=201)
def save_meal(body: MealRequest, user: CurrentUser, db: DB):
    meal = Meal(user_id=user.id, meal_date=body.meal_date or korean_date(datetime.now(timezone.utc)),
                meal_type=body.meal_type, image_upload_id=body.image_upload_id, photo_override=bool(body.image_upload_id),
                analysis_status=body.analysis_status, meal_time=body.meal_time)
    from .services.meal_fallback import owned_photo, fill_item
    owned_photo(db, user, body.image_upload_id)
                  # commit 전 SQL을 반영해 생성 ID·제약 오류를 확인한다. 아직 변경을 최종 확정한 것은 아니다.
    db.add(meal); db.flush()
    # 한 요청 안에서 같은 탐지를 반복 사용한 경우 DB 작업을 확정하기 전에 거부한다.
    ids = [i.detection_id for i in body.items if i.detection_id]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, '같은 탐지 결과를 중복 등록할 수 없습니다.')
    recommendation = None
    # 추천에서 저장한 식단은 추천 로그 소유자·미사용 상태·실제 추천 음식 포함 여부를 함께 검사한다.
    # 10월 15일 박근수 수정: 빈 문자열도 직접 기록으로 우회하지 못하게 추천 ID를 조회·검증한다.
    if body.recommendation_id is not None:
        # DB row 잠금으로 동시에 제출된 저장 요청이 같은 추천을 중복 채택하지 못하게 한다.
        recommendation = db.get(
            RecommendationLog,
            body.recommendation_id,
            with_for_update=True,
        )
        # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
        if not recommendation or recommendation.user_id != user.id:
            raise HTTPException(404, '추천 기록을 찾을 수 없습니다.')
        if recommendation.acted:
            raise HTTPException(409, '이미 기록한 추천입니다.')
        recommended_ids = {item['class_id'] for item in recommendation.recommendation_json if item.get('class_id') is not None}
        if not any(i.class_id in recommended_ids for i in body.items):
            raise HTTPException(422, '추천 메뉴가 식단에 포함되어야 합니다.')
    # 클라이언트 영양 수치는 신뢰하지 않고 기존 Food와 서버 영양 계산으로 항목별 저장 스냅샷을 만든다.
    for entry in body.items:
        if entry.id:
            raise HTTPException(422, 'Existing item ID is not allowed for a new meal.')
        meal.items.append(fill_item(db, user, entry))
    if recommendation:
        # 10월 15일 박근수 수정: 저장한 추천 음식의 실제 class_id를 선택 로그에 남긴다.
        recommendation.acted = True
        recommendation.selected_item = next(i.class_id for i in body.items if i.class_id in recommended_ids)
    try:
        rewards.meal_hook(db, user, meal)  # 리워드 보상 훅(SAVEPOINT 격리, 응답 불변)
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit()
    except IntegrityError:
        # 실패한 트랜잭션을 되돌려 부분 변경이 확정되지 않도록 한다.
        db.rollback(); raise HTTPException(409, '중복 기록을 확인해 주세요.')
    logger.info('meal save')
    return meal_json(meal)


# 한국 시간 기준 오늘의 회원 식단 목록을 공통 분석 서비스에서 가져온다.
# HTTP GET /meals/today: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/meals/today')
def today_meals(user: CurrentUser, db: DB):
    return {'items': get_today_status(db, user.id)['meals']}


# 현재 회원의 기록을 시작/종료 날짜로 필터링하고 최신 날짜·생성 시각 순으로 제한 개수만 반환한다.
# HTTP GET /meals/history: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/meals/history')
def history(user: CurrentUser, db: DB, start: date | None = None, end: date | None = None,
            limit: int = Query(default=100, ge=1, le=500)):
    query = select(Meal).where(Meal.user_id == user.id, Meal.deleted_at.is_(None))
    if start:
        query = query.where(Meal.meal_date >= start)
    if end:
        query = query.where(Meal.meal_date <= end)
    meals = db.scalars(query.order_by(Meal.meal_date.desc(), Meal.created_at.desc()).limit(limit)).all()
    return {'items': [meal_json(m) for m in meals]}


# 현재 회원의 오늘 영양 합계·목표·남은 칼로리·식단을 반환한다.
# HTTP GET /analytics/today: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/analytics/today')
def analytics(user: CurrentUser, db: DB):
    return get_today_status(db, user.id)


# 검증된 연도/월로 현재 회원의 월 전체 기록과 기록일 평균을 반환한다.
# HTTP GET /analytics/month: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/analytics/month')
def month_analytics(user: CurrentUser, db: DB, year: int = Query(ge=1, le=9999),
                    month: int = Query(ge=1, le=12)):
    return get_month_status(db, user.id, year, month)


# 추천 활성화와 최근 식사 범위 설정을 확인하고 후보 생성·기록을 확정한다.
# HTTP POST /recommendations/meals: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/recommendations/meals')
def recommendations(body: RecommendationRequest, user: CurrentUser, db: DB):
    if not settings.recommendation_enabled or not settings.recent_meal_window:
        raise HTTPException(503, '추천 출처와 개발 기준을 설정해 주세요.')
    try:
        # 10월 15일 박근수 수정: 입력 스키마에서 검증한 테마 key를 추천 점수 함수까지 전달한다.
        result = recommend_meals(
            db,
            user,
            body,
            settings.recent_meal_window,
            theme=body.theme,
        )
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit(); logger.info('recommendation generated')
        return result
    except ValueError as error:
        raise HTTPException(422, str(error))



# 추천 카드에서 고른 메뉴를 파는 음식점(카카오 로컬). 지역명 또는 좌표는 검색에만 쓰고 저장·로그하지 않는다.
# HTTP POST /recommendations/places: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/recommendations/places')
def recommendation_places(body: RecommendationPlacesRequest, user: CurrentUser):
    if not places.available():
        raise HTTPException(503, '음식점 검색이 설정되지 않았습니다.')
    try:
        return {'places': places.search(body.query, area=body.area, lat=body.lat, lng=body.lng)}
    except places.PlacesUnavailable:
        raise HTTPException(502, '음식점 검색에 실패했습니다. 잠시 후 다시 시도해 주세요.')

# 소유한 탐지의 음식명을 수정하고 연결된 식단이 있으면 기존 섭취량으로 영양값도 다시 계산한다.
# HTTP POST /detections/{detection_id}/correction: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/detections/{detection_id}/correction')
def correction(detection_id: str, body: CorrectionRequest, user: CurrentUser, db: DB):
    detection = db.get(Detection, detection_id, with_for_update=True)
    # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
    if not detection or detection.user_id != user.id:
        raise HTTPException(404, '탐지 결과를 찾을 수 없습니다.')
    food = db.get(Food, body.class_id)
    if not food:
        raise HTTPException(422, '음식을 찾을 수 없습니다.')
    if food.canonical_name != (detection.corrected_label or detection.predicted_label):
        apply_correction(db, detection, food.canonical_name, user)
        linked = db.scalar(select(MealItem).where(MealItem.detection_log_id == detection.id))
        if linked:
            linked.food_id = food.id; linked.corrected_label = food.canonical_name
            linked.is_edited = True
            # 보정된 음식으로 이미 저장한 식단 항목의 영양값도 재계산하되 기존 섭취량 배율은 유지한다.
            # 2026-10-15 사용자 승인(챗봇 지시서 R3): 섭취 비율까지 반영한 유효 배율로 계산하고 version을 올린다.
            # 비율 1.0인 기존 행은 이전과 같은 값이다.
            linked.nutrition = calculate_nutrition(
                food.id, linked.serving_multiplier * linked.consumption_ratio)['nutrition']
            linked.version = linked.version + 1
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit(); logger.info('detection correction')
    return {'id': detection.id, 'corrected_label': detection.corrected_label}
