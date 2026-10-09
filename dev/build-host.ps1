# Build the Windows host (one-dir) and zip it as the portable download.
#
#   powershell -ExecutionPolicy Bypass -File dev\build-host.ps1
#
# One-dir: the app runs straight from its folder instead of unpacking to %TEMP%
# on every launch, and the installer can ship the same folder.
#
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

$py = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "No .venv found. Run dev\setup.ps1 first." }

$version = (Select-String -Path (Join-Path $repo 'main.py') -Pattern 'VERSION = "v([\d.]+)"').Matches[0].Groups[1].Value
Write-Host "Building ZeroMic Host $version (one-dir) ..."

Push-Location $repo
try {
    & $py -m PyInstaller --noconfirm main.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

$built = Join-Path $repo 'dist\ZeroMic\ZeroMic.exe'
if (-not (Test-Path $built)) { throw "PyInstaller finished but $built is missing." }

$zip = Join-Path $repo "dist\ZeroMic-Portable-$version-windows-x64.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $repo 'dist\ZeroMic\*') -DestinationPath $zip

Write-Host ""
Write-Host "Host built:   $(Join-Path $repo 'dist\ZeroMic')"
Write-Host "Portable zip: $zip  (unzip anywhere, run ZeroMic.exe)"
Write-Host "Installer:    run dev\build-installer.ps1"
