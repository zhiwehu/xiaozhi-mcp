# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# SPECPATH 是由 PyInstaller 注入的全局变量，指向当前 .spec 文件的目录
spec_root = os.path.abspath(SPECPATH)

a = Analysis(
    ['mcp_gui.py'],
    pathex=[spec_root],            # 使用 SPECPATH 作为搜索路径
    binaries=[],
    datas=[
        ('app_icon.ico', '.'),      # 包含图标
        ('.env', '.'),              # 环境变量文件
        ('mcp_pipe.py', '.'),       # 子进程脚本
        ('tools', 'tools'),         # 整个 tools 目录
    ],
    hiddenimports=[
        'dotenv',                   # 显式补充动态导入
        'mcp_pipe',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='mcp_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                 # 禁止命令行窗口
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mcp_gui',
)
