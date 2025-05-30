# XiaozhiMCP.spec

# Helper function to get paths correct during spec file processing
import os

# 获取 .spec 文件所在的目录
SPEC_DIR = os.path.dirname(os.path.abspath(__file__)) # 在 .spec 文件中，__file__ 通常是定义的，指向 .spec 文件本身

def get_resource_path(relative_path):
    return os.path.join(SPEC_DIR, relative_path)

block_cipher = None

a = Analysis(
    ['mcp_gui.py'], # Main script
    pathex=['.'], # Add current directory to Python's path for PyInstaller
    binaries=[],
    datas=[
        (get_resource_path('.env'), '.'), # Bundle a default/example .env.xiaozhi1
        # (get_resource_path('path/to/another/.env.example'), '.'), # if you have others
        (get_resource_path('tools'), 'tools'), # Bundle the entire 'tools' directory
        (get_resource_path('aggregate.py'), '.'), # Bundle aggregate.py
        (get_resource_path('mcp_pipe.py'), '.')    # Bundle mcp_pipe.py explicitly
    ],
    hiddenimports=[
        'asyncio',
        'websockets',
        'dotenv', # python-dotenv
        'requests',
        'psutil',
        'send2trash',
        # Add any other imports PyInstaller might miss, especially from the 'tools'
        # e.g., 'logging', 'smtplib', 'email.mime.text', etc.
        # Often, direct imports are found, but sometimes dynamic ones are missed.
        # Check your 'tools' files for all top-level imports.
        'uvloop', # If websockets or asyncio might use it implicitly
        'charset_normalizer.md__mypyc', # Common hidden import for requests
        'pydantic.v1', # If any part of your code or dependencies uses pydantic v1 features
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='XiaozhiMCP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # Set to False if UPX causes issues
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # True for debugging, False for release (use --windowed for GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico' # Replace with your icon file or remove
)