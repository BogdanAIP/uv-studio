$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv/Scripts/python.exe"

if (-not (Test-Path $Python)) {
    throw "Development environment is not prepared. Run: .\scripts\setup-dev.ps1"
}

Set-Location $RepoRoot
& $Python "tools/uv_dev.py" backend
exit $LASTEXITCODE
