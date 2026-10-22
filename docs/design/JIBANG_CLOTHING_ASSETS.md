# 지방이 착용 이미지 제작 기록

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
