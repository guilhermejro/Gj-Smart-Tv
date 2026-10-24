# -*- mode: python ; coding: utf-8 -*-
# Uso: pyinstaller --noconfirm --clean gj-smart-tv.spec
import os

binaries = []
if os.path.isfile("libs/libmpv-2.dll"):          # colocada por windows/fetch_libmpv.ps1
    binaries.append(("libs/libmpv-2.dll", "."))

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=[("app/resources", "app/resources")],
    hiddenimports=["mpv"],
    excludes=["tkinter", "unittest", "pydoc", "pytest",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick",
              "PySide6.Qt3DCore", "PySide6.QtCharts", "PySide6.QtMultimedia", "PySide6.QtPdf"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="gj-smart-tv",
          console=False, icon="app/resources/icon.ico", upx=False)   # UPX desligado: menos falsos positivos de antivírus
coll = COLLECT(exe, a.binaries, a.datas, name="gj-smart-tv", upx=False)
