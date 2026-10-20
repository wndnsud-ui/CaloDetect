# 리워드(CaloPoint·Growth) 착수 점검과 구현 대조

근거: `docs/rules/CaloDetect_Codex_리워드_업무지시서_20261019_v3_AI경고문추가.md`(이하 지시서), 기획안 v4 · 브랜치 `feature/rewards` · 점검일 2026-10-20

## 범위

- 사용자 결정(2026-10-20): **Stage A와 B를 한 브랜치에서 함께 구현**. 지시서 §1은 Stage마다 별도 PR·병합 후 다음 Stage를 요구하므로 이 점이 지시서와 다르다. Stage C(교환·쿠폰함)는 구현하지 않았다(경로·테이블·화면 없음).
- C1 승인: ROADMAP·PENDING에 기록이 없어 차단 대상이었으나, 사용자가 2026-10-20 범위 승인과 migration 작성을 승인했다.

## §0 착수 전 확인 C1~C13

| ID | 결과 | 근거 |
|---|---|---|
| C1 | 기록 없음 → **사용자 승인으로 해소**. ROADMAP Backlog의 "포인트" 항목과 PENDING "포인트 사용처 미구현" 갱신 | `docs/planning/ROADMAP.md:9`, `docs/rules/PENDING_DECISIONS.md:11` |
| C2 | 단일 head `20261016_01` → 새 migration `20261019_01`(A)·`20261019_02`(B). 개발 DB 업그레이드·단계별 다운그레이드·재업그레이드 확인 | `backend/migrations/versions/20261016_01_community.py:5` |
| C3 | 식단 생성 경로는 `POST /meals`(`api.py save_meal`)와 채팅 확정(`chat_record.py confirm_draft`) 두 곳. 그 밖에는 시드 스크립트(`seed_demo_meals.py:39`, `seed_community_demo.py:68`)뿐이며 훅을 거치지 않아 보상 없음 | `backend/app/api.py:156`, `backend/app/services/chat_record.py:367` |
| C4 | 식단 삭제 경로 없음. 수정은 섭취 비율(`PUT /meals/items/{id}/consumption`)만 있고 회수 대상 아님. 회수 함수(`revoke_lot`)는 커뮤니티 반응 취소·게시물 삭제에 연결 | `backend/app/consumption_api.py:42` |
| C5 | 채팅 첨부는 `image_uploads`를 참조하고 `analyze_attachment`가 탐지(`detect_image`)를 거친다. 원본 파일은 `storage_key`로 서버에서 읽을 수 있음 → `chat_attachment_id`가 있으면 사진 기록 | `models_chat.py:73`, `services/chat_record.py:285-296` |
| C6 | `image_uploads.image_path`·`detection_logs.image_path`·`chat_attachments.storage_key`를 `IMAGE_STORAGE_DIR` 아래에서 읽음. 저장 비활성(미설정)·파일 없음이면 해시 검사를 건너뛰고 `photo_hash_unavailable` 로그만, 지급은 정상 | `config.py:31`, `services/rewards.py photo_hashes` |
| C7 | 목표 칼로리는 `Profile.data['target_calories']`. **당류·나트륨 기준은 없음**(`analytics.py`가 `sugar_sodium_limits: None`, TBD) → 영양 균형 XP는 판정할 수 없어 **지급하지 않음**. 규칙 함수(`reward_rules.balance_ok`)만 두고 기준이 생기면 연결 | `services/analytics.py:82`, `services/profile.py` |
| C8 | PostgreSQL `default_transaction_isolation = read committed` | `SHOW default_transaction_isolation` |
| C9 | `/community/points/me`·`/community/ranking/weekly`는 `Community.jsx`만 사용. 기존 API 응답은 그대로 두고 Stage B로 화면의 주간 랭킹만 `/rewards/ranking`으로 교체 | `frontend/src/Community.jsx:108-109` |
| C10 | `security.get_admin`으로 관리자 API 가능. Streamlit 관리자 화면 메뉴는 Stage C용이라 이번에 변경 없음 | `backend/app/security.py:81` |
| C11 | 채소 판정 불가(채소 계열 카테고리 `채소/나물`·`생채·무침류` 등 소수). 채소 미션 미구현, §6-5 대체 미션 사용 | `foods.category` 집계 |
| C12 | 닉네임 성격 필드 없음(`users.name`만). 피드·랭킹이 `name`을 노출: `services/community.py:63`(피드), `:268-280`(기존 랭킹). 피드는 바꾸지 않음 | `models.py User` |
| C13 | 이메일 가입(`main.jsx authenticate`)·구글(`POST /auth/social/google/register`, `/auth/social/{provider}/complete`)·카카오(`POST /auth/social/kakao/register`) 모두 가입 직후 `open_session`으로 로그인된 상태로 돌아옴 → 가입 API는 그대로 두고 로그인 뒤 `/rewards/me`의 `nickname_prompt="signup"`으로 닉네임 단계를 띄움. 마이페이지는 `AccountInfo.jsx` + `PUT /users/me`(이름만) | `accounts.py:219`, `social_auth.py:341,422`, `kakao_auth.py:185` |

## 지시서와 다르게 정한 점(구현 판단)

| 항목 | 처리 | 이유 |
|---|---|---|
| Stage 순서 | A+B 한 브랜치 | 사용자 결정(2026-10-20) |
| `reward_grant_batches.skip_reason`, lot·xp의 `batch_id` | 컬럼 추가 | 기록 직후 패널의 "방금 받은 보상"과 미지급 이유(§11-2)를 묶음으로 조회하기 위해 |
| `reward_items.sort_order` | 컬럼 추가 | 몰 표시 순서 |
| 신규 가입자 닉네임 | 가입 단계 확정 전에는 행을 만들지 않음. 재로그인 때 단계를 닫으면 자동 생성 닉네임을 만들고 안내 카드 규칙으로 넘어감 | §6-13 "1회 재표시 후 자동 생성 유지"를 추가 컬럼 없이 구현 |
| 자동 생성 닉네임 형식 | "형용사 음식 4자리"(예: 씩씩한 당근 4821), 5회 중복 시 "형용사음식 6자리" | 2~12자 규칙 안에 들도록 3자·2자 단어만 사용 |
| 첫 식단 온보딩 | 한 번만(idem). 출시 시각 이전에 식단을 기록한 회원은 받지 않음 | 기존 회원 소급 금지(§6-2)와 미설정 시 정상 지급(17-6)을 함께 만족 |
| 커뮤니티 공유 포인트 출처 | `community`(교환 제외) | 반응·공유로 실물을 만드는 경로 차단(§2-5 ①) |
| 반응 취소 시 XP | 같은 양을 `revoke` XP로 회수 | 반응 포인트 회수와 대칭(부정 적립 회수) |
| 닉네임 오류 코드 | 중복·변경 주기 409, 형식·금칙어 422, 분당 한도 429 | §9에 상태 코드 지정 없음 |
| 홈 카드 목표 | 상품 없음(Stage C) → 가장 싼 미보유 구매 가능 아이템(보호권 제외) | §6-12 |
| 요일별 XP 막대 | Streamlit ECharts(`kind: xp_week`, 8502) | 팀 규칙: 차트는 모두 Streamlit ECharts |

## §11-10 시안과 다르게 구현한 문구·수치(PR 대조 표)

| 시안 | 구현 |
|---|---|
| 프로틴바까지 137P · 약 10일 등 고정 수치 | 상품 목표는 Stage C라 없음. 목표·예상 일수는 모두 §6-12 계산(`reward_rules.eta_days`) 결과 |
| 두 번째 사진 끼니 +2P / +10 XP | 같은 묶음 합계(+4P / +20 XP)와 항목별 내역 |
| 채소 포함 끼니 미션 | 대체 미션(사진 2끼·주 5일·월 20일) |
| 레벨별로 체형이 다른 지방이 | 2026-10-20 사용자 결정으로 시안대로 레벨별 몸 사용(지시서 §11-0 해제). 꾸미기 아이템은 몸별 기준점에 맞춤 |
| "LV.5 전용 테마를 적용하면 웹 홈 상단 색도 바뀌어요" | 삭제 |
| "하루 약 60 XP면 2주 무렵" | 계산식 결과 "약 n일" |
| 오늘 XP에서 반응만 "레벨에만 반영" | 식단 공유 XP에도 같은 표시 |
| 쿠폰함·교환·바코드 화면 | Stage C 미구현(탭 숨김) |
| 영양 균형 XP +15 | 당류·나트륨 기준 TBD라 미지급(C7) |

## 검증(2026-10-20)

- Backend 리워드 테스트: SQLite 41통과·PostgreSQL 전용 2건 제외 / `RUN_POSTGRES_TESTS=1` 36통과(동시 구매 #16, 같은 끼니 동시 저장 #17, 같은 닉네임 동시 요청 N7 포함).
- Backend 전체: 기존 실패 3건(`test_recommendation_requires_positive_target`, develop에서도 동일하게 실패) 외 통과.
- Frontend: `npm run build` 성공, node 테스트 9통과(`LEVEL_SPRITES` 같은 정면 이미지, 체형 이미지·금지 문구 미사용 검사 포함).
- 실행 중인 앱(8000·8502·5174)에서 신규 가입 → 닉네임 단계 → 목표 저장 → 식단 기록(+1P·첫 기록 +10P) → 모자 구매(가입 보너스 우선 차감) → 착용 → 성장·랭킹(닉네임 표시) → 내역 확인. 확인용 계정은 확인 후 개발 DB에서 삭제.
- 미검증: 브라우저 화면 1400px·390px 수동 확인(§13 #35~41), 구글·카카오 실제 계정 가입.
