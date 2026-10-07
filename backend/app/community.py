from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, field_validator
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from .config import ROOT, settings
from .db import get_db
from .models import CommunityPost as Post, CommunityReaction as Reaction, CommunityComment as Comment, User
from .schemas import RequestModel
from .security import get_user

router=APIRouter(prefix='/community',tags=['community'])
DB=Annotated[Session,Depends(get_db)]
Member=Annotated[User,Depends(get_user)]
KINDS=('meal','exercise','challenge','character')

class CommentBody(RequestModel):
    text: str=Field(min_length=1,max_length=1000)
    @field_validator('text')
    @classmethod
    def clean(cls,value):
        value=value.strip()
        if not value: raise ValueError('댓글을 입력하세요.')
        return value

class ReactionBody(RequestModel):
    active: bool

def accessible(db,post_id,user):
    post=db.get(Post,post_id)
    if post is None or (post.visibility!='public' and post.user_id!=user.id):
        raise HTTPException(404,'게시글을 찾을 수 없습니다.')
    return post

def image_root():
    return (Path(settings.image_storage_dir) if settings.image_storage_dir else ROOT/'.private-uploads')/'community'

def serialize(db,posts,user):
    if not posts:return []
    ids=[p.id for p in posts]
    authors=dict(db.execute(select(User.id,User.name).where(User.id.in_({p.user_id for p in posts}))).all())
    counts={(pid,kind):count for pid,kind,count in db.execute(select(Reaction.post_id,Reaction.kind,func.count()).where(Reaction.post_id.in_(ids)).group_by(Reaction.post_id,Reaction.kind))}
    comments=dict(db.execute(select(Comment.post_id,func.count()).where(Comment.post_id.in_(ids)).group_by(Comment.post_id)).all())
    own=set(db.execute(select(Reaction.post_id,Reaction.kind).where(Reaction.post_id.in_(ids),Reaction.user_id==user.id)).all())
    return [{'id':p.id,'title':p.title,'text':p.text,'category':p.category,'visibility':p.visibility,'author':authors[p.user_id],'owned':p.user_id==user.id,'created_at':p.created_at.isoformat(),'image_url':f'/api/community/posts/{p.id}/image' if p.image_name else None,'likes':counts.get((p.id,'like'),0),'recommendations':counts.get((p.id,'recommend'),0),'comments':comments.get(p.id,0),'liked':(p.id,'like') in own,'recommended':(p.id,'recommend') in own} for p in posts]

@router.get('/posts')
def list_posts(db:DB,user:Member,category:Literal['all','meal','exercise','challenge','character']='all',sort:Literal['latest','best','recommended']='latest',scope:Literal['all','others','mine']='all',offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=60)):
    query=select(Post).where(or_(Post.visibility=='public',Post.user_id==user.id))
    if scope=='others':query=query.where(Post.user_id!=user.id)
    elif scope=='mine':query=query.where(Post.user_id==user.id)
    if category!='all':query=query.where(Post.category==category)
    if sort!='latest':
        kind='like' if sort=='best' else 'recommend'
        count=select(func.count()).where(Reaction.post_id==Post.id,Reaction.kind==kind).correlate(Post).scalar_subquery()
        query=query.order_by(count.desc())
    posts=db.scalars(query.order_by(Post.created_at.desc(),Post.id.desc()).offset(offset).limit(limit+1)).all()
    return {'items':serialize(db,posts[:limit],user),'has_more':len(posts)>limit}

@router.post('/posts')
async def create_post(db:DB,user:Member,title:Annotated[str,Form(min_length=1,max_length=120)],text:Annotated[str,Form(min_length=1,max_length=4000)],category:Annotated[Literal['meal','exercise','challenge','character'],Form()],visibility:Annotated[Literal['public','private'],Form()]='private',file:Annotated[UploadFile|None,File()]=None):
    if not title.strip() or not text.strip():raise HTTPException(422,'제목과 내용을 입력하세요.')
    filename=None
    if file:
        raw=await file.read(10*1024*1024+1)
        if not raw or len(raw)>10*1024*1024:raise HTTPException(422,'사진은 10MB 이하여야 합니다.')
        try:
            with Image.open(BytesIO(raw)) as source:
                if source.format not in ('JPEG','PNG') or source.width*source.height>24000000:raise ValueError()
                normalized=ImageOps.exif_transpose(source).convert('RGB')
                normalized.thumbnail((1600,1600))
                root=image_root();root.mkdir(parents=True,exist_ok=True)
                filename=f'{uuid4().hex}.jpg';normalized.save(root/filename,'JPEG',quality=88)
        except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):
            raise HTTPException(422,'JPG 또는 PNG 사진을 확인하세요.')
    post=Post(user_id=user.id,title=title.strip(),text=text.strip(),category=category,visibility=visibility,image_name=filename)
    try:db.add(post);db.commit();db.refresh(post)
    except Exception:
        db.rollback()
        if filename:(image_root()/filename).unlink(missing_ok=True)
        raise
    return serialize(db,[post],user)[0]

@router.get('/posts/{post_id}')
def detail(post_id:str,db:DB,user:Member):
    post=accessible(db,post_id,user)
    result=serialize(db,[post],user)[0]
    rows=db.execute(select(Comment,User.name).join(User,Comment.user_id==User.id).where(Comment.post_id==post.id).order_by(Comment.created_at,Comment.id).limit(300)).all()
    result['comment_items']=[{'id':c.id,'text':c.text,'author':name,'owned':c.user_id==user.id,'created_at':c.created_at.isoformat()} for c,name in rows]
    return result

@router.get('/posts/{post_id}/image')
def image(post_id:str,db:DB,user:Member):
    post=accessible(db,post_id,user)
    if not post.image_name:raise HTTPException(404,'사진이 없습니다.')
    path=image_root()/post.image_name
    if not path.is_file():raise HTTPException(404,'사진을 찾을 수 없습니다.')
    return FileResponse(path,media_type='image/jpeg',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

@router.put('/posts/{post_id}/reactions/{kind}')
def react(post_id:str,kind:Literal['like','recommend'],body:ReactionBody,db:DB,user:Member):
    post=accessible(db,post_id,user)
    if body.active:
        # An explicit target state makes retries safe; unique keys prevent duplicate counts.
        values={'post_id':post.id,'user_id':user.id,'kind':kind}
        if db.bind.dialect.name=='postgresql':db.execute(pg_insert(Reaction).values(**values).on_conflict_do_nothing())
        else:
            from sqlalchemy.dialects.sqlite import insert
            db.execute(insert(Reaction).values(**values).on_conflict_do_nothing())
    else:db.execute(delete(Reaction).where(Reaction.post_id==post.id,Reaction.user_id==user.id,Reaction.kind==kind))
    db.commit()
    return serialize(db,[post],user)[0]

@router.post('/posts/{post_id}/comments')
def add_comment(post_id:str,body:CommentBody,db:DB,user:Member):
    post=accessible(db,post_id,user)
    comment=Comment(post_id=post.id,user_id=user.id,text=body.text);db.add(comment);db.commit()
    return detail(post.id,db,user)

@router.put('/posts/{post_id}/comments/{comment_id}')
def edit_comment(post_id:str,comment_id:str,body:CommentBody,db:DB,user:Member):
    post=accessible(db,post_id,user);comment=db.get(Comment,comment_id)
    if not comment or comment.post_id!=post.id:raise HTTPException(404,'댓글을 찾을 수 없습니다.')
    if comment.user_id!=user.id:raise HTTPException(403,'본인 댓글만 수정할 수 있습니다.')
    comment.text=body.text;db.commit();return detail(post.id,db,user)

@router.post('/posts/{post_id}/comments/{comment_id}/delete')
def remove_comment(post_id:str,comment_id:str,db:DB,user:Member):
    post=accessible(db,post_id,user);comment=db.get(Comment,comment_id)
    if not comment or comment.post_id!=post.id:raise HTTPException(404,'댓글을 찾을 수 없습니다.')
    if comment.user_id!=user.id:raise HTTPException(403,'본인 댓글만 삭제할 수 있습니다.')
    db.delete(comment);db.commit();return detail(post.id,db,user)

@router.post('/posts/{post_id}/delete')
def remove_post(post_id:str,db:DB,user:Member):
    post=accessible(db,post_id,user)
    if post.user_id!=user.id:raise HTTPException(403,'본인 게시글만 삭제할 수 있습니다.')
    db.execute(delete(Comment).where(Comment.post_id==post.id));db.execute(delete(Reaction).where(Reaction.post_id==post.id));db.delete(post);db.commit()
    if post.image_name:(image_root()/post.image_name).unlink(missing_ok=True)
    return {'deleted':True}
