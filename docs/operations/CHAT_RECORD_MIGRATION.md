# 팀원용 챗봇 DB 업데이트 — 추가 설치 없이

이미 CaloDetect를 실행해 본 Windows PC용입니다. 기존 `.venv-backend`의 Python·Alembic과 Docker PostgreSQL을 그대로 사용합니다. **이번 챗봇 DB 업데이트만을 위해 새 프로그램이나 pip 패키지를 설치할 필요는 없습니다.** 최초 설치가 안 된 PC는 [README](../../README.md)의 설치 절차가 먼저입니다.

## 1. 준비

- 최신 `develop`을 받은 상태에서 Docker Desktop을 켭니다.
- 실행 중인 Backend는 해당 터미널에서 `Ctrl+C`로 종료합니다. Docker DB는 끄지 않습니다.
- VS Code에서 프로젝트 루트(`README.md`와 `.env`가 있는 폴더)의 PowerShell 터미널을 엽니다.
- 아래는 각자의 **로컬 Docker DB**에 적용합니다. 공용/운영 DB용 절차가 아닙니다.

## 2. 아래 블록을 한 번 실행

기존 `.env`·회원·식단·사진을 삭제하지 않습니다. 백업에 실패하면 migration도 실행하지 않습니다.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $chatPython = '.\.venv-backend\Scripts\python.exe'
    if (-not (Test-Path $chatPython)) { throw '기존 Backend 가상환경이 없습니다. 최초 설치가 필요합니다.' }
    if (-not (Test-Path '.env')) { throw '기존 .env가 없습니다. 개인 설정 준비가 먼저입니다.' }

    # DB는 기존 volume 그대로 시작합니다.
    docker compose up -d --wait db
    if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop과 DB 실행 상태를 확인하세요.' }

    # 설정 검사·비공개 설정 보관만 수행합니다. 이 단계는 migration을 실행하지 않습니다.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1 -SettingsOnly
    if ($LASTEXITCODE -ne 0) { throw '로컬 설정 확인 실패. 여기서 중단합니다.' }

    # 기존 DB 이력을 먼저 확인합니다. 모르는 revision이면 여기서 중단합니다.
    & $chatPython -m alembic -c backend/alembic.ini current
    if ($LASTEXITCODE -ne 0) { throw 'DB 이력 확인 실패. 아래 오류 안내를 확인하고 DB 담당자에게 전달하세요.' }

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_local_db.ps1
    if ($LASTEXITCODE -ne 0) { throw '백업 실패. migration을 실행하지 않았습니다.' }

    & $chatPython -m alembic -c backend/alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'migration 실패. 서버를 켜지 말고 오류를 DB 담당자에게 전달하세요.' }

    & $chatPython -m alembic -c backend/alembic.ini current
    if ($LASTEXITCODE -ne 0) { throw '최종 DB 이력 확인 실패' }
    Write-Host '완료: 최종 revision이 20261015_02 (head)인지 확인하세요.'
}
```

이미 최신 migration이 적용된 DB에서는 중복 생성 없이 끝납니다. **수동으로 테이블만 생성하고 이력은 갱신하지 않은 DB**는 중복 테이블/컬럼 오류가 날 수 있으므로 담당자의 상태 확인이 필요합니다.

백업은 `%LOCALAPPDATA%\CaloDetect\backups`에 저장됩니다. 이번 migration은 사진 파일을 바꾸지 않습니다.

## 3. 채팅 메뉴 켜고 Backend 재실행

DB 업데이트에 성공한 경우에만, **같은 터미널**에서 실행합니다.

```powershell
$env:CHAT_RECORD_ENABLED = 'true'
$env:FRONTEND_ORIGIN = 'http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

매번 플래그를 입력하기 싫으면 기존 `.env`의 `CHAT_RECORD_ENABLED` 항목을 `true`로 설정하세요. `.env` 전체를 예시 파일로 덮어쓰지 않습니다. 프론트·그래프 서버는 [기존 로컬 실행 가이드](../../CaloDetect_로컬_실행가이드.md)대로 켜고, 로그인 후 웹을 새로고침하면 `채팅으로 식사기록` 메뉴가 나타납니다. 사진 분석은 기존 이미지 저장·YOLO 설정도 필요하며 OpenAI 키는 필요하지 않습니다.

## 오류가 나면 이것만 전달

| 오류 | 처리 |
|---|---|
| `Can't locate revision identified by '20261007_03'` | 저장소에 없는 DB 이력입니다. 이 절차로 해결할 수 없으므로 오류와 revision을 DB 담당자에게 전달합니다. |
| `already exists` / `DuplicateTable` / `DuplicateColumn` | 스키마가 수동 적용됐을 수 있습니다. 재실행·삭제하지 말고 DB 담당자에게 전달합니다. |
| `No module named alembic` | 기존 설치가 불완전한 환경입니다. 이 가이드의 추가 설치 없는 실행 대상이 아니므로 설치 담당자에게 전달합니다. |
| DB 연결/비밀번호 오류 | Docker 실행 및 자기 PC의 `.env` DB 설정을 확인합니다. 비밀번호·API 키는 공유하지 않습니다. |

`alembic stamp`로 이력을 바꾸거나, 테이블/volume을 삭제해 해결하지 않습니다. [DB 담당자용 이력 인계](../planning/CHAT_RECORD_A0_MIGRATION_HANDOFF.md)를 참고하세요.

적용 내용: `meal_items`의 섭취 비율·version, `meals`의 채팅 첨부 연결, 챗봇 관련 테이블 6개. 기존 회원·식단을 지우거나 더미 데이터를 추가하지 않습니다.
