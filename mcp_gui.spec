# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

# 项目根路径
project_dir = os.path.abspath(os.path.dirname(__file__))

a = Analysis(
    ['mcp_gui.py'],
    pathex=[project_dir],                             # 指定脚本查找路径
    binaries=[],
    datas=[
        ('app_icon.ico', '.'),                        # 包含图标
        ('.env', '.'),                                # 包含环境变量文件
        ('mcp_pipe.py', '.'),                         # 包含子进程脚本
        ('tools', 'tools'),                           # 包含整个 tools 目录
    ],
    hiddenimports=[
        'dotenv',                                      # 显式补充 dotenv
        'mcp_pipe',                                     # 确保 mcp_pipe 被打包
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
    console=False,                                  # GUI 不弹命令行窗口
    icon='app_icon.ico',                            # 指定程序图标
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
