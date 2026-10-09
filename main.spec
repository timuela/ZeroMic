# -*- mode: python ; coding: utf-8 -*-
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files

# 从环境变量获取架构，默认为空（让系统自动决定）
target_arch = os.environ.get('TARGET_ARCH', None)

base_datas = [
    ('webui', 'webui'),
    ('desktop/style.qss', 'desktop'),
    ('desktop/icon-volume-off.png', 'desktop'),
    ('desktop/icon-volume-up.png', 'desktop'),
    ('desktop/icon.png', 'desktop'),
    ('icon.ico', '.'),
]
if sys.platform == 'win32':
    base_datas.append(('drivers/vbcable.zip', 'drivers'))

datas, binaries, hiddenimports = [], [], []

# 原生扩展与随包资源（FFmpeg / PortAudio / SRTP）
for package in ('aiortc', 'av', 'sounddevice', 'pylibsrtp', 'aioice', 'google_crc32c', 'pyee'):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

datas += collect_data_files('segno')

hiddenimports += [
    'engineio.async_drivers.threading',
    'engineio.async_drivers.aiohttp',
    'aiohttp',
    'numpy',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=base_datas + datas,  # 包含前端资源、样式和驱动
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

# One-dir, not one-file. Windows asks the shell for the icon before the app has
# painted anything, and a one-file build re-unpacks the whole payload into %TEMP%
# on every launch; one-dir starts straight from disk and lets the installer ship
# a real folder. The release zips this directory for the portable download.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZeroMic',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Qt / FFmpeg 动态库与 UPX 压缩不兼容
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,  # 注入架构变量
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    uac_admin=False,  # Windows 自动申请管理员权限
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ZeroMic',
)
