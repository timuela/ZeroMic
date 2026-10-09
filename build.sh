#!/usr/bin/env bash
# ZeroMic build script (Linux / macOS)
# Usage: chmod +x build.sh && ./build.sh

set -e

echo "=== Cleaning previous build ==="
rm -rf build dist

echo "=== Building ==="
pyinstaller --noconfirm main.spec

echo "=== Build complete ==="
echo "Executable: $(pwd)/dist/ZeroMic"
