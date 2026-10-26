# CaloDetect Supabase 공유 DB 전환 지시서

## 목표
팀원 모두가 같은 Supabase PostgreSQL(서울 리전, Session pooler 5432)을 쓰도록 백엔드를 수정하고,
Supabase에 테이블과 기본 데이터를 만든다. 작업 브랜치는 develop에서 새로 만든다 (예: `feature/supabase-shared-db`).

## 전제
- 비공개 `.env`의 `DATABASE_URL`은 이미 Supabase Session pooler 주소로 설정되어 있다.
  - 형식: `postgresql+psycopg://postgres.<ref>:***@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres?sslmode=require`
- `.env` 내용, 비밀번호, 접속 주소를 출력하거나 로그·커밋·문서에 쓰지 않는다.
- 로컬 Docker DB 볼륨과 기존 데이터는 삭제하지 않는다.

## 1. 코드 수정
1. `backend/app/config.py`
   - `db_pool_mode: Literal['session', 'transaction'] = 'session'`
   - `db_connect_timeout: int = 10`
   - `run_migrations_on_start: bool = True`
2. `backend/app/db.py`의 `get_engine()`
   - `connect_timeout`을 `settings.db_connect_timeout`으로 변경 (기존 3초는 원격 DB에 짧음)
   - session 모드: `pool_pre_ping=True`, `pool_size=2`, `max_overflow=3`
   - transaction 모드(6543): `poolclass=NullPool`, `connect_args`에 `prepare_threshold=None`
   - 기존 `'postgresql+psycopg://'` 검사는 유지
3. `backend/scripts/start.py`
   - `run_migrations_on_start`가 false면 alembic upgrade와 seed를 건너뛰고 서버만 실행
4. `.env.example`
   - 위 3개 설정과 Supabase Session pooler 주소 예시(비밀번호는 `replace_me`) 추가
   - 공유 DB를 쓰는 팀원은 `RUN_MIGRATIONS_ON_START=false`로 둔다는 주석 추가

## 2. 보안 migration 추가
- 새 revision (`down_revision='20261022_02'`)
  - PostgreSQL일 때만 public 스키마의 모든 앱 테이블에 `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` 실행 (정책은 만들지 않음)
  - 백엔드는 postgres 역할로 직접 접속하므로 영향 없음. Supabase Data API(anon key) 노출 차단 목적
- downgrade는 `DISABLE ROW LEVEL SECURITY`
- SQLite 테스트에서는 실행되지 않도록 dialect 분기

## 3. Supabase에 적용 (순서대로, 각 단계 결과 보고)
1. 연결 확인: `backend.app.db.check_database()`
2. `python -m alembic -c backend/alembic.ini current` → 비어 있어야 정상
3. `python -m alembic -c backend/alembic.ini upgrade head`
4. `python -m backend.scripts.seed_foods`
5. `python -m backend.scripts.seed_reward_items`
6. 테이블 목록과 `alembic current`가 새 head인지 확인

실패하면 우회하지 말고 중단 후 오류 메시지를 보고한다 (비밀번호는 가린다).

## 4. 테스트
- 기본(SQLite) 백엔드 테스트 전체 실행
- `RUN_POSTGRES_TESTS=1`은 공유 DB에서 실행하지 않는다

## 5. 문서
`docs/operations/SUPABASE_SHARED_DB_GUIDE.md`를 추가하고 아래 내용을 담는다.
- 팀원용 `.env` 설정법: `DATABASE_URL`, `DATABASE_URL_DOCKER`에 같은 값, `RUN_MIGRATIONS_ON_START=false`
- migration은 담당자 1명이 develop merge 후에만 실행한다는 규칙
- 팀 공통으로 맞춰야 할 값: `OAUTH_STATE_SECRET`, `PASSWORD_RESET_SECRET`, `REWARD_*` 동작 플래그
- 테스트 계정은 사람별로 만들 것
- 사진은 올린 사람 PC에만 저장되는 현재 제약

README와 `TEAM_LOCAL_TEST_GUIDE.md`에서 이 문서로 링크하고, CHANGELOG에 항목을 추가한다.

## 완료 보고
- 변경 파일 목록
- 실행한 명령과 결과 (비밀 정보 제외)
- 테스트 결과
- 남은 과제 (이미지 Supabase Storage 이전 등)
