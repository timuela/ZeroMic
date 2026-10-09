# Local development

Build and test both halves of ZeroMic on this machine, without waiting for CI.
Nothing here touches your system installs or needs admin rights.

## One-time setup

```powershell
powershell -ExecutionPolicy Bypass -File dev\setup.ps1
```

It downloads two things into `D:\dev\zeromic-tools` (override with the
`ZEROMIC_TOOLS` environment variable):

| What | Why |
|------|-----|
| Temurin **JDK 17** | AGP 8.7 needs JDK 17-21. Your system JDK is 25, which Gradle rejects. |
| **Android SDK** + platform 35, build-tools 35, platform-tools | To compile the APK. |

It also creates `.venv` in the repo (Python + PySide6, aiortc, sounddevice,
PyInstaller, ...) and writes `android/local.properties` so Gradle and Android
Studio find our SDK copy.

Roughly 700 MB of downloads, one time.

## Everyday use

```powershell
dev\run-host.ps1      # run the host from source - use this while fixing things
dev\build-host.ps1    # dist\ZeroMic-Host-Portable-<version>-windows-x64.exe
dev\build-apk.ps1     # dist\ZeroMic-Client-<version>.apk
```

`run-host.ps1` is the fast loop: it launches `main.py` directly, so a code
change just needs a restart rather than a full PyInstaller build.

`build-host.ps1` and `build-apk.ps1` deliberately match what the release
workflow produces - same spec file, same release build type, same committed
signing key, same version numbers - so an APK you build here installs over a
released one instead of being rejected as a different signer.

Version comes from `VERSION` in `main.py`; bump that and both scripts follow.
The APK `versionCode` is derived the same way locally and in CI
(`0.1.6` -> `106`), so builds from either place order correctly.

## Before you tag a release

```powershell
.venv\Scripts\python.exe desktop\smoke_test.py   # headless UI/N-API check
dev\run-host.ps1                                  # then click around
```

`desktop/smoke_test.py` builds the real window, runs every setter, forces a
repaint and checks the window does not resize itself. It catches missing Qt
APIs (it exists because `QApplication.applicationIcon()` shipped once). Add
`QT_QPA_PLATFORM=offscreen` to run it without a window.

## Notes

- The venv uses your system **Python 3.14**; CI builds with **3.11**. All
  dependencies have wheels for both, but if something behaves differently
  between a local build and a released one, that is the first thing to check.
- The **Linux** host needs `libportaudio2` installed to play audio
  (`sudo apt install libportaudio2`); it is a system library and is not bundled.
- `dist/` and `.venv/` are gitignored, as is `android/local.properties`.
