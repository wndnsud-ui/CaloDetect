# 커뮤니티 v5 착수 점검 · 2026-10-16

**최종 상태: 기존 로컬 DB 적용 완료.** 사용자 별도 승인으로 구형 테이블 보관·이력 정리까지 수행했다. 아래 차단 사유는 적용 전 조사 이력이다.

## 실제 DB 전환 결과

- 승인: 2026-10-16 사용자가 “구형 테이블 보관 후 v5 적용 승인” 선택.
- 직전 전체 pg_dump custom archive 백업 및 pg_restore 목록 검사 완료. 비공개 로컬 폴더에만 보관.
- `backend/scripts/apply_community_v5_local.py` 검사 전용 모드 통과. 기존 public schema와 커뮤니티 제외 기준 metadata 차이 없음 확인.
- 한 트랜잭션에서 구형 3개 테이블을 `community_legacy_20261016`으로 이동, v5 4개 테이블 생성, 검증된 스키마에 맞춰 revision을 `20261007_03` → `20261016_01`로 정리. 테이블 삭제·단순 stamp 없음.
- 기존 모든 public 업무 테이블의 행 건수 및 행 hash 전후 동일. 회원 4·식단 127·항목 217건 보존. 보관된 3개 테이블도 전후 동일.
- 적용 후 `alembic current`: `20261016_01 (head)`, `alembic upgrade head` 정상 종료.
- 실제 기존 DB에서 별도 두 회원 쿠키 인증 → 식단 → 공유 → 좋아요/추천 → 취소 예상액 → 취소 감점 → 삭제 예상액 → 삭제 작성자 감점 → 반응자 포인트 유지 → 랭킹 흐름 검증. 외부 트랜잭션을 롤백해 검증 전후 모든 public 테이블 hash 동일 확인.
- 이 전환 도구는 조사된 로컬 `20261007_03` 상태에만 사용한다. 이미 적용된 DB·다른 스키마·비어 있지 않은 구형 테이블에는 적용하지 않으며, 단일 head를 유지한다.

사용자 요청: v5 구현·검증 후 기존 DB 적용. 2026-10-16 사용자 명시 답변으로 Codex의 모델·migration 작성 승인. Master Spec 원문은 보존한다.

| 검사 | 결과와 근거 |
|---|---|
| C1 | DEVELOPMENT_RULES.md:11 및 README.md:511의 Core A 제한 확인. 이번 작업에 한해 사용자 명시 승인. Feed·Like·Calo Point 범위는 v5 §1의 2026-10-14 승인 적용. |
| C2 | 착수 시 Alembic heads: `20261015_02` 단일 head. `20261015_02_chat_record.py:7-8`. 새 revision `20261016_01`의 부모로 사용. |
| C3 | 현재 브랜치에 섭취량 `20261015_01` 및 채팅 `20261015_02` 존재. 이 두 revision 다음에 연결. 원격 미게시 작업 여부 확인 불가. 병합 시 최신 head에 rebase 필요. |
| C4 | `backend/app/security.py:72-76`: GET·HEAD 외 쿠키 요청은 출처 및 CSRF 검사. DELETE도 포함. 기존 의존성 사용. CORS는 DELETE만 추가. |
| C5 | `backend/app/api.py:39-41`: local_test_image_analysis 사용 시 개발 환경·loopback 요청까지 검사. 공개 사본에도 검사 유지하므로 다른 기기 접근 제한. 검사를 완화하지 않음. |
| C6 | `backend/app/models.py:243` consumption_ratio 존재. 원본 기준 배율 × 섭취 비율로 공개 배율 표시. 영양은 저장값 합계. |
| C7 | `backend/requirements.txt:12` Pillow 기존 설치·사용 확인. 새 의존성 없음. |
| C8 | backend/app·backend/scripts 검색 결과 식단 삭제·회원 탈퇴 경로 없음. 세션 삭제만 존재. 기존 auth_sessions·user_profiles·채팅 FK에 CASCADE가 있으나 새 FK에는 사용하지 않음. 향후 삭제 정책 TBD. |
| C9 | `backend/app/db.py:13-23` 격리 수준 오버라이드 없음. 실제 PostgreSQL 연결에서 READ COMMITTED 확인. |

## 기존 DB 적용 차단 사유

- 실제 revision: 저장소에 없는 `20261007_03`.
- 구형 `community_posts`, `community_reactions`, `community_comments` 존재, 각 0건.
- 구형 게시물 컬럼: id, user_id, title, text, category, visibility, image_name, created_at. v5의 meal_id·comment·show_photo·deleted_at 없음.
- 검사 시점 회원 4건, 식단 127건, 식단 항목 217건. 개인정보 원문은 기록하지 않음.
- 실제 DB에 섭취 비율·version·채팅 테이블이 이미 있음. 바로 upgrade하거나 단순 stamp하면 안 됨.

전환안: 전체 백업 → 실제 schema와 20261015_02 기준 대조 → 구형 3개를 보관용 schema로 이동(데이터·FK 보존) → 검증된 기준 이력 정리 → v5 migration 적용 → 기존 데이터 및 보관 테이블 확인. v5 §4의 기존 테이블 변경 금지 예외이므로 별도 사용자 승인 요청. 승인 전 실제 DB 변경하지 않는다.

## 재사용 및 변경 범위

- REUSE: CurrentUser/DB, 쿠키 CSRF·출처 검사, foods 카탈로그, 원본 meals·meal_items·image_uploads, Pillow.
- MODIFY: models 4개 추가, config 4개 추가, schemas 요청 1개, main 라우터/CORS DELETE/status, React 메뉴.
- NEW: community 라우터·서비스·migration·화면·검증.
- DO NOT TOUCH: 모델/CSV/YAML, Master Spec, 기존 식단·사진 API 권한, 챗봇 동작, 운영 TBD.

## 시안 및 검증

제공된 Claude artifact URL은 웹 도구에서 접근 불가. v5 §11의 담벼락·브랜드 초록·접힌 랭킹·모바일 시트 명세를 적용. 원본 시안과 픽셀 단위 일치는 확인하지 못함.

SQLite 커뮤니티·사진·규칙 28통과·PostgreSQL 전용 4제외. PostgreSQL 임시 schema에서 12통과(통합·순서 강제 동시성 4개·migration upgrade/downgrade 왕복 포함). Frontend 빌드 및 표시 규칙 Node 테스트 2개 통과. 전체 Backend는 당시 184통과·2제외·기존 추천 응답 형식 테스트 3실패(`detail` 대신 `error.message` 응답; 기존 CHANGELOG에도 기록된 실패).

Chrome headless와 가상 API fixture로 1400/390px 가로 넘침 없음, 랭킹 클릭 고정·Esc 접힘, 취소 미리보기 연타 1회·기본 취소 포커스·Esc 시 반응 유지, 모바일 랭킹 시트, 사진 공개 기본 해제를 검증했다. `.runtime-logs/community-1400.png`·`community-390.png` 시각 확인. 실제 터치 기기·회원 2명 실서버 검증은 DB 전환 후 필요.

기존 DB 비공개 pg_dump custom archive 백업 및 pg_restore --list 검사 완료. 기존 커뮤니티를 제외한 public schema와 현재 기준 ORM의 Alembic compare_metadata 결과 차이 없음. 구형 테이블 보관 및 이력 전환 승인은 대기 중이다. 백업은 개인 로컬 백업 폴더에만 있으며 Git에 포함하지 않는다.
