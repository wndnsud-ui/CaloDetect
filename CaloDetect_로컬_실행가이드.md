# CaloDetect 로컬 실행 가이드 — 서버 2개 + 프론트엔드 1개

설치를 마친 PC에서 CaloDetect를 다시 켤 때 사용합니다. 처음 설치는 [README 실행 안내](README.md#새-웹-환경-실행--팀원용-간편-설치)를 따르세요.

| 터미널 | 역할 | 포트 |
|---|---|---|
| A | Backend 서버 (uvicorn) | 8000 |
| B | Streamlit 그래프 서버 | 8502 |
| C | Frontend (Vite) | 5174 |

## 0. 시작 전 준비

- **Docker Desktop을 켜고** 왼쪽 아래 **Engine running**이 뜰 때까지 기다립니다. DB(PostgreSQL)는 Docker가 실행하므로 터미널이 필요 없습니다.
- VS Code에서 `C:\CaloDetect` 폴더를 엽니다.
- 아래 터미널은 각각 **터미널 → 새 터미널(PowerShell)**로 따로 열고, 실행한 뒤 **닫지 말고 켜 둡니다.**

## 터미널 A — Backend 서버 (포트 8000)

```powershell
Set-Location 'C:\CaloDetect'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
if ($LASTEXITCODE -ne 0) { throw 'DB 준비 실패. Docker Desktop이 켜져 있는지 확인하세요.' }
$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

`Application startup complete`가 나오면 준비 완료입니다.

## 터미널 B — Streamlit 그래프 서버 (포트 8502)

```powershell
Set-Location 'C:\CaloDetect'
.\.venv-backend\Scripts\python.exe -m streamlit run streamlit/charts.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

`You can now view your Streamlit app`이 나오면 준비 완료입니다. <http://127.0.0.1:8502/_stcore/health>에서 `ok`가 보이면 정상입니다.

## 터미널 C — Frontend (포트 5174)

```powershell
Set-Location 'C:\CaloDetect\frontend'
$env:CALODETECT_API_TARGET='http://[::1]:8000'
$env:VITE_STREAMLIT_URL='http://127.0.0.1:8502/'
npm.cmd run dev -- --host localhost --port 5174
```

`Local: http://localhost:5174/`가 나오면 브라우저에서 **<http://localhost:5174>**를 엽니다.

## 참고

- 실행 순서는 **A → B → C**를 권장합니다.
- 종료할 때는 각 터미널에서 **Ctrl + C**를 누릅니다.
- `git pull`로 업데이트한 뒤에는 서버를 켜기 전에 패키지를 갱신하세요. Backend 패키지에 Streamlit 그래프 패키지도 포함되어 있습니다.
  - 터미널 A: `.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt`
  - 터미널 C(`frontend` 폴더): `npm.cmd ci`

## 오류가 나오면

| 증상 | 원인 | 해결 |
|---|---|---|
| `Backend 연결 실패 ... ECONNREFUSED` | 터미널 A(Backend)가 꺼져 있음 | 터미널 A 블록 실행 |
| 그래프 자리에 `127.0.0.1에서 연결을 거부했습니다` | 터미널 B(Streamlit)가 꺼져 있음 | 터미널 B 블록 실행 후 Ctrl+F5 |
| `DB 준비 실패` / `failed to connect to the docker API` | Docker Desktop이 꺼져 있음 | Docker Desktop 실행 후 Engine running 확인 |
| `Could not read package.json` | `frontend` 폴더가 아닌 곳에서 npm 실행 | `Set-Location 'C:\CaloDetect\frontend'` 후 다시 실행 |
| `Port 5174 is already in use` | 이전 Frontend가 아직 실행 중 | 이전 터미널에서 Ctrl+C로 종료 |
