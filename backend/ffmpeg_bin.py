"""Locate ffmpeg / ffprobe: bundled first, then PATH."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from .paths import RESOURCE_ROOT, ROOT

_CACHE: dict[str, str | None] = {}


def _candidates(name: str) -> list[Path]:
    """Return candidate executable paths (Windows uses .exe)."""
    exe = f"{name}.exe" if sys.platform == "win32" else name
    roots = [
        RESOURCE_ROOT / "vendor" / "ffmpeg" / "windows",
        RESOURCE_ROOT / "vendor" / "ffmpeg" / "bin",
        RESOURCE_ROOT / "bin",
        ROOT / "vendor" / "ffmpeg" / "windows",
        ROOT / "vendor" / "ffmpeg" / "bin",
        ROOT / "bin",
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        roots.insert(0, meipass / "vendor" / "ffmpeg" / "windows")
        roots.insert(1, meipass / "bin")
    out: list[Path] = []
    for root in roots:
        out.append(root / exe)
        out.append(root / name)
    return out


def resolve_binary(name: str) -> str | None:
    """Find absolute path to ffmpeg or ffprobe, or None."""
    key = name.lower()
    if key in _CACHE:
        return _CACHE[key]

    for path in _candidates(name):
        try:
            if path.is_file():
                resolved = str(path.resolve())
                _CACHE[key] = resolved
                return resolved
        except OSError:
            continue

    which = shutil.which(name)
    if which:
        _CACHE[key] = which
        return which
    if sys.platform == "win32":
        which = shutil.which(f"{name}.exe")
        if which:
            _CACHE[key] = which
            return which

    _CACHE[key] = None
    return None


def require_ffmpeg() -> str:
    path = resolve_binary("ffmpeg")
    if not path:
        raise FileNotFoundError(
            "未找到 ffmpeg。请安装并加入 PATH，或使用已内置 ffmpeg 的安装包。"
        )
    return path


def require_ffprobe() -> str:
    path = resolve_binary("ffprobe")
    if not path:
        raise FileNotFoundError(
            "未找到 ffprobe。请安装并加入 PATH，或使用已内置 ffprobe 的安装包。"
        )
    return path


def ffmpeg_status() -> dict:
    """Diagnostic info for logs / settings."""
    ff = resolve_binary("ffmpeg")
    fp = resolve_binary("ffprobe")
    return {
        "ffmpeg": ff,
        "ffprobe": fp,
        "bundled": bool(
            ff
            and (
                "vendor" in ff.replace("\\", "/")
                or (getattr(sys, "frozen", False) and str(RESOURCE_ROOT) in ff)
            )
        ),
        "path_env": os.environ.get("PATH", "")[:200],
    }
