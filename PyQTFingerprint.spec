# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.pyw'],
    pathex=[],
    binaries=[
    (r"C:\Program Files\NFIQ 2\bin\nfiq2.exe", r".\NFIQ 2\bin\.")],
    datas=[('assets\\icon.png', '.\\assets'),('assets\\splash.png', '.\\assets'),(r"C:\Program Files\NFIQ 2",'.\\NFIQ 2')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Clarkson AVHBAC Fingerprint Sensor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.png'],
    version='version.txt'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Fingerprint_application_win',
)