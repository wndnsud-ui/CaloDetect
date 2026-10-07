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
    docker compose exec -T db pg_dump -U $dbUser -d $dbName -Fc -f $containerPath
    if ($LASTEXITCODE -ne 0) { throw 'Database backup failed. Existing database was not modified.' }
    docker compose exec -T db pg_restore --list $containerPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Database backup archive validation failed.' }
    docker compose cp "db:$containerPath" $backupPath
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy backup to the private backup directory.' }
    if ((Get-Item -LiteralPath $backupPath).Length -eq 0) { throw 'Empty backup archive.' }
    docker compose exec -T db rm -- $containerPath
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Backup saved; temporary container archive could not be removed.' }
    Write-Host "Private database backup saved: $backupPath"
    Write-Host 'This archive contains member data. Keep it private and never commit it to Git.'
} finally { Pop-Location }
