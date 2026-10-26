"""로그인 및 기존 CurrentUser의 쿠키 CSRF 검사를 사용하는 커뮤니티 API."""
from typing import Literal
from fastapi import APIRouter, Query, Request, Response, HTTPException
from .api import CurrentUser, DB, require_image_environment
from .models import CommunityPostImage
from .schemas import CommunityCommentRequest, CommunityPostRequest
from .services import community as service
from . import storage

router = APIRouter(prefix='/community', tags=['community'])
Kind = Literal['like', 'recommend']


@router.get('/posts')
def posts(user: CurrentUser, db: DB, limit: int = Query(20, ge=1, le=50), cursor: str | None = None, mine: bool = False):
    return service.feed(db, user, limit, cursor, mine)


@router.get('/eligible-meals')
def eligible(user: CurrentUser, db: DB, limit: int = Query(20, ge=1, le=50)):
    return service.eligible(db, user, limit)


@router.post('/posts', status_code=201)
def share(body: CommunityPostRequest, request: Request, user: CurrentUser, db: DB):
    if body.show_photo:
        require_image_environment(request)
    return service.create_post(db, user, body)


@router.get('/posts/{post_id}/delete-preview')
def delete_preview(post_id: str, user: CurrentUser, db: DB):
    return service.delete_preview(db, user, post_id)


@router.delete('/posts/{post_id}')
def delete_post(post_id: str, user: CurrentUser, db: DB):
    return service.delete_post(db, user, post_id)


@router.post('/posts/{post_id}/reactions/{kind}', status_code=201)
def react(post_id: str, kind: Kind, user: CurrentUser, db: DB):
    return service.react(db, user, post_id, kind)


@router.get('/posts/{post_id}/reactions/{kind}/revoke-preview')
def revoke_preview(post_id: str, kind: Kind, user: CurrentUser, db: DB):
    return service.revoke_preview(db, user, post_id, kind)


@router.delete('/posts/{post_id}/reactions/{kind}')
def revoke(post_id: str, kind: Kind, user: CurrentUser, db: DB):
    return service.react(db, user, post_id, kind, revoke=True)


@router.get('/posts/{post_id}/images/{image_id}')
def photo(post_id: str, image_id: str, request: Request, user: CurrentUser, db: DB):
    require_image_environment(request)
    post = service.active_post(db, post_id)
    image = db.get(CommunityPostImage, image_id)
    if not post.show_photo or not image or image.post_id != post.id:
        raise HTTPException(404, '사진을 찾을 수 없습니다.')
    service.require_storage()
    data = storage.get(service.community_key(image.storage_key))
    if data is None:
        raise HTTPException(404, '사진을 찾을 수 없습니다.')
    media_type = 'image/png' if image.storage_key.endswith('.png') else 'image/jpeg'
    return Response(data, media_type=media_type, headers={'Cache-Control': 'private, no-store'})


@router.get('/posts/{post_id}/comments')
def comments(post_id: str, user: CurrentUser, db: DB):
    return service.comments(db, user, post_id)


@router.post('/posts/{post_id}/comments', status_code=201)
def add_comment(post_id: str, body: CommunityCommentRequest, user: CurrentUser, db: DB):
    return service.add_comment(db, user, post_id, body.body)


@router.delete('/posts/{post_id}/comments/{comment_id}')
def delete_comment(post_id: str, comment_id: str, user: CurrentUser, db: DB):
    return service.delete_comment(db, user, post_id, comment_id)


@router.get('/points/me')
def points(user: CurrentUser, db: DB):
    return service.points(db, user)


@router.get('/ranking/weekly')
def ranking(user: CurrentUser, db: DB):
    return service.ranking(db, user)
