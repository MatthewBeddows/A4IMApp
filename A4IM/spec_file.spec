# spec_file.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all necessary files and data
datas = []
binaries = []
hiddenimports = [
    'PyQt5.sip',
    'bs4',  # BeautifulSoup4
    'soupsieve',  # Required by bs4
    'pygit2',  # Added for libgit2 support
    # Local modules
    'gitbuilding_widget',
    'mainmenu_widget',
    'systemview_widget',
    'download_thread',
    'gitbuilding_setup',
    'ArchitectSelector_widget'
]

# Add libgit2 libraries
binaries.extend([
    ('/usr/lib/x86_64-linux-gnu/libgit2.so.26', '.'),
])

# Additional data files
datas += [
    ('gitbuilding_widget.py', '.'),
    ('mainmenu_widget.py', '.'),
    ('systemview_widget.py', '.'),
    ('download_thread.py', '.'),
    ('gitbuilding_setup.py', '.'),
    ('ArchitectSelector_widget.py', '.')
]

# Collect PyQt5 data
qt_collection = collect_all('PyQt5')
datas.extend(qt_collection[0])
binaries.extend(qt_collection[1])
hiddenimports.extend(qt_collection[2])

# Add additional imports
hiddenimports.extend([
    'git.cmd',
    'git.refs',
    'git.objects',
    'git.repo',
    'requests',
    'subprocess',
    're',
    'math'
])

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GitFileReader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)