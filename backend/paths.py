"""Project path helpers (dev + PyInstaller frozen)."""

from __future__ import annotations

import sys
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def resource_root() -> Path:
    """Read-only bundle root (frontend dist lives here when frozen)."""
    if _is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1]


def app_root() -> Path:
    """User-writable app root (next to .exe when frozen, project root in dev)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


RESOURCE_ROOT = resource_root()
ROOT = app_root()
BACKEND_DIR = RESOURCE_ROOT / "backend"
VOICES_DIR = ROOT / "voices"
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
LOG_DIR = DATA_DIR / "log"
CONFIG_PATH = DATA_DIR / "config.json"
SEGMENTS_DIR = OUTPUT_DIR / "segments"
FRONTEND_DIST = RESOURCE_ROOT / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"

# Only create writable directories (never write into _MEIPASS)
for path in (VOICES_DIR, OUTPUT_DIR, DATA_DIR, LOG_DIR, SEGMENTS_DIR):
    path.mkdir(parents=True, exist_ok=True)
