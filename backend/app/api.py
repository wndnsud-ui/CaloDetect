import io
import logging
import secrets
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings, ROOT
from .db import get_db
from .models import User, AuthSession, Profile, Food, Meal, MealItem, Detection, ImageUpload, RetrainingSample, RecommendationLog, utcnow
from .schemas import SignupRequest, LoginRequest, ConsentRequest, CalorieRequest, MealRequest, CorrectionRequest, RecommendationRequest
from .security import password_hash, password_matches, new_session, get_user, get_admin, hash_token
from .services.profile import calculate_calorie_range
from .services.nutrition import food_catalog, calculate_nutrition
from .services.analytics import get_today_status, get_month_status, meal_json
from .services.timezone import korean_date
from .services.correction import apply_correction
from .services.recommendation import recommend_meals
from .services.vision import detect_image
from .accounts import local_development_environment, local_test_request

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_user)]
Admin = Annotated[User, Depends(get_admin)]
logger = logging.getLogger('calodetect')


def require_image_environment(request):
    if settings.local_test_image_analysis and (not local_development_environment() or not local_test_request(request)):
        raise HTTPException(503, '사진 분석 테스트는 로컬 개발 환경에서만 사용할 수 있습니다.')


def user_json(user):
    return {'id': user.id, 'email': user.email, 'role': user.role, 'age': user.age,
            'model_improvement_consent': user.model_improvement_consent}


@router.get('/users/me/consent')
def get_consent(user: CurrentUser):
    return {'model_improvement_consent': user.model_improvement_consent,
            'changed_at': user.model_improvement_consent_at}


@router.put('/users/me/consent')
def put_consent(body: ConsentRequest, user: CurrentUser, db: DB):
    if body.model_improvement_consent and not settings.model_improvement_consent_text:
        raise HTTPException(503, '모델 개선 활용 동의 문구 확정이 필요합니다.')
    user.model_improvement_consent = body.model_improvement_consent
    user.model_improvement_consent_at = utcnow()
    if not body.model_improvement_consent:
        samples = db.scalars(select(RetrainingSample).join(Detection,
            RetrainingSample.detection_log_id == Detection.id).where(
            Detection.user_id == user.id, RetrainingSample.qa_status == 'PENDING')).all()
        for sample in samples:
            sample.excluded = True
    db.commit(); logger.info('consent change')
    return get_consent(user)


@router.post('/meals/detect')
def detect(file: UploadFile, request: Request, user: CurrentUser, db: DB):
    require_image_environment(request)
    if not settings.image_storage_dir:
        raise HTTPException(503, '업로드 이미지 저장 정책을 설정해 주세요.')
    content = file.file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, '이미지는 10MB 이하로 업로드해 주세요.')
    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in ('JPEG', 'PNG'):
                raise ValueError('format')
            if source.width * source.height > 25_000_000:
                raise ValueError('dimensions')
            image = ImageOps.exif_transpose(source).convert('RGB')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, '정상 JPG/PNG 이미지를 선택해 주세요. 최대 2500만 화소입니다.')
    folder = Path(settings.image_storage_dir)
    if not folder.is_absolute():
        folder = ROOT / folder
    folder.mkdir(parents=True, exist_ok=True)
    group_id = str(uuid4()); filename = group_id + '.jpg'; path = folder / filename
    image.save(path, format='JPEG', quality=90)
    try:
        result = detect_image(path)
        db.add(ImageUpload(id=group_id, user_id=user.id, image_path=filename))
        detections = []
        for item in result['detections']:
            record = Detection(user_id=user.id, image_path=filename, image_group_id=group_id,
                predicted_label=item['predicted_label'], confidence=item['confidence'],
                bbox=item['bbox'], model_version=result['model_version'])
            db.add(record); db.flush()
            detections.append({'id': record.id, **item})
        db.commit(); logger.info('YOLO inference complete')
    except Exception:
        db.rollback(); path.unlink(missing_ok=True)
        raise HTTPException(503, '사진 분석에 실패했습니다. 직접 음식을 선택하거나 다시 시도해 주세요.')
    return {'image_group_id': group_id, 'image_url': f'/api/meals/images/{group_id}',
            'detections': detections, 'detection_ids': [d['id'] for d in detections],
            'manual_selection_available': True}


@router.get('/meals/images/{image_id}')
def meal_image(image_id: str, request: Request, user: CurrentUser, db: DB):
    require_image_environment(request)
    image = db.get(ImageUpload, image_id)
    if not image or image.user_id != user.id:
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    folder = Path(settings.image_storage_dir or '')
    if not folder.is_absolute():
        folder = ROOT / folder
    path = folder / image.image_path
    if not path.is_file():
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'private, no-store'})


@router.post('/meals', status_code=201)
def save_meal(body: MealRequest, user: CurrentUser, db: DB):
    meal = Meal(user_id=user.id, meal_date=body.meal_date or korean_date(datetime.now(timezone.utc)),
                meal_type=body.meal_type)
    db.add(meal); db.flush()
    ids = [i.detection_id for i in body.items if i.detection_id]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, '같은 탐지 결과를 중복 등록할 수 없습니다.')
    recommendation = None
    if body.recommendation_id:
        recommendation = db.get(RecommendationLog, body.recommendation_id)
        if not recommendation or recommendation.user_id != user.id:
            raise HTTPException(404, '추천 기록을 찾을 수 없습니다.')
        if recommendation.acted:
            raise HTTPException(409, '이미 기록한 추천입니다.')
        recommended_ids = {item['class_id'] for item in recommendation.recommendation_json}
        if not any(i.class_id in recommended_ids for i in body.items):
            raise HTTPException(422, '추천 메뉴가 식단에 포함되어야 합니다.')
    for item in body.items:
        food = db.get(Food, item.class_id)
        if not food or not food.active:
            raise HTTPException(422, '음식 데이터를 확인해 주세요.')
        detection = None
        if item.detection_id:
            detection = db.get(Detection, item.detection_id, with_for_update=True)
            if not detection or detection.user_id != user.id:
                raise HTTPException(404, '탐지 결과를 찾을 수 없습니다.')
            if db.scalar(select(MealItem).where(MealItem.detection_log_id == detection.id)):
                raise HTTPException(409, '이미 저장한 탐지 결과입니다.')
            if food.canonical_name != detection.predicted_label:
                apply_correction(db, detection, food.canonical_name, user)
        nutrition = calculate_nutrition(item.class_id, item.serving_multiplier)['nutrition']
        meal.items.append(MealItem(food_id=item.class_id, detection_log_id=detection.id if detection else None,
            predicted_label=detection.predicted_label if detection else None,
            corrected_label=food.canonical_name, confidence=detection.confidence if detection else None,
            serving_multiplier=item.serving_multiplier, nutrition=nutrition))
    if recommendation:
        recommendation.acted = True
        recommendation.selected_item = next(i.class_id for i in body.items if i.class_id in recommended_ids)
    try:
        db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, '중복 기록을 확인해 주세요.')
    logger.info('meal save')
    return meal_json(meal)


@router.get('/meals/today')
def today_meals(user: CurrentUser, db: DB):
    return {'items': get_today_status(db, user.id)['meals']}


@router.get('/meals/history')
def history(user: CurrentUser, db: DB, start: date | None = None, end: date | None = None,
            limit: int = Query(default=100, ge=1, le=500)):
    query = select(Meal).where(Meal.user_id == user.id)
    if start:
        query = query.where(Meal.meal_date >= start)
    if end:
        query = query.where(Meal.meal_date <= end)
    meals = db.scalars(query.order_by(Meal.meal_date.desc(), Meal.created_at.desc()).limit(limit)).all()
    return {'items': [meal_json(m) for m in meals]}


@router.get('/analytics/today')
def analytics(user: CurrentUser, db: DB):
    return get_today_status(db, user.id)


@router.get('/analytics/month')
def month_analytics(user: CurrentUser, db: DB, year: int = Query(ge=1, le=9999),
                    month: int = Query(ge=1, le=12)):
    return get_month_status(db, user.id, year, month)


@router.post('/recommendations/meals')
def recommendations(body: RecommendationRequest, user: CurrentUser, db: DB):
    if not settings.recommendation_enabled or not settings.recent_meal_window:
        raise HTTPException(503, '추천 출처와 개발 기준을 설정해 주세요.')
    try:
        result = recommend_meals(db, user, body, settings.recent_meal_window)
        db.commit(); logger.info('recommendation generated')
        return result
    except ValueError as error:
        raise HTTPException(422, str(error))


@router.post('/detections/{detection_id}/correction')
def correction(detection_id: str, body: CorrectionRequest, user: CurrentUser, db: DB):
    detection = db.get(Detection, detection_id, with_for_update=True)
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
            linked.nutrition = calculate_nutrition(food.id, linked.serving_multiplier)['nutrition']
    db.commit(); logger.info('detection correction')
    return {'id': detection.id, 'corrected_label': detection.corrected_label}


@router.get('/admin/retraining/samples')
def qa_samples(admin: Admin, db: DB):
    rows = db.scalars(select(RetrainingSample).where(RetrainingSample.excluded == False)
                      .order_by(RetrainingSample.created_at.desc()).limit(200)).all()
    return {'items': [{'id': s.id, 'predicted_label': s.predicted_label,
                      'corrected_label': s.corrected_label, 'qa_status': s.qa_status,
                      'detection_log_id': s.detection_log_id} for s in rows]}


@router.get('/admin/retraining/samples/{sample_id}/image')
def qa_image(sample_id: str, admin: Admin, db: DB):
    sample = db.get(RetrainingSample, sample_id)
    if not sample or sample.excluded:
        raise HTTPException(404, '샘플을 찾을 수 없습니다.')
    folder = Path(settings.image_storage_dir or '')
    path = (folder if folder.is_absolute() else ROOT / folder) / sample.image_path
    if not path.is_file():
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'private, no-store'})


def review(sample_id, decision, admin, db):
    sample = db.get(RetrainingSample, sample_id, with_for_update=True)
    if not sample or sample.excluded:
        raise HTTPException(404, '샘플을 찾을 수 없습니다.')
    if sample.qa_status != 'PENDING':
        raise HTTPException(409, '이미 검수된 샘플입니다.')
    owner = db.get(User, db.get(Detection, sample.detection_log_id).user_id)
    if not owner.model_improvement_consent:
        raise HTTPException(409, '모델 개선 동의가 철회되었습니다.')
    sample.qa_status = decision; sample.approved_by = admin.id
    db.commit(); logger.info('admin QA %s', decision)
    return {'id': sample.id, 'qa_status': decision}


@router.post('/admin/retraining/samples/{sample_id}/approve')
def approve(sample_id: str, admin: Admin, db: DB):
    return review(sample_id, 'APPROVED', admin, db)


@router.post('/admin/retraining/samples/{sample_id}/reject')
def reject(sample_id: str, admin: Admin, db: DB):
    return review(sample_id, 'REJECTED', admin, db)
