"""Fallback records use isolated SQLite and local images; no shared DB/LLM writes."""
import io
import pytest
from PIL import Image
from sqlalchemy.orm import Session
from backend.tests.test_p0_flow import env, account
from backend.app.models import NutritionFood


def photo(client, analyze=False):
    buffer = io.BytesIO()
    Image.new('RGB', (20, 20), 'green').save(buffer, 'PNG')
    response = client.post(f'/meals/detect?analyze={str(analyze).lower()}',
                           files={'file': ('photo.png', buffer.getvalue(), 'image/png')})
    assert response.status_code == 200, response.text
    return response.json()


def test_photo_only_then_complete_all_fields(env):
    client, _, monkeypatch = env
    account(client)
    monkeypatch.setattr('backend.app.api.detect_image', lambda *_: pytest.fail('Skipped inference ran'))
    upload = photo(client)
    response = client.post('/meals', json={'meal_type': 'lunch', 'image_upload_id': upload['image_group_id'],
                                         'analysis_status': 'skipped', 'items': []})
    assert response.status_code == 201, response.text
    meal = response.json()
    assert meal['items'] == [] and meal['nutrition_pending']
    assert meal['image_urls'] == [upload['image_url']]
    assert client.get('/analytics/today').status_code == 200
    body = {'expected_version': meal['version'], 'meal_type': 'dinner', 'meal_date': '2026-10-29',
            'meal_time': '18:45', 'items': [{'food_name': '집에서 만든 음식', 'amount': 250, 'amount_unit': 'g',
            'nutrition': {'cal': 450, 'carbs': 50, 'protein': 20, 'fat': 15}}]}
    updated = client.patch(f"/meals/{meal['id']}", json=body)
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data['meal_time'] == '18:45' and data['meal_type'] == 'dinner'
    assert data['items'][0]['source'] == 'manual' and not data['nutrition_pending']
    assert data['image_upload_id'] == upload['image_group_id']
    row = data['items'][0]
    row = {k: row[k] for k in ('id', 'version', 'food_name', 'amount', 'amount_unit', 'nutrition')}
    row['food_name'] = '수정한 음식'
    body = {'expected_version': data['version'], 'items': [row]}
    response = client.patch(f"/meals/{meal['id']}", json=body)
    assert response.status_code == 200, response.text
    assert response.json()['items'][0]['is_edited']
    assert client.patch(f"/meals/{meal['id']}", json=body).status_code == 409


def test_failed_inference_retains_photo_and_allows_manual_record(env):
    client, _, monkeypatch = env
    account(client)
    def fail(*args, **kwargs):
        raise RuntimeError('inference unavailable')
    monkeypatch.setattr('backend.app.api.detect_image', fail)
    upload = photo(client, analyze=True)
    assert upload['analysis_status'] == 'failed' and upload['detections'] == []
    assert client.get(upload['image_url'].replace('/api', '')).status_code == 200
    response = client.post('/meals', json={'meal_type': 'lunch', 'image_upload_id': upload['image_group_id'],
        'analysis_status': 'failed', 'items': [{'food_name': '알 수 없는 음식', 'amount': 1}]})
    assert response.status_code == 201, response.text
    assert response.json()['items'][0]['nutrition']['cal'] is None
    assert response.json()['nutrition_pending']
    assert client.get('/analytics/today').json()['totals']['cal'] == 0


def test_search_and_serving_scaling(env):
    client, engine, _ = env
    account(client)
    # Explicit synthetic fixture; never claimed to be official MFDS nutrition.
    with Session(engine) as db:
        db.add(NutritionFood(id='fixture', name='순대국 테스트', serving_amount=500,
            nutrition={'cal': 400, 'carbs': 20, 'protein': 30, 'fat': 20, 'sodium': None, 'sugar': None},
            source='TEST FIXTURE ONLY'))
        db.commit()
    found = client.get('/foods/search?q=순대국').json()['items']
    assert found[0]['reference_food_id'] == 'fixture'
    response = client.post('/meals', json={'meal_type': 'lunch', 'items': [
        {'reference_food_id': 'fixture', 'amount': 250, 'amount_unit': 'g'}]})
    assert response.status_code == 201, response.text
    row = response.json()['items'][0]
    assert row['nutrition']['cal'] == 200 and row['nutrition']['protein'] == 15
    assert row['source'] == 'search'
    assert row['reference_serving_amount'] == 500
    for amount, expected in ((0.5, 200), (1.5, 600)):
        preview = client.post('/foods/portion', json={'reference_food_id': 'fixture',
            'amount': amount, 'amount_unit': 'serving'})
        assert preview.status_code == 200, preview.text
        assert preview.json()['nutrition']['cal'] == expected
    assert client.get('/foods/search?q=%25').json()['items'] == []


def test_foreign_photo_and_meal_cannot_be_used(env):
    client, _, _ = env
    account(client)
    upload = photo(client)
    meal = client.post('/meals', json={'meal_type': 'lunch', 'items': [{'food_name': '수동 음식'}]}).json()
    account(client, 'other@example.com')
    assert client.post('/meals', json={'meal_type': 'lunch', 'image_upload_id': upload['image_group_id']}).status_code == 404
    assert client.patch(f"/meals/{meal['id']}", json={'expected_version': 1, 'meal_time': '12:30'}).status_code == 404


@pytest.mark.parametrize('nutrition', [{'cal': -1}, {'cal': 'NaN'}, {'protein': 'Infinity'}, {'cal': 100001}])
def test_invalid_nutrition_rejected(env, nutrition):
    client, _, _ = env
    account(client)
    assert client.post('/meals', json={'meal_type': 'lunch', 'items': [
        {'food_name': '검증 음식', 'nutrition': nutrition}]}).status_code == 422


def test_llm_estimation_endpoint_removed(env):
    client, _, _ = env
    account(client)
    assert client.post('/foods/estimate', json={'food_name': 'test', 'amount': 1,
        'amount_unit': 'serving', 'external_ai_consent': True}).status_code == 404


def test_meal_patch_cors_preflight_allowed(env):
    from backend.app.config import settings
    client, _, _ = env
    response = client.options('/meals/example', headers={'Origin':settings.frontend_origin,
        'Access-Control-Request-Method':'PATCH','Access-Control-Request-Headers':'content-type,x-csrf-token'})
    assert response.status_code == 200
    assert 'PATCH' in response.headers['access-control-allow-methods']


@pytest.mark.parametrize('ratio',[0,0.5,1])
def test_history_lunch_to_dinner_only_changes_meal_metadata(env,ratio):
    from backend.app.models import Meal
    client,engine,_=env
    account(client)
    response=client.post('/meals',json={'meal_type':'lunch','items':[
        {'class_id':0,'serving_multiplier':1},{'food_name':'직접 입력 음식','nutrition':{'cal':100}}]})
    assert response.status_code==201,response.text
    saved=response.json()
    with Session(engine) as db:
        meal=db.get(Meal,saved['id'])
        for item in meal.items:
            item.consumption_ratio=ratio
        db.commit()
    before=next(m for m in client.get('/meals/history').json()['items'] if m['id']==saved['id'])
    changed=client.patch(f"/meals/{saved['id']}",json={'meal_type':'dinner','expected_version':before['version']})
    assert changed.status_code==200,changed.text
    after=changed.json()
    assert after['meal_type']=='dinner' and after['version']==before['version']+1
    assert after['items']==before['items']
    assert after['meal_date']==before['meal_date'] and after['image_urls']==before['image_urls']
    assert next(m for m in client.get('/meals/history').json()['items'] if m['id']==saved['id'])['meal_type']=='dinner'


def test_photo_replacement_and_removal(env):
    client, _, _ = env
    account(client)
    first, second = photo(client), photo(client)
    saved = client.post('/meals', json={'meal_type': 'lunch', 'image_upload_id': first['image_group_id'],
        'items': [{'food_name': '사진 교체 테스트'}]}).json()
    updated = client.patch(f"/meals/{saved['id']}", json={'expected_version': saved['version'],
        'image_upload_id': second['image_group_id']}).json()
    assert updated['image_urls'] == [second['image_url']]
    updated = client.patch(f"/meals/{saved['id']}", json={'expected_version': updated['version'],
        'image_upload_id': None}).json()
    assert updated['image_urls'] == []
    # References removed; originals remain private under the existing retention policy.
    assert client.get(first['image_url'].replace('/api', '')).status_code == 200


def test_ml_food_rejects_unsupported_gram_conversion(env):
    client, engine, _ = env
    account(client)
    with Session(engine) as db:
        db.add(NutritionFood(id='liquid', name='ml 기준 음식', serving_amount=100, serving_unit='ml',
            nutrition={'cal': 100, 'carbs': 10, 'protein': 5, 'fat': 2}, source='TEST FIXTURE'))
        db.commit()
    body = {'reference_food_id': 'liquid', 'amount': 200, 'amount_unit': 'ml'}
    assert client.post('/foods/portion', json=body).json()['nutrition']['cal'] == 200
    assert client.post('/foods/portion', json={**body, 'amount_unit': 'g'}).status_code == 422


def test_import_preserves_units_missing_values_and_scales_serving():
    from backend.scripts.import_nutrition_foods import normalize
    row = {'식품코드': 'test', '식품명': '순대국', '영양성분함량기준량': '100ml',
           '식품중량': '500ml', '에너지(kcal)': '50', '탄수화물(g)': '4',
           '단백질(g)': '3', '지방(g)': '2', '나트륨(mg)': ''}
    normalized = normalize(row)
    assert normalized['serving_amount'] == 500 and normalized['serving_unit'] == 'ml'
    assert normalized['nutrition']['cal'] == 250 and normalized['nutrition']['sodium'] is None


def test_edit_add_delete_and_detect_provenance(env):
    client, _, monkeypatch = env
    account(client)
    catalog = client.get('/foods').json()['items']
    monkeypatch.setattr('backend.app.api.detect_image', lambda path: {'model_version': 'fixture',
        'detections': [{'class_id': 0, 'predicted_label': catalog[0]['food_name'],
                        'confidence': 0.2, 'bbox': [0, 0, 10, 10], 'candidates': [
                            {'class_id': 0, 'predicted_label': catalog[0]['food_name'], 'confidence': .2},
                            {'class_id': 1, 'predicted_label': catalog[1]['food_name'], 'confidence': .1},
                            {'class_id': 2, 'predicted_label': catalog[2]['food_name'], 'confidence': .05}]}]})
    scanned = photo(client, analyze=True)
    assert len(scanned['detections'][0]['candidates']) == 3
    meal = client.post('/meals', json={'meal_type': 'lunch', 'items': [
        {'class_id': 1, 'detection_id': scanned['detection_ids'][0], 'serving_multiplier': 2}]}).json()
    item = meal['items'][0]
    assert item['source'] == 'ai' and item['is_edited'] and item['ai_confidence'] == .2
    assert item['amount'] == 2
    changed = client.patch(f"/meals/{meal['id']}", json={'expected_version': meal['version'],
        'items': [{'food_name': '새 수동 항목'}]})
    assert changed.status_code == 200, changed.text
    assert len(changed.json()['items']) == 1 and changed.json()['items'][0]['source'] == 'manual'
