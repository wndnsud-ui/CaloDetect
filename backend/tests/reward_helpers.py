"""리워드 테스트 공통 도구: 고정 시계, 사진 탐지 행, 식단 저장, 원장 조회."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models import Detection, Food
from backend.app.models_rewards import RewardPointLot as Lot, RewardXpEvent as Xp
from backend.app.services import rewards as service
from backend.app.services.timezone import korean_date

# KST 2026-10-21(수) 12:00. 날짜 경계 테스트는 이 값에서 일 단위로 옮긴다.
NOON = datetime(2026, 10, 21, 3, 0, tzinfo=timezone.utc)


def clock(monkeypatch, instant):
    monkeypatch.setattr(service, 'now', lambda: instant)
    return korean_date(instant)


def photo(engine, user_id, content=None):
    """저장 폴더에 사진 파일을 두고 그 사진의 탐지 행을 만든다(YOLO 없이)."""
    name = f'{uuid4()}.jpg'
    Path(settings.image_storage_dir, name).write_bytes(content or uuid4().bytes)
    with Session(engine) as db:
        label = db.get(Food, 0).canonical_name
        detection = Detection(user_id=user_id, image_path=name, image_group_id=str(uuid4()), predicted_label=label,
                              confidence=0.9, bbox=[0, 0, 10, 10], model_version='test')
        db.add(detection); db.commit()
        return detection.id


def save(client, meal_type, day, detection=None):
    response = client.post('/meals', json={'meal_type': meal_type, 'meal_date': str(day),
        'items': [{'class_id': 0, 'serving_multiplier': 1, 'detection_id': detection}]})
    assert response.status_code == 201, response.text
    return response.json()


def lots(engine, user_id):
    with Session(engine) as db:
        return {l.idem_key: (l.source, l.amount, l.remaining) for l in db.scalars(select(Lot).where(Lot.user_id == user_id))}


def xps(engine, user_id):
    with Session(engine) as db:
        return {e.idem_key: e.amount for e in db.scalars(select(Xp).where(Xp.user_id == user_id))}


def balance(client):
    return client.get('/rewards/me').json()['balance']


def days(start, n):
    return [start + timedelta(days=i) for i in range(n)]


def pin_signup(engine, user_id, instant=None):
    """가입 시각을 고정 시계 기준으로 맞춘다(예상 일수 창·가입 주 계산용)."""
    from backend.app.models import User
    with Session(engine) as db:
        db.get(User, user_id).created_at = (instant or NOON) - timedelta(hours=1)
        db.commit()
