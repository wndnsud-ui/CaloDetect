# TEST-ONLY: 챗으로 섭취량 수정(챗봇 지시서 A0) 화면 시연용 로컬 DB를 만든다. 개인 브랜치 한정.
# 개발 DB(calodetect_develop)는 변경하지 않는다. 같은 Docker 컨테이너에 별도 DB를 만들고 migration head까지 적용한 뒤
# 음식 카탈로그·로컬 테스트 계정·더미 식단을 채운다. 시작 전에 개발 DB와 .private-uploads를 개인 백업 폴더에 백업한다.
# 사용: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_chat_demo_db.ps1 [-Reset]
param(
    [string]$DemoDatabase = 'calodetect_chat_demo',
    # 컨테이너 내부 DB 생성 권한이 있는 관리자 계정. 앱 계정에는 CREATEDB 권한이 없다.
    [string]$SuperUser = 'calodetect',
    # 기존 시연 DB를 지우고 다시 만든다. 개발 DB에는 영향이 없다.
    [switch]$Reset
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv-backend\Scripts\python.exe'
if ($DemoDatabase -notmatch '^[a-z_][a-z0-9_]*$' -or $SuperUser -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw 'Unexpected identifiers.' }
Push-Location $root
try {
    # 1. 개발 DB와 업로드 사진 백업
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'backup_local_db.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'DB 백업 실패. 시연 DB를 만들지 않았습니다.' }
    $uploads = Join-Path $root '.private-uploads'
    if (Test-Path $uploads) {
        $photoBackup = Join-Path $env:LOCALAPPDATA ('CaloDetect\backups\private-uploads-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
        Copy-Item -Recurse -LiteralPath $uploads -Destination $photoBackup
        Write-Host "사진 백업: $photoBackup"
    }

    # 2. 앱 DB 접속 정보에서 DB 이름만 바꾼 시연 DB 주소를 만든다(비밀번호는 출력하지 않음).
    $line = [IO.File]::ReadAllLines((Join-Path $root '.env')) | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -Last 1
    if (-not $line) { throw '.env에 DATABASE_URL이 없습니다.' }
    $baseUrl = $line.Substring('DATABASE_URL='.Length)
    if ($baseUrl -notmatch '^(postgresql\+psycopg://([^:]+):[^@]+@(127\.0\.0\.1|localhost|\[::1\]):\d+/)[^/?]+$') {
        throw '로컬 PostgreSQL 주소가 아니면 시연 DB를 만들지 않습니다.'
    }
    $owner = $Matches[2]
    $demoUrl = $Matches[1] + $DemoDatabase

    # 3. 시연 DB 생성
    $exists = docker compose exec -T db psql -U $SuperUser -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname='$DemoDatabase'"
    if ($LASTEXITCODE -ne 0) { throw 'DB 컨테이너에 연결할 수 없습니다. Docker Desktop과 compose db를 확인하세요.' }
    if ($exists -eq '1' -and $Reset) {
        docker compose exec -T db psql -U $SuperUser -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE $DemoDatabase WITH (FORCE)"
        if ($LASTEXITCODE -ne 0) { throw '기존 시연 DB 삭제 실패' }
        $exists = ''
    }
    if ($exists -ne '1') {
        docker compose exec -T db psql -U $SuperUser -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $DemoDatabase OWNER $owner"
        if ($LASTEXITCODE -ne 0) { throw '시연 DB 생성 실패' }
    }

    # 4. migration·시드. 이 프로세스에서만 DATABASE_URL을 시연 DB로 바꾼다(.env는 수정하지 않음).
    $previous = $env:DATABASE_URL
    $env:DATABASE_URL = $demoUrl
    try {
        & $python -m alembic -c backend/alembic.ini upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'migration 실패' }
        & $python -m backend.scripts.seed_foods
        if ($LASTEXITCODE -ne 0) { throw '음식 카탈로그 준비 실패' }
        & $python -m backend.scripts.seed_local_test_account
        if ($LASTEXITCODE -ne 0) { throw '테스트 계정 준비 실패' }
        & $python -m backend.scripts.seed_demo_meals
        if ($LASTEXITCODE -ne 0) { throw '더미 식단 준비 실패' }
    } finally { $env:DATABASE_URL = $previous }

    Write-Host ''
    Write-Host "시연 DB 준비 완료: $DemoDatabase (개발 DB는 변경하지 않음)"
    Write-Host 'Backend 실행(터미널 A, 이 창에서만 적용):'
    Write-Host "  `$env:DATABASE_URL = (Get-Content .env | Select-String '^DATABASE_URL=').Line.Substring(13) -replace '/[^/]+$', '/$DemoDatabase'"
    Write-Host "  `$env:CHAT_RECORD_ENABLED = 'true'"
    Write-Host '  .\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --host ::1 --port 8000'
    Write-Host 'Frontend는 기존과 같이 실행 후 test@calodetect.local 로그인 → 히스토리 → 챗으로 수정'
} finally { Pop-Location }
