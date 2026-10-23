# DevMentor install script (Windows)
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1

param(
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $InstallDir) { $InstallDir = Join-Path $env:USERPROFILE ".devmentor" }

$ProjectRoot = $PSScriptRoot
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"

# --- 1. Check toolchain ---
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) {
    Write-Host "Cannot find Python. Install 3.11+ first: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
Write-Host ("Using Python: " + $python) -ForegroundColor Gray

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Cannot find Node.js. Install 18+ first: https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# --- 2. Install deps and build frontend ---
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
& $python -m pip install -q -e $Backend
if ($LASTEXITCODE -ne 0) {
    Write-Host "" -ForegroundColor Red
    Write-Host "Backend install failed. Try these in order:" -ForegroundColor Red
    Write-Host "  1. python -m pip install --upgrade pip" -ForegroundColor Gray
    Write-Host "  2. python -m pip install -e backend" -ForegroundColor Gray
    Write-Host "     (run the second command by hand to see the full error)" -ForegroundColor Gray
    Write-Host "  3. Or use a virtualenv: python -m venv .venv; .venv\Scripts\activate" -ForegroundColor Gray
    exit 1
}

Write-Host "Building frontend..." -ForegroundColor Yellow
Push-Location $Frontend
npm install --silent
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "npm install failed. Try: cd frontend; npm install (to see the full error)" -ForegroundColor Red
    exit 1
}
npm run build --silent
Pop-Location
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed." -ForegroundColor Red
    exit 1
}

# --- 3. Write launcher ---
$BinDir = Join-Path $InstallDir "bin"
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

Set-Content -Path (Join-Path $BinDir "devmentor.cmd") -Encoding ascii -Value @(
    '@echo off'
    'REM DevMentor - terminal programming mentor'
    'setlocal'
    'if defined DEVMENTOR_PROJECT_ROOT ('
    '    set "PROJECT_ROOT=%DEVMENTOR_PROJECT_ROOT%"'
    ') else ('
    ('    set "PROJECT_ROOT=' + $ProjectRoot + '"')
    ')'
    'node "%PROJECT_ROOT%\\frontend\\dist\\cli.js" %*'
)
Write-Host ("Launcher written to " + (Join-Path $BinDir "devmentor.cmd")) -ForegroundColor Green

# --- 4. Add to PATH ---
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike ("*" + $BinDir + "*")) {
    [Environment]::SetEnvironmentVariable("PATH", ($userPath + ";" + $BinDir), "User")
    Write-Host ("Added " + $BinDir + " to user PATH (restart terminal to take effect)") -ForegroundColor Green
} else {
    Write-Host ($BinDir + " already in PATH") -ForegroundColor Green
}

Write-Host ""
Write-Host "Install complete!" -ForegroundColor Green
Write-Host "  Type devmentor in terminal to start." -ForegroundColor Cyan
Write-Host "  Then /login to pick a model provider." -ForegroundColor Gray