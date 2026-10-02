from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.timezone import korean_date

client = TestClient(app)


def test_original_foods_and_multiplier():
    foods = client.get('/foods').json()['items']
    assert len(foods) == 150
    result = client.post('/nutrition/calculate', json={'class_id': 0, 'serving_multiplier': 1.5}).json()
    assert result['nutrition']['cal'] == round(foods[0]['cal'] * 1.5, 2)
    assert result['food_name'] == foods[0]['food_name']


@pytest.mark.parametrize('multiplier', [0, -1, 101, 'NaN', 'Infinity'])
def test_bad_portion(multiplier):
    response = client.post('/nutrition/calculate', json={'class_id': 0, 'serving_multiplier': multiplier})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_goal_rules():
    payload = {'height': 175, 'weight': 70, 'age': 30, 'sex': 'male',
               'activity_level': 'moderate', 'goal_type': 'weight_loss'}
    result = client.post('/profiles/calorie-preview', json=payload).json()
    assert result['bmr'] == 1648.75
    assert result['tdee'] == round(1648.75 * 1.55, 2)
    assert result['recommended_calorie_min'] >= result['minimum_calories']
    assert client.post('/profiles/calorie-preview', json={**payload, 'target_calories': 1200}).status_code == 422
    assert client.post('/profiles/calorie-preview', json={**payload, 'target_calories': 5001}).status_code == 422


def test_kst_midnight():
    assert str(korean_date(datetime(2026, 10, 2, 14, 59, tzinfo=timezone.utc))) == '2026-10-02'
    assert str(korean_date(datetime(2026, 10, 2, 15, 1, tzinfo=timezone.utc))) == '2026-10-03'
    with pytest.raises(ValueError):
        korean_date(datetime(2026, 10, 2))


def test_status_is_honest():
    assert client.get('/health').status_code == 200
    assert 'auth' in client.get('/system/status').json()['available']
    assert 'image_retention' in client.get('/system/status').json()['policy_tbd']


def test_multi_food_preview_uses_existing_nutrition():
    result = client.post('/nutrition/preview', json={'items': [
        {'class_id': 0, 'serving_multiplier': 1.5}, {'class_id': 1, 'serving_multiplier': 0.5}]}).json()
    assert len(result['items']) == 2
    for key, total in result['totals'].items():
        assert total == round(sum(item['nutrition'][key] for item in result['items']), 2)
    assert client.post('/nutrition/preview', json={'items': []}).status_code == 422
