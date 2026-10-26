# CaloDetect 팀원 실행 가이드 · Supabase 공유 DB

이제 팀 전원이 **같은 Supabase DB**를 씁니다. 내 PC에서 가입한 계정, 기록한 식단, 리워드 포인트가 다른 팀원 PC에서도 그대로 보입니다.
**Docker는 필요 없습니다.** 서버 3개(Backend·그래프·웹)만 켜면 됩니다.

- 명령은 모두 Windows **PowerShell** 기준입니다. 프로젝트 폴더는 `C:\projects\CaloDetect`로 가정합니다. 다른 곳에 받았다면 경로만 바꾸세요.
- 규칙과 배경 설명은 [Supabase 공유 DB 가이드](docs/operations/SUPABASE_SHARED_DB_GUIDE.md)에 있습니다.

> **사전 준비 프로그램:** Git, Python 3.12 권장(3.10 이상), Node.js 22.12 이상(또는 20.19 이상)

---

## 0. 담당자에게 받을 값 (1:1로만)

아래 4개는 비밀값입니다. 단톡방·GitHub·문서에 올리지 말고 **1:1로** 받으세요.

| 값 | 설명 |
|---|---|
| `DATABASE_URL` | Supabase 접속 주소 (`postgresql+psycopg://postgres.…pooler.supabase.com:5432/postgres?sslmode=require`) |
| `OAUTH_STATE_SECRET` | 소셜 로그인·쿠폰 암호화 키. 팀 전원이 같은 값을 써야 함 |
| `PASSWORD_RESET_SECRET` | 비밀번호 재설정 링크 서명 키. 팀 전원이 같은 값을 써야 함 |
| `SUPABASE_SERVICE_ROLE_KEY` | 사진 저장소(Storage) 서버 키 `sb_secret_…`. DB 비밀번호와 같은 수준으로 관리 |

---

## 1. 코드 받기

### 처음 받는 경우

```powershell
New-Item -ItemType Directory -Path 'C:\projects' -Force | Out-Null
Set-Location 'C:\projects'
git clone --branch develop https://github.com/wndnsud-ui/CaloDetect.git
Set-Location 'C:\projects\CaloDetect'
```

### 이미 받아 둔 폴더가 있는 경우

작업 중인 변경이 있으면 먼저 커밋하거나 따로 보관하세요.

```powershell
Set-Location 'C:\projects\CaloDetect'
git switch develop
git pull origin develop
```

---

## 2. Python·Node 패키지 설치

처음 한 번, 그리고 패키지 목록이 바뀌었을 때 실행합니다.

```powershell
Set-Location 'C:\projects\CaloDetect'
if (-not (Test-Path .\.venv-backend)) { py -m venv .venv-backend }
.\.venv-backend\Scripts\python.exe -m pip install --upgrade pip
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -r backend/requirements-vision.txt

Set-Location 'C:\projects\CaloDetect\frontend'
npm.cmd ci
```

---

## 3. `.env` 설정

### 3-1. 기존 `.env` 백업 (이미 쓰던 `.env`가 있는 경우만)

로컬 Docker DB로 돌아갈 때 필요하니 꼭 백업해 두세요.

```powershell
Set-Location 'C:\projects\CaloDetect'
if (Test-Path .env) { Copy-Item .env .env.local-docker.bak }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

`.env`와 `.env.local-docker.bak`은 GitHub에 올라가지 않습니다.

### 3-2. 값 바꾸기

VS Code에서 `.env`를 열어 아래 값으로 **바꾸거나 추가**합니다. 같은 이름의 줄이 이미 있으면 그 줄을 고치고, 한 이름이 두 번 들어가지 않게 하세요.

```dotenv
# ── 공유 DB (0번에서 받은 값. 두 줄에 같은 값) ──
DATABASE_URL=받은_주소
DATABASE_URL_DOCKER=받은_주소
DB_POOL_MODE=session
DB_CONNECT_TIMEOUT=10
# 반드시 false. migration은 담당자 1명만 실행합니다.
RUN_MIGRATIONS_ON_START=false

# ── 팀 공통 비밀키 (0번에서 받은 값) ──
OAUTH_STATE_SECRET=받은_값
PASSWORD_RESET_SECRET=받은_값

# ── 로컬 개발·테스트 메뉴 ──
APP_ENV=development
LOCAL_TEST_SIGNUP=true
LOCAL_TEST_IMAGE_ANALYSIS=true
FRONTEND_ORIGIN=http://localhost:5174
IMAGE_STORAGE_DIR=.private-uploads

# ── 사진 저장소 (공유 버킷). URL의 <ref>는 DATABASE_URL의 postgres. 뒤 문자열 ──
IMAGE_STORAGE_BACKEND=supabase
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=받은_값
SUPABASE_STORAGE_BUCKET=calodetect-images

# ── 팀 공통 기능 설정 (개발 기준값, 운영값 아님) ──
RECOMMENDATION_ENABLED=true
RECENT_MEAL_WINDOW=3
CHAT_RECORD_ENABLED=true
REWARD_ONBOARDING_START_AT=2026-10-20T00:00:00+09:00
REWARD_EXCHANGE_ENABLED=true
REWARD_EXCHANGE_GLOBAL_MONTHLY_CAP=100
REWARD_EXCHANGE_MIN_ACCOUNT_DAYS=0
REWARD_COMMUNITY_XP_MODE=true
COMMUNITY_LIKE_RECEIVED_POINTS=0
COMMUNITY_RECOMMEND_RECEIVED_POINTS=0
COMMUNITY_REACTION_GIVEN_POINTS=0
REWARD_COLLAB_DEMO_ENABLED=true
REWARD_COACHING_ENABLED=true
```

위 기능 설정이 사람마다 다르면, 같은 회원이라도 PC마다 다른 포인트를 받게 됩니다. 값을 바꾸고 싶으면 혼자 바꾸지 말고 팀과 같이 바꾸세요.

### 3-3. 연결 확인

```powershell
Set-Location 'C:\projects\CaloDetect'
.\.venv-backend\Scripts\python.exe -c "from backend.app.db import check_database; check_database(); print('Supabase 연결 OK')"
```

`Supabase 연결 OK`가 나오면 성공입니다.

---

## 4. 서버 3개 켜기 (터미널 3개)

VS Code에서 **터미널 → 새 터미널**로 창 3개를 열고, 창마다 하나씩 실행합니다. 켠 창은 닫지 마세요.

> ⚠️ 공유 DB에서는 `scripts\setup_local.ps1`과 `docker compose`를 **실행하지 않습니다.** 둘 다 로컬 Docker DB용입니다.

**터미널 A: Backend (8000)**. `Application startup complete`가 나오면 준비된 것입니다.

```powershell
Set-Location 'C:\projects\CaloDetect'
$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

**터미널 B: 그래프 서버 (8502)**. 홈과 분석 화면의 그래프에 꼭 필요합니다.

```powershell
Set-Location 'C:\projects\CaloDetect'
.\.venv-backend\Scripts\python.exe -m streamlit run streamlit/charts.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

**터미널 C: 웹 (5174)**

```powershell
Set-Location 'C:\projects\CaloDetect\frontend'
$env:CALODETECT_API_TARGET='http://[::1]:8000'
npm.cmd run dev -- --host localhost --port 5174
```

브라우저에서 **http://localhost:5174** 를 엽니다.

---

## 5. 로그인과 테스트

| 계정 | 비밀번호 | 용도 |
|---|---|---|
| `test@calodetect.local` | `CaloTest!2026` | 리워드 테스트 메뉴(더미 포인트·XP·연속 기록) |
| `admin@calodetect.local` | `CaloAdmin!2026` | 관리자 메뉴(쿠폰 발급·교환 처리·닉네임 관리) |
| 내 이메일로 직접 가입 | 직접 정함 | 식단·커뮤니티 등 일반 기능 테스트 |

- **위 두 계정은 팀 전체가 같이 씁니다.** 테스트 메뉴에서 **더미 실행이나 초기화를 하면 모든 팀원 화면이 바뀝니다.** 초기화는 교환 신청과 쿠폰도 지우니, 실행하기 전에 팀 단톡방에 알려 주세요.
- 일반 기능은 **각자 가입한 계정**으로 테스트하세요. 예: `홍길동-test@calodetect.local`
- 테스트 메뉴가 안 보이면 3-2의 `APP_ENV=development`, `LOCAL_TEST_SIGNUP=true` 값을 확인한 뒤 Backend를 다시 켜세요.

---

## 6. 꼭 지킬 규칙

| 하지 말 것 | 이유 |
|---|---|
| `alembic upgrade`, `downgrade` 실행 | 공유 DB 구조가 바뀝니다. **담당자 1명이 develop merge 후에만** 실행합니다 |
| `scripts\setup_local.ps1` 실행 | 로컬 Docker DB 전용이라 공유 DB에서는 오류가 납니다 |
| `RUN_POSTGRES_TESTS=1` 테스트 실행 | 공유 DB에 테스트 스키마를 만듭니다 |
| 테이블 삭제, 데이터 일괄 삭제 | 팀 전체 데이터가 지워집니다 |
| `.env`, 접속 주소, 비밀키 공유·커밋 | 공유 DB 전체가 노출됩니다 |

---

## 7. 사진

사진은 Supabase Storage 공유 버킷에 저장되어 **누가 올렸든 모든 PC에서 보입니다.** 3-2의 사진 저장소 4줄이 있어야 합니다.

**Storage 적용 전(2026-10-26 이전 코드)에 공유 DB로 사진을 올린 적이 있다면** 한 번만 실행하세요. 내 PC에만 있던 사진을 버킷으로 옮깁니다. 공유 DB가 쓰는 사진만 올리고 로컬 파일은 지우지 않습니다.

```powershell
Set-Location 'C:\projects\CaloDetect'
.\.venv-backend\Scripts\python.exe -m backend.scripts.upload_local_images
```

결과의 `not on this PC`는 다른 팀원이 올린 사진이라 정상입니다.

---

## 8. 자주 나는 오류

| 증상 | 해결 |
|---|---|
| `password authentication failed` | `DATABASE_URL`의 비밀번호를 잘못 넣었습니다. 받은 값을 공백 없이 다시 붙여 넣으세요 |
| `connection timeout`, 연결이 오래 걸림 | 인터넷 연결을 확인하세요. 학교나 회사 와이파이가 5432 포트를 막을 수 있으니 휴대폰 핫스팟으로 시험해 보세요 |
| `DATABASE_URL is not configured` | `.env`가 프로젝트 루트(`C:\projects\CaloDetect\.env`)에 있는지 확인하세요 |
| 그래프가 안 보임 | 터미널 B가 켜져 있는지, http://localhost:8502/_stcore/health 에서 `ok`가 나오는지 확인하세요 |
| `Port 5174 is already in use` | 이전에 켠 웹 서버 창에서 `Ctrl+C`로 끄고 다시 실행하세요 |
| 다른 사람이 올린 사진만 안 보임 | 그 팀원이 7번의 사진 옮기기 명령을 실행해야 보입니다 |
| 사진 업로드 시 `사진을 저장하지 못했습니다` | `SUPABASE_URL`·`SUPABASE_SERVICE_ROLE_KEY` 값을 확인하세요 (`anon`·`publishable` 키는 안 됨) |

서버를 끌 때는 각 터미널에서 `Ctrl + C`를 누릅니다.

---

## 9. 로컬 Docker DB로 돌아가기

3-1에서 만든 백업으로 되돌린 뒤, 예전 방식(README의 `setup_local.ps1` 실행)으로 켜면 됩니다. 로컬 Docker DB의 데이터는 지워지지 않고 그대로 남아 있습니다.

```powershell
Set-Location 'C:\projects\CaloDetect'
Copy-Item .env.local-docker.bak .env -Force
```
