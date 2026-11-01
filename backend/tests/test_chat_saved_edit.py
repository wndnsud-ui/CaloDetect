"""Saved-meal details: confirmation, ownership, versions and replay; isolated DB."""
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.tests.test_chat_record import env, start, photo, say, meals, last_bot, NAMES, GALBI
from backend.tests.test_consumption import account
from backend.app.models import Meal
from backend.app.models_chat import MutationRequest
from backend.app.services.nutrition import calculate_nutrition


def saved_photo(client, engine):
    conversation = start(client)
    photo(client, conversation)
    say(client, conversation, '절반만 먹었어 올려줘')
    return conversation, meals(engine)[0]


def test_change_meal_type_requires_confirmation_and_replays_once(env):
    client, engine, _ = env
    account(client)
    conversation, original = saved_photo(client, engine)
    destination = 'dinner' if original.meal_type != 'dinner' else 'lunch'
    label = '저녁' if destination == 'dinner' else '점심'
    result = say(client, conversation, label+'으로 바꿔줘')
    assert '바꿀까요' in last_bot(result)['text']
    assert meals(engine)[0].meal_type == original.meal_type
    request_id = str(uuid4())
    response = say(client, conversation, '응', request_id)
    assert last_bot(response)['kind'] == 'corrected'
    saved = meals(engine)[0]
    assert saved.meal_type == destination and saved.meal_date == original.meal_date
    assert saved.version == original.version + 1
    assert say(client, conversation, '응', request_id)['replayed']
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(MutationRequest).where(
            MutationRequest.operation == 'meal.details')) == 1


def test_change_saved_food_recalculates_and_keeps_original_detection(env):
    client, engine, _ = env
    account(client)
    conversation, original = saved_photo(client, engine)
    previous = original.items[0]
    result = say(client, conversation, f'{NAMES[GALBI]}가 아니라 {NAMES[0]}야')
    assert '바꿀까요' in last_bot(result)['text']
    assert meals(engine)[0].items[0].food_id == GALBI
    say(client, conversation, '응')
    item = meals(engine)[0].items[0]
    assert item.food_id == 0 and item.is_edited
    assert item.detection_log_id == previous.detection_log_id
    assert item.source == previous.source
    assert item.version == previous.version + 1
    assert item.nutrition == calculate_nutrition(0, .5)['nutrition']


def test_saved_edit_rejects_stale_preview(env):
    client, engine, _ = env
    account(client)
    conversation, original = saved_photo(client, engine)
    result = say(client, conversation, '간식으로 바꿔줘')
    assert '바꿀까요' in last_bot(result)['text']
    with Session(engine) as db:
        db.get(Meal, original.id).version += 1
        db.commit()
    result = say(client, conversation, '응')
    assert '기록이 변경' in last_bot(result)['text']
    assert meals(engine)[0].meal_type == original.meal_type


def test_focus_unknown_food_can_change_meal_type_but_not_another_users_record(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    saved = client.post('/meals', json={'meal_type':'lunch', 'items':[{'food_name':'내 음식'}]}).json()
    focus = client.post('/chat/focus', json={'conversation_id':conversation,'item_id':saved['items'][0]['id']})
    assert focus.status_code == 200, focus.text
    say(client, conversation, '저녁으로 바꿔줘')
    say(client, conversation, '응')
    assert meals(engine)[0].meal_type == 'dinner'
    account(client, 'other@example.com')
    other = start(client)
    assert client.post('/chat/focus', json={'conversation_id':other,'item_id':saved['items'][0]['id']}).status_code == 404


def test_meal_type_edit_asks_which_meal_when_multiple_records_exist(env):
    client, engine, _ = env
    account(client)
    conversation = start(client)
    for kind in ('breakfast','dinner'):
        response = client.post('/meals', json={'meal_type':kind,'items':[{'class_id':GALBI,'serving_multiplier':1}]})
        assert response.status_code == 201
    result = say(client, conversation, '점심으로 바꿔줘')
    assert '어느 끼니' in last_bot(result)['text']
    choice = last_bot(result)['payload']['chips'][0]['text']
    result = say(client, conversation, choice)
    assert '바꿀까요' in last_bot(result)['text']
    say(client, conversation, '응')
    assert sum(meal.meal_type == 'lunch' for meal in meals(engine)) == 1
