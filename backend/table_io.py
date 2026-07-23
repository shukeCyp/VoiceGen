"""Import / export dialogue tables (CSV / JSON)."""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any


TABLE_COLUMNS = (
    "id",
    "speaker",
    "voice",
    "text",
    "tts_text",
    "speed",
    "style",
    "enabled",
)


def new_row(
    *,
    speaker: str = "",
    voice: str = "",
    text: str = "",
    tts_text: str = "",
    speed: float = 1.0,
    style: str = "",
    enabled: bool = True,
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4())[:8],
        "speaker": speaker,
        "voice": voice,
        "text": text,
        "tts_text": tts_text or "",
        "speed": float(speed) if speed not in (None, "") else 1.0,
        "style": style or "",
        "enabled": bool(enabled),
        "status": "idle",
        "duration": None,
        "error": "",
        "segment_path": "",
    }


def row_speak_text(row: dict[str, Any]) -> str:
    """Text actually used for TTS: prefer tts_text, fallback to source text."""
    tts = str(row.get("tts_text") or "").strip()
    if tts:
        return tts
    return str(row.get("text") or "").strip()


def _parse_enabled(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return True
    s = str(value).strip().lower()
    if s in {"0", "false", "no", "n", "否", "关闭", "off"}:
        return False
    return True


def normalize_rows(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not rows:
        return result
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        text = str(
            raw.get("text")
            or raw.get("source_text")
            or raw.get("原文")
            or raw.get("文本")
            or raw.get("台词")
            or raw.get("Text")
            or ""
        )
        tts_text = str(
            raw.get("tts_text")
            or raw.get("translated")
            or raw.get("translation")
            or raw.get("配音文本")
            or raw.get("译文")
            or ""
        )
        row = new_row(
            speaker=str(raw.get("speaker") or raw.get("角色") or raw.get("Speaker") or ""),
            voice=str(raw.get("voice") or raw.get("音色") or raw.get("Voice") or ""),
            text=text,
            tts_text=tts_text,
            speed=raw.get("speed", raw.get("语速", raw.get("Speed", 1.0))),
            style=str(raw.get("style") or raw.get("风格") or ""),
            enabled=_parse_enabled(raw.get("enabled", raw.get("启用", True))),
        )
        if raw.get("id"):
            row["id"] = str(raw["id"])
        for key in ("status", "duration", "error", "segment_path"):
            if key in raw:
                row[key] = raw[key]
        result.append(row)
    return result


# CSV 中文表头（导出默认）；导入仍兼容英文表头
CSV_HEADERS_ZH = ["角色", "音色", "原文", "配音文本", "语速", "风格", "启用"]
CSV_FIELD_MAP = {
    "角色": "speaker",
    "音色": "voice",
    "原文": "text",
    "配音文本": "tts_text",
    "语速": "speed",
    "风格": "style",
    "启用": "enabled",
}


def export_csv(rows: list[dict[str, Any]], *, chinese_headers: bool = True) -> str:
    """Export rows as CSV. Default headers are Chinese for templates and sharing."""
    buf = io.StringIO()
    if chinese_headers:
        fieldnames = list(CSV_HEADERS_ZH)
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "角色": row.get("speaker", ""),
                    "音色": row.get("voice", ""),
                    "原文": row.get("text", ""),
                    "配音文本": row.get("tts_text", ""),
                    "语速": row.get("speed", 1.0),
                    "风格": row.get("style", ""),
                    "启用": row.get("enabled", True),
                }
            )
    else:
        fieldnames = ["speaker", "voice", "text", "tts_text", "speed", "style", "enabled"]
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "speaker": row.get("speaker", ""),
                    "voice": row.get("voice", ""),
                    "text": row.get("text", ""),
                    "tts_text": row.get("tts_text", ""),
                    "speed": row.get("speed", 1.0),
                    "style": row.get("style", ""),
                    "enabled": row.get("enabled", True),
                }
            )
    return buf.getvalue()


def import_csv(content: str) -> list[dict[str, Any]]:
    content = content.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    return normalize_rows(rows)


def export_json(rows: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "version": 2,
        "rows": [
            {
                "speaker": r.get("speaker", ""),
                "voice": r.get("voice", ""),
                "text": r.get("text", ""),
                "tts_text": r.get("tts_text", ""),
                "speed": r.get("speed", 1.0),
                "style": r.get("style", ""),
                "enabled": r.get("enabled", True),
            }
            for r in rows
        ],
    }
    if meta:
        payload.update({k: v for k, v in meta.items() if k not in payload})
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def import_json(content: str) -> dict[str, Any]:
    """Return {rows, source_lang?, target_lang?}."""
    data = json.loads(content)
    if isinstance(data, list):
        return {"rows": normalize_rows(data)}
    if isinstance(data, dict):
        return {
            "rows": normalize_rows(data.get("rows") or data.get("data") or []),
            "source_lang": data.get("source_lang") or data.get("source_language"),
            "target_lang": data.get("target_lang") or data.get("target_language"),
        }
    raise ValueError("JSON 格式不正确")
