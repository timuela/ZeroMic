<div align="center">
  <img src="https://x19.fp.ps.netease.com/file/69f5fc8dfcc7c18f65647c58EUpGTLbr07" width="128" height="128" alt="ZeroMic Logo">
  <h1>ZeroMic</h1>
  <p><strong>No App Required (Mobile) · Portable Single-Binary (PC) · Modern MD3 UI</strong></p>
  <p>Transform your smartphone into a High-Fidelity wireless microphone for your PC instantly.</p>
  
  <p>
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square" alt="Platform">
    <img src="https://img.shields.io/badge/License-GPLv3-green?style=flat-square" alt="License">
    <img src="https://img.shields.io/badge/Built%20with-Python%20%7C%20WebRTC-yellow?style=flat-square" alt="Tech">
  </p>
</div>

---

### 🌍 Help Us Translate ZeroMic!

We need your help to make ZeroMic available in more languages!  
Take a look at the existing language files in the `webui/lang/` directory:
- `en_us.json` (English)
- `zh_cn.json` (Simplified Chinese)

To contribute a new translation or improve an existing one:
1. Create a new JSON file following the same structure (e.g. `ja_jp.json`).
2. Submit a Pull Request with your changes.

Every contribution helps us reach more users around the world — thank you! ❤️
---

## 📖 Introduction

**ZeroMic** is a minimalist, cross-platform wireless microphone transmission tool. 

Whether your desktop lacks a dedicated mic or you need high-quality voice input for gaming (Discord, KOOK) or online meetings, ZeroMic has you covered. Simply run the desktop client and access the local URL via your mobile browser—no app installation required. 

Powered by **WebRTC P2P technology**, audio data is streamed directly within your local network (LAN) **without passing through external servers**, ensuring maximum privacy and millisecond-level latency.

## ✨ Key Features

- **🚀 Out-of-the-Box:** Packaged as a single executable. No installation, no complicated setup—just double-click and go.
- **🔧 Auto-Driver Config:** Automatically creates and configures virtual audio devices without manual intervention.
- **🐧 True Cross-Platform:** Native support for Windows, Linux, and macOS from a single codebase.
- **⚡ Ultra-Low Latency:** WebRTC-powered LAN streaming provides a near-wired audio experience.
- **🎨 Modern Design:** Sleek Dark Mode with MD3 (Material Design 3) aesthetics, responsive interactions, and clear status feedback.
- **🧹 Clean Uninstall:** Built-in cleanup feature ensures no driver residue or registry bloat is left behind.

## 🚀 Quick Start

### Prerequisites
- A PC running Windows 10+, Linux (PulseAudio/PipeWire), or macOS.
- Your phone and PC must be connected to the **same Local Area Network (Wi-Fi)**.

### Usage Steps
1. Download the executable for your platform from the [Releases](https://github.com/hypixice/ZeroMic/releases) page.
2. **Windows**: Right-click and **Run as Administrator**. **Linux/macOS**: Run directly (no root required).
3. On first launch, ZeroMic will automatically set up the virtual audio device. (Windows may take 10-20s for driver setup; Linux/macOS is near-instant).
4. Once configured, a URL (e.g., `https://192.168.x.x:5000`) will be displayed on the PC client.
5. Enter this URL in your mobile browser (Safari, Chrome, or Edge recommended).
6. In your game or voice chat software, set the **Microphone Input Device** to the virtual device created by ZeroMic.
7. Start talking!

## 🖥️ ZeroMic Host — PC (portable)

The PC side is a **native Qt application** (PySide6), not a web page. It hosts the local
HTTPS / Socket.IO signalling server, answers the WebRTC call with `aiortc`, and writes the decoded
audio straight into the virtual cable through `sounddevice`. No WebView2, no browser involved.

Released on Windows as `ZeroMic-Portable-<version>-windows-x64.zip` (unzip and run `ZeroMic.exe`)
and `ZeroMic-Setup-<version>.exe` (installs per-user, with a Start Menu shortcut and an optional
run-at-login entry). On Linux and macOS it is `ZeroMic-Host-<version>-<platform>.tar.gz`.

- Native window + system tray (show / mute / exit).
- `aiortc` as the WebRTC answerer; host-candidate ICE only, so it connects instantly on the LAN.
- Lists **every** network address the PC has (Wi-Fi, Ethernet, VPN, Tailscale), each with its own
  QR code, so the phone can reach it on whichever network you are actually using.
- The listening port can be changed from the window; it is remembered between runs.
- Auto-matches the virtual device (`CABLE Input` / `zeromic_sink` / `BlackHole`).
- Live gain slider and mute that act on the audio callback, so they respond instantly.

> **Building requires Python 3.11 or newer** (PySide6 6.10+ supports 3.14; CI builds on 3.11).

## 📱 ZeroMic Client — Android

The browser client works, but Android browsers (Chrome, Brave, etc.) suspend the page when the
screen turns off, which kills the microphone stream. For reliable screen-off streaming there is a
native client in [`android/`](./android), released as `ZeroMic-Client-<version>.apk`.

- Runs as a foreground service with a partial wake lock + Wi-Fi lock, so the mic keeps streaming
  while the screen is off.
- Speaks the exact same Socket.IO + WebRTC signalling protocol as the web client — the PC side is
  completely unchanged, and it also auto-recovers the session with an ICE restart if the network
  path changes.
- Save hosts as **profiles** and pick one from the Hosts menu instead of retyping the address.
- Type just an IP and the port defaults to `5000`; add `:port` only when the host uses another one.

Requires Android 8.0 (API 26) or newer.

### Build

Open the `android/` folder in Android Studio (JDK 17) and run it on your device, or from the CLI:

```bash
cd android
./gradlew assembleDebug        # Windows: gradlew.bat assembleDebug
```

The APK is written to `android/app/build/outputs/apk/debug/app-debug.apk`.
The [`.github/workflows/android.yml`](./.github/workflows/android.yml) workflow also builds this
debug APK on every push that touches `android/`, so you can grab it as a build artifact.

## 🛠️ Developer Guide (Build from Source)

```bash
# 1. Clone the repository
git clone [https://github.com/hypixice/ZeroMic.git](https://github.com/hypixice/ZeroMic.git)
cd ZeroMic

# 2. Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-windows.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt

# 3. Build Executable
# Windows
.\build.bat

# Linux / macOS
./build.sh
```
The packaged binary will be located in the `dist/` directory.

## ⚠️ FAQ

**Q: Mobile browser shows "Connection is not private"?**
A: This occurs because we use a self-signed certificate for LAN HTTPS (a mandatory requirement for WebRTC). Click "Advanced" -> "Proceed to..." in your browser to continue.

**Q: Why did my PC sound stop working after setup? (Windows)**
A: Windows sometimes sets the new virtual device as the default "Speaker". Click the volume icon in your taskbar and manually switch back to your original speakers/headphones.

**Q: The app opens but there is no audio? (Linux)**
A: Install PortAudio: `sudo apt install libportaudio2`. ZeroMic needs it to reach the virtual sink, and it is a system library rather than something bundled into the binary.

**Q: "pactl command not found" on Linux?**
A: Ensure PulseAudio or PipeWire is installed. Most desktop distros include them. If missing: `sudo apt install pulseaudio-utils` (Debian/Ubuntu) or `sudo pacman -S pulseaudio` (Arch).

**Q: Error when clicking "Uninstall Driver"? (Windows)**
A: Ensure the software is running with **Administrator privileges**. It is recommended to restart your PC after uninstallation to completely clear the audio routing cache.

## 📄 License
This project is licensed under the [GPL-3.0 License](LICENSE). You are free to use, modify, and distribute the code, provided that all derivative works remain open-source under the same license.

---
*Created with ❤️ by Hypixice Studio.*
