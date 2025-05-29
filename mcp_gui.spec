# -*- mode: python ; coding: utf-8 -*

block_cipher = None

a = Analysis(
    ['mcp_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app_icon.ico', '.'),  # 包含图标文件
        ('.env', '.'),  # 包含根目录下的 .env 文件
        ('mcp_pipe.py', '.'), # 确保 mcp_pipe.py 包含在内
        ('tools/', 'tools/'), # 添加这一行来包含 tools 目录
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,  # GUI程序不弹出命令行窗口
    icon='app_icon.ico',  # 指定图标
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mcp_gui',
) 