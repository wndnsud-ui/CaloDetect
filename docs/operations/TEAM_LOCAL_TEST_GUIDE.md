# 팀원별 Docker DB · 관리자/테스트 계정 가이드

리워드몰 구현 업데이트(`7f47570`)를 받은 경우 [리워드몰 DB 마이그레이션 실행 가이드](REWARD_MALL_MIGRATION_GUIDE.md)를 먼저 확인하세요. Docker/로컬 Python 방식별 적용·백업·revision 확인 절차를 안내합니다.

팀 공유 Supabase DB를 쓰는 경우 이 문서 대신 [Supabase 공유 DB 가이드](SUPABASE_SHARED_DB_GUIDE.md)를 따릅니다. 고정 테스트·관리자 계정 자동 생성과 migration은 공유 DB에서 실행하지 않습니다.

각 팀원은 자기 PC의 Docker PostgreSQL에 개발용 계정을 만들어 테스트합니다. 혜영님 PC나 로그인 상태에 의존하지 않습니다. 이메일과 비밀번호가 같아도 계정·식단·포인트·쿠폰은 PC별로 별개입니다. Git pull은 코드만 받으며 다른 사람의 DB 데이터를 가져오지 않습니다.

Windows PowerShell 기준입니다. 명령은 자신의 **CaloDetect 프로젝트 루트**에서 실행합니다. 최초 설치는 [README](../../README.md#새-웹-환경-실행--팀원용-간편-설치), 서버 재실행은 [로컬 실행 가이드](../../CaloDetect_로컬_실행가이드.md)를 참고하세요.

## 1. 공통 준비

1. Docker Desktop을 켜고 Engine running 상태를 확인합니다.
2. 최신 `develop` 코드가 있는지 확인합니다. 작업 중인 변경은 보존하고 팀 Git 절차에 따라 업데이트합니다.
3. 자신의 비공개 `.env`에서 아래 값을 확인합니다.

```dotenv
APP_ENV=development
LOCAL_TEST_SIGNUP=true
FRONTEND_ORIGIN=http://localhost:5174
```

다른 사람의 `.env`나 DB 비밀번호를 복사할 필요는 없습니다. DB 접속 정보는 각자 설정합니다. 설정 준비가 안 된 PC는 README의 설치 절차를 먼저 완료하세요. 개발용 계정은 운영 환경에서 사용하지 않습니다.

아래 A와 B 중 **Backend 실행 방식에 맞는 하나**를 선택합니다. 같은 8000 포트에 Docker Backend와 PC Backend를 동시에 실행하지 않습니다.

## 2-A. Backend도 Docker로 실행하는 팀원

설정 파일이 준비된 상태에서 실행합니다.

```powershell
docker compose up -d --build backend
if ($LASTEXITCODE -ne 0) { throw 'Backend 시작 실패. Docker와 설정을 확인하세요.' }
docker compose logs --tail 60 backend
```

현재 Docker 시작 스크립트는 DB migration → 음식·리워드 아이템 → 개발용 테스트·관리자 계정을 준비한 뒤 API를 실행합니다. `Application startup complete`가 표시되는지 확인합니다.

계정만 다시 확인·생성하려면 다음을 실행합니다.

```powershell
docker compose exec backend python -m backend.scripts.seed_local_admin
docker compose exec backend python -m backend.scripts.seed_local_test_account
```

`.env`를 변경했다면 실행 중인 컨테이너에도 반영합니다.

```powershell
docker compose up -d --force-recreate backend
```

Frontend는 별도 터미널에서 실행합니다. Docker Backend는 IPv4로 노출되므로 프록시 주소를 지정합니다.

```powershell
Set-Location .\frontend
$env:CALODETECT_API_TARGET='http://127.0.0.1:8000'
$env:VITE_STREAMLIT_URL='http://127.0.0.1:8502/'
npm.cmd run dev -- --host localhost --port 5174
```

## 2-B. Docker는 DB만, Backend는 PC에서 실행하는 팀원

`.venv-backend`와 의존성 설치가 완료된 상태에서 실행합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw 'DB 준비 실패. 오류를 해결한 뒤 다시 실행하세요.' }
```

이 스크립트는 DB 시작·기존 migration 적용·테스트 계정·음식 데이터를 준비합니다. 관리자와 리워드 아이템은 추가로 준비합니다.

```powershell
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_local_admin
if ($LASTEXITCODE -ne 0) { throw '관리자 계정 준비 실패' }
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_reward_items
if ($LASTEXITCODE -ne 0) { throw '리워드 아이템 준비 실패' }
$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

Frontend는 별도 터미널에서 프로젝트 루트로 이동한 뒤 실행합니다.

```powershell
Set-Location .\frontend
$env:CALODETECT_API_TARGET='http://[::1]:8000'
$env:VITE_STREAMLIT_URL='http://127.0.0.1:8502/'
npm.cmd run dev -- --host localhost --port 5174
```

기존 DB를 업데이트할 때는 먼저 백업과 Alembic 이력을 확인하세요. 현재 head까지의 migration에는 폐기된 모델 개선 테이블·컬럼 삭제도 포함됩니다. 미등록 revision이나 스키마 충돌 오류가 나면 중단하고 담당자에게 오류를 전달합니다. 임의로 `stamp`하거나 DB volume을 삭제해 우회하지 않습니다.

## 3. 그래프 서버 실행

A/B 모두 그래프를 보려면 별도 터미널에서 프로젝트 루트로 이동해 실행합니다. 로컬 Python 환경에 README의 개발 의존성이 필요합니다.

```powershell
.\.venv-backend\Scripts\python.exe -m streamlit run streamlit/charts.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

## 4. 로그인 및 정상 동작 확인

[http://localhost:5174](http://localhost:5174)에서 **이메일 로그인**을 선택합니다. 이 계정은 Google·카카오 로그인이 아닙니다.

| 용도 | 이메일 | 비밀번호 |
|---|---|---|
| 관리자 | `admin@calodetect.local` | `CaloAdmin!2026` |
| 일반 테스트 회원 | `test@calodetect.local` | `CaloTest!2026` |

- 관리자로 로그인하면 **관리자** 메뉴가 표시됩니다.
- 테스트 회원으로 로그인하면 로컬 개발 설정에서 **테스트** 메뉴가 표시됩니다.
- [DB 연결 확인](http://localhost:5174/api/health/database)은 `{"status":"ok"}`를 반환해야 합니다.
- [그래프 서버 확인](http://127.0.0.1:8502/_stcore/health)은 `ok`를 반환해야 합니다.

계정 생성 스크립트는 기존 계정의 비밀번호나 권한을 덮어쓰지 않습니다. `already exists; unchanged`는 기존 계정을 유지했다는 뜻입니다. 같은 이메일이 일반 회원이면 관리자 스크립트는 `not promoted`를 출력합니다. 이 경우 기존 계정의 비밀번호·역할을 담당자와 확인하세요. 스크립트를 반복 실행해도 비밀번호가 초기화되거나 관리자 권한으로 바뀌지 않습니다.

## 5. 식단·리워드 더미 만들기 (선택)

**v13 시연 / v13 코칭 시연**은 물병 소품·하트 쿠션의 구매 이력과 소유권도 예시로 생성합니다. 직접 구매 버튼을 누르지 않았어도 두 아이템은 '보유 · 바로 적용하기'로 표시됩니다. 일반 더미 실행과 다른 시나리오이며, 기본 안경·리본·운동화는 무료 기본 제공입니다. 실제 구매 문제를 검사할 때는 시연 데이터 생성 여부를 먼저 확인하세요. 시연 실행은 기존 리워드·교환 이력을 초기화하므로 실제 기록을 유지해야 하는 계정에는 실행하지 마세요.

테스트 페이지의 **연속 기록(일)**은 어제까지의 더미 기록을 교체합니다. 실제 식단 기록은 유지하므로 결과 일수가 더 길 수 있습니다. **가입 경과일(일)**은 별도 입력이며 기본 14일입니다. 더미 실행 시 테스트 계정 본인의 가입일을 조정합니다. 건강상품 교환은 가입 경과일·교환 가능 포인트·월 교환 한도로 결정되며 연속 기록 14일이 조건은 아닙니다. 첫 교환은 관리자 확인 후 발급합니다.

로그인만 확인하려면 필요하지 않습니다. 화면에 예시 기록이 필요할 때 자신의 Backend 실행 방식에 맞춰 하나만 실행합니다.

```powershell
# A: Backend도 Docker에서 실행
docker compose exec backend python -m backend.scripts.seed_test_demo
```

```powershell
# B: Backend를 PC에서 실행
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_test_demo
```

관리자·테스트 계정과 테스트 회원의 최근 30일 식단·리워드 아이템·리워드 더미를 준비합니다. 테스트 회원으로 다시 확인하세요. **테스트 메뉴의 리워드 초기화나 `--reset`은 해당 회원의 교환·쿠폰 이력도 삭제합니다.** 필요할 때만 사용합니다.

## 6. 커뮤니티 공유 보상 활성화

2026-10-21 사용자 승인에 따른 Stage B 실행 설정입니다. 각 팀원의 비공개 `.env`에도 아래 값을 적용합니다. 코드 기본값은 자동 전환되지 않습니다.

```dotenv
REWARD_COMMUNITY_XP_MODE=true
COMMUNITY_LIKE_RECEIVED_POINTS=0
COMMUNITY_RECOMMEND_RECEIVED_POINTS=0
COMMUNITY_REACTION_GIVEN_POINTS=0
```

A는 `docker compose up -d --force-recreate backend`, B는 PC Backend를 재시작합니다. 식단 공유는 하루 1회 +1P·+10XP, 좋아요·추천 반응은 포인트 대신 XP로 지급됩니다. 기존 원장은 보존하고 과거 공유에 소급 지급하지 않습니다.

## 7. 건강상품 교환·쿠폰 발급 테스트 (선택)

자신의 로컬 `.env`에서만 아래 개발 설정을 사용합니다. 운영 정책이나 실제 제휴 쿠폰을 의미하지 않습니다.

```dotenv
REWARD_EXCHANGE_ENABLED=true
REWARD_EXCHANGE_GLOBAL_MONTHLY_CAP=100
REWARD_EXCHANGE_MIN_ACCOUNT_DAYS=0
```

교환에는 `OAUTH_STATE_SECRET`도 필요합니다. 설치 스크립트가 생성한 자신의 비공개 값을 사용합니다. 변경 후 A는 Backend 컨테이너 재생성, B는 Backend 프로세스 재시작이 필요합니다.

1. 테스트 회원으로 식단 기록 또는 리워드 더미를 준비합니다.
2. 리워드 몰에서 교환 가능 포인트를 확인하고 건강상품 교환을 신청합니다. 온보딩·커뮤니티 출처 포인트는 실물 교환에서 제외됩니다.
3. 첫 신청은 보류 상태입니다. 관리자 계정으로 로그인해 **관리자** 메뉴에서 신청을 확인하고 테스트용 번호로 발급합니다.
4. 테스트 회원으로 다시 로그인해 쿠폰함을 확인합니다. 테스트 번호는 실제 매장에서 사용할 수 없습니다.

월 1회 제한 등은 유지됩니다. 서로 다른 PC의 관리자에게는 다른 팀원 PC에서 만든 신청이 보이지 않습니다.

## 8. 자주 발생하는 문제

| 증상 | 확인할 사항 |
|---|---|
| 계정이 없거나 로그인 실패 | 웹이 연결한 Backend와 계정 생성 명령이 같은 DB를 사용하는지 확인. 기존 계정이면 비밀번호가 다를 수 있음 |
| `Local development test settings required` 등 | `.env`의 개발 설정 3개 확인. Docker는 컨테이너 재생성 |
| Docker Backend가 시작되지 않음 | `docker compose logs --tail 60 backend` 확인. migration 오류면 담당자에게 전달 |
| `relation ... does not exist` | 해당 DB에 migration이 적용됐는지 확인. 기존 DB는 백업·이력 확인 후 업데이트 |
| Backend 연결 실패·502 | Backend 실행 상태와 A/B별 `CALODETECT_API_TARGET` 확인 |
| 테스트 메뉴가 없음 | 테스트 회원 본인으로 로그인했는지, Backend 개발 설정이 적용됐는지 확인 |
| 관리자 메뉴가 없음 | 관리자 계정의 역할 확인. 기존 일반 계정은 자동 승격되지 않음 |
| 교환 메뉴가 없거나 404 | 교환 활성화·양수 월 상한·서명키 설정과 Backend 재시작 확인 |
| 그래프가 비어 있음 | 8502 그래프 서버 실행 여부 확인 |

`.env`·실제 DB·사진은 Git에 올리지 않습니다. DB를 유지하려면 `docker compose down -v`를 사용하지 마세요. 동일 PC의 새 클론은 고정 volume `calodetect_postgres_data`를 재사용할 수 있습니다. 팀 전체가 같은 기록을 봐야 할 때는 공용 Backend·DB를 별도로 구성해야 합니다.
