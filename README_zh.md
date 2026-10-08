
# ZeroMic

<div align="center">
  <img src="https://x19.fp.ps.netease.com/file/69f5fc8dfcc7c18f65647c58EUpGTLbr07" width="128" height="128" alt="ZeroMic Logo">
  <h1>ZeroMic</h1>
  <p><strong>手机免安装 · 电脑绿色单文件 · MD3 现代 UI 设计</strong></p>
  <p>将你的智能手机瞬间变身为电脑的高保真无线麦克风</p>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/License-GPLv3-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Built%20with-Python%20%7C%20WebRTC-yellow?style=flat-square" alt="Tech">
</div>

[English](./README.md) | [简体中文](./README_zh.md)


### 🌍 帮助我们翻译 ZeroMic！

我们需要你的帮助，让 ZeroMic 支持更多语言！  
请参考 `webui/lang/` 目录下的语言文件：
- `en_us.json`（英语）
- `zh_cn.json`（简体中文）

贡献新语言或改进现有翻译的方法：
1. 按照相同的结构创建一个新的 JSON 文件（例如 `ja_jp.json`）。
2. 提交 Pull Request。

你的每一份贡献都能帮助全球更多用户用上 ZeroMic——非常感谢！❤️
---

## 📖 简介

**ZeroMic** 是一款极简的跨平台无线麦克风传输工具。
当你台式机没有麦克风，或者需要高质量的语音输入来进行游戏开黑（如 Discord、KOOK）或网络会议时，只需运行 ZeroMic，用手机访问局域网地址，即可利用手机的高性能麦克风进行毫秒级延迟的音频传输。

核心采用 P2P **WebRTC 技术**，音频数据完全在局域网内直连，**不经过任何外部服务器**，保证极致的安全与极低的延迟。


# ✨ 特点
🚀 拿来就用：打包为单个可执行文件，无需安装，双击即用。

🔧 虚拟音频自动配置：自动创建虚拟音频设备，无需手动折腾驱动。

🐧 跨平台支持：Windows / Linux / macOS，一套代码三端运行。

⚡ 延迟够低：WebRTC 局域网直连，通话跟插了线差不多。

🎨 看着舒服：深色界面，MD3 风格，交互跟手，状态反馈清楚。

🧹 走也干净：内置清理功能，卸载不留残留。


## 🚀 快速开始

### 准备工作
- 一台 Windows 10+ / Linux（需 PulseAudio 或 PipeWire）/ macOS 电脑。
- 手机与电脑需要处于 **同一个局域网（Wi-Fi）** 下。

### 使用步骤
1. 前往 [Releases](https://github.com/hypixice/ZeroMic/releases) 页面下载对应平台的可执行文件。
2. **Windows**：右键以管理员身份运行。**Linux/macOS**：直接运行（无需管理员权限）。
3. 首次启动时软件会自动配置虚拟音频设备。Windows 可能需要下载驱动（10-20 秒），Linux/macOS 秒级完成。
4. 配置完毕后，电脑端会显示一个 URL 地址（如 `https://192.168.x.x:5000`）。
5. 在手机浏览器（推荐 Safari / Chrome / Edge）中输入该地址。
6. 在游戏或语音软件的设置中，将 **麦克风输入设备** 更改为软件提示的虚拟设备名称。
7. 开始说话吧！

## 📱 原生 Android 客户端

浏览器客户端可用，但 Android 浏览器（Chrome、Brave 等）在息屏后会挂起页面，导致麦克风流被中断。
如需在息屏后稳定传输，可使用 [`android/`](./android) 目录下的原生客户端。

- 以前台服务 + 部分唤醒锁（Partial Wake Lock）+ Wi-Fi 锁运行，息屏后麦克风仍持续传输。
- 与网页客户端使用完全相同的 Socket.IO + WebRTC 信令协议，电脑端无需任何改动；网络路径变化时还会通过 ICE 重启自动恢复会话。
- 输入电脑端界面显示的 `IP:端口`，点击连接即可（会自动记住上次地址）。

需要 Android 8.0（API 26）及以上版本。

### 构建

用 Android Studio（JDK 17）打开 `android/` 目录直接运行，或使用命令行：

```bash
cd android
./gradlew assembleDebug        # Windows 使用 gradlew.bat assembleDebug
```

APK 输出在 `android/app/build/outputs/apk/debug/app-debug.apk`。
[`.github/workflows/android.yml`](./.github/workflows/android.yml) 也会在每次改动 `android/` 时自动构建调试包，可直接下载产物。

## 🛠️ 开发者指南 (从源码构建)

```bash
# 1. 克隆仓库
git clone https://github.com/hypixice/ZeroMic.git
cd ZeroMic

# 2. 创建并激活虚拟环境
python -m venv .venv

# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-windows.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt

# 3. 一键打包
# Windows
.\build.bat

# Linux / macOS
./build.sh
```

打包后的可执行文件位于 `dist/` 目录。

## ⚠️ 常见问题 (FAQ)

**Q: 手机浏览器提示”不安全”或拒绝访问？**
A: 因为我们使用了自签名证书来开启局域网 HTTPS（WebRTC 的强制要求）。请在浏览器拦截页面点击”高级” -> “继续访问”即可。

**Q: 为什么装完之后电脑突然没声音了？（Windows）**
A: Windows 可能会将新安装的虚拟声卡设为默认扬声器。请点击电脑右下角的喇叭图标，手动切换回原来的扬声器设备。

**Q: Linux 下提示 pactl 命令不可用？**
A: 请确认已安装 PulseAudio 或 PipeWire。大多数桌面发行版已自带。如果缺失：`sudo apt install pulseaudio-utils`（Debian/Ubuntu）或 `sudo pacman -S pulseaudio`（Arch）。

**Q: 点击卸载驱动报错？（Windows）**
A: 请确保软件是以**管理员身份**运行的。卸载完成后建议重启电脑以彻底清理音频路由表的残留。

## 📄 许可协议
本项目采用 [GPL-3.0 License](LICENSE) 许可协议。任何人都可以自由使用、修改和分发，但衍生作品必须同样开源并采用相同协议。

---
*Created with ❤️ by Hypixice Studio.*
