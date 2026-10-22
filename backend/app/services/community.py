"""원본 식단 조회 및 포인트 원장. 잠금 순서는 게시물 → 반응으로 고정한다."""
import logging
from pathlib import Path
from sqlalchemy import select, func, or_, and_, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from ..models import (CommunityPost as Post, CommunityPostImage as Photo,
    CommunityReaction as Reaction, PointTransaction as Tx, Meal, Food, User, Detection, ImageUpload, utcnow)
from ..config import settings, ROOT
from .community_images import save_sanitized_copy
from . import rewards
from .community_rules import week_start, encode_cursor, decode_cursor, RECEIVED_REASONS, KST

log = logging.getLogger(__name__)
NUTRIENTS = ('cal', 'carbs', 'protein', 'fat', 'sugar', 'sodium')


def storage_folder():
    if not settings.image_storage_dir:
        raise HTTPException(503, '사진 저장 설정이 필요합니다.')
    path = Path(settings.image_storage_dir)
    return path if path.is_absolute() else ROOT / path


def source_images(db, meals):
    """페이지 단위 소유권 검사. 탐지 사진과 채팅 직접 선택 사진을 모두 지원한다."""
    from ..models_chat import ChatAttachment
    detections = {x.id: x for x in db.scalars(select(Detection).where(
        Detection.id.in_([i.detection_log_id for m in meals for i in m.items if i.detection_log_id])))}
    attachments = {x.id: x for x in db.scalars(select(ChatAttachment).where(
        ChatAttachment.id.in_([m.chat_attachment_id for m in meals if m.chat_attachment_id])))}
    ids_by_meal = {}
    for meal in meals:
        ids = []
        for item in meal.items:
            det = detections.get(item.detection_log_id)
            if det and det.user_id == meal.user_id and det.image_group_id not in ids:
                ids.append(det.image_group_id)
        attachment = attachments.get(meal.chat_attachment_id)
        if attachment and attachment.user_id == meal.user_id and attachment.image_upload_id not in ids:
            ids.append(attachment.image_upload_id)
        ids_by_meal[meal.id] = ids
    images = {x.id: x for x in db.scalars(select(ImageUpload).where(
        ImageUpload.id.in_([i for ids in ids_by_meal.values() for i in ids])))}
    return {m.id: [images[i] for i in ids_by_meal[m.id] if i in images and images[i].user_id == m.user_id]
            for m in meals}


def meal_data(meal, foods):
    items = [{'class_id': i.food_id, 'food_name': foods[i.food_id].canonical_name,
              'category': foods[i.food_id].category, 'unit': foods[i.food_id].serving_unit,
              'serving_multiplier': i.serving_multiplier * i.consumption_ratio,
              'nutrition': i.nutrition} for i in sorted(meal.items, key=lambda i: (i.created_at, i.id))]
    return {'meal_date': str(meal.meal_date), 'meal_type': meal.meal_type, 'items': items,
            'totals': {k: round(sum(i['nutrition'].get(k, 0) for i in items), 2) for k in NUTRIENTS}}


def serialize(db, posts, user):
    meals = {m.id: m for m in db.scalars(select(Meal).options(selectinload(Meal.items)).where(
        Meal.id.in_([p.meal_id for p in posts])))}
    foods = {f.id: f for f in db.scalars(select(Food).where(Food.id.in_(
        [i.food_id for m in meals.values() for i in m.items])))}
    names = rewards.display_names(db, [p.user_id for p in posts])
    reactions = list(db.scalars(select(Reaction).where(Reaction.post_id.in_([p.id for p in posts]))))
    photos = list(db.scalars(select(Photo).where(Photo.post_id.in_([p.id for p in posts])).order_by(Photo.position)))
    return [{'id': p.id, 'created_at': p.created_at, 'author': {'name': names[p.user_id], 'is_me': p.user_id == user.id},
        'is_mine': p.user_id == user.id, 'meal_id': p.meal_id if p.user_id == user.id else None,
        'comment': p.comment, 'show_photo': p.show_photo, 'meal': meal_data(meals[p.meal_id], foods),
        'image_urls': [f'/api/community/posts/{p.id}/images/{i.id}' for i in photos if i.post_id == p.id] if p.show_photo else [],
        'counts': {k: sum(r.post_id == p.id and r.kind == k for r in reactions) for k in ('like', 'recommend')},
        'my_reactions': [r.kind for r in reactions if r.post_id == p.id and r.user_id == user.id]} for p in posts]


def feed(db, user, limit, cursor=None, mine=False):
    query = select(Post).where(Post.deleted_at.is_(None))
    if mine:
        query = query.where(Post.user_id == user.id)
    if cursor:
        try:
            instant, post_id = decode_cursor(cursor)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        query = query.where(or_(Post.created_at < instant, and_(Post.created_at == instant, Post.id < post_id)))
    posts = list(db.scalars(query.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)))
    last = posts[-1] if posts else None
    # SQLite datetime은 timezone 정보가 없지만 저장 시각은 UTC다. 잠금 로직에는 방언 분기가 없다.
    from datetime import timezone
    next_cursor = encode_cursor(last.created_at.replace(tzinfo=timezone.utc) if last.created_at.tzinfo is None
        else last.created_at, last.id) if len(posts) == limit else None
    return {'items': serialize(db, posts, user), 'next_cursor': next_cursor}


def eligible(db, user, limit):
    meals = list(db.scalars(select(Meal).options(selectinload(Meal.items)).where(Meal.user_id == user.id,
        ~select(Post.id).where(Post.meal_id == Meal.id).exists(), Meal.items.any())
        .order_by(Meal.meal_date.desc(), Meal.created_at.desc()).limit(limit)))
    foods = {f.id: f for f in db.scalars(select(Food))}
    images = source_images(db, meals)
    return {'items': [{'meal_id': m.id, 'meal_date': str(m.meal_date), 'meal_type': m.meal_type,
        'has_photo': bool(images[m.id]), 'items': [{k: i[k] for k in ('class_id', 'food_name', 'category')}
            for i in meal_data(m, foods)['items']]} for m in meals]}


def create_post(db, user, body):
    meal = db.scalar(select(Meal).options(selectinload(Meal.items)).where(Meal.id == body.meal_id, Meal.user_id == user.id))
    if not meal:
        raise HTTPException(404, '식단을 찾을 수 없습니다.')
    old = db.scalar(select(Post).where(Post.meal_id == meal.id))
    if old:
        raise HTTPException(409, '삭제한 게시물의 식단은 다시 공유할 수 없어요.' if old.deleted_at else '이미 커뮤니티에 공유한 식단이에요.')
    if not meal.items:
        raise HTTPException(422, '음식이 없는 식단은 공유할 수 없어요.')
    sources = source_images(db, [meal])[meal.id] if body.show_photo else []
    if body.show_photo and not sources:
        raise HTTPException(422, '사진 없는 식단은 사진을 공개할 수 없어요.')
    files = []
    try:
        post = Post(user_id=user.id, meal_id=meal.id, comment=body.comment.strip(), show_photo=body.show_photo)
        db.add(post)
        db.flush()
        for position, source in enumerate(sources):
            folder = storage_folder()
            path = (folder / source.image_path).resolve()
            if not path.is_relative_to(folder.resolve()):
                raise ValueError('Invalid source')
            copied = save_sanitized_copy(path, folder / 'community')
            files.append(copied)
            db.add(Photo(post_id=post.id, source_image_id=source.id, storage_key=copied.name, position=position))
        rewards.community_share(db, user.id, post.id)  # 리워드 식단 공유(XP 모드에서만)
        db.commit()
    except Exception as error:
        db.rollback()
        for path in files:
            path.unlink(missing_ok=True)
        if isinstance(error, IntegrityError):
            old = db.scalar(select(Post).where(Post.meal_id == meal.id))
            raise HTTPException(409, '삭제한 게시물의 식단은 다시 공유할 수 없어요.' if old and old.deleted_at
                else '이미 커뮤니티에 공유한 식단이에요.') from None
        if isinstance(error, (ValueError, OSError)):
            log.warning('community image sanitize failed')
            raise HTTPException(422, '사진 사본을 만들 수 없습니다.') from None
        raise
    log.info('community post created')
    return serialize(db, [post], user)[0]


def active_post(db, post_id, lock=None):
    query = select(Post).where(Post.id == post_id).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update(read=lock == 'share')
    post = db.scalar(query)
    if post is None or post.deleted_at is not None:
        raise HTTPException(404, '게시물을 찾을 수 없습니다.')
    return post


def originals(db, reaction):
    return list(db.scalars(select(Tx).where(Tx.reaction_id == reaction.id, Tx.amount > 0)))


def revoke_preview(db, user, post_id, kind):
    post = active_post(db, post_id)
    reaction = db.scalar(select(Reaction).where(Reaction.post_id == post.id, Reaction.user_id == user.id, Reaction.kind == kind))
    if not reaction:
        raise HTTPException(404, '반응을 찾을 수 없습니다.')
    rows = originals(db, reaction)
    return {'me': -sum(t.amount for t in rows if t.user_id == user.id),
            'author': -sum(t.amount for t in rows if t.user_id == post.user_id), 'counts_in_week': 'current'}


def commit_or_404(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(404, '이미 처리된 요청입니다.') from None


def react(db, user, post_id, kind, revoke=False):
    post = active_post(db, post_id, 'share')  # 반드시 첫 서비스 쿼리. 삭제와 직렬화.
    if post.user_id == user.id:
        raise HTTPException(403, '본인 게시물에는 반응할 수 없어요.')
    query = select(Reaction).where(Reaction.post_id == post.id, Reaction.user_id == user.id, Reaction.kind == kind)
    reaction = db.scalar(query.with_for_update() if revoke else query)
    deducted = {'me': 0, 'author': 0}
    if revoke:
        if not reaction:
            raise HTTPException(404, '반응을 찾을 수 없습니다.')
        if db.execute(delete(Reaction).where(Reaction.id == reaction.id)).rowcount != 1:
            db.rollback()
            raise HTTPException(404, '이미 취소된 반응입니다.')
        already = db.scalar(select(Tx.id).where(Tx.reaction_id == reaction.id, Tx.reason.endswith('_revoked', autoescape=True)))
        if already is None:
            for tx in originals(db, reaction):
                db.add(Tx(user_id=tx.user_id, amount=-tx.amount, reason=tx.reason + '_revoked',
                          post_id=post.id, reaction_id=reaction.id))
                deducted['me' if tx.user_id == user.id else 'author'] -= tx.amount
        rewards.community_reaction_revoked(db, reaction.id)  # 리워드 원장 회수
        commit_or_404(db)
    else:
        if reaction:
            raise HTTPException(409, '이미 누른 반응이에요.')
        reaction = Reaction(post_id=post.id, user_id=user.id, kind=kind)
        reaction_inserted = False
        try:
            db.add(reaction)
            db.flush()
            reaction_inserted = True
            received = settings.community_like_received_points if kind == 'like' else settings.community_recommend_received_points
            for user_id, amount, suffix in ((post.user_id, received, 'received'), (user.id, settings.community_reaction_given_points, 'given')):
                if amount:
                    db.add(Tx(user_id=user_id, amount=amount, reason=f'{kind}_{suffix}', post_id=post.id, reaction_id=reaction.id))
            rewards.community_reaction(db, reaction.id, post.user_id, user.id, kind)  # 리워드 lot 미러링·XP 모드
            db.commit()
        except IntegrityError:
            db.rollback()
            if reaction_inserted:
                raise HTTPException(404, '이미 처리된 요청입니다.') from None
            raise HTTPException(409, '이미 누른 반응이에요.') from None
    log.info('community reaction %s%s', kind, ' revoked' if revoke else '')
    result = serialize(db, [post], user)[0]
    if revoke:
        result['deducted'] = deducted
    return result


def deletion_net(db, post):
    return db.scalar(select(func.coalesce(func.sum(Tx.amount), 0)).where(Tx.user_id == post.user_id,
        Tx.post_id == post.id, Tx.reason.in_(RECEIVED_REASONS)))


def delete_preview(db, user, post_id):
    post = active_post(db, post_id)
    if post.user_id != user.id:
        raise HTTPException(403, '본인 게시물만 삭제할 수 있어요.')
    return {'me': -max(0, deletion_net(db, post)), 'reactors_affected': False}


def delete_post(db, user, post_id):
    post = active_post(db, post_id, 'update')
    if post.user_id != user.id:
        raise HTTPException(403, '본인 게시물만 삭제할 수 있어요.')
    net = deletion_net(db, post)
    already = db.scalar(select(Tx.id).where(Tx.post_id == post.id, Tx.reason == 'post_deleted_revoked'))
    deducted = -net if net > 0 and already is None else 0
    if deducted:
        db.add(Tx(user_id=user.id, amount=deducted, reason='post_deleted_revoked', post_id=post.id))
    if db.execute(update(Post).where(Post.id == post.id, Post.deleted_at.is_(None)).values(deleted_at=utcnow())).rowcount != 1:
        db.rollback()
        raise HTTPException(404, '이미 삭제된 게시물입니다.')
    rewards.community_post_deleted(db, user.id, post.id, -deducted)  # 리워드 원장 회수
    commit_or_404(db)
    log.info('community post deleted deducted=%d', deducted)
    return {'deleted': True, 'deducted': {'me': deducted}}


def points(db, user):
    def total(*filters):
        return db.scalar(select(func.coalesce(func.sum(Tx.amount), 0)).where(Tx.user_id == user.id, *filters))
    start = week_start()
    rows = list(db.scalars(select(Tx).where(Tx.user_id == user.id).order_by(Tx.created_at.desc(), Tx.id.desc()).limit(30)))
    result = {'balance': total(), 'earned_this_week': total(Tx.created_at >= start, Tx.amount > 0),
        'deducted_this_week': total(Tx.created_at >= start, Tx.amount < 0), 'points_usage': None,
        'rules': {'like_received': settings.community_like_received_points, 'recommend_received': settings.community_recommend_received_points,
                  'like_given': settings.community_reaction_given_points, 'recommend_given': settings.community_reaction_given_points},
        'recent': [{'id': t.id, 'amount': t.amount, 'reason': t.reason, 'created_at': t.created_at} for t in rows[:30]]}
    if settings.reward_enabled and settings.reward_community_xp_mode:
        result['reward_view'] = {
            'balance': rewards.balance_info(db, user.id)['balance'],
            'recent': rewards.ledger(db, user)['items'],
            'share_points': settings.reward_share_points, 'share_xp': settings.reward_share_xp,
            'like_xp': settings.reward_reaction_received_like_xp,
            'recommend_xp': settings.reward_reaction_received_recommend_xp,
            'given_xp': settings.reward_reaction_given_xp,
            'received_daily_cap': settings.reward_reaction_received_daily_cap,
            'given_daily_cap': settings.reward_reaction_given_daily_cap,
        }
    return result


def ranking(db, user):
    start = week_start()
    score = func.sum(Tx.amount)
    rows = db.execute(select(User.id, User.name, score.label('points')).join(Tx, Tx.user_id == User.id)
        .where(Tx.created_at >= start).group_by(User.id, User.name).having(score > 0)
        .order_by(score.desc(), User.id)).all()
    items, my_rank, previous, rank = [], None, None, 0
    my_points = db.scalar(select(func.coalesce(score, 0)).where(Tx.user_id == user.id, Tx.created_at >= start))
    names = rewards.display_names(db, [row.id for row in rows[:settings.community_ranking_size]])
    for index, row in enumerate(rows):
        if row.points != previous:
            rank = index + 1
        previous = row.points
        if row.id == user.id:
            my_rank = rank
        if index < settings.community_ranking_size:
            items.append({'rank': rank, 'name': names[row.id], 'points': row.points, 'is_me': row.id == user.id})
    deducted = db.scalar(select(func.coalesce(score, 0)).where(Tx.user_id == user.id, Tx.created_at >= start, Tx.amount < 0))
    return {'timezone': 'Asia/Seoul', 'week_start': start.astimezone(KST).isoformat(), 'items': items,
            'me': {'rank': my_rank, 'points': my_points, 'deducted_this_week': deducted}}
