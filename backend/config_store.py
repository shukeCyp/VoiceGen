"""Local app configuration (API key stored only on disk, never logged)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .paths import CONFIG_PATH

DEFAULT_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.5-tts-voiceclone"
DEFAULT_LLM_MODEL = "mimo-v2.5-pro"
DEFAULT_STYLE = "自然清晰的配音，语气符合角色与语境。"
DEFAULT_SPEED = 1.0
DEFAULT_GAP_MS = 200
DEFAULT_SOURCE_LANG = "zh-CN"
DEFAULT_TARGET_LANG = "en-US"
DEFAULT_TTS_WORKERS = 4
DEFAULT_TRANSLATE_WORKERS = 3
DEFAULT_TRANSLATE_BATCH_SIZE = 8


def _defaults() -> dict[str, Any]:
    env_key = os.environ.get("MIMO_API_KEY", "").strip()
    return {
        "api_key": env_key,
        "base_url": DEFAULT_BASE_URL,
        "model": DEFAULT_MODEL,
        "llm_model": DEFAULT_LLM_MODEL,
        "default_style": DEFAULT_STYLE,
        "default_speed": DEFAULT_SPEED,
        "gap_ms": DEFAULT_GAP_MS,
        "source_lang": DEFAULT_SOURCE_LANG,
        "target_lang": DEFAULT_TARGET_LANG,
        "tts_workers": DEFAULT_TTS_WORKERS,
        "translate_workers": DEFAULT_TRANSLATE_WORKERS,
        "translate_batch_size": DEFAULT_TRANSLATE_BATCH_SIZE,
        "window_width": 1280,
        "window_height": 860,
    }


def load_config() -> dict[str, Any]:
    cfg = _defaults()
    if CONFIG_PATH.is_file():
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if key in cfg:
                        cfg[key] = value
        except (OSError, json.JSONDecodeError):
            pass
    # Environment key wins when config file has no key.
    if not str(cfg.get("api_key") or "").strip():
        cfg["api_key"] = os.environ.get("MIMO_API_KEY", "").strip()
    return cfg


def save_config(updates: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    allowed = set(_defaults().keys())
    for key, value in updates.items():
        if key in allowed:
            cfg[key] = value
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Never write secrets into stdout; only persist to local file.
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return public_config(cfg)


def public_config(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return config safe for the UI (mask API key)."""
    data = dict(cfg or load_config())
    key = str(data.get("api_key") or "")
    data["api_key_set"] = bool(key.strip())
    data["api_key_masked"] = _mask_key(key) if key.strip() else ""
    data.pop("api_key", None)
    return data


def get_api_key(cfg: dict[str, Any] | None = None) -> str:
    data = cfg or load_config()
    return str(data.get("api_key") or "").strip()


def _mask_key(key: str) -> str:
    key = key.strip()
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"
