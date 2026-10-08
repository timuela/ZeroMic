#!/usr/bin/env bash
# ZeroMic 构建脚本 (Linux / macOS)
# 使用方法: chmod +x build.sh && ./build.sh

set -e

echo "=== 清理旧构建 ==="
rm -rf build dist

echo "=== 开始打包 ==="
pyinstaller --noconfirm main.spec

echo "=== 打包完成 ==="
echo "可执行文件在: $(pwd)/dist/ZeroMic"
