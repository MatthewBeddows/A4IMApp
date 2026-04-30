# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None
datas = []
binaries = []
hiddenimports = ['PyQt5.sip', 'git']

qt_collection = collect_all('PyQt5')
datas.extend(qt_collection[0])
binaries.extend(qt_collection[1])
hiddenimports.extend(qt_collection[2])
hiddenimports.extend(['git.cmd', 'git.refs', 'git.objects', 'git.repo', 'requests'])

# pyserial
serial_collection = collect_all('serial')
datas.extend(serial_collection[0])
binaries.extend(serial_collection[1])
hiddenimports.extend(serial_collection[2])
hiddenimports.extend(['serial', 'serial.tools', 'serial.tools.list_ports'])

# avrdude (Linux)
binaries.append(('tools/avrdude/linux/avrdude_Linux_64bit/bin/avrdude', '.'))
datas.append(('tools/avrdude/linux/avrdude_Linux_64bit/etc/avrdude.conf', '.'))

a = Analysis(['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='GitFileReader_linux',
    debug=False,
    strip=False,
    upx=True,
    console=True)
