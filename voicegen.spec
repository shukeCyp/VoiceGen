# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: single-file Windows EXE named 多人配音工具."""

from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
ROOT = Path(SPECPATH).resolve()

datas = [
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
    (str(ROOT / "voices" / "README.txt"), "voices"),
    (str(ROOT / "VERSION"), "."),
]

binaries = []
hiddenimports = [
    "backend",
    "backend.api",
    "backend.audio_utils",
    "backend.config_store",
    "backend.languages",
    "backend.mimo_chat",
    "backend.mimo_tts",
    "backend.paths",
    "backend.table_io",
    "backend.version",
    "backend.voices",
    "webview",
    "bottle",
    "proxy_tools",
    "clr",
]

# Pull platform-specific webview extras (EdgeChromium / pythonnet on Windows)
for pkg in ("webview",):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

try:
    hiddenimports += collect_submodules("webview")
except Exception:
    pass

# De-duplicate while preserving order
_seen = set()
_unique_hidden = []
for name in hiddenimports:
    if name not in _seen:
        _seen.add(name)
        _unique_hidden.append(name)
hiddenimports = _unique_hidden

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
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
    name="多人配音工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
