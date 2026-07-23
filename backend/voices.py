"""Local voice library under project /voices folder."""

from __future__ import annotations

import shutil
from pathlib import Path

from .paths import VOICES_DIR

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac"}


def list_voices() -> list[dict]:
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    voices: list[dict] = []
    for path in sorted(VOICES_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTS:
            continue
        if path.name.startswith("."):
            continue
        voices.append(
            {
                "id": path.stem,
                "name": path.stem,
                "filename": path.name,
                "path": str(path.resolve()),
                "ext": path.suffix.lower(),
                "size": path.stat().st_size,
            }
        )
    return voices


def resolve_voice(voice_id: str) -> Path:
    voice_id = (voice_id or "").strip()
    if not voice_id:
        raise ValueError("未选择音色")
    # Exact stem match first.
    for path in VOICES_DIR.iterdir():
        if path.is_file() and path.stem == voice_id and path.suffix.lower() in AUDIO_EXTS:
            return path.resolve()
    # Filename match.
    candidate = VOICES_DIR / voice_id
    if candidate.is_file():
        return candidate.resolve()
    raise FileNotFoundError(f"音色不存在: {voice_id}（请放入 voices/ 文件夹）")


def import_voice(source: str, name: str | None = None) -> dict:
    src = Path(source).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"找不到文件: {src}")
    if src.suffix.lower() not in AUDIO_EXTS:
        raise ValueError(f"不支持的音频格式: {src.suffix}")
    stem = (name or src.stem).strip() or src.stem
    # Sanitize filename
    safe = "".join(c if c.isalnum() or c in "-_ .（）()【】" else "_" for c in stem).strip()
    if not safe:
        safe = "voice"
    dest = VOICES_DIR / f"{safe}{src.suffix.lower()}"
    n = 1
    while dest.exists() and dest.resolve() != src:
        dest = VOICES_DIR / f"{safe}_{n}{src.suffix.lower()}"
        n += 1
    if dest.resolve() != src:
        shutil.copy2(src, dest)
    return {
        "id": dest.stem,
        "name": dest.stem,
        "filename": dest.name,
        "path": str(dest.resolve()),
    }


def delete_voice(voice_id: str) -> bool:
    path = resolve_voice(voice_id)
    path.unlink(missing_ok=True)
    return True


def voices_dir() -> str:
    return str(VOICES_DIR.resolve())
