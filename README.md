# CaloDetect · 칼로디텍트

작업 전 [필수 적용 규칙](docs/rules/README.md)을 먼저 읽어 주세요.

## 2026-10-07 develop 업데이트와 데이터 보존

이미 설치·실행한 팀원은 [업데이트 간편 가이드](CaloDetect_업데이트_간편가이드.md)의 터미널 A/B 블록을 그대로 따라 실행하세요.

이번 업로드는 Google 로그인(GIS / Authorization Code + PKCE), Apple 버튼 제거, 이메일 비밀번호 찾기·변경, 로컬 테스트 계정 생성, 재클론 설정 재사용, DB 백업, 실행 가이드, 홈페이지 배경 교체를 포함합니다. 네이버 주소도 재설정 메일을 받을 수 있으며 발신 Gmail 설정은 비공개 `.env`에 필요합니다.

| 보존 대상 | 같은 PC에서 업데이트 / 새 클론 | 다른 PC에서 새 클론 |
|---|---|---|
| 테스트 계정 | 기존 계정·변경한 비밀번호 보존; 없으면 개발 설정에서 생성 | 새 로컬 DB에 테스트 계정 생성 |
| 가입한 이메일·Google 회원, 프로필·식단 | 기존 DB 연결과 `calodetect_postgres_data` volume 재사용 시 보존 | 자동 복사되지 않음; 비공개 DB 백업 복원 또는 공용 DB 필요 |
| Google 코드·공개 Client ID | Git으로 제공 | Git으로 제공; 등록 원본·테스트 사용자·가입 동의 설정 필요 |
| DB 접속 정보·OAuth 키·SMTP 자격정보·동의 문구 | 같은 Windows 계정의 `%LOCALAPPDATA%\CaloDetect\local.env` 재사용 | Git에 포함하지 않음; 별도 설정 필요 |
| 로그인 세션 | 같은 DB·브라우저·접속 주소이며 만료 전이면 유지 | 새 브라우저에서 재로그인 |
| 업로드 사진 | 기존 `.private-uploads` 폴더 별도 보존·복사 필요 | Git에 포함하지 않음; 별도 비공개 복사 필요 |

GitHub는 회원 DB 백업 저장소가 아닙니다. 개인 회원 DB·`.env`·앱 비밀번호·OAuth 비밀키는 업로드하지 않습니다. 재클론 전에 기존 프로젝트 루트에서 최신 개인 설정과 DB를 보관하세요(Docker Desktop 실행 필요).

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1 -SettingsOnly
if ($LASTEXITCODE -ne 0) { throw '개인 설정 저장 실패' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_local_db.ps1
if ($LASTEXITCODE -ne 0) { throw 'DB 백업 실패' }
```

`-SettingsOnly`는 DB를 변경하지 않고 설정만 보관합니다. DB archive는 `%LOCALAPPDATA%\CaloDetect\backups\*.dump`에 저장되며 `pg_dump` 사용자 정의 형식과 archive 목록 검사를 사용합니다. `.env`와 사진 파일은 DB archive에 포함되지 않습니다. 다른 PC로 이전하려면 archive·개인 설정·필요한 사진을 비공개로 전달하고 별도 새 DB에 `pg_restore`로 복원해야 합니다. 기존 DB에 덮어쓰지 말고 복원 후 계정·기록을 확인하세요. `docker compose down -v`, volume 삭제·정리, 개인 설정 폴더 삭제는 보존을 깨뜨릴 수 있습니다. 공용 DB 운영 환경은 미확정입니다.

### 이번 변경 파일 목록

직전 `develop` 기준 커밋 `7fbf089` 이후 변경 묶음입니다. 원본 모델·CSV·YAML·Master Spec과 DB schema는 변경하지 않습니다.

| 묶음 | 변경·추가 파일 | 변경 내용 |
|---|---|---|
| 인증 Backend | `backend/app/accounts.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/social_auth.py`, `backend/app/passwords.py`, `backend/requirements.txt` | Google·이메일 인증, 비밀번호 변경·재설정, 변조 가입 쿠키 거부 |
| 인증 화면 | `frontend/src/EmailAuthForm.jsx`, `frontend/src/SocialLogin.jsx`, `frontend/src/PasswordTools.jsx`, `frontend/src/entry.jsx`, `frontend/src/main.jsx`, `frontend/src/reference.css` | Google만 표시, 비밀번호 찾기·변경·링크 화면 |
| 로컬 실행·보존 | `.env.example`, `.gitignore`, `compose.yaml`, `scripts/setup_local.ps1`, `scripts/backup_local_db.ps1`, `backend/scripts/seed_local_test_account.py`, `backend/scripts/start.py`, `frontend/vite.config.js` | 설정 재사용, DB 고정 volume·백업, 테스트 계정, API 프록시 |
| 검증 | `backend/tests/test_social_auth.py`, `backend/tests/test_passwords.py`, `backend/tests/test_local_test_account.py`, `backend/tests/test_local_setup.py` | 인증·비밀번호·계정 보존·재클론 설정 검사 |
| 문서 | `README.md`, `CHANGELOG.md`, `docs/rules/PENDING_DECISIONS.md`, `CaloDetect_팀원_실행가이드.md`, `google_oauth_2_0.md` | 실행·설정·변경사항·보존 조건 |
| 이미지 | `frontend/public/images/hero-bg.webp` | 홈페이지 배경 교체 |

### 변경된 내용만 업데이트하기

기존 Git 클론에서는 전체 폴더를 다시 다운로드할 필요가 없습니다. `git pull`은 변경분을 받아 일관된 버전으로 적용하며, Git이 추적하지 않는 `.env`와 DB volume은 유지합니다. 개발 서버를 각 터미널에서 `Ctrl+C`로 종료하고 아래 순서로 진행하세요.

```powershell
# 프로젝트 루트에서 실행. 수정 파일은 먼저 커밋하거나 별도 보관하세요.
git branch --show-current
git status --short
git switch develop
if ($LASTEXITCODE -ne 0) { throw 'develop 전환 실패' }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw '원격 조회 실패' }
git diff --name-status HEAD origin/develop
git pull --ff-only origin develop
if ($LASTEXITCODE -ne 0) { throw '업데이트 실패. 로컬 변경과 브랜치 차이를 확인하세요.' }
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend 의존성 설치 실패' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw '설정 또는 DB 준비 실패' }
Push-Location frontend
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend 의존성 설치 실패' }
} finally { Pop-Location }
```

이후 아래 터미널 A/B 재실행 안내를 따릅니다. `.env.example`을 기존 `.env`에 덮어쓰지 않습니다. SMTP 값을 수정한 뒤에도 `setup_local.ps1 -SettingsOnly`로 최신 개인 설정을 보관하세요.

일부 파일만 필요하면 `git fetch origin` 후 아래처럼 독립된 이미지 파일만 골라 받을 수 있습니다. 해당 파일의 로컬 수정을 덮어쓰므로 먼저 `git diff -- frontend/public/images/hero-bg.webp`로 확인하세요. 브랜치 커밋은 이동하지 않고 파일만 수정된 상태가 됩니다.

```powershell
git restore --source=origin/develop -- frontend/public/images/hero-bg.webp
```

인증 기능은 Backend·Frontend·설정·의존성이 연결되어 있어 파일 하나만 교체하면 오류가 생길 수 있습니다. Google/비밀번호 기능은 위 전체 `git pull` 절차로 업데이트하세요. GitHub ZIP 다운로드에는 `.git`이 없어 이후 `git pull`을 사용할 수 없습니다.

- `docs/rules/`: 개발 규칙, 원본 업무지시서, 결정 대기 사항, 동의 초안
- `docs/design/`: 아키텍처와 데이터 스키마
- `docs/operations/`: 배포 및 기존 Streamlit 실행 안내 (프로젝트 루트에서 실행)
- `docs/planning/`: 구현 계획과 로드맵
- `docs/model/`: 모델 실험 및 현황
- `docs/UI_VALIDATION.md`, `docs/ui-preview/`: UI 검증과 화면 자료

루트에는 README·CHANGELOG·AGENTS 진입점과 실행·환경 설정·모델·데이터 파일을 둡니다.

식단 저장에 성공하면 “식단을 저장했습니다.” 안내와 함께 히스토리로 이동합니다. 저장한 음식명·섭취량·영양 정보를 확인할 수 있으며, 후속 정보 조회가 실패해도 방금 저장한 결과는 유지됩니다.

웹앱 새로고침 시 마지막 화면과 서버 로그인 세션을 복원합니다. 인증은 HttpOnly 쿠키로 유지하며 기본 만료는 24시간(`SESSION_HOURS`)입니다. 접속 주소는 동일하게 사용하세요. `localhost`와 `127.0.0.1`은 서로 다른 쿠키를 사용합니다.

홈페이지 상단에서도 로그인한 회원에게 “○○님 환영합니다”와 내 계정 버튼을 표시합니다.

회원 홈은 초록색 주간 달력과 식단 기록 카드로 구성합니다. 아침·점심·저녁·간식의 추가 버튼을 누르면 해당 식사 구분으로 기록 화면을 열며, 저장된 사진과 실제 영양 섭취량을 표시합니다. 모바일에서는 카드를 세로로 배치합니다.

PC의 모든 사용자 화면은 콘텐츠 영역 전체 너비를 사용하는 와이드 배치를 유지합니다. 홈 기록 안내의 문구·버튼과 식사 일러스트를 좌우로 배치합니다. 좁은 화면은 기존 반응형 배치를 사용합니다.

음식 추가의 영양 미리보기는 총 열량·탄단지 가로 누적 그래프·당류·나트륨을 표시합니다. 그래프는 실제 영양값을 4/4/9 kcal/g으로 환산한 구성 비율이며 목표 비율을 의미하지 않습니다.

히스토리는 음식 한 개당 한 행의 데이터베이스형 표로 날짜·식사·음식·섭취량과 6개 영양 수치를 표시합니다. 음식명 검색·식사 필터·날짜 정렬을 제공하며 모바일에서는 표를 가로로 스크롤할 수 있습니다.

홈의 주간 달력 날짜를 누르면 해당 날짜의 식단·저장 사진·영양 합계를 확인합니다. 날짜 입력으로 다른 주도 조회할 수 있고 “오늘로 돌아가기”로 오늘의 기록을 다시 표시합니다.

공통 로고는 `frontend/src/Visuals.jsx`의 Brand SVG와 워드마크로 표시하며 크기와 색상은 `frontend/src/reference.css`에서 조정합니다.

홈페이지 배너 배경은 `frontend/public/images/hero-bg.webp`를 사용합니다. 같은 파일명으로 교체하면 배경에 반영됩니다.

주요 기능 카드에는 같은 폴더의 `feature-meal.webp.png`, `feature-nutrition.webp.png`, `feature-recommendation.webp.png`, `feature-nearby.webp.png`를 사용합니다. 처음 세 카드는 기존 기능에 연결되며 주변 맛집·제품은 준비 중입니다.

음식 확인과 영양 계산을 기반으로 식단 기록·오늘 상태·식사 추천까지 연결하는 웹 서비스입니다. 내부 프로젝트 버전은 CaloDetect 2.0이며 사용자 화면에는 CaloDetect를 사용합니다.

**팀 공용 저장소 / Source of Truth:** <https://github.com/wndnsud-ui/CaloDetect>

UX 변경과 미확정 정책은 [보류 및 결정 대기 사항](docs/rules/PENDING_DECISIONS.md)에서 관리합니다. 목표 설정은 왼쪽 입력 카드와 오른쪽 칼로리 결과 카드로 구성합니다. 계산·저장 후에도 두 카드를 유지하며, 모바일에서는 결과가 입력 아래에 표시됩니다. 탄단지 비율은 확정 전까지 미설정으로 표시합니다.

개발 기준은 [v11 업무지시서](docs/rules/CaloDetect_Codex_통합_업무지시서_20261002_v11.md)입니다. 원문은 보존하며 결정 변경은 [CHANGELOG.md](CHANGELOG.md)에 기록합니다. 현재 회원·사진 분석·식단 저장·추천을 통합했습니다. **가입·이미지·추천 정책 설정은 팀 확정 전이며 운영 배포 상태가 아닙니다.**

## 현재 구현 범위

| 구성 | 현재 상태 |
|---|---|
| React + Vite 사용자 웹 | 첨부 이미지 기준 홈페이지, 로그인/가입, 회원정보 수정, 프로필·목표 저장, 사진 분석/수정, 식단 저장, 오늘 상태, History, 추천, 동의 설정 |
| FastAPI | 회원·프로필·식단·탐지·추천·Correction·관리자 QA API |
| PostgreSQL/SQLAlchemy | 회원/식단/탐지/추천/QA 영구 저장, 순차 Alembic revision 20261002_01 → 20261002_02 |
| 기존 YOLO26m | best.pt 재사용. 원본 유지. JPG/PNG 분석 API, 이미지별 탐지 ID 반환 |
| 기존 Streamlit | app.py 보존, 별도 streamlit/admin_qa.py 인증된 관리자 QA 클라이언트 추가 |
| 정책 미확정 | 동의 문구, 이미지 저장/보관, 추천 출처/기준·영양 목표 |

가상 회원/식단/추천 결과를 실제 데이터처럼 제공하지 않습니다. 영양값은 사용자 승인된 기존 `CaloDetect_nutrition_all_matched.csv`를 사용합니다. v11의 `(1).csv`는 현재 없으며 원본 데이터를 변경하지 않았습니다. 추천 엔진은 남은 칼로리·최근 음식 반복·제외 음식·선호 분류·다양성을 적용하고 실제 데이터의 영양값과 이유를 반환합니다. 미정 탄단지 목표·당류/나트륨 기준·끼니 적합성을 평가했다고 표시하지 않습니다.

## 새 웹 환경 실행 — 팀원용 간편 설치

[팀원 실행 가이드](CaloDetect_팀원_실행가이드.md)의 터미널 A/B 방식을 반영한 로컬 개발용 안내입니다. 최초 클론은 해당 가이드의 `develop`을 사용하며, 기존 저장소의 브랜치는 자동 변경하지 않습니다. 코드 변경은 아래 팀 GitHub 협업 방침의 브랜치·PR 절차를 따릅니다. DB 볼륨과 기존 폴더는 삭제하지 않습니다.

`.env`와 PostgreSQL 데이터는 GitHub에 올리지 않습니다. `scripts/setup_local.ps1`은 첫 설정에서 비공개 `%LOCALAPPDATA%\CaloDetect\local.env`에 환경 설정을 보관하고, 같은 Windows 계정의 새 클론에서는 이를 재사용합니다. DB는 고정된 Docker volume `calodetect_postgres_data`를 사용하므로 저장소 폴더 이름이나 재클론이 달라져도 같은 PC의 기존 회원·식단 데이터를 유지합니다. 다른 PC는 별도 로컬 DB를 사용합니다. `.env`·비밀번호·API 키·업로드 사진을 커밋하지 마세요.

> **사전 필수 프로그램**
> - **Docker Desktop** (반드시 먼저 실행해 두세요)
> - **Git**, **Python 3.12 권장(3.10 이상)**, **Node.js 22.12 이상(또는 20.19 이상)**
> - 터미널은 Windows **PowerShell**(`PS C:\...>`)을 기준으로 작성되었습니다.

---

### 주요 접속 주소

- **웹 프런트엔드:** [http://localhost:5174](http://localhost:5174)
- **백엔드 API 문서 (로컬 개발 서버):** [API 문서](<http://[::1]:8000/docs>)

---

### 1. 처음 설치 및 전체 실행하기

#### [Step 1] 코드 내려받기 (Git Clone)
VS Code에서 새 터미널을 열고(PowerShell), 아래 블록 전체를 복사해 실행합니다.
*(이미 정상적으로 클론된 폴더가 있다면 자동으로 감지하고 다음 단계로 안내합니다.)*

```powershell
New-Item -ItemType Directory -Path 'C:\projects' -Force | Out-Null
Set-Location 'C:\projects'

if (Test-Path .\CaloDetect\.git) {
    Write-Host "이미 CaloDetect 저장소가 존재합니다. Step 2로 이동합니다." -ForegroundColor Green
    Set-Location 'C:\projects\CaloDetect'
} else {
    if (Test-Path .\CaloDetect) {
        throw "기존 CaloDetect 폴더가 있습니다. 내용을 확인하고 다른 경로에 클론하세요."
    }
    git clone --branch develop https://github.com/wndnsud-ui/CaloDetect.git
    if ($LASTEXITCODE -ne 0) { throw '클론 실패. 저장소 접근 권한과 develop 브랜치를 확인하세요.' }
    Set-Location 'C:\projects\CaloDetect'
}

git branch --show-current
git remote -v
Get-ChildItem -Name
```

---

#### [Step 2] 터미널 A — 가상환경 구축, DB 초기화, 백엔드 서버 구동
* **주의:** `Application startup complete`가 뜨면 **이 창을 절대 닫지 마세요.**

```powershell
Set-Location 'C:\projects\CaloDetect'

# 1. Python 가상환경 생성 및 패키지 설치
if (-not (Test-Path .\.venv-backend)) {
    py -m venv .venv-backend
    if ($LASTEXITCODE -ne 0) { throw '명령 실패. 오류를 해결한 뒤 해당 단계부터 다시 실행하세요.' }
}
.\.venv-backend\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw '명령 실패. 오류를 해결한 뒤 해당 단계부터 다시 실행하세요.' }
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -r backend/requirements-vision.txt
if ($LASTEXITCODE -ne 0) { throw '명령 실패. 오류를 해결한 뒤 해당 단계부터 다시 실행하세요.' }

# 2. 같은 PC의 기존 .env와 DB volume 재사용·신규 설정·테스트 계정 준비
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw '로컬 설정 또는 데이터베이스 준비에 실패했습니다.' }

# 5. 백엔드 서버 실행
$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

---

#### [Step 3] 터미널 B — 프런트엔드 설치 및 실행
VS Code 상단 메뉴에서 **터미널 → 새 터미널**을 열어 새 창(PowerShell)에 붙여넣습니다.
포트 충돌 시 아래 오류 해결 안내로 사용 중인 앱을 확인하세요.

```powershell
Set-Location 'C:\projects\CaloDetect\frontend'


# 패키지 설치 및 개발 서버 실행
npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw '명령 실패. 오류를 해결한 뒤 해당 단계부터 다시 실행하세요.' }
$env:CALODETECT_API_TARGET='http://[::1]:8000'
npm.cmd run dev -- --host localhost --port 5174
```

> 브라우저에서 **http://localhost:5174** 로 접속한 뒤 **회원가입**을 진행하고 테스트를 시작하세요!

---

### 2. 평소 재실행할 때 (설치 완료 후 다시 켤 때)

Docker Desktop을 켜고 VS Code에서 프로젝트 폴더를 엽니다.

#### 터미널 A (백엔드)
```powershell
Set-Location 'C:\projects\CaloDetect'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw '로컬 설정 또는 데이터베이스 준비에 실패했습니다.' }
$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

#### 터미널 B (프런트엔드)
```powershell
Set-Location 'C:\projects\CaloDetect\frontend'
$env:CALODETECT_API_TARGET='http://[::1]:8000'
npm.cmd run dev -- --host localhost --port 5174
```

---

### 3. 자주 발생하는 오류 및 해결법

| 증상 | 원인 | 해결책 |
|---|---|---|
| `FATAL: password authentication failed` | 기존 DB와 현재 `.env`가 서로 다른 설정 사용 | 기존 클론에서 `.env`를 보존하거나 `scripts/setup_local.ps1`의 안내를 따르세요. `docker compose down -v` 및 volume 삭제는 회원·식단 데이터를 지우므로 사용하지 마세요. |
| `Port 5174 is already in use` | 이전 프런트엔드 프로세스가 종료되지 않음 | `Get-NetTCPConnection -LocalPort 5174 -State Listen -ErrorAction SilentlyContinue`로 PID를 확인하고 `Get-Process -Id 확인한PID`로 앱을 확인합니다. 자신의 이전 개발 서버 터미널에서 `Ctrl+C`로 종료하세요. |
| `python.exe 용어가 인식되지 않습니다` | 가상환경(`.venv-backend`) 미설치 | Step 2의 `py -m venv .venv-backend` 재실행 |
| 서버 종료 방법 | - | 각 터미널에서 `Ctrl + C` 누름 |

의존성이 변경되면 패키지 설치 명령을 다시 실행하고, 새 migration이 추가되면 `scripts/setup_local.ps1`을 다시 실행하세요. 로컬 Backend는 Docker의 IPv4 포트 전달과 충돌하지 않도록 IPv6 loopback(`::1`)에서 실행합니다. 다른 포트를 쓰면 Frontend의 `CALODETECT_API_TARGET`도 `http://[::1]:포트`로 맞춥니다.

기존 기본 포트 5173을 사용하려면 Backend의 `FRONTEND_ORIGIN`과 Frontend 실행 명령의 `--port`를 모두 5173으로 맞추세요. macOS/Linux에서는 `npm`과 `.venv-backend/bin/python`을 사용합니다. 로컬 테스트 설정은 운영 동의·이미지 보관 정책 확정을 의미하지 않습니다.

### 일간·월별 식단 분석

회원 홈의 오늘의 식단은 아침·점심·저녁·간식별 저장한 음식명·칼로리와 저장 완료 상태를 표시합니다. 사진 분석 결과를 식단으로 저장하면 해당 사진도 표시되며, 직접 입력한 식단은 직접 기록으로 표시합니다. 사진 선택만 한 상태는 저장된 식단에 포함되지 않습니다.

로그인 후 사이드바의 **식단 분석**에서 일간·월별 차트를 확인합니다. 날짜 또는 월과 영양 항목(칼로리·탄수화물·단백질·지방·당류·나트륨)을 선택할 수 있습니다. 일간 분석은 식사별 구성과 하루 합계를, 월별 분석은 일별 추이와 기록한 날의 하루 평균을 표시합니다. 월 차트의 날짜를 누르면 해당 일간 분석으로 이동합니다.

한국 시간의 식단 날짜를 기준으로 저장된 영양값을 Backend에서 집계합니다. 미기록일은 평균에서 제외하며 일부 식사만 기록한 날은 포함합니다. 영양소 목표·당류·나트륨 기준은 기존 미확정 상태를 유지합니다.

### 로컬 테스트 로그인

현재 개발 DB에 생성한 테스트 계정으로 로그인할 수 있습니다.

1. <http://localhost:5174>에 접속합니다(위 간편 실행 기준).
2. 상단 **로그인**을 누르고 이메일 로그인 방식을 선택합니다.
3. 아래 이메일과 비밀번호를 입력합니다.

| 항목 | 값 |
|---|---|
| 이메일 | `test@calodetect.local` |
| 비밀번호 | `CaloTest!2026` |
| 권한 | 일반 사용자 (`user`) |

로컬 개발 전용 계정입니다. 최초 설치에서 migration 다음에 실행하는 `backend.scripts.seed_local_test_account`가 로컬 테스트 설정이 켜진 개발 DB에 생성합니다. 기존 계정이 있으면 비밀번호나 데이터를 덮어쓰지 않습니다. 각자 로컬 DB에 생성되므로 회원·식단 데이터는 PC마다 별도이며, 운영 환경에서는 생성 명령이 차단됩니다.

### 정책 설정과 사진 분석 환경

사용자가 승인한 **로컬 이메일 테스트 가입**은 `.env`에 `APP_ENV=development`, `LOCAL_TEST_SIGNUP=true`, `FRONTEND_ORIGIN=http://localhost:5173`을 설정하고 Backend를 재시작하면 활성화됩니다. 만 18세 이상이며 화면의 테스트용 안내에 명시적으로 동의해야 합니다. 실제 개인정보 대신 테스트용 이름·이메일을 사용합니다. 승인된 `SERVICE_CONSENT_TEXT`가 없는 경우에만 테스트 안내를 사용하며 해당 내용을 개발 DB의 동의 이력에 저장합니다. 로컬 호스트와 루프백 접속에서만 허용하고 전달된 프록시 접속은 차단합니다. `APP_ENV=production` 또는 `LOCAL_TEST_SIGNUP=false`이면 테스트 가입을 허용하지 않습니다. `.env.example` 기본값은 운영 차단을 유지합니다. 소셜 가입은 이 테스트 설정으로 활성화하지 않습니다.

인증 방식은 이메일/비밀번호 및 사용자 요청으로 추가한 Google 로그인 + HttpOnly 세션 쿠키입니다. 로그인 후 마이페이지에서 이름을 수정할 수 있으며 이메일과 role 변경은 제공하지 않습니다. HTTPS 운영에서는 `COOKIE_SECURE=true`가 필요합니다. 홈페이지 기능 카드는 음식 영양 조회·목표 계산·오늘의 식단으로 연결되고 웹앱은 실제 API 기록을 표시합니다. 홈페이지의 휴대폰·포케·기능 카드·하단 배너 이미지 영역은 고품질 이미지 선정 전까지 빈 박스로 유지합니다. 회원 웹앱의 기존 CSS 식사 일러스트는 유지합니다. 위치 기반 맛집/포인트는 후속 범위입니다.

Vite의 `CALODETECT_API_TARGET` 환경변수로 검증용 API 주소를 바꿀 수 있습니다(로컬 개발 서버 기준 `http://[::1]:8000`). 다른 웹 포트를 쓰면 Backend `FRONTEND_ORIGIN`도 해당 주소와 일치시켜야 합니다. 컨테이너 migration은 `docker compose exec backend python -m alembic -c backend/alembic.ini upgrade head`로 실행합니다.

가입·로그인 최소 연령은 사용자 승인에 따라 **만 18세**이며 `AGE_MIN` 기본값은 `18`입니다. 가입 시 입력한 만 나이를 기준으로 검사하며 본인인증이나 생년월일에 따른 자동 갱신은 제공하지 않습니다. 기존 계정의 로그인과 인증 API도 연령을 확인합니다. `SERVICE_CONSENT_TEXT`는 아직 미확정이므로 승인된 문구가 설정되어야 회원가입을 활성화합니다. 동의 문구는 가입 요청과 DB에 보존합니다. 선택 모델 개선 동의는 `MODEL_IMPROVEMENT_CONSENT_TEXT` 확정·설정 후 활성화하며, 문구 미설정 상태에서도 기존 동의 철회는 허용합니다. `IMAGE_STORAGE_DIR` 미설정이면 사진 업로드는 정책 안내를 반환하고 음식 직접 선택·식단 저장은 가능합니다. `RECOMMENDATION_ENABLED=true`, `RECENT_MEAL_WINDOW`는 기존 CSV를 추천 출처로 사용하는 개발 기준이 승인된 뒤 설정합니다. 예시 `3`을 운영 정책으로 간주하지 않습니다. 연령 외 미확정 정책은 TBD를 유지합니다.

음식 추가 화면의 **사진 선택** 또는 **사진 바로 찍기**로 JPG/PNG(최대 10MB)를 선택하고 미리볼 수 있습니다. 모바일 촬영은 기기의 카메라 입력을 사용하고 PC는 웹캠 권한이 필요합니다(HTTPS 또는 localhost). 사진 선택은 로그인 없이 가능하며, 선택 사진은 로그인 중 유지되고 새로고침하면 해제됩니다. 로그인 후 **사진 분석하기 → 음식/섭취량 확인 → 식단 저장하기** 순서로 기록합니다. 촬영 취소·화면 이탈 시 웹캠 사용을 종료합니다. 서버 분석에는 기존 이미지 저장 정책 설정과 YOLO 환경이 필요합니다.

사진 분석은 기존 `.venv`가 있으면 그 Python/YOLO 환경을 재사용하는 worker를 호출합니다. 다른 PC에서 기존 환경이 없으면 새 환경에 설치합니다:

로컬 사진 분석 테스트는 `APP_ENV=development`, `LOCAL_TEST_IMAGE_ANALYSIS=true`, `IMAGE_STORAGE_DIR=.private-uploads`로 활성화합니다. Backend를 재시작한 뒤 로그인 → 사진 선택 → **사진 분석하기**를 누릅니다. 테스트 원본 사진은 Git에서 제외된 `.private-uploads`에 저장되고 분석 결과는 개발 DB에 기록됩니다. 자동 삭제·보관기간은 아직 정하지 않았으므로 테스트 사진만 사용하며, 이 설정을 운영 정책으로 사용하지 않습니다. 루프백 접속에서만 테스트 분석·원본 조회를 허용합니다. 모델 개선 선택 동의와 관리자 QA 조건은 유지합니다. YOLO 첫 실행 안내는 JSON 결과와 분리하고 런타임 설정은 `.runtime-logs/ultralytics`에 저장합니다.

```powershell
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-vision.txt
```

분석 기준은 conf=0.11, iou=0.45, imgsz=960, CPU입니다. 파일명 대신 서버 UUID로 이미지를 구분하고 사용자별 이미지 권한을 검사합니다. 탐지되지 않거나 추론 오류가 나도 직접 음식 선택을 제공합니다.

### Google 로그인 설정

로그인 화면 상단의 **로그인 / 회원가입**에서 방식을 선택합니다. 회원가입에는 **Google로 회원가입**, **이메일로 회원가입**을 제공하며, 소셜 가입은 비밀번호를 따로 입력하지 않습니다. 서버 설정이 없는 제공자는 연결 준비 상태를 안내하고 버튼을 누르면 진행할 수 없는 이유를 표시합니다. 기존 이메일 로그인은 신규 가입 동의 문구 설정 여부와 무관하게 사용할 수 있습니다. 새 소셜 계정은 제공자 인증 후 이름·만 나이·승인된 서비스 동의를 입력해 가입을 마칩니다. 기존 소셜 계정은 `(oauth_provider, oauth_subject)`로 로그인하며 이메일 변경으로 새 계정을 만들거나 기존 이메일 회원과 자동 연결하지 않습니다. 기존 이메일과 충돌하면 기존 방식으로 로그인해야 하며 계정 연결 UI는 제공하지 않습니다.

사용자 요청에 따라 [가입 동의 검토용 초안](docs/rules/SERVICE_CONSENT_DRAFT.md)을 작성했습니다. 초안을 환경변수로 자동 적용하지 않습니다. Google 로그인은 공개 Web Client ID와 기존 ID 토큰 검증 흐름을 사용하므로 Client Secret을 새 클론마다 복사할 필요가 없습니다. OAuth state 서명키·DB 비밀번호는 비공개 `.env`를 같은 PC의 `%LOCALAPPDATA%\CaloDetect\local.env`에서 재사용하고, 운영 설정과 비밀은 GitHub에 올리지 않습니다. 승인된 로컬 동의와 만 나이를 확인하며 기존 이메일 계정과 자동 연결하지 않습니다. Google Cloud의 테스트 사용자 등록이 필요합니다.

1. Backend 의존성을 설치합니다: `.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements.txt`. 기본 Google GIS 흐름은 공개 Client ID와 Backend의 서명·발급자·대상 앱·만료·nonce 검증을 사용하며 Client Secret은 필요하지 않습니다. Secret이 비공개 `.env`에 설정된 환경은 Authorization Code + PKCE도 사용합니다. state/nonce와 신규 가입 정보는 5분짜리 HttpOnly 쿠키로 보호하며 이메일·이름·토큰을 URL에 싣지 않습니다.
2. Google Cloud에서 웹용 OAuth 클라이언트를 만들고 승인된 JavaScript 원본에 `http://localhost:5174`를 등록합니다. Authorization Code 흐름을 쓸 경우 승인된 리디렉션 URI에 `http://localhost:8000/api/auth/google/callback`도 등록합니다. OAuth 동의 화면은 테스트용 사용자로 제한하고 실제 Google 계정을 테스트 사용자로 추가합니다. 공개 `GOOGLE_CLIENT_ID`는 `.env.example`에 포함되어 새 클론에서도 사용됩니다.
3. `scripts/setup_local.ps1`이 `OAUTH_STATE_SECRET`과 PostgreSQL 접속 정보를 생성하고 `%LOCALAPPDATA%\CaloDetect\local.env`에 저장합니다. 새 클론도 같은 Windows 계정이면 이 설정을 재사용합니다. HTTPS 환경에서는 `COOKIE_SECURE=true`, `FRONTEND_ORIGIN`은 실제 웹앱 원본으로 설정합니다.
4. 서버를 재시작하고 Google의 로그인·취소·신규 가입·재로그인을 확인합니다. 기본 API와 `/api` 프록시를 같은 웹앱 원본에서 사용합니다. Google 신규 가입은 서비스 동의와 만 나이 확인을 마친 후 완료되며, 기존 이메일 계정과 자동 연결하지 않습니다. 소셜 로그인은 프로필 인증만 요청하며 Google Drive·Calendar 또는 Apple Health 권한을 요청하지 않습니다.

제공자 앱 자격정보가 없는 환경에서는 실제 Google 로그인 검증을 완료할 수 없습니다. 자동 테스트는 로컬 RSA 서명 토큰으로 인증 검증·18세 경계·동의·이메일 충돌을 검사하며 제공자 공개키 조회를 격리합니다. 기존 DB 식별자 컬럼과 비밀번호 NOT NULL 제약을 보존하여 migration은 추가하지 않습니다. 소셜 계정의 비밀번호 컬럼은 공개하지 않는 무작위 비밀번호 해시로 채우며 비밀번호 설정·계정 연결·소셜 토큰 갱신·제공자 연결 해제는 이번 범위에 포함하지 않습니다.

### 이메일 계정 비밀번호 찾기·변경 (Gmail SMTP)

로그인 화면의 **비밀번호 찾기**에 이메일 가입 주소를 입력하면 재설정 링크를 발송합니다. 링크는 15분 동안 유효하며 비밀번호 변경 후 다시 사용할 수 없습니다. **마이페이지 → 비밀번호 변경**에서는 현재 비밀번호와 새 비밀번호·확인을 입력합니다. 새 비밀번호는 8~128자이며 기존 비밀번호와 달라야 합니다. 변경 완료 시 모든 기기의 기존 세션을 종료하고 새 비밀번호로 재로그인합니다. Google 가입 계정은 Google 계정 설정에서 비밀번호를 관리합니다.

발신 Gmail 계정에서 2단계 인증을 활성화하고 [Google 앱 비밀번호](https://support.google.com/mail/answer/185833?hl=ko)를 발급하세요. 계정의 일반 비밀번호나 Google OAuth Client Secret을 SMTP 비밀번호로 사용하지 않습니다. 서버의 비공개 `.env`에 아래 값을 설정합니다. [Gmail SMTP 공식 설정](https://support.google.com/mail/answer/7104828?hl=ko)은 STARTTLS 포트 587을 사용합니다.

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USERNAME=발신계정@gmail.com
SMTP_FROM=발신계정@gmail.com
SMTP_PASSWORD=발급한앱비밀번호
PASSWORD_RESET_SECRET=32자이상의무작위서버비밀키
```

`PASSWORD_RESET_SECRET`은 `.venv-backend\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"`로 생성해 `.env`에만 저장합니다. 앱 비밀번호와 재설정 비밀키를 Git에 올리지 않습니다. `FRONTEND_ORIGIN`은 메일에서 열 실제 프런트엔드 주소여야 하며 운영 환경에서는 HTTPS가 필수입니다. 로컬은 `APP_ENV=development`와 localhost 주소를 사용합니다. 변경 후 Backend를 재시작하고, Docker Backend는 `docker compose up -d --force-recreate backend`로 환경변수를 다시 반영합니다. 설정이 완성되지 않으면 화면에 발송 준비 안내를 표시합니다.

등록되지 않은 이메일·Google 계정에도 동일한 응답을 표시합니다. 실제 발송 실패는 계정 여부를 노출하지 않도록 서버에 일반 오류로 기록합니다. 요청 제한은 프로세스별로 발송 요청 IP당 10회·이메일당 3회/15분, 재설정 IP당 20회/15분, 변경 사용자당 5회/15분입니다. 여러 worker/서버를 운영하면 게이트웨이에서 공통 제한을 추가해야 합니다. 토큰은 URL fragment로 전달해 HTTP 요청·접근 로그에 담기지 않으며 화면 로드 시 주소에서 제거합니다. DB migration은 필요하지 않습니다.

### 관리자 QA 실행

최초 관리자는 A 담당이 내부 CLI로만 생성합니다. 공개 승격 API는 없습니다.

```powershell
.\.venv-backend\Scripts\python.exe -m backend.scripts.create_admin --email admin@example.com --age 승인된연령
.\.venv\Scripts\python.exe -m streamlit run streamlit/admin_qa.py --server.port 8502
```

비밀번호는 CLI에서 숨김 입력합니다. 관리자 QA는 FastAPI에 로그인하고 서버의 /admin/* API만 호출합니다. 일반 사용자는 403입니다. 동의한 사용자 수정만 PENDING 후보로 등록하고, 철회 시 대기 샘플을 제외합니다. APPROVED 이력은 유지하며 재수정은 새 검수 후보로 남깁니다. 실제 재학습은 구현하지 않았습니다.

## PostgreSQL / Docker 개발 실행

먼저 `scripts/setup_local.ps1`을 실행해 로컬 `.env`, DB 사용자/URL 및 테스트 계정을 준비합니다. PostgreSQL volume 이름은 `calodetect_postgres_data`로 고정되어 같은 PC의 새 클론도 기존 로컬 DB를 다시 사용합니다. volume을 삭제하면 회원·식단 데이터가 제거되므로 `docker compose down -v`를 사용하지 마세요.

```powershell
docker compose up --build -d
```

이 구성은 PostgreSQL과 Backend만 실행합니다. Frontend는 위 npm 개발 명령으로 별도 실행합니다. `GET /health/database`로 DB 연결을 확인할 수 있습니다. `docker compose down`은 컨테이너만 중지하며 고정 저장 volume은 유지합니다. 다른 PC와 데이터를 공유하려면 별도 운영 PostgreSQL이 필요하며 로컬 Docker DB는 GitHub에 업로드되지 않습니다. 운영 배포 구성은 [DEPLOYMENT.md](docs/operations/DEPLOYMENT.md)를 참고하세요.

## 검사

2026-10-07 업로드 전 확인: Backend 테스트 62개 통과·기본 검사에서 실제 YOLO smoke 1개 제외, 격리된 PostgreSQL+실제 YOLO 통합 테스트 9개 통과, React production build·pip check 성공. 임시 두 클론에서 비공개 DB·OAuth·SMTP 설정과 비밀키 재사용 확인, 기존 로컬 계정·비밀번호 해시·OAuth 식별자 및 프로필·식단 건수 유지 확인, 비공개 DB archive 생성·목록 검사 완료. 실제 Gmail 발송은 발신 계정 설정 후 검증이 필요하며 Google 실계정 인증 검증은 별도입니다. 음식 정확도 평가는 포함하지 않습니다. 이전 브라우저 검증 기록은 [화면과 검증 상세](docs/UI_VALIDATION.md)를 참고하세요.

```powershell
.\.venv-backend\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm.cmd run build
```

실제 PostgreSQL+YOLO 검사(격리된 테스트 스키마 생성 후 제거):

```powershell
$env:RUN_POSTGRES_TESTS='1'
$env:RUN_VISION_TEST='1'
.\.venv-backend\Scripts\python.exe -m pytest backend/tests/test_p0_flow.py -q
Remove-Item Env:RUN_POSTGRES_TESTS
Remove-Item Env:RUN_VISION_TEST
```

기존 앱 검증은 기존 `.venv`에서 `python validate_data.py`로 수행합니다. 기존 데이터와 모델은 그대로 유지합니다.

## 팀 GitHub 협업 방침

모든 팀원은 이 저장소 하나를 기준으로 작업합니다. 외부 복사본이나 `.upload-repo`를 팀 기준으로 사용하지 않습니다. 로컬 작업 시작 전에 `git remote -v`로 origin이 `https://github.com/wndnsud-ui/CaloDetect.git`인지 확인하세요.

### 최초 클론

```bash
git clone https://github.com/wndnsud-ui/CaloDetect.git
cd CaloDetect
git remote -v
git switch main
git pull --ff-only origin main
```

기존 로컬 프로젝트가 이 저장소를 이미 연결했다면 다시 `git init`하거나 중첩 클론하지 않습니다. 필요한 경우 `git remote set-url origin https://github.com/wndnsud-ui/CaloDetect.git`으로 주소를 정정하세요.

### 브랜치와 작업 순서

`main`은 검증된 통합 코드입니다. 직접 대규모 변경·직접 push·force push를 하지 않습니다. `feature/*`, `fix/*`, `docs/*` 브랜치에서 작업하고 PR로 합칩니다. `develop`은 팀이 실제 생성하고 통합 기준으로 확정한 뒤 사용합니다. 현재 명령은 main 기준입니다.

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/meal-scan
# 구현 → 테스트 → 변경 내용 확인
git status
git diff
git add 변경한파일경로
git commit -m "feat: 음식 분석 API 연결"
git push -u origin feature/meal-scan
```

`git add .` 대신 관련 파일을 지정하고 staged diff(`git diff --cached`)를 확인하세요. 새 기능/수정/문서는 `feat:`, `fix:`, `docs:` 등의 접두어로 기능 단위 커밋을 권장합니다. 개인 환경·비밀키·업로드 사용자 사진을 커밋하지 않습니다.

### PR와 머지

1. GitHub에서 작업 브랜치 → main으로 Pull Request를 만듭니다.
2. PR에 문제/변경 후 동작, 변경 범위, 실행한 검사와 결과, DB·의존성 변경, TBD 영향 여부를 적습니다.
3. 다른 팀원 최소 1명이 검토하고 테스트 결과를 확인한 후 합칩니다. 기능 단위 squash merge를 권장합니다.
4. 머지 후 로컬 main을 `git pull --ff-only origin main`으로 갱신합니다. 작업 브랜치는 필요 없어진 뒤 삭제합니다.

GitHub 관리자는 main에 PR 필수, 최소 승인 1명, force push/삭제 금지의 branch protection 또는 ruleset을 설정하는 것을 권장합니다. **이 README 작성만으로 GitHub 보호 설정이 적용되지는 않습니다.** CI 필수 검사 지정은 실제 CI가 추가된 뒤 설정합니다.

### 최신 main 반영과 충돌 해결

먼저 변경을 커밋하거나 `git stash push -m "작업 임시 보관"`으로 보관한 뒤 자신의 작업 브랜치에서:

```bash
git fetch origin
git merge origin/main
# 충돌이 있으면 파일의 충돌 표시를 해결하고 검사 실행
git add 해결한파일경로
git commit
git push
```

해결이 어려우면 담당자와 확인하고 `git merge --abort`로 병합 전 상태로 돌아갑니다. 공유 브랜치를 임의 rebase/force push하지 않습니다. `git reset --hard`, 원본 모델/CSV 덮어쓰기로 충돌을 해결하지 않습니다.

### 담당과 공동 파일

| 담당 | 범위 |
|---|---|
| A · Backend Core | Auth, Profile, DB, API schema, Meal/Today, 관리자 권한, Alembic |
| B · Vision/Data/Recommendation | YOLO, 기존 데이터, 추천, Detection/Correction, Streamlit QA |
| C · Frontend/Integration/Deploy | React, API 통합, Docker/배포 |

**Alembic revision 생성은 A만 수행합니다.** B/C는 필요한 스키마 변경을 A에게 전달합니다. 모델·CSV·YAML 원본은 보존합니다. 공동 파일 변경은 PR에서 명시하고, 요청·응답·오류 schema는 API 담당자와 맞춥니다. P1은 P0 완료 뒤에만 시작합니다.

### 매 작업 종료 확인

- 실제 변경 파일과 staged diff 확인, 관련 검사 실행.
- 실행법 변경 시 README, 정책 변경 시 CHANGELOG 갱신.
- 원본 업무지시서·모델·데이터 보존 및 secret 제외 확인.
- PR/머지 후 main 최신 상태 확인.

## 프로젝트 문서

[개발 규칙](AGENTS.md) · [구현 계획/TBD](docs/planning/IMPLEMENTATION_PLAN.md) · [구조](docs/design/ARCHITECTURE.md) · [데이터 스키마](docs/design/DATA_SCHEMA.md) · [모델 현황](docs/model/MODEL_EXPERIMENTS.md) · [로드맵](docs/planning/ROADMAP.md) · [변경 이력](CHANGELOG.md)

## 기존 Streamlit 실행 안내

최초 설치는 `01_SETUP_AND_RUN.bat`, 이후 실행은 `02_RUN_ONLY.bat`을 더블 클릭하세요.
현재 PC에 설치된 Python과 프로젝트 내 차트 패키지를 사용합니다.
가상환경이 있으면 해당 환경을 우선 사용하며, 준비된 환경이 없으면 설치 스크립트를 실행합니다.

## 모델 및 데이터

- `best.pt`: 프로젝트 폴더에 있는 최신 모델 (150 클래스)
- `data.yaml`: 클래스 번호 0~149와 한글 음식명
- `CaloDetect_nutrition_all_matched.csv`: YAML 순서대로 정렬된 150행
- `data_config.py`: 경로와 컬럼 정의, 데이터 검증
- `validate_data.py`: 실제 모델/YAML/CSV 매칭 확인

앱은 프로젝트 폴더의 `best.pt`를 사용합니다. 모델을 교체한 뒤에는 실행 중인 앱을 종료하고 다시 실행하세요.
앱, YAML, CSV, 샘플 경로는 실행하는 폴더에 영향을 받지 않습니다.

## 영양 CSV 컬럼

| 컬럼 | 의미 / 단위 |
| --- | --- |
| class_id | data.yaml의 클래스 번호 (0~149) |
| food_name | 모델의 한글 음식명과 정확히 일치 |
| category | 음식 분류 |
| unit | 영양값의 기준 섭취량 (원본 값 유지) |
| cal | kcal |
| carbs | 탄수화물 g |
| protein | 단백질 g |
| fat | 지방 g |
| sugar | 당류 g |
| sodium | 나트륨 mg |

영양 수치는 원본 그대로 유지했습니다. 각 수치는 `unit`에 적힌 기준량의 값입니다.
음식명 누락/중복, 잘못된 클래스 번호, 빈 분류/기준량, 음수 또는 잘못된 영양 수치는 실행 시 오류로 알려줍니다.

## 다른 PC에서 최초 설치

Python 3.10 이상이 설치된 상태에서 `01_SETUP_AND_RUN.bat`을 실행하세요.
패키지 설치 후 모델과 컬럼을 검증하고 Streamlit을 실행합니다.
이후에는 `02_RUN_ONLY.bat`을 실행하세요.

직접 실행하는 경우 이 폴더에서:

```powershell
python -m pip install -r requirements.txt
python validate_data.py
python -m streamlit run app.py
```

접속 주소: http://localhost:8501

샘플 사진은 `samples/` 폴더에 넣거나 화면에서 업로드할 수 있습니다.
