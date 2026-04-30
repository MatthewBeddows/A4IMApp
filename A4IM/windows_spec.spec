# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

binaries = []
# Add the CFFI DLL explicitly
if sys.platform.startswith('win'):
    import _cffi_backend
    binaries.append((_cffi_backend.__file__, '.'))

# pyserial
serial_collection = collect_all('serial')
_serial_datas, _serial_binaries, _serial_hiddenimports = serial_collection
binaries.extend(_serial_binaries)

# avrdude (Windows)
binaries.append(('tools/avrdude/windows/avrdude.exe', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=[
        ('gitbuilding_widget.py', '.'),
        ('mainmenu_widget.py', '.'),
        ('systemview_widget.py', '.'),
        ('download_thread.py', '.'),
        ('gitbuilding_setup.py', '.'),
        ('ArchitectSelector_widget.py', '.'),
        ('tools/avrdude/windows/avrdude.conf', '.'),
        *_serial_datas,
    ],
    hiddenimports=[
        'PyQt5.sip',
        'pygit2',
        'bs4',
        'soupsieve',
        'cffi',
        '_cffi_backend',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'gitbuilding_widget',
        'mainmenu_widget',
        'systemview_widget',
        'download_thread',
        'gitbuilding_setup',
        'ArchitectSelector_widget',
        *_serial_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    target_platform='win64'
)