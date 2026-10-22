"""리워드몰 v1.3 카탈로그 시드(지시서 §5). 가격·정가·평점·리뷰 수·만족도·제휴사는 모두 시연용 자리표시다.

- 기존 상품 ID와 가격은 그대로 둔다. 시드는 이름·하위분류·옵션·max_qty·listed·collab_brand·content만 갱신한다.
- 문구는 §8 표현 규칙(효능·기능 암시 금지)을 통과한 것만 넣는다. 시안 문구를 바꾼 곳은 주석으로 남긴다.
- 이미지는 키만 둔다(frontend/public/rewards/<키>). 2026-10-22 사용자 결정으로 시안 이미지를 그대로 쓴다
  (지시서 §5-3과 다름: 사진 안 '동영상 보기' 버튼·손글씨·로고 포함, 내부 시연용). 파일이 없으면 화면이 자리표시 그림을 쓴다.
"""

COLLAB = '태극사계'
MEAL_TAGS = [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '건강한 한 끼', 'tone': 'gold'}]


# 시안 이미지: 썸네일 수, 상세 광고 이미지 유무·바탕색(시안 adBg).
GALLERY = {'pita_sandwich': (5, '#F7EEE3'), 'energy_bar': (5, '#F7EEE3'), 'energy_drink': (5, '#F5F1E8'), 'greek_yogurt': (5, '#F7EEE3'),
           'protein_bar': (5, '#F7EEE3'), 'chicken_sandwich': (5, '#F7EEE3'), 'salad_box': (5, '#F7EEE3'), 'bristick15': (4, '#F4EFE7'),
           'ginseng_daily10': (0, '#F4EBDF'), 'ginseng_premium30': (0, '#1E1915')}


def images(product_id):
    base = f'products/{product_id}'
    thumbs, detail_bg = GALLERY.get(product_id, (0, None))
    return {'hero': f'{base}/hero.jpg', 'thumbs': [f'{base}/t{i}.jpg' for i in range(1, thumbs + 1)],
            'detail': f'{base}/detail.jpg' if detail_bg else None, 'detail_bg': detail_bg}


# (id, 이름, 종류, 가격, 판매, 설명, 하위분류, 정가, 옵션, max_qty, listed, 콜라보, content)
PRODUCTS = (
    ('energy_bar', '고소한 견과 에너지바', 'goods', 120, True, '곡물·견과 에너지바 1개', '간편식', 3900,
     ['오리지널 견과', '크랜베리 믹스'], 1, True, None, {
        'tags': MEAL_TAGS,
        # 시안 "건강한 에너지를 더하세요" → 기능 암시 문구라 상황 묘사로 바꿈(§8)
        'summary': '곡물과 견과로 채우는 든든한 간식 에너지바\n바쁜 일상에 간편하게 챙기는 한 입 간식이에요.',
        'features': [['leaf', '곡물&견과', '오트, 아몬드 등 다양한 견과'], ['bolt', '든든한 간식', '한 개로 채우는 포만감'],
                     ['clock', '간편 휴대', '언제 어디서나 간편하게']],
        'storage': '직사광선을 피해 서늘한 곳에 보관', 'rating': '4.7', 'review_count': '412',
        'satisfaction': [['맛 만족도', 95], ['포만감 만족도', 92], ['재구매 의사', 90]], 'related_ids': [],
        **images('energy_bar')}),
    ('energy_drink', '데일리 에너지 드링크', 'goods', 150, True, '무가당 드링크 1캔', '음료', 4900,
     ['레몬 라임', '베리 부스트'], 1, True, None, {
        # §5-1: 태그 "건강한 한 끼" → "가벼운 음료"
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '가벼운 음료', 'tone': 'gold'}],
        'summary': '무가당으로 가볍게 마시는\n데일리 에너지 드링크',
        # 시안 "비타민 B군 함유 · 상쾌한 리프레시" → "무가당 · 0kcal 상쾌한 맛"(§8)
        'features': [['leaf', '무가당', '0g 설탕으로 가볍게'], ['bolt', '상쾌한 맛', '무가당 · 0kcal'],
                     ['clock', '간편 섭취', '언제 어디서나 간편하게']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.6', 'review_count': '412',
        'satisfaction': [['맛 만족도', 95], ['상쾌함 만족도', 92], ['재구매 의사', 89]], 'related_ids': [],
        **images('energy_drink')}),
    ('pita_sandwich', '바질치즈 프로틴 피타샌드', 'goods', 150, True, '바질치즈 피타샌드 1개', '간편식', 4900,
     ['바질치즈', '바질토마토치즈'], 1, True, None, {
        'tags': MEAL_TAGS,
        'summary': '향긋한 바질과 고소한 치즈가 가득한\n맛있고 든든한 고단백 피타샌드',
        'features': [['dumbbell', '단백질 15g', '든든한 고단백'], ['leaf', '포만감 UP', '한 끼 식사로 충분'],
                     ['clock', '간편한 한 끼', '전자레인지 1분']],
        'storage': '냉동보관 (-18°C 이하)', 'rating': '4.8', 'review_count': '532',
        'satisfaction': [['맛 만족도', 96], ['포만감 만족도', 93], ['재교환 의사', 91]], 'related_ids': [],
        **images('pita_sandwich')}),
    ('greek_yogurt', '플레인 그릭요거트', 'goods', 180, True, '플레인 그릭요거트 1개', '간편식', 4900,
     ['베리 토핑', '그래놀라 토핑'], 1, True, None, {
        'tags': MEAL_TAGS,
        'summary': '꾸덕한 식감과 깔끔한 맛의\n고단백 플레인 그릭요거트',
        'features': [['dumbbell', '단백질 간식', '단백질 10g'], ['leaf', '깔끔한 플레인', '무가당의 순수한 맛'],
                     ['clock', '아침 추천', '가볍게 시작하는 한 끼']],
        'storage': '냉장보관 (0~10°C)', 'rating': '4.8', 'review_count': '412',
        'satisfaction': [['맛 만족도', 96], ['포만감 만족도', 93], ['재구매 의사', 92]], 'related_ids': [],
        **images('greek_yogurt')}),
    ('ginseng_daily10', '진한홍삼 데일리 10포', 'goods', 180, True, '스틱 홍삼 10포', '브랜드 콜라보', 18000,
     [], 3, True, COLLAB, {
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '데일리 케어', 'tone': 'soft'}],
        # 시안 "홍삼 한 포로 시작하는 건강한 하루의 루틴" → 기능 암시라 구성 설명으로 바꿈(§8)
        'summary': '바쁜 일상 속, 간편하게 챙기는\n하루 한 포 스틱 홍삼 10포 구성',
        'features': [['clock', '하루 한 포', '매일 간편하게 챙기는 구성'], ['leaf', '스틱 타입', '언제 어디서나 간편 섭취'],
                     ['gift', '선물용 추천', '소중한 분께 마음을 전해요']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.8', 'review_count': '1,254',
        'satisfaction': [['맛 만족도', 96], ['간편한 섭취', 98], ['선물 만족도', 94], ['재구매 의사', 97]],
        'related_ids': ['ginseng_premium10', 'ginseng_daily30'], **images('ginseng_daily10')}),
    ('protein_bar', '고단백 프로틴바', 'goods', 200, True, '단백질 20g 프로틴바 1개', '간편식', 5900,
     ['초코 크런치', '곡물 넛츠'], 1, True, None, {
        'tags': MEAL_TAGS,
        # 시안 "건강한 에너지" "활력 있는 에너지" → 기능 암시라 상황 묘사로 바꿈(§8)
        'summary': '단백질 20g으로 채우는 든든한 프로틴 간식\n맛있게 즐기는 고단백 간식을 언제 어디서나.',
        'features': [['dumbbell', '단백질 20g', '든든한 고단백 간식'], ['bolt', '든든한 간식', '바쁜 날 간편하게'],
                     ['clock', '간편 섭취', '언제 어디서나']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.7', 'review_count': '412',
        'satisfaction': [['맛 만족도', 95], ['포만감 만족도', 92], ['재구매 의사', 90]], 'related_ids': [],
        **images('protein_bar')}),
    ('chicken_sandwich', '통닭가슴살 샌드위치', 'goods', 250, True, '통밀빵 닭가슴살 샌드위치 1개', '간편식', 5900,
     ['허브치킨', '에그치킨'], 1, True, None, {
        'tags': MEAL_TAGS,
        'summary': '단백질을 맛있게 채우는 든든한\n닭가슴살 샌드위치',
        'features': [['dumbbell', '고단백 한 끼', '닭가슴살 20g'], ['leaf', '신선한 채소', '신선한 야채 듬뿍'],
                     ['clock', '간편한 식사', '언제 어디서나']],
        'storage': '냉장보관 (0~10°C)', 'rating': '4.8', 'review_count': '532',
        'satisfaction': [['맛 만족도', 96], ['포만감 만족도', 94], ['재구매 의사', 92]], 'related_ids': [],
        **images('chicken_sandwich')}),
    ('bristick15', '브리스틱 15포', 'goods', 290, True, '스틱 홍삼 15포', '브랜드 콜라보', 29000,
     [], 1, True, COLLAB, {
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '브랜드 콜라보', 'tone': 'dark'}],
        # 시안 "오늘의 활력" → "간편하게 챙기는 하루 한 포"(§8 교체 예)
        'summary': '바쁜 일상 속,\n간편하게 챙기는 하루 한 포',
        'features': [['clock', '간편 스틱', '언제 어디서나 간편하게'], ['leaf', '하루 한 포', '15포 구성'],
                     ['shield', '부담 없는 섭취', '꼼꼼하게 엄선한 원료']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.7', 'review_count': '128', 'satisfaction': [],
        'related_ids': ['bristick30'], **images('bristick15')}),
    ('salad_box', '프레시 샐러드 박스', 'goods', 300, True, '채소·단백질 샐러드 1팩', '간편식', 6900,
     ['그릴드 치킨', '에그 & 퀴노아'], 1, True, None, {
        'tags': MEAL_TAGS,
        'summary': '채소와 단백질을 한 번에 담은\n신선한 샐러드 박스',
        'features': [['leaf', '채소 가득', '신선한 채소 듬뿍'], ['dumbbell', '단백질 균형', '닭가슴살·계란 등'],
                     ['clock', '가벼운 한 끼', '맛있고 든든하게']],
        'storage': '냉장보관 (0~5°C)', 'rating': '4.8', 'review_count': '412',
        'satisfaction': [['맛 만족도', 97], ['신선도 만족도', 95], ['포만감 만족도', 93]], 'related_ids': [],
        **images('salad_box')}),
    ('ginseng_premium30', '진한홍삼 프리미엄 30포', 'goods', 750, True, '프리미엄 스틱 홍삼 30포', '브랜드 콜라보', 75000,
     [], 3, True, COLLAB, {
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '프리미엄 선물', 'tone': 'gold'}],
        # 시안 "매일의 건강을 위한 특별한 선택" → 기능 암시라 선물 설명으로 바꿈(§8)
        'summary': '진하게 담은 프리미엄 홍삼,\n소중한 분께 전하는 특별한 선물',
        'features': [['shield', '프리미엄 패키지', '고급스러운 선물용 패키지'], ['leaf', '30포 구성', '하루 한 포 간편 구성'],
                     ['gift', '선물 추천', '소중한 분을 위한 특별한 선물']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.9', 'review_count': '328', 'satisfaction': [],
        'related_ids': ['ginseng_premium10', 'ginseng_lady30'], **images('ginseng_premium30')}),
    # 콜라보 라인업(listed=false): 몰 그리드에는 없고 상세·신청·기획전에서만 연다.
    ('ginseng_premium10', '진한홍삼 프리미엄 10포', 'goods', 250, True, '프리미엄 스틱 홍삼 10포', '브랜드 콜라보', 25000,
     [], 1, False, COLLAB, {
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '브랜드 콜라보', 'tone': 'dark'}],
        'summary': '더 진하게 담은\n프리미엄 홍삼 10포 구성', 'line': '더 진하게, 더 특별한 하루',
        'features': [['shield', '프리미엄 패키지', '선물용 패키지'], ['leaf', '10포 구성', '하루 한 포 간편 구성'],
                     ['gift', '선물 추천', '가볍게 전하는 마음']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.8', 'review_count': '214', 'satisfaction': [],
        'related_ids': ['ginseng_premium30'], **images('ginseng_premium10')}),
    ('ginseng_daily30', '진한홍삼 데일리 30포', 'goods', 450, True, '스틱 홍삼 30포', '브랜드 콜라보', 45000,
     [], 1, False, COLLAB, {
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '데일리 케어', 'tone': 'soft'}],
        # 시안 "매일 더 건강한 일상을 위해" → 구성 설명으로 바꿈(§8)
        'summary': '하루 한 포 스틱 홍삼\n넉넉한 30포 데일리 구성', 'line': '넉넉한 30포 데일리 구성',
        'features': [['clock', '하루 한 포', '매일 간편하게 챙기는 구성'], ['leaf', '30포 구성', '한 달 분량'],
                     ['gift', '선물용 추천', '소중한 분께 마음을 전해요']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.8', 'review_count': '406', 'satisfaction': [],
        'related_ids': ['ginseng_daily10'], **images('ginseng_daily30')}),
    ('bristick30', '브리스틱 30포', 'goods', 550, True, '스틱 홍삼 30포', '브랜드 콜라보', 59000,
     [], 1, False, COLLAB, {
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '브랜드 콜라보', 'tone': 'dark'}],
        # 시안 "꾸준한 건강 관리를 위한 넉넉한 구성" → 구성 설명으로 바꿈(§8)
        'summary': '간편하게 챙기는 하루 한 포\n넉넉한 30포 구성', 'line': '넉넉한 30포 구성',
        'features': [['clock', '간편 스틱', '언제 어디서나 간편하게'], ['leaf', '하루 한 포', '30포 구성'],
                     ['shield', '부담 없는 섭취', '꼼꼼하게 엄선한 원료']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.7', 'review_count': '96', 'satisfaction': [],
        'related_ids': ['bristick15'], **images('bristick30')}),
    ('ginseng_lady30', '진한홍삼 더 레이디 30포', 'goods', 600, True, '스틱 홍삼 30포', '브랜드 콜라보', 75000,
     [], 1, False, COLLAB, {
        'tags': [{'t': 'CaloPoint 전용', 'tone': 'green'}, {'t': '브랜드 콜라보', 'tone': 'dark'}],
        # 시안 "여성을 위한 데일리 홍삼" → "데일리 홍삼 30포 구성"(§8 교체 예)
        'summary': '하루 한 포 스틱 홍삼\n데일리 홍삼 30포 구성', 'line': '데일리 홍삼 30포 구성',
        'features': [['clock', '하루 한 포', '매일 간편하게 챙기는 구성'], ['leaf', '30포 구성', '한 달 분량'],
                     ['gift', '선물용 추천', '소중한 분께 마음을 전해요']],
        'storage': '직사광선을 피해 실온 보관', 'rating': '4.8', 'review_count': '187', 'satisfaction': [],
        'related_ids': ['ginseng_premium30'], **images('ginseng_lady30')}),
    # 비활성(§5-2): AI 서비스 탭 제거, 전문 코칭은 코치별 이용권(M4)으로 전환.
    ('ai_report', 'AI 식단 리포트', 'ai', 300, False, '준비 중이에요', None, None, [], 1, False, None, {}),
    ('pro_coaching', '영양사 1:1 코칭', 'pro', 1000, False, '준비 중이에요', None, None, [], 1, False, None, {}),
)
RETIRED = frozenset({'ai_report', 'pro_coaching'})

# M4: 코치별 7회 이용권(category='pro'). 판매 여부는 REWARD_COACHING_ENABLED가 정한다.
COACH_PRODUCTS = (('coach_kim', 'kim', '김지윤 코치 · 7회 코칭'), ('coach_park', 'park', '박재현 코치 · 7회 코칭'),
                  ('coach_lee', 'lee', '이수민 코치 · 7회 코칭'))
COACH_PRICE = 700
COACH_SESSIONS = 7

# 프로모션 슬라이더(M3) 순서: 기획전 → 피타샌드 → 샐러드 박스 → 에너지 드링크 → 프리미엄 30포. 문구는 텍스트로 쓴다.
PROMOTIONS = (
    {'id': 'collab', 'target': 'collab', 'eyebrow': 'SPECIAL COLLABORATION', 'title': 'CaloPoint × 태극사계\n프리미엄 홍삼을 포인트로',
     'desc': '홍삼 브랜드와 함께하는 시연용 기획전. 쌓아둔 포인트로 프리미엄 홍삼을 만나보세요.', 'cta': '콜라보 제품 둘러보기',
     'image': 'products/bristick15/hero.jpg', 'theme': 'light'},
    {'id': 'pita', 'target': 'pita_sandwich', 'eyebrow': 'THIS WEEK', 'title': '맛있는 건강 습관,\n바질치즈 프로틴 피타샌드',
     'desc': '단백질 15g의 든든한 한 끼를 포인트로 받아 보세요.', 'cta': '피타샌드 보러가기', 'theme': 'light'},
    {'id': 'salad', 'target': 'salad_box', 'eyebrow': 'FRESH MEAL', 'title': '채소와 단백질을\n한 번에 담은 샐러드',
     'desc': '프레시 샐러드 박스 · 그릴드 치킨 / 에그 & 퀴노아', 'cta': '샐러드 박스 보러가기', 'theme': 'light'},
    {'id': 'drink', 'target': 'energy_drink', 'eyebrow': 'REFRESH', 'title': '무가당으로 가볍게,\n데일리 에너지 드링크',
     'desc': '레몬 라임 · 베리 부스트 2가지 맛', 'cta': '에너지 드링크 보러가기', 'theme': 'light'},
    {'id': 'premium30', 'target': 'ginseng_premium30', 'eyebrow': 'PREMIUM GIFT', 'title': '소중한 분을 위한\n진한홍삼 프리미엄 30포',
     'desc': '목표로 정해 두면 진행률과 예상 달성일을 볼 수 있어요.', 'cta': '프리미엄 30포 보러가기', 'theme': 'dark'},
)

# 콜라보 기획전 추천 3종 설명(§7-6). 시안 "깊은 홍삼의 활력" 등은 구성 설명으로 바꿈(§8).
COLLAB_PICKS = (('bristick15', '간편하게 하루 한 포 챙기는 스틱 15포'), ('ginseng_daily10', '매일 즐기는 진한 홍삼 스틱 10포'),
                ('ginseng_premium30', '소중한 분을 위한 프리미엄 선물 세트'))
COLLAB_LINEUP = ('bristick30', 'bristick15', 'ginseng_daily10', 'ginseng_premium30', 'ginseng_premium10', 'ginseng_daily30',
                 'ginseng_lady30')
# 기획전 화면 이미지(시안). 추천 카드·전체 라인업 썸네일은 상품 대표 사진과 다른 구도라 따로 둔다.
COLLAB_IMAGES = {'banner': 'collab/banner.jpg', 'story': 'collab/story.jpg', 'event': 'collab/event.jpg'}
COLLAB_PICK_IMAGES = {pid: f'collab/pick_{pid}.jpg' for pid in ('bristick15', 'ginseng_daily10', 'ginseng_premium30')}
COLLAB_LINEUP_IMAGES = {pid: f'collab/lineup_{pid}.jpg' for pid in ('bristick15', 'ginseng_daily10', 'ginseng_premium30')}
