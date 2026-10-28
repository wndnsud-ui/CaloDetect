# 메뉴 배경 이미지

## 현재 적용: 메뉴별 파스텔 지방이 삽화 7종 (2026-10-28)

최신 사용자 요청: 일률적인 베이지색을 메뉴별 파스텔 팔레트로 구분한다. 기존 `*-illustrated.png`를 내장 image_gen으로 색상 편집해 `*-pastel.png`로 저장한다. 캐릭터의 크림색 몸·표정·동작, 소품·구도, 수채화 질감과 빛은 유지한다. 기존 원본은 보존하고 현재 CSS는 새 파일을 참조한다.

| 메뉴 | 새 파일 | 배경 팔레트 |
|---|---|---|
| 홈 | home-pastel.png | 살구·코럴·따뜻한 피치 |
| 식단 기록·칼로T코치 | record-pastel.png | 시폼 민트·맑은 하늘색 |
| 오늘 뭐먹지? | recommend-pastel.png | 피치 핑크·연한 귤색 |
| 식단 관리 | management-pastel.png | 파우더블루·페리윙클 |
| 커뮤니티 | community-pastel.png | 라벤더·라일락·블러시 |
| 리워드몰 | rewards-pastel.png | 버터옐로·허니골드 |
| 내 정보 & 설정 | account-pastel.png | 더스티로즈·연한 모브 |

색상 편집 공통 프롬프트: `Change ONLY the environmental color palette. Clearly visible watercolor wall washes and right-side environmental accents. Preserve original composition, mascot cream body, face, pose, props, watercolor paper texture, soft brown outlines and window lighting. Left 55% stays very light for dark green text. Retain natural food colors. No added UI, text, cropping or subject movement.` 메뉴별 위 팔레트를 추가한다.

### 최초 삽화 제작

사용자 최신 요청으로 메인 메뉴 전체를 첨부한 식단 관리 시안처럼 아이보리·연한 민트·피치 톤의 수채화 삽화로 통일한다. 기존 사진·추상 배경은 보존하며 아래 파일로 대체한다. 식단 기록은 사진/직접 기록·칼로T코치에 공통 적용한다. 기존 제목·버튼·카드·기능은 유지한다.

| 파일 | 장면 |
|---|---|
| home-illustrated.png | 화분 옆에서 손 흔드는 지방이 |
| record-illustrated.png | 카메라로 식사를 촬영하는 지방이 |
| recommend-illustrated.png | 다음 메뉴를 고민하는 지방이 |
| management-illustrated.png | 노트에 기록하는 지방이·책·찻잔 |
| community-illustrated.png | 대화하는 지방이 둘 |
| rewards-illustrated.png | 민트 선물을 든 지방이 |
| account-illustrated.png | 작은 거울과 프로필 노트를 살펴보는 지방이 |

후속 요청으로 ‘내 정보 & 설정’(회원정보·건강 목표·지방이 성장·쿠폰함)에도 전용 배경을 적용한다. 공통 프롬프트에 `small round mint tabletop mirror, open personal profile notebook with pictograms, green pencil, tiny plant, calm self-care`를 추가하고 기존 홈 삽화를 스타일 참조로 사용한다.

제작: 내장 image_gen. 캐릭터 참조는 `frontend/public/jibang/front.png`(크림색 둥근 몸·분홍 볼·갈색 윤곽선·작은 머리 돌기). 왼쪽 60%는 제목을 위한 여백, 오른쪽 35%는 삽화. 배경에는 UI·문자·버튼을 넣지 않는다. 데스크톱은 삽화를 선명하게 표시하고 가장자리·아래만 페이드, 모바일은 농도를 낮춰 글자와 탭의 가독성을 확보한다.

공통 프롬프트: `3:1 panoramic web app background illustration; warm ivory paper, soft morning sunlight diagonal window shadows, translucent pale mint and peach washes; hand-drawn cozy storybook watercolor with delicate brown outlines; Jibang identity from front.png; left 60% quiet ivory, mascot and props in right 35%; no UI, text, logo or watermark.` 각 장면은 위 표에 맞게 지정한다.

## 이전 배경 제작 이력

2026-10-28 사용자 요청. 식단 기록 이외 메인 메뉴 5종에 개별 배경 적용.
밥·식사 사진 제외, 초록색 통일 제외. 배경 소재보다 메뉴 내용이 주인공이어야 하며 색상뿐 아니라 형태·질감도 구분한다.

제작: 내장 image_gen 도구. 최종 PNG는 `frontend/public/images/menu-backgrounds/`에 보존.
기존 잎사귀 배경은 유지. 배경에만 투명 페이드와 낮은 불투명도를 적용하고 콘텐츠·카드는 불투명하게 유지한다.

2026-10-28 최신 사용자 요청: 식단 관리(나의 기록·영양 분석)는 첨부한 아이보리 노트·연필·허브 이미지와 동일한 기존 생성 원본을 `management-notebook-herbs.png`로 복사해 사용한다(2172×724). 앞서 적용한 `home-ambient.png`를 대체하며 기존 배경 파일은 보존한다. 공통 페이드·불투명도·탭·추가 버튼 배치는 유지한다.

## 최종 프롬프트

2026-10-28 후속 사용자 요청: 커뮤니티에 첨부한 민트 선물 상자·아이보리 리본·햇살 이미지와 동일한 기존 생성 원본을 `community-gift.png`로 복사해 적용한다(2172×724). 기존 `community-ambient.png`는 보존하고 공통 페이드·불투명도·화면 배치는 유지한다.

2026-10-28 후속 사용자 요청: ‘오늘 뭐먹지?’ 배경은 첨부한 창가·물컵·허브 이미지와 동일한 기존 생성 원본을 `recommend-window-herbs.png`로 복사해 적용한다(2172×724). 기존 `recommend-ambient.png`는 보존한다. 공통 페이드·불투명도·제목·버튼 배치는 유지한다.

### home-ambient.png
+
+```text
Create a panoramic 3:1 web application BACKGROUND asset. Sophisticated quiet editorial design. Foreground UI must be the protagonist, so keep contrast gentle and left 65% almost empty warm ivory. Visible but restrained details clustered at far right and fading inward. No food, rice, dishes, bowls, text, logos, UI or people. Not a poster, not a product photograph, not a generic pastel gradient cloud. Distinct concept HOME: photographic late morning sunlight casting long diagonal window-frame shadows and delicate plant shadows across cream plaster wall. Natural tactile wall, warm honey and sand tones. Architectural diagonal shadow composition, not bokeh.
+```
+
### recommend-ambient.png
+
+```text
Create a panoramic 3:1 web application BACKGROUND asset. Sophisticated quiet editorial design. Foreground UI must be the protagonist, so keep contrast gentle and left 65% almost empty warm ivory. Visible but restrained details clustered at far right and fading inward. No food, rice, dishes, bowls, text, logos, UI or people. Not a poster, not a product photograph, not a generic pastel gradient cloud. Distinct concept NEXT CHOICE: matte abstract sculptural broad curved ribbons in muted terracotta and peach, forming two softly diverging paths along far right edge. Minimal paper sculpture photographed on warm ivory. Crisp gentle curved edges, soft shadow, no spotlight or central object.
+```
+
### management-ambient.png
+
+```text
Create a panoramic 3:1 web application BACKGROUND asset. Sophisticated quiet editorial design. Foreground UI must be the protagonist, so keep contrast gentle and left 65% almost empty warm ivory. Visible but restrained details clustered at far right and fading inward. No food, rice, dishes, bowls, text, logos, UI or people. Not a poster, not a product photograph, not a generic pastel gradient cloud. Distinct concept DAILY RECORD: pale blue-gray translucent paper sheets, three overlapping rectangular edges with faint unmarked graph-paper grid only at far right, tiny subtly embossed calendar-like squares without numerals or letters. Flat-lay stationery texture, cool powder blue, precise quiet geometry.
+```
+
### community-ambient.png
+
+```text
Create a panoramic 3:1 web application BACKGROUND asset. Sophisticated quiet editorial design. Foreground UI must be the protagonist, so keep contrast gentle and left 65% almost empty warm ivory. Visible but restrained details clustered at far right and fading inward. No food, rice, dishes, bowls, text, logos, UI or people. Not a poster, not a product photograph, not a generic pastel gradient cloud. Distinct concept CONNECTION: a few very fine woven threads in dusty lavender and muted rose, gently crossing into an open loose textile mesh at far right against ivory fabric. Macro textile photography, thin elegant lines, irregular spacious weave, quiet tactile warmth, no circles or bokeh.
+```
+
### rewards-ambient.png
+
+```text
Create a panoramic 3:1 web application BACKGROUND asset. Sophisticated quiet editorial design. Foreground UI must be the protagonist, so keep contrast gentle and left 65% almost empty warm ivory. Visible but restrained details clustered at far right and fading inward. No food, rice, dishes, bowls, text, logos, UI or people. Not a poster, not a product photograph, not a generic pastel gradient cloud. Distinct concept SMALL REWARDS: pale champagne textured paper at right with a thin softly curling satin ribbon and three tiny embossed four-point stars. No gift boxes, no products. Understated restrained celebration, ivory and muted gold with soft peach glints. Delicate angular star detail, not glitter cloud.
+```
+
