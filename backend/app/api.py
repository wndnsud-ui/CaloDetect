# 회원 식단·사진 탐지·영양 분석·추천과 관리자 QA 라우트.
# CurrentUser/Admin 의존성이 인증·역할을 검사하며, 개별 조회와 저장에서도 소유자와 중복 기록을 확인한다.
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

# 라우터를 main.py에 등록하면 아래 경로가 앱에 연결된다. DB/회원/관리자 타입 별칭은 FastAPI Depends를 포함한다.
router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_user)]
Admin = Annotated[User, Depends(get_admin)]
logger = logging.getLogger('calodetect')


# 로컬 사진 분석 테스트가 활성화된 경우 개발 환경/loopback 접속인지 검사한다.
def require_image_environment(request):
    if settings.local_test_image_analysis and (not local_development_environment() or not local_test_request(request)):
        raise HTTPException(503, '사진 분석 테스트는 로컬 개발 환경에서만 사용할 수 있습니다.')


# 회원의 ID·이메일·역할·연령·모델 개선 동의 상태를 공개 응답 형태로 만든다.
def user_json(user):
    return {'id': user.id, 'email': user.email, 'role': user.role, 'age': user.age,
            'model_improvement_consent': user.model_improvement_consent}


# 현재 회원의 모델 개선 동의 여부와 최근 변경 시점을 반환한다.
# HTTP GET /users/me/consent: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/users/me/consent')
def get_consent(user: CurrentUser):
    return {'model_improvement_consent': user.model_improvement_consent,
            'changed_at': user.model_improvement_consent_at}


# 승인된 문구가 있을 때 선택 동의를 저장하며 철회 시 해당 회원의 PENDING 후보를 제외한다.
# HTTP PUT /users/me/consent: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.put('/users/me/consent')
def put_consent(body: ConsentRequest, user: CurrentUser, db: DB):
    # 현재 선택 동의 상태를 확인해 모델 개선 후보의 등록/검수 가능 여부를 제한한다.
    if body.model_improvement_consent and not settings.model_improvement_consent_text:
        raise HTTPException(503, '모델 개선 활용 동의 문구 확정이 필요합니다.')
    user.model_improvement_consent = body.model_improvement_consent
    user.model_improvement_consent_at = utcnow()
    # 현재 선택 동의 상태를 확인해 모델 개선 후보의 등록/검수 가능 여부를 제한한다.
    if not body.model_improvement_consent:
        samples = db.scalars(select(RetrainingSample).join(Detection,
            RetrainingSample.detection_log_id == Detection.id).where(
            Detection.user_id == user.id, RetrainingSample.qa_status == 'PENDING')).all()
        for sample in samples:
            sample.excluded = True
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit(); logger.info('consent change')
    return get_consent(user)


# 업로드 크기·이미지 형식·화소 수를 확인하고 회전을 보정해 UUID JPEG로 저장한 뒤 YOLO를 호출한다.
# 탐지 기록과 업로드 정보를 함께 확정하고 DB/추론 실패 시 rollback과 저장 파일 정리를 수행한다.
# HTTP POST /meals/detect: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/meals/detect')
def detect(file: UploadFile, request: Request, user: CurrentUser, db: DB):
    require_image_environment(request)
    if not settings.image_storage_dir:
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
    folder = Path(settings.image_storage_dir)
    if not folder.is_absolute():
        folder = ROOT / folder
    folder.mkdir(parents=True, exist_ok=True)
    # 서버 UUID를 사진 그룹과 파일명에 함께 사용한다. 같은 사진의 여러 탐지는 같은 group_id를 공유한다.
    group_id = str(uuid4()); filename = group_id + '.jpg'; path = folder / filename
    image.save(path, format='JPEG', quality=90)
    try:
        result = detect_image(path)
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
        db.rollback(); path.unlink(missing_ok=True)
        raise HTTPException(503, '사진 분석에 실패했습니다. 직접 음식을 선택하거나 다시 시도해 주세요.')
    return {'image_group_id': group_id, 'image_url': f'/api/meals/images/{group_id}',
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
    folder = Path(settings.image_storage_dir or '')
    if not folder.is_absolute():
        folder = ROOT / folder
    path = folder / image.image_path
    if not path.is_file():
        raise HTTPException(404, '이미지를 찾을 수 없습니다.')
    return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'private, no-store'})


# 회원·음식·탐지·추천의 소유권과 중복 사용을 검사하고 서버 계산 영양값으로 식단을 저장한다.
# 탐지 행 잠금과 DB 제약으로 중복 기록을 방지하며 식단·보정·추천 선택 상태를 같은 트랜잭션에 반영한다.
# HTTP POST /meals: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/meals', status_code=201)
def save_meal(body: MealRequest, user: CurrentUser, db: DB):
    meal = Meal(user_id=user.id, meal_date=body.meal_date or korean_date(datetime.now(timezone.utc)),
                meal_type=body.meal_type)
                  # commit 전 SQL을 반영해 생성 ID·제약 오류를 확인한다. 아직 변경을 최종 확정한 것은 아니다.
    db.add(meal); db.flush()
    # 한 요청 안에서 같은 탐지를 반복 사용한 경우 DB 작업을 확정하기 전에 거부한다.
    ids = [i.detection_id for i in body.items if i.detection_id]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, '같은 탐지 결과를 중복 등록할 수 없습니다.')
    recommendation = None
    # 추천에서 저장한 식단은 추천 로그 소유자·미사용 상태·실제 추천 음식 포함 여부를 함께 검사한다.
    if body.recommendation_id:
        recommendation = db.get(RecommendationLog, body.recommendation_id)
        # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
        if not recommendation or recommendation.user_id != user.id:
            raise HTTPException(404, '추천 기록을 찾을 수 없습니다.')
        if recommendation.acted:
            raise HTTPException(409, '이미 기록한 추천입니다.')
        recommended_ids = {item['class_id'] for item in recommendation.recommendation_json}
        if not any(i.class_id in recommended_ids for i in body.items):
            raise HTTPException(422, '추천 메뉴가 식단에 포함되어야 합니다.')
    # 클라이언트 영양 수치는 신뢰하지 않고 기존 Food와 서버 영양 계산으로 항목별 저장 스냅샷을 만든다.
    for item in body.items:
        food = db.get(Food, item.class_id)
        if not food or not food.active:
            raise HTTPException(422, '음식 데이터를 확인해 주세요.')
        detection = None
        if item.detection_id:
            # 탐지 행을 잠가 두 요청이 동시에 같은 탐지로 식단을 저장하는 경쟁을 줄인다.
            detection = db.get(Detection, item.detection_id, with_for_update=True)
            # 인증된 회원과 리소스 소유자를 대조해 다른 회원의 기록 접근을 차단한다.
            if not detection or detection.user_id != user.id:
                raise HTTPException(404, '탐지 결과를 찾을 수 없습니다.')
            if db.scalar(select(MealItem).where(MealItem.detection_log_id == detection.id)):
                raise HTTPException(409, '이미 저장한 탐지 결과입니다.')
            if food.canonical_name != detection.predicted_label:
                apply_correction(db, detection, food.canonical_name, user)
        # CSV 기준량에 요청 배율을 적용한 서버 결과를 저장해 이후 집계에서 같은 수치를 사용한다.
        nutrition = calculate_nutrition(item.class_id, item.serving_multiplier)['nutrition']
        meal.items.append(MealItem(food_id=item.class_id, detection_log_id=detection.id if detection else None,
            predicted_label=detection.predicted_label if detection else None,
            corrected_label=food.canonical_name, confidence=detection.confidence if detection else None,
            serving_multiplier=item.serving_multiplier, nutrition=nutrition))
    if recommendation:
        recommendation.acted = True
        recommendation.selected_item = next(i.class_id for i in body.items if i.class_id in recommended_ids)
    try:
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
    query = select(Meal).where(Meal.user_id == user.id)
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
        result = recommend_meals(db, user, body, settings.recent_meal_window)
        # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
        db.commit(); logger.info('recommendation generated')
        return result
    except ValueError as error:
        raise HTTPException(422, str(error))


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
            # 보정된 음식으로 이미 저장한 식단 항목의 영양값도 재계산하되 기존 섭취량 배율은 유지한다.
            linked.nutrition = calculate_nutrition(food.id, linked.serving_multiplier)['nutrition']
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit(); logger.info('detection correction')
    return {'id': detection.id, 'corrected_label': detection.corrected_label}


# 관리자에게 제외되지 않은 최근 QA 후보 최대 200개를 반환한다.
# HTTP GET /admin/retraining/samples: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.get('/admin/retraining/samples')
def qa_samples(admin: Admin, db: DB):
    rows = db.scalars(select(RetrainingSample).where(RetrainingSample.excluded == False)
                      .order_by(RetrainingSample.created_at.desc()).limit(200)).all()
    return {'items': [{'id': s.id, 'predicted_label': s.predicted_label,
                      'corrected_label': s.corrected_label, 'qa_status': s.qa_status,
                      'detection_log_id': s.detection_log_id} for s in rows]}


# 관리자 권한으로 유효한 QA 후보의 실제 이미지 파일을 조회한다.
# HTTP GET /admin/retraining/samples/{sample_id}/image: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
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


# QA 후보를 잠그고 대기 상태·현재 회원 동의를 다시 확인한 뒤 결정과 검수자 ID를 저장한다.
def review(sample_id, decision, admin, db):
    # 검수 행을 잠가 동시 승인/거절을 조정하고 이미 완료된 결정을 다시 덮어쓰지 않는다.
    sample = db.get(RetrainingSample, sample_id, with_for_update=True)
    if not sample or sample.excluded:
        raise HTTPException(404, '샘플을 찾을 수 없습니다.')
    if sample.qa_status != 'PENDING':
        raise HTTPException(409, '이미 검수된 샘플입니다.')
    owner = db.get(User, db.get(Detection, sample.detection_log_id).user_id)
    # 현재 선택 동의 상태를 확인해 모델 개선 후보의 등록/검수 가능 여부를 제한한다.
    if not owner.model_improvement_consent:
        raise HTTPException(409, '모델 개선 동의가 철회되었습니다.')
    sample.qa_status = decision; sample.approved_by = admin.id
    # 이 트랜잭션의 변경을 DB에 확정한다. 이후 응답/재조회에서 저장된 결과를 사용할 수 있다.
    db.commit(); logger.info('admin QA %s', decision)
    return {'id': sample.id, 'qa_status': decision}


# 공통 검수 처리에 APPROVED 결정을 전달한다. 모델 재학습이나 교체를 실행하지 않는다.
# HTTP POST /admin/retraining/samples/{sample_id}/approve: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/admin/retraining/samples/{sample_id}/approve')
def approve(sample_id: str, admin: Admin, db: DB):
    return review(sample_id, 'APPROVED', admin, db)


# 공통 검수 처리에 REJECTED 결정을 전달해 같은 권한·상태·동의 검사를 적용한다.
# HTTP POST /admin/retraining/samples/{sample_id}/reject: 의존성/요청 모델 검사 후 아래 핸들러가 실행된다.
@router.post('/admin/retraining/samples/{sample_id}/reject')
def reject(sample_id: str, admin: Admin, db: DB):
    return review(sample_id, 'REJECTED', admin, db)
