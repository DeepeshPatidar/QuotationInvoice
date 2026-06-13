# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Quote.py'],
    pathex=[],
    binaries=[],
    datas=[('quotation.db', '.'), ('DSUB9PIN.png', '.'), ('templates', 'templates')],
    hiddenimports=['PyQt6', 'jinja2', 'python_dateutil', 'PIL', 'charset_normalizer', 'dateutil'],
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
    a.binaries,
    a.datas,
    [],
    name='QuotationManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
