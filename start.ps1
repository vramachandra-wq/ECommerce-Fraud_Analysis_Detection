# Metro Cart — start PostgreSQL + Keycloak + FastAPI (analyst portal + customer shop).
# Opens http://127.0.0.1:8000/portal/ and http://127.0.0.1:8000/shop/
# Usage (from project root): .\start.ps1
# Optional: .\start.ps1 -BuildPortal   # rebuild React into static/analyst-portal (destructive)

param(
    [switch]$BuildPortal
)

$ErrorActionPreference = "Stop"

$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Set-Location $ProjectRoot

$RunDir = Join-Path $ProjectRoot ".run"
$LogDir = Join-Path $RunDir "logs"
$StateFile = Join-Path $RunDir "services.json"

$ApiHost = "127.0.0.1"
$ApiPort = 8000
$ApiBase = "http://${ApiHost}:${ApiPort}"
$PortalUrl = "$ApiBase/portal/"
$ShopUrl = "$ApiBase/shop/"
$HealthUrl = "$ApiBase/health"
$DocsUrl = "$ApiBase/docs"
$ProjectUrls = @($PortalUrl, $ShopUrl)

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-PodmanComposePlugin {
    if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
        return $false
    }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & podman compose version 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Find-PodmanComposeExecutable {
    $fromPath = Get-Command podman-compose -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $roots = @()
    if ($env:APPDATA) { $roots += Join-Path $env:APPDATA "Python" }
    if ($env:LOCALAPPDATA) { $roots += Join-Path $env:LOCALAPPDATA "Programs\Python" }

    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $match = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                $candidate = Join-Path $_.FullName "Scripts\podman-compose.exe"
                if (Test-Path $candidate) { $candidate }
            } |
            Select-Object -First 1
        if ($match) { return $match }
    }
    return $null
}

function Get-ComposeCommand {
    $podmanCompose = Find-PodmanComposeExecutable
    if ($podmanCompose) {
        return @{ Executable = $podmanCompose; Arguments = @() }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        try {
            & python -c "import podman_compose" 1>$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @{ Executable = "python"; Arguments = @("-m", "podman_compose") }
            }
        }
        finally {
            $ErrorActionPreference = $previousPreference
        }
    }

    if (Test-PodmanComposePlugin) {
        return @{ Executable = "podman"; Arguments = @("compose") }
    }

    throw "Neither podman-compose nor 'podman compose' is available. Install with: pip install podman-compose"
}

function Invoke-Compose {
    param([string[]]$ComposeArgs)

    $compose = Get-ComposeCommand
    $args = @($compose.Arguments + $ComposeArgs) | Where-Object { $_ }
    & $compose.Executable @args
    if ($LASTEXITCODE -ne 0) {
        throw "Compose command failed: $($compose.Executable) $($args -join ' ')"
    }
}

function Get-VenvPythonPath {
    return Join-Path $ProjectRoot ".venv\Scripts\python.exe"
}

function Test-ProjectReady {
    return (Test-Path (Get-VenvPythonPath)) -and (Test-Path (Join-Path $ProjectRoot ".env"))
}

function Get-PythonExecutable {
    $venvPython = Get-VenvPythonPath
    if (Test-Path $venvPython) {
        return $venvPython
    }
    throw 'Python virtual environment not found. Run .\start.ps1 to create it automatically.'
}

function Initialize-Project {
    Write-Step "First-time setup detected - preparing project..."

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw "Python not found. Install Python 3.10+ and ensure 'python' is on PATH."
    }

    $venvPython = Get-VenvPythonPath
    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating virtual environment (.venv)..."
        & python -m venv (Join-Path $ProjectRoot ".venv")
        if (-not (Test-Path $venvPython)) {
            throw "Failed to create virtual environment at .venv"
        }
    }

    $envFile = Join-Path $ProjectRoot ".env"
    $envExample = Join-Path $ProjectRoot ".env.example"
    if (-not (Test-Path $envFile)) {
        if (-not (Test-Path $envExample)) {
            throw ".env.example not found. Cannot create .env automatically."
        }
        Write-Step "Creating .env from .env.example..."
        Copy-Item $envExample $envFile
        Write-Host "Review .env and set DB_PASSWORD / GROQ_API_KEY if needed." -ForegroundColor Yellow
    }

    $requirements = Join-Path $ProjectRoot "requirements.txt"
    if (-not (Test-Path $requirements)) {
        throw "requirements.txt not found."
    }

    Write-Step "Installing Python dependencies..."
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "pip install -r requirements.txt failed."
    }

    Write-Host "First-time project setup complete." -ForegroundColor Green
}

function Build-AnalystPortal {
    if (-not $BuildPortal) {
        Write-Host "Serving static analyst portal from static/analyst-portal/ (pass -BuildPortal to rebuild from React)." -ForegroundColor DarkGray
        return
    }

    $portalDir = Join-Path $ProjectRoot "analyst-portal"
    $packageJson = Join-Path $portalDir "package.json"
    if (-not (Test-Path $packageJson)) { return }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) {
        Write-Host "npm not found. Reusing previously built analyst portal assets." -ForegroundColor Yellow
        return
    }

    Write-Step "Building analyst portal from React source into static/analyst-portal/..."
    $nodeModules = Join-Path $portalDir "node_modules"
    if (-not (Test-Path $nodeModules)) {
        & $npm.Source install --prefix $portalDir
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed for analyst-portal."
        }
    }

    & $npm.Source run build --prefix $portalDir
    if ($LASTEXITCODE -ne 0) {
        throw "npm run build failed for analyst-portal."
    }
}

function Test-PortListening([int]$Port) {
    $match = netstat -ano | Select-String ":$Port\s" | Select-String "LISTENING"
    return $null -ne $match
}

function Test-DatabaseRunning {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $status = podman inspect ecommerce_fraud --format "{{.State.Health.Status}}" 2>$null
        if ($status -eq "healthy") { return $true }
        $running = podman inspect ecommerce_fraud --format "{{.State.Running}}" 2>$null
        return $running -eq "true"
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Test-HttpOk([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    }
    catch {
        return $false
    }
}

function Test-PlatformHealthy {
    if (-not (Test-DatabaseRunning)) { return $false }
    if (-not (Test-PortListening $ApiPort)) { return $false }
    if (-not (Test-HttpOk $HealthUrl)) { return $false }
    if (-not (Test-HttpOk $PortalUrl)) { return $false }
    if (-not (Test-HttpOk $ShopUrl)) { return $false }
    return $true
}

function Test-ServiceRunning([int]$ProcessId) {
    return (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) -ne $null
}

function Start-ApiProcess {
    $python = Get-PythonExecutable
    $stdout = Join-Path $LogDir "api.log"
    $stderr = "$stdout.err"
    $arguments = @(
        "-m", "uvicorn", "api.main:app",
        "--reload",
        "--host", $ApiHost,
        "--port", "$ApiPort"
    )

    $process = Start-Process `
        -FilePath $python `
        -ArgumentList $arguments `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr

    return @{
        name = "api"
        pid  = $process.Id
        log  = $stdout
    }
}

function Get-DbPortFromEnv {
    $defaultPort = 5434
    $envPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envPath)) { return $defaultPort }

    foreach ($line in Get-Content $envPath) {
        if ($line -match '^\s*DB_PORT=(.+)$') {
            return [int]$Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $defaultPort
}

function Get-EnvValue {
    param(
        [string]$Key,
        [string]$Default = ""
    )
    $envPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envPath)) { return $Default }
    foreach ($line in Get-Content $envPath) {
        if ($line -match "^\s*$Key=(.+)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $Default
}

$KeycloakPort = [int](Get-EnvValue -Key "KEYCLOAK_PORT" -Default "8080")
$KeycloakRealm = Get-EnvValue -Key "KEYCLOAK_REALM" -Default "metro-cart"
$KeycloakUrl = "http://127.0.0.1:$KeycloakPort"
$KeycloakRealmUrl = "$KeycloakUrl/realms/$KeycloakRealm"

function Wait-ForDatabasePort {
    param([int]$TimeoutSeconds = 60)

    $dbPort = Get-DbPortFromEnv
    Write-Step "Waiting for PostgreSQL port $dbPort..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening $dbPort) {
            Write-Host "PostgreSQL port $dbPort is accepting connections." -ForegroundColor Green
            Start-Sleep -Seconds 3
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "PostgreSQL port $dbPort did not open within $TimeoutSeconds seconds."
}

function Wait-ForDatabase {
    param([int]$TimeoutSeconds = 90)

    Write-Step "Waiting for PostgreSQL to become healthy..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        while ((Get-Date) -lt $deadline) {
            if (Test-DatabaseRunning) {
                Write-Host "PostgreSQL is ready." -ForegroundColor Green
                return
            }
            Start-Sleep -Seconds 2
        }
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    throw "PostgreSQL did not become ready within $TimeoutSeconds seconds. Check: podman logs ecommerce_fraud"
}

function Wait-ForKeycloak {
    param([int]$TimeoutSeconds = 120)

    Write-Step "Waiting for Keycloak (SSO)..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $status = podman inspect metro_cart_keycloak --format "{{.State.Health.Status}}" 2>$null
        if ($status -eq "healthy") {
            Write-Host "Keycloak container healthcheck is healthy." -ForegroundColor Green
            return
        }
        if (Test-HttpOk $KeycloakRealmUrl) {
            Write-Host "Keycloak realm is ready ($KeycloakRealmUrl)." -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 3
    }

    Write-Host "Keycloak did not become ready within $TimeoutSeconds seconds." -ForegroundColor Yellow
    Write-Host "Password login still works. Check: podman logs metro_cart_keycloak" -ForegroundColor Yellow
}

function Wait-ForHttp {
    param(
        [string]$Url,
        [string]$Label,
        [int]$TimeoutSeconds = 90
    )

    Write-Host "  Checking $Label ($Url)..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk $Url) {
            Write-Host "  $Label is ready." -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "$Label did not become ready within $TimeoutSeconds seconds. See log: $(Join-Path $LogDir 'api.log')"
}

function Wait-ForApiAndPortals {
    Write-Step "Waiting for FastAPI and portals..."
    Wait-ForHttp -Url $HealthUrl -Label "API"
    Wait-ForHttp -Url $PortalUrl -Label "Analyst portal"
    Wait-ForHttp -Url $ShopUrl -Label "Customer shop"
}

function Get-ChromeExecutable {
    $candidates = @(
        (Join-Path ${env:ProgramFiles} "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
    )

    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) { return $path }
    }

    $fromPath = Get-Command chrome -ErrorAction SilentlyContinue
    if ($fromPath) { return $fromPath.Source }
    return $null
}

function Open-ProjectInBrowser {
    param([string[]]$Urls)

    $chrome = Get-ChromeExecutable
    if ($chrome) {
        Write-Step "Opening portals in Google Chrome..."
        Start-Process -FilePath $chrome -ArgumentList $Urls
        return
    }

    Write-Host "Google Chrome not found. Opening URLs in the default browser." -ForegroundColor Yellow
    foreach ($url in $Urls) {
        Start-Process $url
    }
}

function Show-ProjectInfo {
    Write-Host ""
    Write-Host "Metro Cart platform is running." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Analyst portal:  $PortalUrl"
    Write-Host "  Customer shop:   $ShopUrl"
    Write-Host "  API docs:        $DocsUrl"
    Write-Host "  Keycloak SSO:    $KeycloakUrl (realm metro-cart)"
    Write-Host ""
    Write-Host "Analyst login (password or SSO): admin / admin123  |  analyst / secure123"
    Write-Host "Logs: $LogDir"
    Write-Host "Stop everything with: .\stop.ps1"
}

function Ensure-ApiService {
    if (Test-PortListening $ApiPort) {
        Write-Host "  API already listening on port $ApiPort." -ForegroundColor Green
        return @()
    }

    Write-Host "  Starting FastAPI (uvicorn)..."
    $processInfo = Start-ApiProcess
    Start-Sleep -Seconds 2

    if (-not (Test-ServiceRunning $processInfo.pid)) {
        throw "Failed to start API. See log: $($processInfo.log)"
    }

    return @($processInfo)
}

function Save-ServiceState {
    param([array]$StartedServices)

    $state = @()
    foreach ($svc in $StartedServices) {
        if (Test-ServiceRunning $svc.pid) {
            $state += $svc
        }
    }

    if ($state.Count -gt 0) {
        $state | ConvertTo-Json -Depth 3 | Set-Content -Path $StateFile -Encoding UTF8
    }
    elseif (Test-Path $StateFile) {
        # Keep existing state if we reused an already-running API
    }
}

Write-Host ""
Write-Host "Metro Cart - starting platform (API + portal + shop)..." -ForegroundColor White
Write-Host ""

if (Test-PlatformHealthy) {
    Write-Host "All services are already running (database + API + portals)." -ForegroundColor Green
    Show-ProjectInfo
    Open-ProjectInBrowser -Urls $ProjectUrls
    exit 0
}

if (-not (Test-ProjectReady)) {
    Initialize-Project
}

Build-AnalystPortal

Write-Step "Ensuring PostgreSQL + Keycloak containers are up..."
Invoke-Compose -ComposeArgs @("-f", "podman-compose.yaml", "up", "-d")
Wait-ForDatabase
Wait-ForDatabasePort
Wait-ForKeycloak

Write-Step "Starting FastAPI..."
$startedServices = Ensure-ApiService
Wait-ForApiAndPortals
Save-ServiceState -StartedServices $startedServices

Show-ProjectInfo
Open-ProjectInBrowser -Urls $ProjectUrls
