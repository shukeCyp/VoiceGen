"""Audio post-processing: speed change, silence gap, concat to MP3."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .app_log import get_logger
from .ffmpeg_bin import require_ffmpeg, require_ffprobe

log = get_logger("audio")


class AudioError(RuntimeError):
    pass


def _require_ffmpeg() -> str:
    try:
        path = require_ffmpeg()
        log.debug("using ffmpeg: %s", path)
        return path
    except FileNotFoundError as exc:
        raise AudioError(str(exc)) from exc


def _require_ffprobe() -> str:
    try:
        path = require_ffprobe()
        log.debug("using ffprobe: %s", path)
        return path
    except FileNotFoundError as exc:
        raise AudioError(str(exc)) from exc


def probe_duration(path: Path) -> float:
    ffprobe = _require_ffprobe()
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        log.error("ffprobe failed for %s: %s", path, (result.stderr or "")[-300:])
        raise AudioError(f"无法读取时长: {path.name}")
    data = json.loads(result.stdout or "{}")
    duration = float(data.get("format", {}).get("duration") or 0.0)
    log.debug("probe duration %s = %.3fs", path.name, duration)
    return duration


def _atempo_filters(speed: float) -> list[str]:
    """Build ffmpeg atempo chain for speed in (0.5, 2.0] per filter; chain for wider range."""
    speed = float(speed)
    if speed <= 0:
        raise ValueError("语速必须大于 0")
    filters: list[str] = []
    speed = max(0.25, min(4.0, speed))
    remaining = speed
    while remaining > 2.0 + 1e-9:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5 - 1e-9:
        filters.append("atempo=0.5")
        remaining /= 0.5
    if abs(remaining - 1.0) > 1e-6:
        filters.append(f"atempo={remaining:.6f}")
    return filters


def apply_speed(input_path: Path, output_path: Path, speed: float = 1.0) -> Path:
    ffmpeg = _require_ffmpeg()
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log.info(
        "apply_speed · in=%s · out=%s · speed=%s",
        input_path.name,
        output_path.name,
        speed,
    )

    if abs(float(speed) - 1.0) < 1e-6:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "24000",
            str(output_path),
        ]
    else:
        filters = _atempo_filters(speed)
        af = ",".join(filters)
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-filter:a",
            af,
            "-ac",
            "1",
            "-ar",
            "24000",
            str(output_path),
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not output_path.is_file():
        err = result.stderr[-400:] if result.stderr else "unknown"
        log.error("apply_speed failed: %s", err)
        raise AudioError(f"变速失败: {err}")
    return output_path


def make_silence(output_path: Path, duration_ms: int, sample_rate: int = 24000) -> Path:
    ffmpeg = _require_ffmpeg()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0, int(duration_ms)) / 1000.0
    if duration <= 0:
        raise ValueError("silence duration must be positive")
    log.debug("make_silence · %sms → %s", duration_ms, output_path.name)
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r={sample_rate}:cl=mono",
        "-t",
        f"{duration:.3f}",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not output_path.is_file():
        log.error("make_silence failed: %s", (result.stderr or "")[-300:])
        raise AudioError("生成静音失败")
    return output_path


def concat_to_mp3(segment_paths: list[Path], output_mp3: Path, gap_ms: int = 200) -> dict:
    """Concatenate wav segments with optional gap silence into a stereo MP3."""
    ffmpeg = _require_ffmpeg()
    if not segment_paths:
        raise AudioError("没有可合并的音频片段")

    output_mp3 = Path(output_mp3)
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    log.info(
        "concat_to_mp3 · segments=%s · gap_ms=%s · out=%s",
        len(segment_paths),
        gap_ms,
        output_mp3,
    )

    with tempfile.TemporaryDirectory(prefix="voicegen_concat_") as tmp:
        tmp_dir = Path(tmp)
        list_file = tmp_dir / "list.txt"
        pieces: list[Path] = []
        silence_path = None
        if gap_ms and gap_ms > 0:
            silence_path = tmp_dir / "gap.wav"
            make_silence(silence_path, gap_ms)

        for i, seg in enumerate(segment_paths):
            seg = Path(seg)
            if not seg.is_file():
                raise AudioError(f"片段不存在: {seg}")
            normalized = tmp_dir / f"seg_{i:04d}.wav"
            apply_speed(seg, normalized, 1.0)
            pieces.append(normalized)
            if silence_path is not None and i < len(segment_paths) - 1:
                pieces.append(silence_path)

        lines = []
        for p in pieces:
            escaped = str(p).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-ac",
            "2",
            "-ar",
            "48000",
            "-b:a",
            "192k",
            str(output_mp3),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not output_mp3.is_file():
            err = result.stderr[-500:] if result.stderr else "unknown"
            log.error("concat_to_mp3 failed: %s", err)
            raise AudioError(f"合并 MP3 失败: {err}")

    duration = probe_duration(output_mp3)
    log.info("concat_to_mp3 done · duration=%.2fs · path=%s", duration, output_mp3)
    return {
        "path": str(output_mp3.resolve()),
        "duration": duration,
        "segments": len(segment_paths),
    }
