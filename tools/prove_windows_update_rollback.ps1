param(
    [Parameter(Mandatory = $true)][string]$PrimaryInstallerPath,
    [Parameter(Mandatory = $true)][string]$MakeNsisPath,
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [Parameter(Mandatory = $true)][string]$PrimaryReleaseId,
    [Parameter(Mandatory = $true)][string]$ProductVersion,
    [Parameter(Mandatory = $true)][string]$NsiScriptPath,
    [Parameter(Mandatory = $true)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($PrimaryReleaseId -notmatch '^[A-Za-z0-9._-]+$') {
    throw "primary release id is not Windows-path-safe: $PrimaryReleaseId"
}
if ($PrimaryReleaseId.Length -lt 1) {
    throw 'primary release id must not be empty'
}
$last = $PrimaryReleaseId.Substring($PrimaryReleaseId.Length - 1, 1)
$replacement = if ($last -ceq 'b') { 'c' } else { 'b' }
$secondaryReleaseId = $PrimaryReleaseId.Substring(0, $PrimaryReleaseId.Length - 1) + $replacement
if ($secondaryReleaseId -eq $PrimaryReleaseId -or $secondaryReleaseId.Length -ne $PrimaryReleaseId.Length) {
    throw 'secondary release id must be distinct and the same length as the primary release id'
}
if ($secondaryReleaseId -notmatch '^[A-Za-z0-9._-]+$') {
    throw "secondary release id is not Windows-path-safe: $secondaryReleaseId"
}

$primaryInstaller = (Resolve-Path -LiteralPath $PrimaryInstallerPath).Path
$makensis = (Resolve-Path -LiteralPath $MakeNsisPath).Path
$releaseRootPath = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$nsiScript = (Resolve-Path -LiteralPath $NsiScriptPath).Path
$outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$secondaryInstaller = Join-Path $outputRoot 'uv-studio-update-probe-setup.exe'

$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\UV Studio'
$userDataRoot = Join-Path $env:LOCALAPPDATA 'UV Studio'
$startMenuRoot = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\UV Studio'
$shortcutPath = Join-Path $startMenuRoot 'UV Studio.lnk'

function Invoke-Installer([string]$Path) {
    $process = Start-Process -FilePath $Path -ArgumentList '/S' -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        $diagnostic = Join-Path $userDataRoot 'logs\installer-verification-error.txt'
        if (Test-Path -LiteralPath $diagnostic -PathType Leaf) {
            Write-Host 'Installer verification diagnostic:'
            Get-Content -LiteralPath $diagnostic | Write-Host
        }
        throw "silent installer failed with exit $($process.ExitCode): $Path"
    }
}

function Get-ReleaseBackend([string]$ReleaseId) {
    return Join-Path $installRoot "versions\$ReleaseId\backend\uv-studio-backend.exe"
}

function Assert-ReleaseSelected([string]$ReleaseId) {
    $currentRelease = Join-Path $installRoot 'current-release.txt'
    if (-not (Test-Path -LiteralPath $currentRelease -PathType Leaf)) {
        throw 'current-release.txt is missing'
    }
    $selected = (Get-Content -LiteralPath $currentRelease -Raw).Trim()
    if ($selected -ne $ReleaseId) {
        throw "expected selected release $ReleaseId, got $selected"
    }
    $backend = Get-ReleaseBackend $ReleaseId
    if (-not (Test-Path -LiteralPath $backend -PathType Leaf)) {
        throw "selected release backend is missing: $backend"
    }
    if (-not (Test-Path -LiteralPath $shortcutPath -PathType Leaf)) {
        throw 'Start Menu launcher shortcut is missing'
    }
    $shell = New-Object -ComObject WScript.Shell
    try {
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $target = [IO.Path]::GetFullPath($shortcut.TargetPath)
    } finally {
        if ($shell) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell) }
    }
    if ($target -ne [IO.Path]::GetFullPath($backend)) {
        throw "Start Menu shortcut selected unexpected target: $target"
    }
    & $backend --verify-release
    if ($LASTEXITCODE -ne 0) {
        throw "selected release failed deep verification: $ReleaseId"
    }
}

function Invoke-DesktopSmoke([string]$ReleaseId) {
    $backend = Get-ReleaseBackend $ReleaseId
    $env:UV_STUDIO_USER_DATA_DIR = $userDataRoot
    & $backend --desktop-smoke
    if ($LASTEXITCODE -ne 0) {
        throw "desktop smoke failed for selected release: $ReleaseId"
    }
}

if (Test-Path -LiteralPath $installRoot) {
    Remove-Item -LiteralPath $installRoot -Recurse -Force
}
if (Test-Path -LiteralPath $userDataRoot) {
    Remove-Item -LiteralPath $userDataRoot -Recurse -Force
}
if (Test-Path -LiteralPath $startMenuRoot) {
    Remove-Item -LiteralPath $startMenuRoot -Recurse -Force
}

& $makensis `
    /V3 `
    "/DUV_RELEASE_ROOT=$releaseRootPath" `
    "/DUV_RELEASE_ID=$secondaryReleaseId" `
    "/DUV_PRODUCT_VERSION=$ProductVersion" `
    "/DUV_OUTPUT_FILE=$secondaryInstaller" `
    $nsiScript
if ($LASTEXITCODE -ne 0) {
    throw "NSIS update-probe compilation failed with exit $LASTEXITCODE"
}
if (-not (Test-Path -LiteralPath $secondaryInstaller -PathType Leaf)) {
    throw 'secondary update-probe installer is missing'
}

# Clean install A.
Invoke-Installer $primaryInstaller
Assert-ReleaseSelected $PrimaryReleaseId
Invoke-DesktopSmoke $PrimaryReleaseId

New-Item -ItemType Directory -Force -Path $userDataRoot | Out-Null
$sentinel = Join-Path $userDataRoot 'update-preserve-sentinel.txt'
Set-Content -LiteralPath $sentinel -Value 'PRESERVE_USER_DATA_ACROSS_UPDATE' -Encoding utf8 -NoNewline

# Forward update A -> B. A must remain an immutable rollback sibling.
Invoke-Installer $secondaryInstaller
if (-not (Test-Path -LiteralPath (Get-ReleaseBackend $PrimaryReleaseId) -PathType Leaf)) {
    throw 'forward update removed the previous immutable release'
}
Assert-ReleaseSelected $secondaryReleaseId
Invoke-DesktopSmoke $secondaryReleaseId
if ((Get-Content -LiteralPath $sentinel -Raw) -ne 'PRESERVE_USER_DATA_ACROSS_UPDATE') {
    throw 'forward update modified D-045 user data'
}

# Application rollback B -> A by re-running A's installer. B remains available.
Invoke-Installer $primaryInstaller
if (-not (Test-Path -LiteralPath (Get-ReleaseBackend $secondaryReleaseId) -PathType Leaf)) {
    throw 'rollback activation removed the newer immutable sibling'
}
Assert-ReleaseSelected $PrimaryReleaseId
Invoke-DesktopSmoke $PrimaryReleaseId
if ((Get-Content -LiteralPath $sentinel -Raw) -ne 'PRESERVE_USER_DATA_ACROSS_UPDATE') {
    throw 'rollback activation modified D-045 user data'
}

$uninstaller = Join-Path $installRoot 'Uninstall.exe'
if (-not (Test-Path -LiteralPath $uninstaller -PathType Leaf)) {
    throw 'uninstaller is missing after rollback activation'
}
$uninstall = Start-Process -FilePath $uninstaller -ArgumentList '/S' -PassThru -Wait
if ($uninstall.ExitCode -ne 0) {
    throw "silent uninstaller failed with exit $($uninstall.ExitCode)"
}
$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline -and (Test-Path -LiteralPath $installRoot)) {
    Start-Sleep -Milliseconds 250
}
if (Test-Path -LiteralPath $installRoot) {
    throw 'uninstaller left the immutable application root behind'
}
if (Test-Path -LiteralPath $startMenuRoot) {
    throw 'uninstaller left the Start Menu group behind'
}
if (-not (Test-Path -LiteralPath $sentinel -PathType Leaf)) {
    throw 'uninstaller deleted D-045 user data after update/rollback proof'
}
if ((Get-Content -LiteralPath $sentinel -Raw) -ne 'PRESERVE_USER_DATA_ACROSS_UPDATE') {
    throw 'uninstaller modified D-045 user data after update/rollback proof'
}
Remove-Item -LiteralPath $userDataRoot -Recurse -Force

Write-Host "versioned installer update/rollback proof passed: $PrimaryReleaseId -> $secondaryReleaseId -> $PrimaryReleaseId"
