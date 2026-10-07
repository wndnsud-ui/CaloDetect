# 이미 실행한 팀원용 — 변경분 업데이트하고 다시 실행하기

**기존에 `git clone`으로 받은 폴더에서 진행합니다. 새로 클론하거나 폴더를 지울 필요가 없습니다.**
Git이 바뀐 코드만 받아 기존 파일을 업데이트합니다. 기존 `.env`·가상환경·회원 DB는 재사용합니다.

## 먼저 GitHub에서 최신 파일 확인하기

1. [CaloDetect GitHub develop 브랜치](https://github.com/wndnsud-ui/CaloDetect/tree/develop)를 엽니다.
2. 파일 목록 위 왼쪽 브랜치 선택란이 **develop**인지 확인합니다.
3. 파일 목록의 **CaloDetect_업데이트_간편가이드.md**를 눌러 **GitHub에 올라온 최신 안내**를 읽습니다. 기존 PC의 안내 파일은 업데이트 전까지 예전 내용일 수 있습니다.
4. 아래 순서대로 기존 클론 폴더에서 `git pull`을 실행합니다. 이 명령이 **GitHub에서 바뀐 파일을 받아 기존 폴더에 적용하는 단계**입니다.

**이번에는 `Code → Download ZIP`이나 `git clone`을 다시 실행하지 않습니다.** 기존 클론에 변경분만 받으므로 GitHub에서 파일을 하나씩 다운로드해 붙여넣을 필요가 없습니다.

## 1. 실행 중인 서버 끄고 프로젝트 열기

1. Backend와 Frontend가 실행 중인 터미널에서 각각 **Ctrl+C**를 누릅니다.
2. **Docker Desktop을 켭니다.**
3. VS Code에서 **파일 → 폴더 열기**를 눌러 처음 클론했던 **CaloDetect 폴더**를 선택합니다. `README.md`, `backend`, `frontend`가 보이는 폴더입니다.
4. **터미널 → 새 터미널 → PowerShell**을 선택합니다. 프롬프트가 `PS ...>`인지 확인하세요.

아래 코드는 **PowerShell 전용**입니다. 각 블록 전체를 복사해 붙여넣고, 마지막 명령이 실행되지 않으면 Enter를 누르세요.

## 2. GitHub에서 바뀐 파일 받기 — 기존 폴더에 업데이트

**아래 블록 전체를 복사해서 실행하세요.** 프로젝트 안에 열린 터미널이면 `frontend` 폴더에 있어도 루트를 자동으로 찾습니다.

```powershell
$projectRoot = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw 'VS Code에서 기존 Git 클론 폴더를 열어 주세요.' }
Set-Location -LiteralPath $projectRoot

# 직접 수정한 파일이 있으면 덮어쓰지 않고 중단합니다.
$localChanges = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Git 상태 확인 실패' }
if ($localChanges) {
    git status --short
    throw '수정 파일이 있습니다. 아래 오류 안내의 임시 보관 방법을 확인하세요.'
}

git switch develop
if ($LASTEXITCODE -ne 0) { throw 'develop 전환 실패. 팀 리드에게 오류를 전달하세요.' }
# GitHub origin/develop에서 최신 변경분을 내려받아 현재 폴더에 적용합니다.
git pull --ff-only origin develop
if ($LASTEXITCODE -ne 0) { throw '업데이트 실패. 다음 단계로 넘어가지 마세요.' }
git log -1 --oneline
```

`Updating ...`, `Fast-forward`, 변경 파일 목록이 나오면 **다운로드·적용 완료**입니다. `Already up to date`는 이미 최신이라는 뜻입니다. 마지막 줄에 최신 커밋이 표시되고, VS Code의 파일도 새 내용으로 바뀝니다. 오류가 나오면 아래 오류 안내를 확인하고 다음 단계로 넘어가지 않습니다.

## 3. 같은 터미널 A — Backend 실행

**2번 업데이트가 끝난 뒤 아래 블록 전체를 같은 터미널에 붙여넣습니다.**

```powershell
$projectRoot = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw '기존 CaloDetect 폴더 안에서 실행하세요.' }
Set-Location -LiteralPath $projectRoot

.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend 패키지 갱신 실패' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw '로컬 설정 또는 DB 준비 실패. 오류 안내를 확인하세요.' }

$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

**`Application startup complete`가 나오면 성공입니다. 터미널 A는 켜 둡니다.**

## 4. 새 터미널 B — Frontend 실행

VS Code의 **터미널 → 새 터미널**을 눌러 PowerShell 창을 하나 더 엽니다.
**아래 블록 전체를 복사해서 실행하세요.**

```powershell
$projectRoot = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw '기존 CaloDetect 폴더 안에서 실행하세요.' }
Set-Location -LiteralPath (Join-Path $projectRoot 'frontend')

npm.cmd ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend 패키지 갱신 실패' }
$env:CALODETECT_API_TARGET='http://[::1]:8000'
npm.cmd run dev -- --host localhost --port 5174
```

브라우저에서 **http://localhost:5174**를 엽니다. 화면이 이전과 같으면 **Ctrl+F5**로 새로고침합니다.
**기존에 가입한 계정으로 로그인하세요.** 테스트 계정은 `test@calodetect.local` / `CaloTest!2026`입니다. 이미 테스트 비밀번호를 변경했다면 변경한 비밀번호를 사용하세요.

## 5. 이번 업데이트에서 달라진 기능

- 소셜 로그인은 **Google만 제공**합니다. Apple 버튼을 제거했습니다.
- 이메일 로그인에 **비밀번호 찾기**, 마이페이지에 **비밀번호 변경**을 추가했습니다.
- 로컬 테스트 계정이 없으면 생성하고, 기존 계정은 유지합니다.
- 같은 PC에서 다시 클론할 때 개인 설정을 재사용하고 DB 백업 명령을 제공합니다.
- 실행 안내와 홈페이지 배경 이미지를 갱신했습니다.

전체 변경 파일 목록은 [README](README.md#이번-변경-파일-목록)에 있습니다. 인증 화면·API·설정은 서로 연결되어 있으므로 개별 파일을 골라 복사하지 말고 위 `git pull`로 함께 업데이트하세요.

## 6. 막히면 여기만 확인하세요

| 메시지 / 증상 | 처리 방법 |
|---|---|
| `Already up to date` | 이미 최신 코드입니다. 패키지 갱신·서버 실행을 이어서 진행합니다. |
| `수정 파일이 있습니다` | 본인이 수정한 코드를 먼저 커밋하거나 아래처럼 임시 보관합니다. |
| `Not possible to fast-forward`, 브랜치 전환·충돌 오류 | 오류와 `git status` 결과를 팀 리드에게 전달합니다. 강제로 덮어쓰지 않습니다. |
| `password authentication failed` | 기존 DB와 `.env` 접속 정보가 다릅니다. 기존 설정을 확인합니다. DB volume을 삭제해서 해결하지 않습니다. |
| `LOCAL_TEST_SIGNUP`, `POSTGRES_PASSWORD` 설정 오류 | 기존 `.env`를 유지하고 팀 리드에게 오류를 전달합니다. `.env.example`로 덮어쓰지 않습니다. |
| 포트 8000 / 5174 사용 중 | 이전 서버 터미널에서 Ctrl+C를 누른 뒤 다시 실행합니다. |
| 이메일 발송 설정 준비 안 됨 | 비밀번호 찾기에는 발신 Gmail 주소·앱 비밀번호 설정이 필요합니다. 네이버 주소로 받는 것은 가능합니다. [SMTP 설정](README.md#이메일-계정-비밀번호-찾기변경-gmail-smtp)을 확인하세요. |
| Google 로그인 연결 준비 / 가입 동의 안내 | 개인 서버 설정·Google 테스트 사용자·가입 동의 문구를 확인합니다. [Google 설정](README.md#google-로그인-설정)을 참고하세요. |

직접 수정한 파일을 임시 보관하려면 프로젝트 루트에서 다음 명령을 실행한 뒤 **2번 블록을 다시 실행**합니다. 수정·새 파일은 Git stash에 보관하고, Git에서 제외된 `.env`는 그대로 둡니다.

```powershell
git stash push -u -m "업데이트 전 개인 작업 보관"
if ($LASTEXITCODE -ne 0) { throw '임시 보관 실패' }
git stash list
```

개인 작업을 복원할 때는 `git stash list`에서 해당 항목을 확인하고 `git stash apply 'stash@{0}'`처럼 적용합니다. 다른 보관 항목이 있으면 번호를 맞추세요. 충돌이 나면 팀 리드와 해결합니다. 보관 항목은 자동 삭제하지 않습니다.

**기존 폴더·`.env`·Docker DB volume을 지우지 마세요.** 같은 PC의 기존 DB 연결을 유지하면 회원·기록을 계속 사용할 수 있습니다. 다른 PC의 회원 DB가 GitHub 다운로드로 복사되는 것은 아닙니다. DB 이전·백업 안내는 [README](README.md#2026-10-07-develop-업데이트와-데이터-보존)를 참고하세요.
