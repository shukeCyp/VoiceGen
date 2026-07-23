"""Application version (single source of truth: /VERSION)."""

from __future__ import annotations

from pathlib import Path

from .paths import RESOURCE_ROOT, ROOT

APP_NAME = "多人配音工具"
APP_NAME_EN = "VoiceGen"


def _read_version_file() -> str:
    for base in (RESOURCE_ROOT, ROOT, Path(__file__).resolve().parents[1]):
        path = base / "VERSION"
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text.splitlines()[0].strip()
    return "0.0.0-dev"


__version__ = _read_version_file()


def version_info() -> dict:
    return {
        "name": APP_NAME,
        "name_en": APP_NAME_EN,
        "version": __version__,
        "display": f"{APP_NAME} v{__version__}",
        "window_title": f"{APP_NAME} v{__version__}",
    }
