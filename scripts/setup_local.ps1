# Windows 로컬 개발 설정 준비. 현재 .env 또는 Windows 계정의 비공개 설정을 재사용하고 DB 연결 값을 검사한다.
# SettingsOnly는 설정 준비만 수행하며 기본 실행은 DB·migration·seed도 준비한다. 기존 DB volume과 회원 데이터는 보존한다.
# SettingsOnly 호출은 .env 재사용/검사만 수행한다. DB를 준비하려면 스위치 없이 실행한다.
param([switch]$SettingsOnly)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$envPath = Join-Path $root '.env'
$sharedConfigDirectory = Join-Path $env:LOCALAPPDATA 'CaloDetect'
$sharedEnvPath = Join-Path $sharedConfigDirectory 'local.env'

# 환경설정 행에서 지정 키를 갱신하거나 추가한다. 중첩 배열 방지를 위해 배열을 하나의 반환값으로 유지한다.
function Set-EnvValue([string[]]$Lines, [string]$Key, [string]$Value) {
    $found = $false
    for ($index = 0; $index -lt $Lines.Count; $index++) {
        if ($Lines[$index] -match ('^' + [regex]::Escape($Key) + '=')) {
            $Lines[$index] = "$Key=$Value"
            $found = $true
        }
    }
    if (-not $found) {
        $Lines += "$Key=$Value"
    }
    return ,$Lines
}

# 동일 키가 여러 번 있으면 마지막 값을 읽고 없으면 null을 반환한다.
function Get-EnvValue([string[]]$Lines, [string]$Key) {
    $line = $Lines | Where-Object { $_ -match ('^' + [regex]::Escape($Key) + '=') } | Select-Object -Last 1
    if (-not $line) { return $null }
    return $line.Substring($Key.Length + 1)
}

New-Item -ItemType Directory -Path $sharedConfigDirectory -Force | Out-Null

# 현재 클론에 .env가 없을 때만 기존 개인 설정을 복사하거나 최초 템플릿을 만든다.
if (-not (Test-Path $envPath)) {
    if (Test-Path $sharedEnvPath) {
        Copy-Item -LiteralPath $sharedEnvPath -Destination $envPath
        Write-Host 'Reused this Windows account''s private CaloDetect settings.'
    } else {
        $password = [guid]::NewGuid().ToString('N')
        $template = [IO.File]::ReadAllText((Join-Path $root '.env.example'))
        $template = $template.Replace('replace_me', $password)
        $template = $template.Replace('APP_ENV=production', 'APP_ENV=development')
        $template = $template.Replace('LOCAL_TEST_SIGNUP=false', 'LOCAL_TEST_SIGNUP=true')
        $template = $template.Replace('LOCAL_TEST_IMAGE_ANALYSIS=false', 'LOCAL_TEST_IMAGE_ANALYSIS=true')
        $template = $template.Replace('# IMAGE_STORAGE_DIR=.private-uploads', 'IMAGE_STORAGE_DIR=.private-uploads')
        [IO.File]::WriteAllText($envPath, $template, (New-Object Text.UTF8Encoding($false)))
        Write-Host 'Created local development settings from .env.example.'
    }
}

$lines = [IO.File]::ReadAllLines($envPath)
$databaseUrl = Get-EnvValue $lines 'DATABASE_URL'
$postgresPassword = Get-EnvValue $lines 'POSTGRES_PASSWORD'
if (-not $databaseUrl -or -not $postgresPassword) {
    throw 'DATABASE_URL and POSTGRES_PASSWORD are required in .env. Existing settings were not overwritten.'
}

try {
    $uri = [Uri]($databaseUrl -replace '^postgresql\+psycopg://', 'postgresql://')
    $credentials = $uri.UserInfo.Split(':', 2)
    if (($uri.Scheme -ne 'postgresql') -or ($uri.Port -ne 5432) -or ($credentials.Count -ne 2) -or
            [string]::IsNullOrEmpty($uri.AbsolutePath.Trim('/'))) {
        throw 'Unexpected database URL.'
    }
    $dbUser = [Uri]::UnescapeDataString($credentials[0])
    $dbPassword = [Uri]::UnescapeDataString($credentials[1])
    $dbName = [Uri]::UnescapeDataString($uri.AbsolutePath.Trim('/'))
} catch {
    throw 'DATABASE_URL must be a valid local PostgreSQL URL. Existing data was not changed.'
}

if (($uri.Host -notin @('localhost', '127.0.0.1')) -or ($dbUser -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') -or
        ($dbName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$')) {
    throw 'Local setup requires a localhost PostgreSQL URL with simple user and database names.'
}
if ($dbPassword -cne $postgresPassword) {
    throw 'DATABASE_URL and POSTGRES_PASSWORD do not match. Existing database credentials were left unchanged.'
}

# 동일 DB 자격정보를 유지하면서 호스트 실행의 localhost를 Compose 내부 서비스 db로 바꾼다.
$dockerUrl = $databaseUrl -replace '@(localhost|127\.0\.0\.1):5432/', '@db:5432/'
if ($dockerUrl -eq $databaseUrl) {
    throw 'Could not create the Docker database URL from DATABASE_URL.'
}
$lines = Set-EnvValue $lines 'DATABASE_URL_DOCKER' $dockerUrl
$lines = Set-EnvValue $lines 'POSTGRES_USER' $dbUser
$lines = Set-EnvValue $lines 'POSTGRES_DB' $dbName

$clientId = Get-EnvValue $lines 'GOOGLE_CLIENT_ID'
if (-not $clientId) {
    $template = [IO.File]::ReadAllLines((Join-Path $root '.env.example'))
    $clientId = Get-EnvValue $template 'GOOGLE_CLIENT_ID'
    if ($clientId) { $lines = Set-EnvValue $lines 'GOOGLE_CLIENT_ID' $clientId }
}

# 기존 키가 있으면 보존한다. 키를 매번 바꾸면 진행 중인 OAuth state/가입 쿠키를 검증할 수 없게 된다.
if (-not (Get-EnvValue $lines 'OAUTH_STATE_SECRET')) {
    $secretBytes = New-Object byte[] 48
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $random.GetBytes($secretBytes) } finally { $random.Dispose() }
    $stateSecret = ([BitConverter]::ToString($secretBytes) -replace '-', '').ToLowerInvariant()
    $lines = Set-EnvValue $lines 'OAUTH_STATE_SECRET' $stateSecret
}

# 재설정 비밀키도 누락된 경우에만 안전한 난수로 생성해 재클론/재실행에서 기존 링크 기준을 유지한다.
if (-not (Get-EnvValue $lines 'PASSWORD_RESET_SECRET')) {
    $resetBytes = New-Object byte[] 48
    $random = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $random.GetBytes($resetBytes) } finally { $random.Dispose() }
    $lines = Set-EnvValue $lines 'PASSWORD_RESET_SECRET' (([BitConverter]::ToString($resetBytes) -replace '-', '').ToLowerInvariant())
}
foreach ($entry in @(@('SMTP_HOST', 'smtp.gmail.com'), @('SMTP_PORT', '587'), @('SMTP_SECURITY', 'starttls'))) {
    if (-not (Get-EnvValue $lines $entry[0])) {
        $lines = Set-EnvValue $lines $entry[0] $entry[1]
    }
}

$appEnv = Get-EnvValue $lines 'APP_ENV'
$signupEnabled = Get-EnvValue $lines 'LOCAL_TEST_SIGNUP'
if ($appEnv -ne 'development' -or $signupEnabled -ne 'true') {
    throw 'Local test setup requires APP_ENV=development and LOCAL_TEST_SIGNUP=true. Existing settings were not changed.'
}

# 검사를 통과한 설정을 BOM 없는 UTF-8로 기록하고 Windows 계정 전용 위치에 재사용 사본을 둔다.
[IO.File]::WriteAllLines($envPath, $lines, (New-Object Text.UTF8Encoding($false)))
Copy-Item -LiteralPath $envPath -Destination $sharedEnvPath -Force
Write-Host 'Saved private settings for future CaloDetect clones under this Windows account.'
# 설정 전용 요청이면 DB 준비 명령 전에 종료한다.
if ($SettingsOnly) { return }

Push-Location $root
try {
    # 기존 고정 volume을 유지한 채 DB가 ready가 될 때까지 기다린다. 실패하면 migration/seed를 실행하지 않는다.
    docker compose up -d --wait db
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not start. Existing database volume was preserved.' }

    $python = Join-Path $root '.venv-backend\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        throw 'Create .venv-backend and install backend requirements before running local setup.'
    }
    # 설치된 Backend Python으로 기존 Alembic 이력을 최신 revision까지 적용한다. 새 revision은 생성하지 않는다.
    & $python -m alembic -c backend/alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed. Existing data was preserved.' }
    & $python -m backend.scripts.seed_local_test_account
    if ($LASTEXITCODE -ne 0) { throw 'Local test account setup failed.' }
    & $python -m backend.scripts.seed_foods
    if ($LASTEXITCODE -ne 0) { throw 'Food data setup failed.' }
} finally {
    Pop-Location
}

Write-Host 'Local database, migrations, foods, and test account are ready.'
Write-Host 'Google GIS login uses the public Web client ID; no Google client secret is needed.'
