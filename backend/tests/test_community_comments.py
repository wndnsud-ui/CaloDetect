# 커뮤니티 댓글: 작성·목록·개수, 공백 거부, 삭제 권한(작성자·게시물 주인·관리자), 보상 없음, 삭제 게시물 차단.
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.models import User, PointTransaction
from backend.app.models_rewards import RewardXpEvent as Xp
from backend.tests.test_p0_flow import env, account  # noqa: F401 (fixture)
from backend.tests.test_community import users, post  # noqa: F401 (fixture)


def comments(client, p):
    r = client.get(f'/community/posts/{p["id"]}/comments')
    assert r.status_code == 200, r.text
    return r.json()['items']


def add(client, p, body):
    return client.post(f'/community/posts/{p["id"]}/comments', json={'body': body})


def test_comment_create_list_count_and_no_reward(users):
    a, b, au, bu, engine, _ = users
    p = post(a)
    with Session(engine) as db:
        before = (db.scalar(select(func.count()).select_from(PointTransaction)),
                  db.scalar(select(func.count()).select_from(Xp)))
    r = add(b, p, '  맛있어 보여요!  ')
    assert r.status_code == 201
    made = r.json()
    assert made['body'] == '맛있어 보여요!' and made['is_mine'] and made['can_delete']
    assert add(b, p, '   ').status_code == 422
    assert add(b, p, 'x' * 301).status_code == 422
    listed = comments(a, p)
    assert [c['body'] for c in listed] == ['맛있어 보여요!']
    assert listed[0]['is_mine'] is False and listed[0]['can_delete'] is True  # 게시물 주인
    feed = a.get('/community/posts').json()['items']
    assert next(i for i in feed if i['id'] == p['id'])['comment_count'] == 1
    with Session(engine) as db:
        after = (db.scalar(select(func.count()).select_from(PointTransaction)),
                 db.scalar(select(func.count()).select_from(Xp)))
    assert after == before


def test_comment_delete_permissions(users):
    a, b, au, bu, engine, _ = users
    p = post(a)
    with TestClient(app) as c:
        account(c, f'c{uuid4().hex}@example.com')
        by_b = add(b, p, 'B의 댓글').json()
        by_c = add(c, p, 'C의 댓글').json()
        assert comments(c, p)[0]['can_delete'] is False
        # 다른 회원은 남의 댓글을 지울 수 없다.
        assert c.delete(f'/community/posts/{p["id"]}/comments/{by_b["id"]}').status_code == 403
        # 작성자 본인 삭제, 게시물 주인 삭제.
        assert b.delete(f'/community/posts/{p["id"]}/comments/{by_b["id"]}').status_code == 200
        assert a.delete(f'/community/posts/{p["id"]}/comments/{by_c["id"]}').status_code == 200
        assert comments(a, p) == []
        assert b.delete(f'/community/posts/{p["id"]}/comments/{by_b["id"]}').status_code == 404
        # 관리자는 어떤 댓글이든 삭제할 수 있다.
        by_c2 = add(c, p, '다시').json()
        with Session(engine) as db:
            db.get(User, bu['id']).role = 'admin'; db.commit()
        assert comments(b, p)[0]['can_delete'] is True
        assert b.delete(f'/community/posts/{p["id"]}/comments/{by_c2["id"]}').status_code == 200


def test_comments_on_deleted_or_wrong_post(users):
    a, b, *_ = users
    p, other = post(a), post(b)
    made = add(b, p, '댓글').json()
    assert a.delete(f'/community/posts/{other["id"]}/comments/{made["id"]}').status_code == 404
    assert a.delete(f'/community/posts/{p["id"]}').status_code == 200
    assert b.get(f'/community/posts/{p["id"]}/comments').status_code == 404
    assert add(b, p, '늦은 댓글').status_code == 404
