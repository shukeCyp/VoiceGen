#!/usr/bin/env python3
"""Download Windows ffmpeg essentials (ffmpeg.exe + ffprobe.exe) into vendor/."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

# Gyan.dev release essentials build (widely used, includes ffprobe)
FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "vendor" / "ffmpeg" / "windows"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_ff = OUT_DIR / "ffmpeg.exe"
    target_fp = OUT_DIR / "ffprobe.exe"
    if target_ff.is_file() and target_fp.is_file():
        print(f"already present: {target_ff}")
        print(f"already present: {target_fp}")
        return 0

    print(f"downloading {FFMPEG_ZIP_URL} …")
    with urlopen(FFMPEG_ZIP_URL, timeout=300) as resp:
        data = resp.read()
    print(f"downloaded {len(data) / (1024 * 1024):.1f} MB, extracting…")

    found = {"ffmpeg.exe": None, "ffprobe.exe": None}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            base = Path(name).name.lower()
            if base in found and name.lower().endswith(base):
                # prefer bin/ffmpeg.exe over other copies
                if found[base] is None or "/bin/" in name.replace("\\", "/").lower():
                    found[base] = name
        for base, member in found.items():
            if not member:
                print(f"error: {base} not found in zip", file=sys.stderr)
                return 1
            dest = OUT_DIR / base
            print(f"  extract {member} -> {dest}")
            with zf.open(member) as src, open(dest, "wb") as out:
                out.write(src.read())

    if not target_ff.is_file() or not target_fp.is_file():
        print("error: extraction incomplete", file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
