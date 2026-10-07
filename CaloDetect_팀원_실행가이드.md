# CaloDetect 실행 명령 — 팀원 공유용

이번 업데이트의 변경 파일 목록·선택 다운로드·같은 PC 재클론·다른 PC DB 이전 조건은 [README의 업데이트와 데이터 보존](README.md#2026-10-07-develop-업데이트와-데이터-보존)을 먼저 확인하세요. GitHub에는 개인 회원 DB와 비밀 설정이 포함되지 않습니다.

Windows PowerShell 기준. Git·Python·Node.js·Docker Desktop 설치 필요.
**먼저 터미널 종류를 확인하세요.** `PS C:\...>`로 시작하면 PowerShell입니다. `C:\...>` 또는 `(.venv-backend) C:\...>`만 보이면 CMD이므로 아래 명령을 **먼저 따로 실행하고 Enter를 누른 뒤**, `PS` 프롬프트가 나오면 본문의 코드 블록을 붙여넣으세요. 새 터미널 B에서도 확인합니다.

```cmd
powershell.exe -NoProfile
```

**Docker Desktop을 먼저 켜세요. 명령 중 오류가 나면 다음 단계로 넘어가지 마세요.**
**웹 주소: http://localhost:5174**
각 상황에서 **터미널 A 실행 → A를 켜 둔 채 새 터미널 B 실행** 순서입니다.
**PowerShell에서는 해당 코드 블록 전체를 복사해서 붙여넣고 실행해 주세요. 한 줄씩 입력할 필요가 없습니다. 마지막 명령이 실행되지 않으면 Enter를 한 번 눌러 주세요.**
**터미널 A에서 `Application startup complete`가 나오면 A는 그대로 두고, 새 PowerShell 터미널 B에서 B 코드 전체를 붙여넣습니다.**
이미 서버가 실행 중이면 중복 실행하지 않습니다. 업데이트 전에는 기존 서버를 종료합니다.

## 1. 처음 클론했을 때 — 설치부터 실행까지

### 1-1. GitHub 저장소 클론하기

클론은 GitHub 프로젝트를 내 PC에 내려받는 작업입니다. **처음 한 번만** 진행합니다. 이미 클론한 팀원은 1-2로 넘어갑니다.

1. Git이 없다면 https://git-scm.com/downloads 에서 Windows용 Git을 설치합니다. 설치 후 VS Code를 다시 엽니다.
2. 브라우저에서 https://github.com/wndnsud-ui/CaloDetect/tree/develop 를 열어 저장소를 확인합니다. 접근 권한이 필요하면 자신의 GitHub 계정으로 로그인하고 팀 리드에게 저장소 접근 권한을 요청합니다.
3. VS Code에서 **터미널 → 새 터미널**을 누릅니다. 터미널의 프로필을 **PowerShell**로 선택합니다. 프롬프트가 `PS`로 시작하는지 확인합니다.
4. 아래 명령으로 `C:\projects`에 `CaloDetect` 폴더를 내려받습니다. GitHub의 `Code → HTTPS` 주소는 `https://github.com/wndnsud-ui/CaloDetect.git`입니다. 아래 명령은 `develop` 브랜치를 선택해서 받습니다.

**PowerShell (`PS` 프롬프트)에서 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.**

```powershell
git --version
if ($LASTEXITCODE -ne 0) { throw 'Git을 설치한 뒤 VS Code를 다시 열어 주세요.' }
New-Item -ItemType Directory -Path 'C:\projects' -Force | Out-Null
Set-Location 'C:\projects'
if (Test-Path .\CaloDetect) { throw 'CaloDetect 폴더가 이미 있습니다. 기존 클론을 확인하고 1-2로 넘어가세요.' }
git clone --branch develop --single-branch https://github.com/wndnsud-ui/CaloDetect.git
if ($LASTEXITCODE -ne 0) { throw '클론 실패. 기존 폴더가 있으면 그 폴더를 사용하세요.' }
Set-Location 'C:\projects\CaloDetect'
git branch --show-current
git remote get-url origin
Test-Path .\backend\requirements-dev.txt
Test-Path .\frontend\package.json
```

5. 다운로드가 끝나고 아래 결과가 나오면 클론 성공입니다. 인증 창이 뜨면 자신의 GitHub 계정으로 로그인합니다.

| 확인 명령 | 정상 결과 |
|---|---|
| `git branch --show-current` | `develop` |
| `git remote get-url origin` | `https://github.com/wndnsud-ui/CaloDetect.git` |
| 두 `Test-Path` 명령 | 각각 `True` |

6. VS Code에서 **파일 → 폴더 열기 → `C:\projects\CaloDetect` 선택 → 폴더 선택**을 누릅니다. 프로젝트 신뢰 확인이 나오면 직접 클론한 저장소인지 확인하고 진행합니다.
7. 왼쪽 탐색기에 `backend`, `frontend`, `README.md`가 보이는지 확인합니다. 다시 **터미널 → 새 터미널**을 열어 아래 1-2를 진행합니다.

**이미 받은 폴더를 삭제하거나 다시 클론하지 마세요.** 설치까지 완료한 경우에는 2번 또는 3번을 사용합니다. 클론만 했고 설치가 처음이면 1-2부터 진행합니다. Download ZIP으로 받은 파일은 Git 업데이트가 연결되지 않으므로 이 가이드는 `git clone`으로 받은 폴더를 기준으로 합니다.

### 1-2. 터미널 A — 설치·DB·백엔드 실행

기본 클론 위치는 `C:\projects\CaloDetect`입니다. 다른 위치에 이미 클론했다면 아래 첫 줄을 자신의 실제 경로로 바꾸세요.

**PowerShell (`PS` 프롬프트)에서 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.**

```powershell
Set-Location 'C:\projects\CaloDetect'
if (-not (Test-Path .\backend\requirements-dev.txt)) { throw '클론한 CaloDetect 폴더인지 확인하세요.' }

py -m venv .venv-backend
if ($LASTEXITCODE -ne 0) { throw 'Python 설치와 py 명령을 확인하세요.' }
.\.venv-backend\Scripts\python.exe -m pip install --upgrade pip
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -r backend/requirements-vision.txt
if ($LASTEXITCODE -ne 0) { throw '패키지 설치 실패. 오류를 해결하고 다시 설치하세요.' }

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw '로컬 설정·DB·테스트 계정 준비 오류를 확인하세요.' }

$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

### 1-3. 새 터미널 B — 프런트엔드 설치·실행

**둘 중 자신의 터미널에 맞는 블록 하나만 실행합니다.** `PS`로 시작하면 PowerShell, `C:\...>` 또는 `(.venv-backend) C:\...>`이면 CMD입니다. 새 터미널도 같은 종류라고 가정하지 말고 확인하세요.

**PowerShell (`PS` 프롬프트)에서 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.**

```powershell
if (Test-Path .\CaloDetect\frontend\package.json) { Set-Location .\CaloDetect\frontend }
elseif (Test-Path .\frontend\package.json) { Set-Location .\frontend }
elseif (-not (Test-Path .\package-lock.json)) { throw 'VS Code에서 클론한 CaloDetect 폴더를 열고 새 터미널을 실행하세요.' }
if (-not (Test-Path .\package-lock.json)) { throw 'CaloDetect의 frontend 폴더인지 확인하세요.' }
npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw '프런트엔드 설치 오류를 확인하세요.' }
$env:CALODETECT_API_TARGET='http://[::1]:8000'
npm.cmd run dev -- --host localhost --port 5174
```

**CMD에서는 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.** VS Code에서 클론한 CaloDetect 폴더 또는 그 상위 폴더를 연 상태에서 사용합니다.

```cmd
if exist "CaloDetect\frontend\package.json" cd /d "CaloDetect\frontend"
if exist "frontend\package.json" cd /d "frontend"
if exist "package-lock.json" (npm.cmd ci && set "CALODETECT_API_TARGET=http://[::1]:8000" && npm.cmd run dev -- --host localhost --port 5174) else (echo CaloDetect frontend 폴더에서 실행해 주세요.)
```

http://localhost:5174 → 로그인 → `test@calodetect.local` / `CaloTest!2026`.
같은 Windows 계정·PC에서 GitHub를 다시 클론하면 비공개 로컬 설정과 DB volume을 재사용합니다. 다른 PC의 테스트 계정과 식단은 해당 PC의 로컬 DB에 따로 생성되며 PC 간 자동 공유는 되지 않습니다.
Google 로그인은 Google Cloud OAuth 동의 화면에 테스트 계정을 등록하고 승인된 JavaScript 원본에 `http://localhost:5174`를 추가해야 합니다. 새 PC에서는 공개 Client ID 기반 로그인에 Client Secret이 필요하지 않습니다.

## 2. 업데이트된 것을 받아서 다시 실행할 때

기존 두 서버를 종료하고 VS Code에서 **기존 CaloDetect 폴더**를 엽니다.
아래는 `develop` 브랜치 기준이며 `git status --short`에 변경 파일이 나오면 먼저 커밋하거나 보관해야 합니다.

### 터미널 A — 업데이트·설치 갱신·DB·백엔드

**PowerShell (`PS` 프롬프트)에서 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.**

```powershell
# VS Code 터미널이 상위 폴더에서 열렸다면 프로젝트 폴더로 이동
if (Test-Path .\CaloDetect\backend) { Set-Location .\CaloDetect }
if (-not (Test-Path .\backend\requirements-dev.txt)) { throw 'CaloDetect 루트 폴더에서 실행하세요.' }
if ((git branch --show-current) -ne 'develop') { throw 'develop 브랜치에서 실행하세요.' }
git status --short
if (git status --porcelain) { throw '로컬 변경을 먼저 커밋하거나 git stash push -u로 보관하세요.' }
git pull --ff-only origin develop
if ($LASTEXITCODE -ne 0) { throw '업데이트 오류를 확인하세요.' }

.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -r backend/requirements-vision.txt
if ($LASTEXITCODE -ne 0) { throw '패키지 설치 오류를 확인하세요.' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw '로컬 설정·DB·테스트 계정 준비 오류를 확인하세요.' }

$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

### 새 터미널 B — 프런트엔드 갱신·실행

**PowerShell (`PS` 프롬프트)에서 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.**

```powershell
if (Test-Path .\CaloDetect\frontend) { Set-Location .\CaloDetect }
if (Test-Path .\frontend\package.json) { Set-Location .\frontend }
if (-not (Test-Path .\package.json)) { throw 'CaloDetect의 frontend 폴더에서 실행하세요.' }
npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw '프런트엔드 설치 오류를 확인하세요.' }
$env:CALODETECT_API_TARGET='http://[::1]:8000'
npm.cmd run dev -- --host localhost --port 5174
```

http://localhost:5174 → 기존 계정으로 로그인. 기존 `.env`는 유지합니다.

## 3. 열어 놓은 프로젝트를 실행할 때 — 재설치 없이 켜기

**이 PC에서 1번의 설치를 완료한 경우입니다.** VS Code에서 CaloDetect 폴더를 열고 Docker Desktop을 켭니다.

### 터미널 A — DB·백엔드

**PowerShell (`PS` 프롬프트)에서 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.**

```powershell
if (Test-Path .\CaloDetect\backend) { Set-Location .\CaloDetect }
if (-not (Test-Path .\.venv-backend\Scripts\python.exe)) { throw 'CaloDetect 루트인지 확인하세요. 아직 설치하지 않았다면 1번을 진행하세요.' }
$env:FRONTEND_ORIGIN='http://localhost:5174'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw '로컬 설정·DB·테스트 계정 준비 오류를 확인하세요.' }
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

### 새 터미널 B — 프런트엔드

**PowerShell (`PS` 프롬프트)에서 아래 코드 전체를 복사해서 붙여넣고 실행해 주세요.**

```powershell
if (Test-Path .\CaloDetect\frontend) { Set-Location .\CaloDetect }
if (Test-Path .\frontend\package.json) { Set-Location .\frontend }
if (-not (Test-Path .\node_modules\vite)) { throw 'frontend 위치를 확인하세요. 첫 설치라면 1번을 진행하세요.' }
$env:CALODETECT_API_TARGET='http://[::1]:8000'
npm.cmd run dev -- --host localhost --port 5174
```

**CMD를 그대로 쓰는 경우에는 위 블록 대신 아래 명령을 사용합니다.** 자신의 실제 클론 경로로 바꿔 입력하세요.

```cmd
cd /d "C:\projects\CaloDetect\frontend"
set CALODETECT_API_TARGET=http://[::1]:8000
npm.cmd run dev -- --host localhost --port 5174
```

http://localhost:5174 → 기존 계정으로 로그인.
종료는 두 터미널에서 각각 `Ctrl+C`. DB 중지는 루트에서 `docker compose stop db`.

---

기존 DB의 비밀번호 오류는 기존 `.env` 연결 정보와 맞춰야 합니다. `docker compose down -v`로 데이터를 삭제하지 마세요.
8000·5174 포트가 이미 사용 중이면 기존 CaloDetect 서버를 먼저 종료하세요. 다른 프로젝트는 임의로 종료하지 않습니다.
`.env`·비밀번호는 공유하지 않습니다. 자신의 상황에 해당하는 터미널 A 코드 전체를 실행한 뒤, 새 터미널 B 코드 전체를 실행합니다.
