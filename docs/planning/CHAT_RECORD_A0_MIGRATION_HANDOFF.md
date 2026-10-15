# 챗으로 섭취량 수정(A0) migration 인계 — Backend Core A 담당

작성: 2026-10-15 · 브랜치 `test/chatbot-record` · 기준 커밋 `de87df6`

개발 규칙상 migration은 Backend Core A 담당 범위입니다. 아래 revision은 개인 브랜치에서 TEST-ONLY로 작성·검증했습니다. 팀 저장소에 반영할지, 번호와 연결 위치를 어떻게 할지 결정해 주세요.

## 대상

| 항목 | 내용 |
|---|---|
| 파일 | `backend/migrations/versions/20261015_01_consumption.py` |
| revision / down_revision | `20261015_01` / `20261002_02` |
| 변경 | `meal_items.consumption_ratio` Float NOT NULL 기본 1, CHECK 0~1 · `meal_items.version` Integer NOT NULL 기본 1, CHECK ≥1 · 신규 `mutation_requests` 테이블(unique `user_id, operation, request_id`) |
| 성격 | 추가만 함. 기존 컬럼·제약·행 값 변경 없음. 기존 행은 기본값으로 비율 1, version 1 |
| 모델 | `backend/app/models.py`(컬럼 2개, 신규 모델 import 1줄), `backend/app/models_chat.py`(신규) |

## 검증한 것

- 별도 로컬 DB에서 upgrade → downgrade → upgrade 왕복을 실행했습니다. 기존 값은 보존되고, 되돌린 뒤의 스키마는 변경 전과 같습니다.
- 새 컬럼을 지정하지 않는 기존 INSERT(`POST /meals`, `seed_foods`, `seed_demo_meals`)가 수정 없이 동작합니다.
- 범위를 벗어나는 값(비율 1.5, version 0)은 CHECK 제약으로 거부됩니다.
- 수정 전 백업을 복원하면 합계가 일치합니다.

## 결정이 필요한 것

1. **head 충돌.** 일부 로컬 DB가 저장소에 없는 revision `20261007_03`(커뮤니티 테이블)에 있습니다. 커뮤니티 migration이 저장소에 들어오면 `down_revision`을 그 뒤로 옮겨 하나의 체인으로 만들어야 합니다.
2. **팀 반영 여부와 revision 번호.**
3. **기능 플래그.** `CHAT_RECORD_ENABLED`는 기본 false입니다. migration은 플래그와 관계없이 적용됩니다.

## 함께 반영된 동작 변경 (2026-10-15 사용자 승인)

- `POST /detections/{id}/correction`: 연결된 식단 항목을 `serving_multiplier × consumption_ratio`로 다시 계산하고 `version`을 1 올립니다. 비율 1.0인 기존 행은 이전과 같은 값입니다.
- 추천: 섭취 비율 0인 항목은 "최근 먹은 음식" 제외 목록에 넣지 않습니다. 기존 행은 비율 1.0이므로 결과가 바뀌지 않습니다.
