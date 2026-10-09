# Build the Windows installer (Inno Setup) from the built host exe.
#
#   powershell -ExecutionPolicy Bypass -File dev\build-installer.ps1
#
# Needs Inno Setup 6 (https://jrsoftware.org/isdl.php). Produces
# dist\ZeroMic-Setup-<version>.exe next to the portable exe.
#
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

$version = (Select-String -Path (Join-Path $repo 'main.py') -Pattern 'VERSION = "v([\d.]+)"').Matches[0].Groups[1].Value

# Prefer the exe the release names; fall back to a plain build.
$exe = Join-Path $repo "dist\ZeroMic-Host-Portable-$version-windows-x64.exe"
if (-not (Test-Path $exe)) { $exe = Join-Path $repo 'dist\ZeroMic.exe' }
if (-not (Test-Path $exe)) { throw "No built host exe in dist\. Run dev\build-host.ps1 first." }

$iscc = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    foreach ($candidate in @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe"
    )) {
        if (Test-Path $candidate) { $iscc = $candidate; break }
    }
}
if (-not $iscc) { throw "Inno Setup not found. Install it from https://jrsoftware.org/isdl.php" }

Write-Host "Building ZeroMic installer $version ..."
Write-Host "  exe: $exe"
Write-Host "  iscc: $iscc"

$iss = Join-Path $repo 'installer\zeromic.iss'
& $iscc "/DAppVersion=$version" "/DSourceExe=$exe" $iss
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit code $LASTEXITCODE" }

$out = Join-Path $repo "dist\ZeroMic-Setup-$version.exe"
if (-not (Test-Path $out)) { throw "ISCC finished but $out is missing." }

Write-Host ""
Write-Host "Installer built: $out"
Write-Host "Installs per-user (no UAC); Start Menu + optional desktop shortcut, and an optional run-at-login entry."
