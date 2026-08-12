$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $RepoRoot ".venv"
$UVDevRequirements = Join-Path $RepoRoot "requirements-uv-dev.txt"
$FrontendDir = Join-Path $RepoRoot "frontend"
$FrontendPackage = Join-Path $FrontendDir "package.json"

Set-Location $RepoRoot

if (-not (Test-Path $UVDevRequirements)) {
    throw "UV Studio development dependency file is missing: requirements-uv-dev.txt"
}

if (-not (Test-Path $FrontendPackage)) {
    throw "UV Studio frontend is missing. Run: python tools/promote_frontend.py"
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
Write-Host "[uv-studio] Installing product-owned Python dependencies"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r $UVDevRequirements
& $Python -m pip check

Write-Host "[uv-studio] Installing UV Studio frontend dependencies"
Push-Location $FrontendDir
try {
    npm ci
}
finally {
    Pop-Location
}

Write-Host "[uv-studio] Development environment is ready."
Write-Host "Optional provider/runtime packages are installed separately when needed."
Write-Host "Backend:  .\scripts\run-backend.ps1"
Write-Host "Frontend: .\scripts\run-frontend.ps1"
