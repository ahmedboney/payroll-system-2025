# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec لنظام المرتبات - نسخة exe واحدة بدون CMD

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('seed_demo.py', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask.json',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'reportlab',
        'arabic_reshaper',
        'bidi',
        'sqlite3',
        'webbrowser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['unittest', 'pydoc', 'tkinter', 'test'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='نظام_المرتبات',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
