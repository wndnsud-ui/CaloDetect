# 회귀 테스트: foundation 관련 기능의 성공·오류·권한 조건을 검사한다.
# fixture/monkeypatch로 테스트 의존성을 준비하며 실제 외부 인증·메일 발송 검증과는 구분한다.
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.timezone import korean_date

client = TestClient(app)


# 회귀 검사: 원본 · 음식 · 배율.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_original_foods_and_multiplier():
    foods = client.get('/foods').json()['items']
    assert len(foods) == 150
    result = client.post('/nutrition/calculate', json={'class_id': 0, 'serving_multiplier': 1.5}).json()
    assert result['nutrition']['cal'] == round(foods[0]['cal'] * 1.5, 2)
    assert result['food_name'] == foods[0]['food_name']


# 회귀 검사: 섭취량.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
@pytest.mark.parametrize('multiplier', [0, -1, 101, 'NaN', 'Infinity'])
def test_bad_portion(multiplier):
    response = client.post('/nutrition/calculate', json={'class_id': 0, 'serving_multiplier': multiplier})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


# 회귀 검사: 목표 · 규칙.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_goal_rules():
    payload = {'height': 175, 'weight': 70, 'age': 30, 'sex': 'male',
               'activity_level': 'moderate', 'goal_type': 'weight_loss'}
    result = client.post('/profiles/calorie-preview', json=payload).json()
    assert result['bmr'] == 1648.75
    assert result['tdee'] == round(1648.75 * 1.55, 2)
    assert result['recommended_calorie_min'] >= result['minimum_calories']
    assert client.post('/profiles/calorie-preview', json={**payload, 'target_calories': 1200}).status_code == 422
    assert client.post('/profiles/calorie-preview', json={**payload, 'target_calories': 5001}).status_code == 422


# 회귀 검사: 한국 시간 · 자정.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_kst_midnight():
    assert str(korean_date(datetime(2026, 10, 2, 14, 59, tzinfo=timezone.utc))) == '2026-10-02'
    assert str(korean_date(datetime(2026, 10, 2, 15, 1, tzinfo=timezone.utc))) == '2026-10-03'
    with pytest.raises(ValueError):
        korean_date(datetime(2026, 10, 2))


# 회귀 검사: 상태 · 실제 상태.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_status_is_honest():
    assert client.get('/health').status_code == 200
    assert 'auth' in client.get('/system/status').json()['available']
    assert 'image_retention' in client.get('/system/status').json()['policy_tbd']


# 회귀 검사: 여러 · 음식 · 미리보기 · 기존 · 영양.
# 아래 요청·준비 데이터와 assert로 성공 결과 및 실패 시 제한이 유지되는지 확인한다.
def test_multi_food_preview_uses_existing_nutrition():
    result = client.post('/nutrition/preview', json={'items': [
        {'class_id': 0, 'serving_multiplier': 1.5}, {'class_id': 1, 'serving_multiplier': 0.5}]}).json()
    assert len(result['items']) == 2
    for key, total in result['totals'].items():
        assert total == round(sum(item['nutrition'][key] for item in result['items']), 2)
    assert client.post('/nutrition/preview', json={'items': []}).status_code == 422
