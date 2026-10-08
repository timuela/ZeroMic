@echo off
REM ZeroMic 构建脚本 (Windows)
if not exist ".venv\Scripts\pyinstaller" (
    echo 请先创建虚拟环境并安装依赖：
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo   .venv\Scripts\pip install -r requirements-windows.txt
    exit /b 1
)

.venv\Scripts\pyinstaller --noconfirm main.spec
