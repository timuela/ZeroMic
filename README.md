<div align="center">
  <img src="https://x19.fp.ps.netease.com/file/69f5fc8dfcc7c18f65647c58EUpGTLbr07" width="128" height="128" alt="ZeroMic Logo">
  <h1>ZeroMic</h1>
  <p><strong>Use your phone as your PC's microphone.</strong></p>
  <p>Nothing to install on the phone. No account. Nothing leaves your Wi-Fi.</p>

  <p>
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square" alt="Platform">
    <img src="https://img.shields.io/badge/License-GPLv3-green?style=flat-square" alt="License">
  </p>
</div>

---

## What is this?

Your desktop either has no microphone or a poor one. ZeroMic turns your phone into a good one —
for Discord, in-game voice chat, meetings, streaming, or recording.

You run a small app on the PC. It shows a web address. You open that address on your phone. From
then on your voice travels from the phone, over your own Wi-Fi, straight into whatever app you're
using on the PC.

- **Nothing to install on the phone** — it's just a web page.
- **Nothing goes over the internet.** Audio goes phone → PC directly, so it stays private and fast.
- **Works with any app** that lets you choose a microphone.

## Getting started

**You need:** a Windows, Linux or macOS PC, a phone, and both on the same Wi-Fi.

**1. Download ZeroMic for your PC** from the [Releases page](https://github.com/timuela/ZeroMic/releases):

| Your PC | File | What to do |
| --- | --- | --- |
| Windows (64-bit) | `ZeroMic-Host-Setup-<version>-windows-x64.exe` | Run it — installs with a Start Menu shortcut |
| Windows (64-bit) | `ZeroMic-Host-Portable-<version>-windows-x64.exe` | One single file — just run it, nothing to unpack |
| Windows (ARM) | `ZeroMic-Host-Portable-<version>-windows-arm64.exe` | Same, for ARM PCs |
| Linux | `ZeroMic-Host-<version>-linux-x64.tar.gz` | Extract, then run `ZeroMic` |
| macOS (Apple silicon) | `ZeroMic-Host-<version>-macos-arm64.tar.gz` | Extract, then run `ZeroMic` |
| macOS (Intel) | `ZeroMic-Host-<version>-macos-x64.tar.gz` | Extract, then run `ZeroMic` |

**2. Run it.** ZeroMic needs a virtual audio device to play into, and sets one up like this:

- **Windows** — installs it for you on first launch (10–20 seconds), and Windows asks for
  permission. Say yes.
- **Linux** — creates one instantly.
- **macOS** — install [BlackHole](https://github.com/ExistentialAudio/BlackHole) first:
  `brew install blackhole-2ch`. The app tells you if it's missing.

**3. Open the address on your phone.** The PC window shows something like `https://192.168.1.42:5000`,
and a QR code you can scan instead of typing. Your phone and PC must be on the same Wi-Fi.

**4. Accept the security warning.** Your phone will say the connection isn't private. That's
expected — browsers only allow microphone access over HTTPS, so ZeroMic makes its own certificate.
Tap **Advanced → Proceed**.

**5. Type the PIN** shown on the PC window. (You can change it, or turn the PIN off entirely, in
Settings.)

**6. Point your app at ZeroMic's microphone.** In the game, Discord, Zoom, OBS — wherever — pick
the virtual device as the microphone input:

| Your PC | Choose this microphone |
| --- | --- |
| Windows | `CABLE Output (VB-Audio Virtual Cable)` |
| Linux | `ZeroMic Virtual Output Monitor` |
| macOS | `BlackHole 2ch` |

*(On Windows you'll also see a `CABLE Input` device — that's the other end of the same cable.
The app plays into it, so you record from `CABLE Output`.)*

**7. Talk.**

ZeroMic remembers your port and PIN and starts listening again by itself next time. Close it and
it keeps running in the tray, or turn that off in Settings.

## On the PC

The window is small on purpose. From it you can:

- See whether your phone is connected.
- Pick the audio output device ZeroMic plays into (it finds the virtual one automatically).
- Set the volume, and mute — the tray icon can mute too.
- Copy any of your PC's addresses (Wi-Fi, Ethernet, VPN, Tailscale), and show a QR code for
  whichever network your phone is actually on.
- Change the **port**, the **PIN**, the **language** (English / 中文 / Tiếng Việt), whether it
  starts with Windows, and whether closing the window quits or hides to the tray.

## The phone app (optional)

The web page is all most people need. But Android phones stop a web page's microphone when the
screen turns off, so for long calls there's a small native app:
**`ZeroMic-Client-<version>.apk`** from the same [Releases page](https://github.com/timuela/ZeroMic/releases).
Needs Android 8.0 or newer.

- Keeps streaming with the screen off (it runs as a proper foreground service).
- Save your PCs as **profiles** and switch between them instead of retyping the address.
- Type just the IP — the port defaults to `5000`.

## Troubleshooting

**My phone says the connection isn't private.**
That's normal and safe. It's ZeroMic's own certificate, not a broken site. Tap **Advanced**, then
**Proceed**.

**My PC suddenly has no sound (Windows).**
The driver installer sometimes makes the virtual cable your default speaker. Click the speaker
icon in the taskbar and switch back to your real speakers or headphones. ZeroMic reminds you about
this after installing.

**No audio at all on Linux.**
Install PortAudio: `sudo apt install libportaudio2`. It's a system library, so it isn't bundled
inside the app.

**"pactl: command not found" (Linux).**
You need PulseAudio or PipeWire. Most desktops already have one; if not, `sudo apt install
pulseaudio-utils` (Debian/Ubuntu) or `sudo pacman -S pulseaudio` (Arch).

**My phone can't reach the PC.**
Check both are on the same Wi-Fi, and that you used the address the PC is actually showing —
if you're on a VPN or Tailscale, pick that address. Guest Wi-Fi and "client isolation" block
phone-to-PC traffic entirely.

**Uninstalling the driver on Windows fails.**
Run ZeroMic as administrator for that, and restart the PC afterwards to clear the audio routing.

## Building from source

Requires **Python 3.11 or newer** (PySide6 supports 3.14 from 6.10; the CI builds on 3.11).

```bash
git clone https://github.com/timuela/ZeroMic.git
cd ZeroMic

python -m venv .venv

# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-windows.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt

# Build the desktop host — Windows
.\build.bat

# Build the desktop host — Linux / macOS
./build.sh
```

The app lands in `dist/ZeroMic/`. On Windows, `dev\build-host.ps1` also produces the single-file
portable exe, and `dev\build-installer.ps1` builds the installer (needs [Inno Setup 6](https://jrsoftware.org/isdl.php)).

For the Android client, open `android/` in Android Studio (JDK 17) or use the CLI:

```bash
cd android
./gradlew assembleDebug        # Windows: gradlew.bat assembleDebug
```

The APK is written to `android/app/build/outputs/apk/debug/app-debug.apk`.

## License

[GPL-3.0](LICENSE) — free to use, modify and share, as long as derivatives stay open under the
same licence.

---
*Made with ❤️ by Hypixice Studio.*
