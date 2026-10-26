# Supabase 공유 DB 사용 가이드

팀원 모두가 같은 Supabase PostgreSQL(서울 리전 `ap-northeast-2`, Session pooler 5432)에 접속해 계정·식단·포인트·커뮤니티 데이터를 함께 봅니다. 기존 각자 PC의 Docker DB는 그대로 남아 있으며 삭제하지 않습니다(`docker compose down -v` 금지).

Windows PowerShell 기준이며 명령은 **CaloDetect 프로젝트 루트**에서 실행합니다. 설치부터 실행까지 단계별 절차는 [Supabase 팀원 실행 가이드](../../CaloDetect_Supabase_팀원_실행가이드.md)를 따릅니다.

## 1. 팀원용 `.env` 설정

접속 주소와 비밀번호는 담당자에게 비공개로 받습니다. 메신저 공개 채널·Git·문서·스크린샷에 올리지 않습니다.

```dotenv
# 두 값에 같은 Supabase Session pooler 주소를 넣는다 (PC Backend / Docker Backend 공용)
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<비밀번호>@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require
DATABASE_URL_DOCKER=postgresql+psycopg://postgres.<project-ref>:<비밀번호>@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require
DB_POOL_MODE=session
DB_CONNECT_TIMEOUT=10
# 공유 DB 팀원은 반드시 false. 서버 시작 시 migration·seed·고정 테스트 계정 생성을 건너뛴다.
RUN_MIGRATIONS_ON_START=false
```

- `DB_POOL_MODE=transaction`은 Transaction pooler(6543) 주소를 쓸 때만 지정합니다. 기본은 `session`입니다.
- Docker Backend는 `docker compose up -d --force-recreate backend`로 환경변수를 다시 읽습니다. compose 구성상 로컬 `db` 컨테이너도 함께 켜지지만 Backend는 Supabase에 접속합니다.
- 연결 확인: `.\.venv-backend\Scripts\python.exe -c "from backend.app.db import check_database; check_database(); print('OK')"` 또는 `GET /health/database`.

로컬 Docker DB로 돌아가려면 두 URL을 기존 로컬 값으로 되돌리고 `RUN_MIGRATIONS_ON_START=true`로 바꿉니다.

## 2. Migration 규칙

- 공유 DB의 `alembic upgrade`와 seed는 **담당자 1명**이 **develop에 merge된 뒤에만** 실행합니다.
- 작업 브랜치의 migration을 공유 DB에 적용하지 않습니다. 다른 팀원의 코드와 스키마가 어긋납니다.
- 담당자 실행 순서:

```powershell
.\.venv-backend\Scripts\python.exe -m alembic -c backend/alembic.ini current
.\.venv-backend\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_foods
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_reward_items
.\.venv-backend\Scripts\python.exe -m alembic -c backend/alembic.ini current
```

- `RUN_POSTGRES_TESTS=1` 테스트는 공유 DB에서 실행하지 않습니다(로컬 Docker DB에서만).
- `downgrade`·테이블 삭제·데이터 초기화 등 파괴적 작업은 팀 합의 후에만 실행합니다.
- revision `20261026_01`은 public 스키마 모든 테이블에 RLS를 켭니다(정책 없음). Backend는 테이블 소유자(postgres)로 접속하므로 영향이 없고, Supabase Data API(anon key)로 테이블이 노출되는 것만 막습니다. 새 테이블을 추가하는 migration은 같은 방식으로 RLS를 켭니다.

## 3. 팀 공통으로 맞춰야 할 값

같은 DB를 쓰므로 아래 값이 사람마다 다르면 로그인·쿠폰·보상 동작이 어긋납니다. 담당자에게 받은 같은 값을 사용합니다.

| 값 | 이유 |
|---|---|
| `OAUTH_STATE_SECRET` | 소셜 로그인 state 서명, 쿠폰 번호 암호화 키. 다르면 다른 사람이 발급한 쿠폰을 복호화하지 못함 |
| `PASSWORD_RESET_SECRET` | 비밀번호 재설정 링크 서명. 다르면 다른 PC에서 받은 링크가 무효 |
| `REWARD_*` 동작 플래그 | `REWARD_ENABLED`, `REWARD_ONBOARDING_START_AT`, `REWARD_COMMUNITY_XP_MODE`, `REWARD_EXCHANGE_*`, `REWARD_COLLAB_DEMO_ENABLED`, `REWARD_COACHING_ENABLED` 등. 다르면 같은 회원에게 PC마다 다른 보상이 지급됨 |
| `COMMUNITY_*_POINTS` | 커뮤니티 반응 포인트 지급·회수 금액 |

## 4. 테스트 계정

- 사용자 결정(2026-10-26)으로 공유 DB에 리워드 테스트용 `test@calodetect.local` 계정을 만들었습니다. **팀 전체가 한 계정을 함께 씁니다.** 누군가 테스트 페이지에서 더미 실행·초기화를 하면 다른 팀원 화면의 포인트·XP·교환 이력도 바뀝니다. 더미를 돌리기 전에 팀에 알립니다.
- 리워드 테스트 페이지는 각자 `.env`에 `APP_ENV=development`, `LOCAL_TEST_SIGNUP=true`, `FRONTEND_ORIGIN=http://localhost:5174`가 있어야 보입니다. 계정은 다시 만들 필요가 없습니다.
- 식단·커뮤니티 등 일반 기능 테스트는 **사람별로** 다른 이메일로 가입해 사용합니다(예: `이름-test@calodetect.local`).
- 같은 결정으로 관리자 계정 `admin@calodetect.local`도 Docker와 동일하게 만들었습니다(쿠폰 발급·교환 처리·닉네임 관리). 두 계정의 비밀번호는 저장소에 공개된 개발용 값이므로, 공유 DB 접속 정보가 외부로 나가지 않게 관리하고 운영 환경에서는 사용하지 않습니다.
- 공유 DB에서는 `scripts/setup_local.ps1`을 실행하지 않습니다(로컬 Docker DB 전용). Backend는 uvicorn만 실행합니다.

## 5. 현재 제약: 사진

사진 파일은 DB가 아니라 **올린 사람 PC의 `IMAGE_STORAGE_DIR`(예: `.private-uploads`)** 에 저장됩니다. DB 기록은 공유되지만 다른 PC에서는 그 사진 파일이 없어 식단·커뮤니티 이미지가 보이지 않을 수 있습니다. Supabase Storage 이전은 남은 과제입니다.
