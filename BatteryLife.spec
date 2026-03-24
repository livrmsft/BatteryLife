# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for BatteryLife

from PyInstaller.utils.hooks import collect_all

openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all("openpyxl")

a = Analysis(
    ["bltest.py"],
    pathex=[],
    binaries=openpyxl_binaries,
    datas=openpyxl_datas,
    hiddenimports=openpyxl_hiddenimports + [
        "openpyxl",
        "openpyxl.cell._writer",
        "openpyxl.styles.stylesheet",
        "openpyxl.workbook.child",
        "openpyxl.reader.excel",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BatteryLife",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # needs Terminal output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,   # matches current machine arch (arm64 / x86_64)
    codesign_identity=None,
    entitlements_file=None,
)
