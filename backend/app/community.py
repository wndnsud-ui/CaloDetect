"""로그인 및 기존 CurrentUser의 쿠키 CSRF 검사를 사용하는 커뮤니티 API."""
from typing import Literal
from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import FileResponse
from .api import CurrentUser, DB, require_image_environment
from .models import CommunityPostImage
from .schemas import CommunityPostRequest
from .services import community as service

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
    folder = (service.storage_folder() / 'community').resolve()
    path = (folder / image.storage_key).resolve()
    if not path.is_relative_to(folder) or not path.is_file():
        raise HTTPException(404, '사진을 찾을 수 없습니다.')
    return FileResponse(path, headers={'Cache-Control': 'private, no-store'})


@router.get('/points/me')
def points(user: CurrentUser, db: DB):
    return service.points(db, user)


@router.get('/ranking/weekly')
def ranking(user: CurrentUser, db: DB):
    return service.ranking(db, user)
