# build.py
import os
import subprocess

def build():
    # Create both spec files and run PyInstaller for each
    with open('linux_spec.spec', 'w') as f:
        f.write('''# -*- mode: python ; coding: utf-8 -*-
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
''')

    with open('windows_spec.spec', 'w') as f:
        f.write('''# -*- mode: python ; coding: utf-8 -*-
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
    name='GitFileReader.exe',
    debug=False,
    strip=False,
    upx=True,
    console=True)
''')

    # Build both versions
    subprocess.run(['pyinstaller', 'linux_spec.spec'])
    subprocess.run(['pyinstaller', 'windows_spec.spec'])

if __name__ == '__main__':
    build()