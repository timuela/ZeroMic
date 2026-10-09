# Build the Windows host binary, exactly like the release workflow does.
#
#   powershell -ExecutionPolicy Bypass -File dev\build-host.ps1
#
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

$py = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "No .venv found. Run dev\setup.ps1 first." }

$version = (Select-String -Path (Join-Path $repo 'main.py') -Pattern 'VERSION = "v([\d.]+)"').Matches[0].Groups[1].Value
Write-Host "Building ZeroMic Host $version ..."

Push-Location $repo
try {
    & $py -m PyInstaller --noconfirm main.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

$built = Join-Path $repo 'dist\ZeroMic.exe'
if (-not (Test-Path $built)) { throw "PyInstaller finished but $built is missing." }

$out = Join-Path $repo "dist\ZeroMic-Host-Portable-$version-windows-x64.exe"
Move-Item $built $out -Force

Write-Host ""
Write-Host "Host built: $out"
Write-Host "That is the same name the release uses, so you can run it side by side."
