$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $RepoRoot ".venv"
$BackendRequirements = Join-Path $RepoRoot "vendor/videoclaw-app/backend/requirements.txt"
$FrontendDir = Join-Path $RepoRoot "vendor/videoclaw-app/frontend"

Set-Location $RepoRoot

if (-not (Test-Path $BackendRequirements)) {
    throw "Vendored runtime is missing. Run: python tools/vendor_videoclaw.py"
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found on PATH. Install Node.js 20+ for development."
}

if (-not (Test-Path $VenvDir)) {
    Write-Host "[uv-studio] Creating .venv"
    python -m venv $VenvDir
}

$Python = Join-Path $VenvDir "Scripts/python.exe"
Write-Host "[uv-studio] Installing backend dependencies"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r $BackendRequirements

Write-Host "[uv-studio] Installing frontend dependencies"
Push-Location $FrontendDir
try {
    npm ci
}
finally {
    Pop-Location
}

Write-Host "[uv-studio] Development environment is ready."
Write-Host "Backend:  .\scripts\run-backend.ps1"
Write-Host "Frontend: .\scripts\run-frontend.ps1"
