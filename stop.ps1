# Metro Cart — stop FastAPI and the PostgreSQL container.
# Usage (from project root): .\stop.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
Set-Location $ProjectRoot

$RunDir = Join-Path $ProjectRoot ".run"
$StateFile = Join-Path $RunDir "services.json"
$ApiPort = 8000

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

    return $null
}

function Invoke-Compose {
    param([string[]]$ComposeArgs)

    $compose = Get-ComposeCommand
    if (-not $compose) {
        Write-Host "Compose not found; trying direct podman stop..." -ForegroundColor Yellow
        if (Get-Command podman -ErrorAction SilentlyContinue) {
            & podman stop ecommerce_fraud 2>$null
        }
        return
    }

    $args = @($compose.Arguments + $ComposeArgs) | Where-Object { $_ }
    & $compose.Executable @args
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: compose command returned exit code $LASTEXITCODE; trying direct podman stop..." -ForegroundColor Yellow
        if (Get-Command podman -ErrorAction SilentlyContinue) {
            & podman stop ecommerce_fraud 2>$null
        }
    }
}

function Stop-ProcessTree {
    param([int]$ProcessId)

    if ($ProcessId -le 0) { return }

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ParentProcessId -eq $ProcessId } |
        ForEach-Object { Stop-ProcessTree -ProcessId $_.ProcessId }

    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-PortListeners {
    param([int[]]$Ports)

    foreach ($port in $Ports) {
        $connections = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
        foreach ($line in $connections) {
            if ($line -match "\s(\d+)\s*$") {
                $targetPid = [int]$Matches[1]
                if ($targetPid -gt 0) {
                    Write-Host "Stopping listener on port $port (PID $targetPid)..."
                    Stop-ProcessTree -ProcessId $targetPid
                }
            }
        }
    }
}

Write-Step "Stopping FastAPI..."

if (Test-Path $StateFile) {
    $services = Get-Content $StateFile -Raw | ConvertFrom-Json
    # ConvertFrom-Json returns a single object when one entry exists
    if ($services -isnot [System.Array]) {
        $services = @($services)
    }
    foreach ($svc in $services) {
        if ($svc.pid -and (Get-Process -Id $svc.pid -ErrorAction SilentlyContinue)) {
            Write-Host "Stopping $($svc.name) (PID $($svc.pid))..."
            Stop-ProcessTree -ProcessId $svc.pid
        }
    }
    Remove-Item $StateFile -Force -ErrorAction SilentlyContinue
}
else {
    Write-Host "No service state file found. Cleaning API port..." -ForegroundColor Yellow
}

# Only the FastAPI port — Streamlit ports are no longer used
Stop-PortListeners -Ports @($ApiPort)

Write-Step "Stopping PostgreSQL container..."
Invoke-Compose -ComposeArgs @("-f", "podman-compose.yaml", "down")

Write-Host ""
Write-Host "All services stopped." -ForegroundColor Green
exit 0
