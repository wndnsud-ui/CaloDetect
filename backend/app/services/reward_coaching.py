"""리워드몰 v1.3 M4: 전문 코칭 이용권(외부 채널 연결형, 지시서 §6-4). REWARD_COACHING_ENABLED=false(기본)면 API 404.

- 코치별 7회 이용권 700P. 구매 즉시 카카오톡·연락처 공개, 사용자 취소 없음(관리자 수동 환불만).
- 가입 14일·월 1회·월 전체 상한·첫 교환 보류는 적용하지 않는다. 교환 제외 출처 lot은 쓰지 않는다.
- 잠금 순서: reward_accounts → reward_point_lots → reward_coach_passes. 같은 (user_id, idem_key)는 같은 결과를 돌려준다.
- 연락처(kakao_link·phone)는 목록·피드·비구매자 상세·로그에 넣지 않는다. 로그에는 코치 ID·포인트만 남긴다.
- 코치 정보·평점·누적 코칭 수·후기는 시연용이다. 연락처는 자리표시 값만 쓴다.
"""
import logging
from fastapi import HTTPException
from sqlalchemy import select
from ..config import settings
from ..models_rewards import (RewardCoachProfile as Coach, RewardCoachContent as Content, RewardCoachPass as Pass,
    RewardProduct as Product, RewardPointSpend as Spend)
from . import rewards, reward_rules as rules, reward_catalog as catalog

log = logging.getLogger('calodetect')
SPECIALTIES = ('nutrition', 'diet', 'exercise', 'lifestyle')
PHONE = '010-0000-0000'
KAKAO = 'https://pf.kakao.com/[시연용]'
STEPS = [['fork', '식단 확인', '평소 식사 패턴을\n구체적으로 체크해요.'], ['search', '생활 패턴 분석', '직장, 수면, 외식 등\n라이프스타일을 살펴봐요.'],
         ['chat', '1:1 피드백', '카카오톡으로 맞춤 피드백과\n실행 가능한 조언을 드려요.'], ['check', '실천 가이드', '지속할 수 있는 식습관으로\n변화를 만들어가요.']]
NOTICE = '코치 정보는 시연용이에요. 코칭은 영양·생활습관 조언이며 질병 진단이나 처방은 제공하지 않아요.'

# 시안 CW1·CW2 데이터(시연용). 자격·경력 증빙은 실제 코치 등록 시 확인한다.
COACHES = (
    {'id': 'kim', 'name': '김지윤 코치', 'headline': '영양 · 직장인 식단관리', 'specialties': ['nutrition', 'diet'],
     'quote': '현실적으로 지속할 수 있는 식단을 함께 만들어갑니다.',
     'philosophy': '먹지 말라는 코칭보다\n지속할 수 있는 식사를 찾습니다.', 'career': ['영양관리 8년', '누적 코칭 320회'],
     'introduction': '현실적으로 지속할 수 있는 식단을 함께 만들어갑니다. 회식과 외식이 잦은 직장인도 무리 없이 이어갈 수 있는 식사 기준을 같이 세워요.',
     'rating_text': '4.9', 'coaching_count': 320, 'tone': 'nutrition', 'crumb': '식단관리 코치',
     'photo': 'coaches/kim.png', 'side': 'coaches/kim_side.png', 'side_note': '지속 가능한\n변화를 응원해요!',
     'content_images': ['coaches/kim-1.png', 'coaches/kim-2.png', 'coaches/kim-3.png'],
     'sticky': '건강한\n식습관이 만드는\n좋은 변화,\n함께해요. :)', 'how': '개인의 생활 패턴에 맞춘 현실적인 식단 코칭을 진행합니다.',
     'areas': [['bag', '직장인 식단'], ['scale', '체중 관리'], ['fork', '외식 관리'], ['leaf', '영양 밸런스']],
     'includes': ['식단 피드백', '영양 상담', '생활습관 조언', '추가 질문'],
     'reviews': [['현실적인 식단이라 꾸준히 할 수 있었어요. 외식 많은 직장인에게 특히 추천합니다!', '30대 직장인 · 2주 전'],
                 ['제 생활패턴을 꼼꼼히 봐주시고 실천 가능한 방법만 알려주셔서 좋았어요.', '20대 대학원생 · 1개월 전'],
                 ['식단뿐 아니라 생활 습관까지 체크해주셔서 많이 도움이 됐어요.', '40대 직장인 · 1개월 전']],
     'contents': [['column', '칼럼', '다이어트 중에도 국밥 먹을 수 있습니다', '국물은 반만, 밥은 2/3 공기. 먹는 방법을 바꾸면 메뉴를 포기하지 않아도 돼요.'],
                  ['tip', '영양 TIP', '편의점 한 끼, 이렇게 골라요', '단백질 하나, 채소 하나를 먼저 담고 나머지를 고르면 균형이 쉬워져요.'],
                  ['case', '외식 관리', '회식 다음 날 식사', '굶기보다 평소 끼니 시간을 지키는 게 먼저예요.']]},
    {'id': 'park', 'name': '박재현 코치', 'headline': '운동 · 홈트레이닝 루틴', 'specialties': ['exercise'],
     'quote': '운동보다 중요한 것은 지속 가능한 루틴입니다.',
     'philosophy': '하루 20분이라도\n매일 할 수 있는 운동을 함께 정합니다.', 'career': ['운동 지도 6년', '누적 코칭 210회'],
     'introduction': '운동보다 중요한 것은 지속 가능한 루틴입니다. 바쁜 일정 안에서 무리 없이 이어갈 수 있는 운동과 식사 타이밍을 같이 잡아요.',
     'rating_text': '4.8', 'coaching_count': 210, 'tone': 'exercise', 'crumb': '운동 코치',
     'sticky': '매일 20분,\n작은 루틴부터\n함께해요!', 'how': '생활 리듬에 맞춘 운동 루틴과 식사 타이밍을 함께 잡아요.',
     'areas': [['bag', '직장인 운동'], ['scale', '근력 루틴'], ['fork', '운동 전후 식사'], ['leaf', '홈트레이닝']],
     'includes': ['운동 루틴 피드백', '운동 전후 식사 조언', '생활습관 조언', '추가 질문'], 'reviews': [],
     'contents': [['tip', '운동 TIP', '처음 2주는 시간부터 고정하세요', '같은 시간에 20분, 종목보다 습관을 먼저 만들어요.'],
                  ['tip', '식사 TIP', '운동 전후 식사', '운동 1~2시간 전에는 소화가 편한 식사를 가볍게 드세요.'],
                  ['column', '칼럼', '운동보다 중요한 것은 루틴입니다', '빠지는 날이 생겨도 다음 날 다시 시작하면 루틴은 이어져요.']]},
    {'id': 'lee', 'name': '이수민 코치', 'headline': '생활습관 · 야식·수면 패턴', 'specialties': ['lifestyle', 'diet'],
     'quote': '야식이 반복되는 이유부터 찾아보는 것이 중요합니다.',
     'philosophy': '참는 법보다\n반복되는 패턴을 바꾸는 법을 찾습니다.', 'career': ['생활습관 코칭 5년', '누적 코칭 185회'],
     'introduction': '야식이 반복되는 이유부터 찾아보는 것이 중요합니다. 식사 시간, 수면, 스트레스가 어떻게 이어지는지 기록을 함께 돌아봐요.',
     'rating_text': '4.9', 'coaching_count': 185, 'tone': 'lifestyle', 'crumb': '생활습관 코치',
     'sticky': '참는 대신\n패턴을 바꿔요.\n함께해요!', 'how': '반복되는 생활 패턴을 찾아 하나씩 바꿔가요.',
     'areas': [['bag', '식사 시간 관리'], ['scale', '야식 습관'], ['fork', '스트레스 식사'], ['leaf', '수면 리듬']],
     'includes': ['식사 패턴 피드백', '생활습관 상담', '루틴 조언', '추가 질문'], 'reviews': [],
     'contents': [['tip', '생활습관', '야식이 반복된다면', '저녁을 너무 이르거나 적게 먹은 날이었는지 먼저 살펴보세요.'],
                  ['tip', '수면 TIP', '잠들기 전 2시간', '이 시간의 간식 기록만 따로 모아 보면 패턴이 보여요.'],
                  ['column', '칼럼', '참지 말고 바꾸기', '참는 힘보다 환경을 바꾸는 게 오래 가요.']]},
    {'id': 'choi', 'name': '최하은 코치', 'headline': '다이어트 · 감량·요요 관리', 'specialties': ['diet', 'nutrition'],
     'quote': '빠르게 빼는 것보다 다시 찌지 않는 것이 목표입니다.',
     'philosophy': '굶는 감량보다\n유지할 수 있는 감량을 함께 설계합니다.', 'career': ['체중관리 코칭 7년', '누적 코칭 260회'],
     'introduction': '빠르게 빼는 것보다 다시 찌지 않는 것이 목표입니다. 감량 속도와 식사량을 무리 없이 조절해 요요 없는 체중 관리를 함께해요.',
     'rating_text': '4.8', 'coaching_count': 260, 'tone': 'diet', 'crumb': '다이어트 코치',
     'sticky': '천천히, 꾸준히\n요요 없는 감량,\n함께해요!', 'how': '감량 속도와 식사량을 기록으로 확인하며 조절해요.',
     'areas': [['scale', '체중 감량'], ['leaf', '요요 관리'], ['fork', '식사량 조절'], ['bag', '간식 관리']],
     'includes': ['감량 식단 피드백', '체중 변화 점검', '생활습관 조언', '추가 질문'], 'reviews': [],
     'contents': [['tip', '다이어트 TIP', '정체기가 왔다면', '2주 정도는 평소 식사를 유지하며 기록부터 다시 확인해 보세요.'],
                  ['tip', '식사 TIP', '배고픈 감량은 오래 못 가요', '단백질과 채소를 먼저 먹으면 같은 칼로리도 더 든든해요.'],
                  ['column', '칼럼', '요요를 막는 마지막 한 달', '목표 체중에 닿은 뒤 한 달은 유지 연습 기간으로 잡아요.']]},
)
FEED_ORDER = (('kim', 0), ('park', 0), ('lee', 0), ('choi', 0), ('kim', 1))


def require_enabled():
    if not settings.reward_coaching_enabled:
        raise HTTPException(404, 'Not Found')


def ensure_coaches(db):
    """시연용 코치·콘텐츠 시드. 없으면 추가, 있으면 화면 데이터만 갱신(연락처는 자리표시 값으로 둔다)."""
    # 요청마다 불리므로 한 요청(세션)에서는 한 번만 하고, 코치·콘텐츠는 한 번에 읽어 항목마다 조회하지 않는다.
    if db.info.get('reward_coaches_synced'):
        return
    coaches = {c.id: c for c in db.scalars(select(Coach))}
    contents = {c.id: c for c in db.scalars(select(Content))}
    for order, data in enumerate(COACHES):
        steps = {'steps': STEPS, 'how': data['how'], 'areas': data['areas'], 'includes': data['includes'],
                 'reviews': data['reviews'], 'tone': data['tone'], 'crumb': data['crumb'], 'sticky': data['sticky'],
                 'side_note': data.get('side_note')}
        row = coaches.get(data['id'])
        if row is None:
            rewards.savepoint(db, lambda: (db.add(Coach(
                id=data['id'], name=data['name'], headline=data['headline'], specialties=list(data['specialties']),
                quote=data['quote'], philosophy=data['philosophy'], career=list(data['career']),
                introduction=data['introduction'], steps=steps, rating_text=data['rating_text'],
                coaching_count=data['coaching_count'], profile_image_key=data.get('photo'), side_image_key=data.get('side'),
                kakao_link=KAKAO, phone=PHONE, active=True, sort_order=order, is_mock=True)), db.flush()))
        else:
            row.name, row.headline, row.specialties, row.quote = data['name'], data['headline'], list(data['specialties']), data['quote']
            row.philosophy, row.career, row.introduction, row.steps = data['philosophy'], list(data['career']), data['introduction'], steps
            row.rating_text, row.coaching_count = data['rating_text'], data['coaching_count']
            row.profile_image_key, row.side_image_key = data.get('photo'), data.get('side')
        pictures = data.get('content_images', [])
        for index, (kind, label, title, body) in enumerate(data['contents']):
            content_id = f"{data['id']}-{index + 1}"
            picture = pictures[index] if index < len(pictures) else None
            item = contents.get(content_id)
            if item is None:
                rewards.savepoint(db, lambda: (db.add(Content(id=content_id, coach_id=data['id'], kind=kind, label=label,
                                                              title=title, body=body, image_key=picture, sort_order=index)), db.flush()))
            else:
                item.kind, item.label, item.title, item.body, item.image_key = kind, label, title, body, picture
    db.info['reward_coaches_synced'] = True


def seeded(db):
    from .reward_exchange import ensure_products
    ensure_products(db)


def product_of(db, coach_id):
    return db.scalar(select(Product).where(Product.coach_id == coach_id, Product.active.is_(True)))


def in_use(db, user_id, coach_id):
    # 목록에서 코치마다 부르므로 사용 중 이용권을 한 번에 읽어 같은 요청 안에서 재사용한다.
    passes = rewards.request_cache(db, ('coach_passes_in_use', user_id), lambda: {
        p.coach_id: p for p in db.scalars(select(Pass).where(Pass.user_id == user_id, Pass.status == 'in_use'))})
    return passes.get(coach_id)


def coach_card(db, coach, user):
    """목록·피드·비구매자 상세에 쓰는 공개 정보. 연락처는 넣지 않는다."""
    extra = coach.steps or {}
    return {'id': coach.id, 'name': coach.name, 'headline': coach.headline, 'specialties': list(coach.specialties or []),
            'quote': coach.quote, 'rating_text': coach.rating_text, 'coaching_count': coach.coaching_count,
            'tone': extra.get('tone'), 'profile_image': coach.profile_image_key, 'is_mock': coach.is_mock,
            'pass_status': 'in_use' if in_use(db, user.id, coach.id) else 'none'}


def pass_offer(db, user, product):
    balance = rewards.balance_info(db, user.id)
    left = max(0, product.price - balance['exchangeable'])
    return {'product_id': product.id, 'price': product.price, 'sessions': catalog.COACH_SESSIONS,
            'exchangeable': balance['exchangeable'], 'shortfall': left,
            'eta_days': rewards.eta_points(db, user, left, exchange_only=True) if left else 0,
            'is_goal': (rewards.account(db, user.id).goal_ref == f'product:{product.id}')}


def coaches(db, user, specialty=None):
    require_enabled()
    seeded(db)
    if specialty and specialty not in SPECIALTIES:
        raise HTTPException(422, '분야를 확인해 주세요.')
    rows = [c for c in db.scalars(select(Coach).where(Coach.active.is_(True)).order_by(Coach.sort_order))
            if not specialty or specialty in (c.specialties or [])]
    first = product_of(db, rows[0].id) if rows else db.scalar(select(Product).where(Product.coach_id.is_not(None)))
    result = {'items': [coach_card(db, c, user) for c in rows], 'offer': pass_offer(db, user, first) if first else None,
              'notice': NOTICE}
    db.commit()
    return result


def feed(db, user):
    require_enabled()
    seeded(db)
    names = {c.id: c for c in db.scalars(select(Coach).where(Coach.active.is_(True)))}
    contents = {c.coach_id: [] for c in db.scalars(select(Content))}
    for content in db.scalars(select(Content).order_by(Content.sort_order)):
        contents.setdefault(content.coach_id, []).append(content)
    items = []
    for coach_id, index in FEED_ORDER:
        rows = contents.get(coach_id) or []
        if coach_id in names and index < len(rows):
            c = rows[index]
            items.append({'id': c.id, 'coach_id': coach_id, 'coach_name': names[coach_id].name,
                          'tone': (names[coach_id].steps or {}).get('tone'), 'kind': c.kind, 'label': c.label,
                          'title': c.title, 'body': c.body})
    db.commit()
    return {'items': items}


def contact(coach):
    return {'kakao_link': coach.kakao_link, 'phone': coach.phone}


def coach_detail(db, user, coach_id):
    require_enabled()
    seeded(db)
    coach = db.get(Coach, coach_id)
    product = product_of(db, coach_id) if coach else None
    if coach is None or not coach.active or product is None:
        raise HTTPException(404, '코치를 찾을 수 없습니다.')
    extra = coach.steps or {}
    current = in_use(db, user.id, coach_id)
    result = {**coach_card(db, coach, user), 'philosophy': coach.philosophy, 'career': list(coach.career or []),
              'introduction': coach.introduction, 'steps': extra.get('steps', []), 'how': extra.get('how'),
              'areas': extra.get('areas', []), 'includes': extra.get('includes', []), 'reviews': extra.get('reviews', []),
              'crumb': extra.get('crumb'), 'sticky': extra.get('sticky'), 'side_image': coach.side_image_key,
              'side_note': extra.get('side_note'),
              'contents': [{'id': c.id, 'kind': c.kind, 'label': c.label, 'title': c.title, 'body': c.body, 'image': c.image_key}
                           for c in db.scalars(select(Content).where(Content.coach_id == coach_id).order_by(Content.sort_order))],
              'offer': pass_offer(db, user, product), 'notice': NOTICE,
              'pass': pass_json(db, current, coach) if current else None}
    db.commit()
    return result


def pass_json(db, row, coach=None):
    """본인 이용권 응답. 연락처는 사용 중(in_use)인 이용권 주인에게만 넣는다."""
    coach = coach or db.get(Coach, row.coach_id)
    data = {'id': row.id, 'coach_id': row.coach_id, 'coach_name': coach.name if coach else None,
            'headline': coach.headline if coach else None, 'tone': (coach.steps or {}).get('tone') if coach else None,
            'product_id': row.product_id, 'sessions': row.sessions, 'points': row.points, 'status': row.status,
            'purchased_at': rules.as_aware(row.purchased_at), 'closed_at': rules.as_aware(row.closed_at)}
    if row.status == 'in_use' and coach:
        data.update(contact(coach))
    return data


def buy(db, user, coach_id, idem_key):
    """이용권 구매(한 트랜잭션, §6-4). 잠금: 계정 → lot(spend_points 안) → 이용권."""
    require_enabled()
    seeded(db)
    coach = db.get(Coach, coach_id)
    product = product_of(db, coach_id) if coach else None
    if coach is None or not coach.active or product is None or not product.available:
        raise HTTPException(404, '코치를 찾을 수 없습니다.')
    rewards.account(db, user.id, lock=True)                       # 1) 계정
    done = db.scalar(select(Pass).where(Pass.user_id == user.id, Pass.idem_key == idem_key))
    if done is not None:                                         # 2) 같은 요청 → 같은 결과(연타 방지)
        if done.coach_id != coach_id:
            db.rollback()
            raise HTTPException(409, {'code': 'IDEM_CONFLICT', 'message': '다른 구매 요청에 쓰인 키예요.'})
        result = {**pass_json(db, done, coach), 'balance': rewards.balance_info(db, user.id)['balance']}
        db.commit()
        return result
    if in_use(db, user.id, coach_id):                            # 3) 같은 코치 사용 중(D7)
        db.rollback()
        raise HTTPException(409, {'code': 'PASS_IN_USE', 'message': '이 코치의 이용권을 이미 사용 중이에요.'})
    try:                                                         # 4) 교환 가능 lot만 만료 빠른 순으로 잠금·차감
        spend, _ = rewards.spend_points(db, user.id, product.price, 'coach_pass', 'coach', coach_id, order='exchange')
    except rewards.Insufficient as error:
        db.rollback()
        raise HTTPException(409, {'code': 'INSUFFICIENT_POINTS',
                                  'message': f'실물 교환에 쓸 수 있는 포인트가 {error.needed}P 부족해요.'}) from None
    row = Pass(user_id=user.id, coach_id=coach_id, product_id=product.id, sessions=catalog.COACH_SESSIONS,
               points=product.price, status='in_use', purchased_at=rewards.now(), spend_id=spend.id, idem_key=idem_key)
    db.add(row)                                                  # 5) 이용권
    db.flush()
    result = {**pass_json(db, row, coach), 'balance': rewards.balance_info(db, user.id)['balance']}
    db.commit()
    log.info('reward coach pass %s %d', coach_id, product.price)
    return result


def my_passes(db, user):
    require_enabled()
    rows = list(db.scalars(select(Pass).where(Pass.user_id == user.id).order_by(Pass.purchased_at.desc())))
    result = {'items': [pass_json(db, row) for row in rows], 'notice': 'CaloDetect는 카카오톡 대화 내용을 보지 않아요. 연락처는 시연용이에요.'}
    db.commit()
    return result


def admin_list(db):
    require_enabled()
    from ..models_rewards import RewardNickname as Nickname
    nicknames = {n.user_id: n.nickname for n in db.scalars(select(Nickname))}
    rows = db.scalars(select(Pass).order_by(Pass.purchased_at.desc()).limit(200))
    return {'items': [{'id': r.id, 'user_id': r.user_id, 'nickname': nicknames.get(r.user_id), 'coach_id': r.coach_id,
                       'points': r.points, 'status': r.status, 'purchased_at': rules.as_aware(r.purchased_at),
                       'closed_at': rules.as_aware(r.closed_at)} for r in rows]}


def admin_refund(db, pass_id):
    """코치 연락 불가 같은 예외의 관리자 수동 환불: allocation 역순 복원, status='refunded'."""
    require_enabled()
    from .reward_exchange import refund_spend
    row = db.get(Pass, pass_id)
    if row is None:
        raise HTTPException(404, '이용권을 찾을 수 없습니다.')
    rewards.account(db, row.user_id, lock=True)
    row = db.scalar(select(Pass).where(Pass.id == pass_id).with_for_update().execution_options(populate_existing=True))
    if row.status != 'in_use':
        db.rollback()
        raise HTTPException(409, '사용 중인 이용권만 환불할 수 있어요.')
    refund_spend(db, row.user_id, row.spend_id, 'coach_pass', row.id)
    row.status, row.closed_at = 'refunded', rewards.now()
    db.commit()
    log.info('reward coach pass refunded %s %d', row.coach_id, row.points)
    return {'id': row.id, 'status': row.status, 'points': row.points}


def spend_label(db, spend):
    coach = db.get(Coach, spend.ref_id) if spend.ref_id else None
    return f'{coach.name if coach else "코치"} 코칭 이용권 구매'
