# Build the React analyst portal into static/analyst-portal/ (served by FastAPI at /portal/)
# Usage (from project root): .\scripts\build_analyst_portal.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { (Get-Location).Path }
$PortalDir = Join-Path $ProjectRoot "analyst-portal"

Set-Location $PortalDir

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm is required to build the analyst portal. Install from https://nodejs.org/"
}

Write-Host "==> Installing analyst-portal dependencies..." -ForegroundColor Cyan
npm install

Write-Host "==> Building analyst portal to static/analyst-portal/ ..." -ForegroundColor Cyan
npm run build

$bgSource = Join-Path $PortalDir "public\assets\portal-bg.png"
$bgTarget = Join-Path $ProjectRoot "static\analyst-portal\assets\portal-bg.png"
if (Test-Path $bgSource) {
    Copy-Item $bgSource $bgTarget -Force
}

Write-Host ""
Write-Host "Analyst portal build complete." -ForegroundColor Green
Write-Host "Start the API and open http://127.0.0.1:8000/portal/" -ForegroundColor Green
