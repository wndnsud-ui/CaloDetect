# 데이터 스키마

기존 데이터: class_id 0~149, food_name, category, unit, cal(kcal), carbs/protein/fat/sugar(g), sodium(mg). 새로운 nutrition key를 만들지 않는다. serving multiplier는 unit 기준 배율이다. grams가 없는 행에 grams를 생성하지 않는다.

계획 DB: users(이메일, password_hash, role=user, 동의/시각), user_profiles(신체정보·활동·목표), foods(기존 class_id), nutrition(원본 수치), meals(user_id, KST meal_date, meal_type), meal_items(food_id, nullable detection_log_id, 배율, 계산 snapshot), detection_logs(사용자·image_group_id·bbox·예측/수정·모델 버전), retraining_samples(PENDING/APPROVED/REJECTED, 관리자), recommendation_logs(snapshot, 결과, acted).

Backend Core A 범위에서 단일 migration 체인 20261002_01(기존 회원) → 20261002_02(P0 식단/탐지/QA)을 작성·PostgreSQL 적용했다. 기존 회원 id는 Integer로 유지하고 식단/탐지/이미지는 UUID 문자열을 사용한다. 기존 class_id 0~149를 foods.id로 보존한다.
user_profiles.data에 프로필/칼로리 계산 결과를 저장하고 foods.nutrition/meal_items.nutrition은 기존 CSV 컬럼명 기반 JSON snapshot이다. 새로운 nutrition key 체계를 만들지 않는다. image_uploads는 음식이 탐지되지 않은 이미지에도 사용자 소유권을 보존한다.
Meal/Correction/추천 acted 갱신은 한 DB transaction이며 타 사용자 detection/추천 참조는 거부한다. 승인된 retraining sample은 수정하지 않고 새 correction을 PENDING으로 추가한다. 동의 철회는 PENDING.excluded만 변경한다.
