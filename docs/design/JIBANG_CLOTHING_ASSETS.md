# 지방이 착용 이미지 제작 기록

## 2026-10-27 현재 레벨에 맞는 착용 이미지

사용자 요청: 옷을 입거나 몰에서 미리 볼 때 현재 지방이의 성장 단계와 다른 몸이 표시되지 않게 한다. 전용 의상의 LV.1·2, 정원사 코스튬의 LV.1·2·3, 탐험가 코스튬의 LV.1·2·3·4 착용 이미지 9개를 추가 제작한다. 기존 운동복과 이미 있는 LV.3~5 착용 파일은 보존한다.

`dressedSprite`는 LV.1~5에서 정확히 현재 레벨의 이미지·자세 메타데이터를 선택한다. 누락 레벨을 첫 번째 등록 레벨로 대체하던 동작을 제거했다. 몰 미리보기·방·홈·온보딩 등 `JibangFigure` 사용 화면에 공통 적용한다. 구매 제한·가격·아이템 ID·장착 API는 변경하지 않는다.

생성 도구: 내장 image_gen 편집, transparent_background=true. 첫 입력은 해당 레벨의 원본 몸, 두 번째는 해당 의상 스타일 참고. 첫 입력의 체형·표정·팔다리·머리 형태·비율을 유지하도록 요청하고, 두 번째 이미지의 체형을 복사하지 않게 명시했다. LV.1은 낮고 넓게 누운 몸과 시큰둥한 눈, LV.2는 짧고 둥근 몸·닫힌 입·원래 팔 위치를 유지한다. 배경·부유 장식은 제외해 기존 앱 장식을 재사용한다.

새 파일: `sailor-lv1.png`, `sailor-lv2.png`, `garden-lv1.png`, `garden-lv2.png`, `garden-lv3.png`, `explorer-lv1.png`, `explorer-lv2.png`, `explorer-lv3.png`, `explorer-lv4.png` (frontend/public/jibang/clothing).

검증: 의상/레벨 선택·누락 레벨 방어·원본 몸 테스트 총 5개 통과, production build 통과. Chrome 테스트 화면에 기본 몸과 의상 4종을 LV.1~5로 나란히 렌더링(25개), 이미지 누락 없음과 레벨별 체형 대조 확인. 새 PNG 9개가 빌드 출력과 SHA256 일치. 실제 계정 구매·원장 변경은 이 이미지 검증에서 수행하지 않았다.

## 2026-10-26 탐험가 코스튬 시안

- 사용자 선택: 탐험가 — 사파리 의상과 가방. 내장 `image_gen` 편집 모드, `transparent_background=true` 사용.
- 입력: `frontend/public/jibang/lv5.png`. 출력: `frontend/public/jibang/clothing/explorer-lv5-concept.png`. 사용자 승인 가격 200P로 `costume_explorer`에 연결. 현재 LV.5 착용 이미지를 모든 레벨에서 공통 사용하며 기존 의상 이미지 fallback 방식으로 표시한다.
- 프롬프트: Use case: identity-preserve. Transparent full-body CaloDetect Jibang explorer sprite. Preserve exact cream bean mascot, happy closed eyes, smiling mouth, pink cheeks, leaf sprout, raised right arm, feet, proportions and warm watercolor style with dark brown outlines. Dress in fitted sandy khaki short-sleeved safari shirt with two chest pockets, matching shorts, brown belt and small brown crossbody expedition satchel, sage accents. No hat; keep sprout clear. Bare hands and feet, curved seams and watercolor fabric folds. Remove background, hearts and sparkles. One centered full-body character, minimal transparent margins, genuinely transparent background, no text.

2026-10-22 사용자 요청으로 제작. 내장 `image_gen`의 이미지 편집 모드와 `transparent_background=true`를 사용했다. 원본 몸 이미지는 보존하고 `frontend/public/jibang/clothing/`에 투명 PNG 11개를 추가했다.

운동복은 정면·LV.1~5, 전용 의상은 착용 가능한 LV.3~5, 코스튬은 LV.4~5에 대응한다. `frontend/src/jibangClothing.js`가 이미지 경로를 관리한다. 옷을 벗기면 기존 레벨 이미지를 사용한다. 모자·안경·운동화·장식은 기존 SVG 오버레이를 재사용한다. 의상 미리보기에서 해당 레벨 변형이 없으면 최초 착용 가능한 레벨의 변형을 보여준다.

운동복은 기존 prop 슬롯·아이템 ID를 유지한다. 새 의상 착용 시 다른 슬롯의 몸통 의상만 같은 트랜잭션에서 벗기며, 물병 같은 일반 소품·아이템 소유권은 유지한다. 기존 두 옷 장착 상태의 표시 우선순위는 outfit 슬롯이다.

## 최종 프롬프트 세트

각 항목의 입력은 `frontend/public/jibang/`의 해당 원본 이미지다. 결과물은 얼굴·자세·배색을 대조해 선택했다. 생성 이미지 특성상 원본 픽셀 단위의 동일성을 보장하지 않는다.

### workout-lv5.png

Use case: identity-preserve. Asset: transparent PNG game character sprite for CaloDetect.
Edit target: attached lv5.png, the cream-colored bean mascot Jibang with sprout on its head, closed happy eyes and raised right arm.
Dress THIS EXACT character in a fitted coral-orange sleeveless athletic jersey with ivory piping and dark teal sporty shorts. Draw clothing as part of the illustration with soft watercolor shading, rounded seams and cloth folds that conform to the existing rounded belly. Armholes curve around the existing arms; hands/arms must emerge naturally in front of the outfit. Shorts have two separate openings above the bare little feet. Keep the face, sprout, pose, proportions, anatomy and dark brown hand-drawn outlines identical. Preserve the exact placement of facial features and hands relative to the body. Do not add headbands, hats, shoes, props or text. Remove the pink background, sparkles and floating hearts; output ONLY the full dressed character on genuinely transparent background, with all of head and feet visible. Tightly frame the character; minimal transparent margins. Existing cute warm hand-painted style, not flat vector.

### workout-lv4.png

Use case: identity-preserve. Edit target: attached lv4.png, existing CaloDetect Jibang mascot. Create a transparent PNG game sprite, the SAME mascot actually wearing coral-orange sleeveless athletic jersey with ivory piping, dark teal shorts; no hat or headband. Clothes wrap around the round body with curved hems, sewn edges, subtle watercolor folds and shadow under arms. Preserve EXACT original silhouette/proportions, head/face/sprout, expressions, pose, arm/hand and foot locations. Bare arms in front of the cloth, distinct sleeve openings, bare feet visible below shorts. Match warm cream watercolor painting, dark brown sketch outline. Full body head to feet, minimal transparent margin, genuinely transparent background. Remove background, floating hearts, sparkle decorations and ground shadow. No text, no props. Only change clothing, do not redesign the character.

### workout-lv3.png

Use case: identity-preserve. Edit target: attached lv3.png, existing CaloDetect Jibang mascot. Create a transparent PNG game sprite, the SAME mascot actually wearing coral-orange sleeveless athletic jersey with ivory piping, dark teal shorts; no hat or headband. Clothes wrap around the round body with curved hems, sewn edges, subtle watercolor folds and shadow under arms. Preserve EXACT original silhouette/proportions, head/face/sprout, expressions, pose, arm/hand and foot locations. Bare arms in front of the cloth, distinct sleeve openings, bare feet visible below shorts. Match warm cream watercolor painting, dark brown sketch outline. Full body head to feet, minimal transparent margin, genuinely transparent background. Remove background, floating hearts, sparkle decorations and ground shadow. No text, no props. Only change clothing, do not redesign the character.

### workout-lv2.png

Use case: identity-preserve. Edit target attached lv2.png, existing Jibang mascot from CaloDetect. Dress THIS EXACT character in fitted coral-orange sleeveless sports jersey with ivory piping and dark teal shorts. Keep round wide body, small feet and bent arm. Preserve same identity, expression, proportions, face and original pose. Clothing must curve around the existing body with natural armhole openings, brown sketched seams, rounded cloth hems, folds and soft watercolor shadow. Arms/hands exposed naturally in front of clothes; feet visible below the two shorts openings. Same creamy watercolor illustration and brown outlines. No headband, no hat, no shoes, no props, no text. Remove original background, ground shadow and floating decorations. Output one entire dressed character only, tightly framed with minimal transparent margins, truly transparent PNG.

### workout-lv1.png

Use case: identity-preserve. Edit target attached lv1_gloomy.png, existing Jibang mascot from CaloDetect. Dress THIS EXACT character in fitted coral-orange sleeveless sports jersey with ivory piping and dark teal shorts. Keep the wide squashed lying body, low little feet, sad face and bent arm. Fit jersey around this wide belly; do NOT turn it upright. Preserve same identity, expression, proportions, face and original pose. Clothing must curve around the existing body with natural armhole openings, brown sketched seams, rounded cloth hems, folds and soft watercolor shadow. Arms/hands exposed naturally in front of clothes; feet visible below the two shorts openings. Same creamy watercolor illustration and brown outlines. No headband, no hat, no shoes, no props, no text. Remove original background, ground shadow and floating decorations. Output one entire dressed character only, tightly framed with minimal transparent margins, truly transparent PNG.

### workout-front.png

Use case: identity-preserve. Edit target attached front.png, existing Jibang mascot from CaloDetect. Dress THIS EXACT character in fitted coral-orange sleeveless sports jersey with ivory piping and dark teal shorts. Keep frontal face, both downwards arms and original round body. Preserve same identity, expression, proportions, face and original pose. Clothing must curve around the existing body with natural armhole openings, brown sketched seams, rounded cloth hems, folds and soft watercolor shadow. Arms/hands exposed naturally in front of clothes; feet visible below the two shorts openings. Same creamy watercolor illustration and brown outlines. No headband, no hat, no shoes, no props, no text. Remove original background, ground shadow and floating decorations. Output one entire dressed character only, tightly framed with minimal transparent margins, truly transparent PNG.

### sailor-lv3.png

Use case: identity-preserve. Edit target attached lv3.png: existing cream bean Jibang mascot of CaloDetect. Draw THIS SAME character actually wearing a fitted sky-blue sailor shirt with ivory collar, a small ivory embroidered star on chest, blue scarf tied at side of neck, navy shorts. Keep EXACT head, expression, face, sprout if present, body proportions and pose including raised right arm and feet locations. Sleeves must wrap upper arms, bare hands emerge naturally in front of the outfit. Clothes wrap belly with gently curved hems, hand-drawn seams and watercolor fabric folds/shadows matching the original warm creamy watercolor illustration with dark brown outlines. Head and feet all visible; no shoes, no props, no text, no headwear. Remove background, ground shadow, floating hearts and sparkles. Full-body dressed character only, minimal transparent margins, truly transparent PNG.

### sailor-lv4.png

Use case: identity-preserve. Edit target attached lv4.png: existing cream bean Jibang mascot of CaloDetect. Draw THIS SAME character actually wearing a fitted sky-blue sailor shirt with ivory collar, a small ivory embroidered star on chest, blue scarf tied at side of neck, navy shorts. Keep EXACT head, expression, face, sprout if present, body proportions and pose including raised right arm and feet locations. Sleeves must wrap upper arms, bare hands emerge naturally in front of the outfit. Clothes wrap belly with gently curved hems, hand-drawn seams and watercolor fabric folds/shadows matching the original warm creamy watercolor illustration with dark brown outlines. Head and feet all visible; no shoes, no props, no text, no headwear. Remove background, ground shadow, floating hearts and sparkles. Full-body dressed character only, minimal transparent margins, truly transparent PNG.

### sailor-lv5.png

Use case: identity-preserve. Edit target: attached lv5.png, existing CaloDetect Jibang mascot. Create a transparent PNG game sprite, the SAME mascot actually wearing soft sky-blue short-sleeved fitted sailor-style shirt, ivory collar, small ivory star embroidered at center chest, a little matching blue scarf tied at the side of the collar, and navy blue shorts; no hat. Clothes wrap around the round body with curved hems, sewn edges, subtle watercolor folds and shadow under arms. Preserve EXACT original silhouette/proportions, head/face/sprout, expressions, pose, arm/hand and foot locations. Bare arms in front of the cloth, distinct sleeve openings, bare feet visible below shorts. Match warm cream watercolor painting, dark brown sketch outline. Full body head to feet, minimal transparent margin, genuinely transparent background. Remove background, floating hearts, sparkle decorations and ground shadow. No text, no props. Only change clothing, do not redesign the character.

### garden-lv4.png

Use case: identity-preserve. Edit target attached lv4.png: existing cream bean Jibang mascot of CaloDetect. Draw THIS SAME character actually wearing a cream short-sleeved undershirt and sage-green gardener short overalls, tan straps, two little brass buttons, a cream chest pocket embroidered with a tiny green sprout, rolled shorts hems. No hat. Keep EXACT head, expression, face, sprout if present, body proportions and pose including raised right arm and feet locations. Sleeves must wrap upper arms, bare hands emerge naturally in front of the outfit. Clothes wrap belly with gently curved hems, hand-drawn seams and watercolor fabric folds/shadows matching the original warm creamy watercolor illustration with dark brown outlines. Head and feet all visible; no shoes, no props, no text, no headwear. Remove background, ground shadow, floating hearts and sparkles. Full-body dressed character only, minimal transparent margins, truly transparent PNG.

### garden-lv5.png

Use case: identity-preserve. Edit target attached lv5.png: existing cream bean Jibang mascot of CaloDetect. Draw THIS SAME character actually wearing a cream short-sleeved undershirt and sage-green gardener short overalls, tan straps, two little brass buttons, a cream chest pocket embroidered with a tiny green sprout, rolled shorts hems. No hat. Keep EXACT head, expression, face, sprout if present, body proportions and pose including raised right arm and feet locations. Sleeves must wrap upper arms, bare hands emerge naturally in front of the outfit. Clothes wrap belly with gently curved hems, hand-drawn seams and watercolor fabric folds/shadows matching the original warm creamy watercolor illustration with dark brown outlines. Head and feet all visible; no shoes, no props, no text, no headwear. Remove background, ground shadow, floating hearts and sparkles. Full-body dressed character only, minimal transparent margins, truly transparent PNG.

### workout-front.png 배경 정리

undefined
