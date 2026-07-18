# -*- mode: python ; coding: utf-8 -*-
import os

# 从环境变量获取架构，默认为空（让系统自动决定）
target_arch = os.environ.get('TARGET_ARCH', None)
import sys

base_datas = [('webui', 'webui'), ('icon.ico', '.')]
if sys.platform == 'win32':
    base_datas.append(('drivers/vbcable.zip', 'drivers'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=base_datas,  # 包含前端资源和驱动
    hiddenimports=['engineio.async_drivers.threading', 'pystray', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZeroMic',  # 先生成固定名称，后续由 Actions 改名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch, # 注入架构变量
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    uac_admin=False,  # Windows 自动申请管理员权限
)
