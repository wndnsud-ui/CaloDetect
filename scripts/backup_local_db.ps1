# 현재 앱 설정의 PostgreSQL을 custom archive로 백업하고 목록·파일 크기를 확인한다.
# 백업은 Windows 계정의 비공개 폴더에 저장한다. 이 스크립트는 복원이나 원본 DB 변경을 수행하지 않는다.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backupDirectory = Join-Path $env:LOCALAPPDATA 'CaloDetect\backups'
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
$backupName = 'calodetect-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N') + '.dump'
$containerPath = '/tmp/' + $backupName
$backupPath = Join-Path $backupDirectory $backupName
Push-Location $root
try {
    # Use the app's actual database, which can differ from the container initialization database.
    $envLines = [IO.File]::ReadAllLines((Join-Path $root '.env'))
    $dbUserLine = $envLines | Where-Object { $_ -match '^POSTGRES_USER=' } | Select-Object -Last 1
    $dbNameLine = $envLines | Where-Object { $_ -match '^POSTGRES_DB=' } | Select-Object -Last 1
    if (-not $dbUserLine -or -not $dbNameLine) { throw 'Run setup_local.ps1 -SettingsOnly first.' }
    $dbUser = $dbUserLine.Substring('POSTGRES_USER='.Length)
    $dbName = $dbNameLine.Substring('POSTGRES_DB='.Length)
    if ($dbUser -notmatch '^[A-Za-z_][A-Za-z0-9_]*$' -or $dbName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        throw 'Unexpected local database identifiers.'
    }
# 앱이 사용하는 실제 DB를 custom 형식으로 내보낸다. 기존 테이블을 수정하지 않는다.
    docker compose exec -T db pg_dump -U $dbUser -d $dbName -Fc -f $containerPath
    if ($LASTEXITCODE -ne 0) { throw 'Database backup failed. Existing database was not modified.' }
# 백업을 복원하지 않고 archive 목록만 읽어 형식이 정상인지 검사한다.
    docker compose exec -T db pg_restore --list $containerPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Database backup archive validation failed.' }
# 검사한 archive를 컨테이너 밖의 개인 백업 폴더로 복사한다.
    docker compose cp "db:$containerPath" $backupPath
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy backup to the private backup directory.' }
    if ((Get-Item -LiteralPath $backupPath).Length -eq 0) { throw 'Empty backup archive.' }
    docker compose exec -T db rm -- $containerPath
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Backup saved; temporary container archive could not be removed.' }
    Write-Host "Private database backup saved: $backupPath"
    Write-Host 'This archive contains member data. Keep it private and never commit it to Git.'
} finally { Pop-Location }
