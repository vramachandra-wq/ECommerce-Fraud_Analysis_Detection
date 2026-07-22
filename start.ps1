# Starts PostgreSQL (Podman), FastAPI, and both Streamlit portals.
# First run: creates .venv, .env, and installs dependencies.
# If all services are already up: opens Google Chrome immediately.
# Usage (from project root in PowerShell): .\start.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Get-Location }
Set-Location $ProjectRoot

$RunDir = Join-Path $ProjectRoot ".run"
$LogDir = Join-Path $RunDir "logs"
$StateFile = Join-Path $RunDir "services.json"

$ProjectUrls = @(
    "http://127.0.0.1:8000/docs",
    "http://localhost:8501",
    "http://localhost:8502"
)

$AppServices = @(
    @{
        name      = "api"
        port      = 8000
        healthUrl = "http://127.0.0.1:8000/"
        logFile   = "api.log"
        arguments = @("-m", "uvicorn", "api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000")
    },
    @{
        name      = "customer"
        port      = 8501
        healthUrl = "http://127.0.0.1:8501/"
        logFile   = "customer.log"
        arguments = @("-m", "streamlit", "run", "customer_app.py", "--server.port", "8501", "--server.headless", "true")
    },
    @{
        name      = "analyst"
        port      = 8502
        healthUrl = "http://127.0.0.1:8502/"
        logFile   = "analyst.log"
        arguments = @("-m", "streamlit", "run", "analyst_app.py", "--server.port", "8502", "--server.headless", "true")
    }
)

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
    if ($env:APPDATA) {
        $roots += Join-Path $env:APPDATA "Python"
    }
    if ($env:LOCALAPPDATA) {
        $roots += Join-Path $env:LOCALAPPDATA "Programs\Python"
    }

    foreach ($root in $roots) {
        if (-not (Test-Path $root)) {
            continue
        }
        $match = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
            ForEach-Object {
                $candidate = Join-Path $_.FullName "Scripts\podman-compose.exe"
                if (Test-Path $candidate) { $candidate }
            } |
            Select-Object -First 1
        if ($match) {
            return $match
        }
    }

    return $null
}

function Get-ComposeCommand {
    # Prefer podman-compose: Windows Podman often lacks the "podman compose" provider.
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

function Test-PortListening([int]$Port) {
    $match = netstat -ano | Select-String ":$Port\s" | Select-String "LISTENING"
    return $null -ne $match
}

function Test-DatabaseRunning {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"

    try {
        $status = podman inspect ecommerce_fraud --format "{{.State.Health.Status}}" 2>$null
        if ($status -eq "healthy") {
            return $true
        }

        $running = podman inspect ecommerce_fraud --format "{{.State.Running}}" 2>$null
        return $running -eq "true"
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Test-AllServicesHealthy {
    if (-not (Test-DatabaseRunning)) {
        return $false
    }

    foreach ($svc in $AppServices) {
        if (-not (Test-PortListening $svc.port)) {
            return $false
        }
    }

    return $true
}

function Test-ServiceRunning([int]$ProcessId) {
    return (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) -ne $null
}

function Start-AppProcess {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [string]$LogFile
    )

    $python = Get-PythonExecutable
    $stdout = Join-Path $LogDir $LogFile
    $stderr = "$stdout.err"

    $process = Start-Process `
        -FilePath $python `
        -ArgumentList $Arguments `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr

    return @{
        name = $Name
        pid  = $process.Id
        log  = $stdout
    }
}

function Get-DbPortFromEnv {
    $defaultPort = 5434
    $envPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envPath)) {
        return $defaultPort
    }

    foreach ($line in Get-Content $envPath) {
        if ($line -match '^\s*DB_PORT=(.+)$') {
            return [int]$Matches[1].Trim().Trim('"').Trim("'")
        }
    }

    return $defaultPort
}

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

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
            # Service still starting
        }
        Start-Sleep -Seconds 2
    }

    return $false
}

function Wait-ForAllAppServices {
    Write-Step "Waiting for application services to respond..."
    foreach ($svc in $AppServices) {
        Write-Host "  Checking $($svc.name) on port $($svc.port)..."
        if (-not (Wait-ForHttp -Url $svc.healthUrl -TimeoutSeconds 90)) {
            throw "$($svc.name) did not become ready. See log: $(Join-Path $LogDir $svc.logFile)"
        }
        Write-Host "  $($svc.name) is ready." -ForegroundColor Green
    }
}

function Get-ChromeExecutable {
    $candidates = @(
        (Join-Path ${env:ProgramFiles} "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
    )

    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }

    $fromPath = Get-Command chrome -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    return $null
}

function Open-ProjectInBrowser {
    param([string[]]$Urls)

    $chrome = Get-ChromeExecutable
    if ($chrome) {
        Write-Step "Opening project in Google Chrome..."
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
    Write-Host "  API docs:         http://127.0.0.1:8000/docs"
    Write-Host "  Customer portal:  http://localhost:8501"
    Write-Host "  Analyst portal:   http://localhost:8502"
    Write-Host ""
    Write-Host "Logs: $LogDir"
    Write-Host "Stop everything with: .\stop.ps1"
}

function Ensure-ApplicationServices {
    $started = @()

    foreach ($svc in $AppServices) {
        if (Test-PortListening $svc.port) {
            Write-Host "  $($svc.name) already listening on port $($svc.port)." -ForegroundColor Green
            continue
        }

        Write-Host "  Starting $($svc.name)..."
        $processInfo = Start-AppProcess -Name $svc.name -Arguments $svc.arguments -LogFile $svc.logFile
        Start-Sleep -Seconds 2

        if (-not (Test-ServiceRunning $processInfo.pid)) {
            throw "Failed to start $($svc.name). See log: $($processInfo.log)"
        }

        $started += $processInfo
    }

    return $started
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
}

Write-Host ""
Write-Host "Metro Cart - starting platform..." -ForegroundColor White
Write-Host ""

# Fast path: everything already healthy
if (Test-AllServicesHealthy) {
    Write-Host "All services are already running (database + API + portals)." -ForegroundColor Green
    Show-ProjectInfo
    Open-ProjectInBrowser -Urls $ProjectUrls
    exit 0
}

# Bootstrap project files on first run
if (-not (Test-ProjectReady)) {
    Initialize-Project
}

Write-Step "Ensuring PostgreSQL container is up..."
Invoke-Compose -ComposeArgs @("-f", "podman-compose.yaml", "up", "-d")
Wait-ForDatabase
Wait-ForDatabasePort

Write-Step "Starting application services..."
$startedServices = Ensure-ApplicationServices
Wait-ForAllAppServices
Save-ServiceState -StartedServices $startedServices

Show-ProjectInfo
Open-ProjectInBrowser -Urls $ProjectUrls
