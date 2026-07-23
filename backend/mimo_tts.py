"""Xiaomi MiMo VoiceClone TTS client."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .app_log import get_logger

log = get_logger("mimo_tts")

MODEL_ID = "mimo-v2.5-tts-voiceclone"
OFFICIAL_BASE_URLS = {
    "https://api.xiaomimimo.com/v1": "pay_as_you_go",
    "https://token-plan-cn.xiaomimimo.com/v1": "token_plan",
    "https://token-plan-sgp.xiaomimimo.com/v1": "token_plan",
    "https://token-plan-ams.xiaomimimo.com/v1": "token_plan",
}
MAX_ENCODED_REFERENCE_BYTES = 10 * 1024 * 1024
DEFAULT_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"


def normalize_base_url(value: str) -> str:
    base_url = (value or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or base_url not in OFFICIAL_BASE_URLS:
        raise ValueError("请使用官方 MiMo Base URL（HTTPS）")
    return base_url


def validate_key_for_base_url(api_key: str, base_url: str) -> None:
    if not api_key:
        raise ValueError("请先配置 MIMO API Key")
    family = OFFICIAL_BASE_URLS[base_url]
    if api_key.startswith("tp-") and family != "token_plan":
        raise ValueError("Token Plan 密钥（tp-）需使用 token-plan 节点")
    if api_key.startswith("sk-") and family != "pay_as_you_go":
        raise ValueError("按量密钥（sk-）需使用 https://api.xiaomimimo.com/v1")
    if not api_key.startswith(("tp-", "sk-")):
        raise ValueError("API Key 需以 tp- 或 sk- 开头")


_voice_b64_cache: dict[tuple[str, float, int], str] = {}
_voice_cache_lock = threading.Lock()


def encode_reference_audio(path: Path) -> str:
    """Encode reference audio; cache by path+mtime+size for concurrent reuse."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"参考音色不存在: {path}")
    st = path.stat()
    key = (str(path.resolve()), float(st.st_mtime), int(st.st_size))
    with _voice_cache_lock:
        hit = _voice_b64_cache.get(key)
        if hit is not None:
            return hit

    raw = path.read_bytes()
    encoded = base64.b64encode(raw)
    if len(encoded) > MAX_ENCODED_REFERENCE_BYTES:
        raise ValueError("参考音频 Base64 超过 MiMo 10MB 限制")
    suffix = path.suffix.lower().lstrip(".") or "wav"
    mime = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
    }.get(suffix, "audio/wav")
    voice_data = f"data:{mime};base64," + encoded.decode("ascii")
    with _voice_cache_lock:
        # bound cache size
        if len(_voice_b64_cache) > 24:
            _voice_b64_cache.clear()
        _voice_b64_cache[key] = voice_data
    return voice_data


def build_payload(text: str, style: str, voice_data: str, model: str = MODEL_ID) -> dict:
    narration = (text or "").strip()
    if not narration:
        raise ValueError("配音文本不能为空")
    style_text = (style or "自然清晰的配音。").strip()
    return {
        "model": model or MODEL_ID,
        "messages": [
            {"role": "user", "content": style_text},
            {"role": "assistant", "content": narration},
        ],
        "audio": {"format": "wav", "voice": voice_data},
    }


def validate_models_response(payload: dict, model: str = MODEL_ID) -> None:
    model_ids = {item.get("id") for item in payload.get("data", [])}
    if model not in model_ids:
        raise RuntimeError(f"当前账号未开放模型 {model}")


def _safe_api_error(exc: urllib.error.HTTPError) -> RuntimeError:
    message = f"MiMo API 返回 HTTP {exc.code}"
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        detail = payload.get("error", {}).get("message") or payload.get("message")
        if detail:
            message += f": {detail}"
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        pass
    return RuntimeError(message)


def fetch_models(base_url: str, api_key: str, timeout: float = 20.0) -> dict:
    url = f"{base_url}/models"
    log.info("GET %s", url)
    request = urllib.request.Request(
        url,
        headers={"api-key": api_key, "Accept": "application/json"},
    )
    try:
        t0 = time.perf_counter()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
        log.info("GET /models ok · %.2fs", time.perf_counter() - t0)
        return data
    except urllib.error.HTTPError as exc:
        log.warning("GET /models HTTP %s", exc.code)
        raise _safe_api_error(exc) from None
    except Exception as exc:
        log.error("GET /models network error: %s", exc)
        raise


def request_audio(
    base_url: str, api_key: str, payload: dict, timeout: float = 180.0
) -> bytes:
    url = f"{base_url}/chat/completions"
    model = payload.get("model")
    text_len = 0
    try:
        for m in payload.get("messages") or []:
            if m.get("role") == "assistant":
                text_len = len(str(m.get("content") or ""))
    except Exception:
        pass
    log.info("POST TTS %s · model=%s · text_len=%s", url, model, text_len)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        t0 = time.perf_counter()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
        log.info(
            "POST TTS ok · model=%s · %.2fs · resp_bytes=%s",
            model,
            time.perf_counter() - t0,
            len(body),
        )
        return body
    except urllib.error.HTTPError as exc:
        log.warning("POST TTS HTTP %s · model=%s", exc.code, model)
        raise _safe_api_error(exc) from None
    except Exception as exc:
        log.error("POST TTS network error · model=%s · %s", model, exc)
        raise


def write_audio_response(response_bytes: bytes, output: Path) -> Path:
    try:
        payload = json.loads(response_bytes)
        encoded = payload["choices"][0]["message"]["audio"]["data"]
        audio = base64.b64decode(encoded, validate=True)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise RuntimeError("MiMo 响应中没有有效的 Base64 音频") from exc
    if len(audio) <= 44:
        raise RuntimeError("MiMo 返回了空音频")

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False
        ) as temporary:
            temporary.write(audio)
            temporary_name = temporary.name
        os.replace(temporary_name, output)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return output


def check_service(base_url: str, api_key: str, model: str = MODEL_ID) -> dict:
    base = normalize_base_url(base_url)
    validate_key_for_base_url(api_key, base)
    models = fetch_models(base, api_key)
    validate_models_response(models, model or MODEL_ID)
    return {
        "ok": True,
        "base_url": base,
        "model": model or MODEL_ID,
        "status": "ready",
    }


def synthesize(
    *,
    text: str,
    reference_audio: Path,
    output: Path,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    model: str = MODEL_ID,
    style: str = "自然清晰的配音。",
) -> Path:
    base = normalize_base_url(base_url)
    validate_key_for_base_url(api_key, base)
    ref = Path(reference_audio)
    log.info(
        "synthesize · model=%s · ref=%s · text_len=%s · out=%s",
        model or MODEL_ID,
        ref.name,
        len((text or "").strip()),
        Path(output).name,
    )
    voice_data = encode_reference_audio(ref)
    payload = build_payload(text, style, voice_data, model=model or MODEL_ID)
    out = write_audio_response(request_audio(base, api_key, payload), Path(output))
    log.info("synthesize done · out=%s · size=%s", out.name, out.stat().st_size)
    return out
