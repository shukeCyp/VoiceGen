"""Xiaomi MiMo chat completions client (translation / localization)."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Literal

from . import languages, mimo_tts
from .app_log import get_logger

log = get_logger("mimo_chat")

LLM_MODEL = "mimo-v2.5-pro"
TranslateMode = Literal["literal", "localize"]

# Smaller batches return faster and parallelize better than one huge request
BATCH_SIZE = 8


def _safe_api_error(exc: urllib.error.HTTPError) -> RuntimeError:
    message = f"MiMo API 返回 HTTP {exc.code}"
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        detail = (
            payload.get("error", {}).get("message")
            or payload.get("message")
            or payload.get("error")
        )
        if isinstance(detail, dict):
            detail = detail.get("message") or str(detail)
        if detail:
            message += f": {detail}"
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError):
        pass
    return RuntimeError(message)


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    messages: list[dict[str, str]],
    model: str = LLM_MODEL,
    temperature: float = 0.3,
    timeout: float = 120.0,
) -> str:
    base = mimo_tts.normalize_base_url(base_url)
    mimo_tts.validate_key_for_base_url(api_key, base)
    payload = {
        "model": model or LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    url = f"{base}/chat/completions"
    log.info(
        "POST chat · model=%s · temp=%s · messages=%s",
        model or LLM_MODEL,
        temperature,
        len(messages),
    )
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
            body = json.load(response)
        log.info(
            "POST chat ok · model=%s · %.2fs",
            model or LLM_MODEL,
            time.perf_counter() - t0,
        )
    except urllib.error.HTTPError as exc:
        log.warning("POST chat HTTP %s · model=%s", exc.code, model or LLM_MODEL)
        raise _safe_api_error(exc) from None
    except Exception as exc:
        log.error("POST chat network error · model=%s · %s", model or LLM_MODEL, exc)
        raise

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        log.error("chat response missing content: keys=%s", list(body.keys()) if isinstance(body, dict) else type(body))
        raise RuntimeError("MiMo 聊天响应格式无效") from exc

    if isinstance(content, list):
        # multimodal-style content blocks
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif isinstance(block, str):
                parts.append(block)
        content = "".join(parts)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("MiMo 返回空翻译结果")
    return content.strip()


def check_llm(base_url: str, api_key: str, model: str = LLM_MODEL) -> dict:
    base = mimo_tts.normalize_base_url(base_url)
    mimo_tts.validate_key_for_base_url(api_key, base)
    models = mimo_tts.fetch_models(base, api_key)
    model_ids = {item.get("id") for item in models.get("data", [])}
    mid = model or LLM_MODEL
    if mid not in model_ids:
        raise RuntimeError(f"当前账号未开放模型 {mid}")
    return {"ok": True, "base_url": base, "model": mid, "status": "ready"}


def _build_system_prompt(
    mode: TranslateMode,
    source_lang: str,
    target_lang: str,
) -> str:
    src = languages.language_label(source_lang)
    tgt = languages.language_label(target_lang)
    target = languages.get_language(target_lang)
    target_native = target.get("native") or target_lang

    if mode == "localize":
        return f"""你是资深本地化（Localization / L10n）专家与配音编剧。
任务：把台词从「{src}」本土化到「{tgt}」，供口播/配音使用。

本土化要求（不是机械直译）：
1. 意思完整，但对目标语言听众自然、口语、可听。
2. 替换文化梗、习语、货币、称谓、网络用语、幽默等，用目标市场观众熟悉的表达。
3. 保持角色语气、情绪与人设；不要写成说明书。
4. 适合配音：句子长度适中，避免生硬书面腔。
5. 专有名词（角色名、品牌、地名）在无明确本地译名时保留原文或常用译法。
6. 输出必须是地道的 {target_native}。

严格输出 JSON 数组，不要 Markdown，不要解释：
[
  {{"id": "原id", "text": "本土化后的台词"}}
]
数组顺序与输入一致，条数必须相同。"""
    # literal — keep prompt short for lower latency
    return f"""你是专业配音翻译。把台词从「{src}」译为「{tgt}」（{target_native}）。
要求：忠实、通顺、适合朗读；不增删情节；专有名词前后一致。
只输出 JSON 数组，无 Markdown、无解释，条数与顺序与输入一致：
[{{"id":"…","text":"译文"}}]"""


def _extract_json_array(raw: str) -> list[Any]:
    text = raw.strip()
    # strip ```json fences if any
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data["items"]
        if isinstance(data, dict) and isinstance(data.get("translations"), list):
            return data["translations"]
    except json.JSONDecodeError:
        pass
    # try find first [...] block
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, list):
            return data
    raise RuntimeError("无法解析模型返回的翻译 JSON")


def translate_batch(
    items: list[dict[str, str]],
    *,
    mode: TranslateMode,
    source_lang: str,
    target_lang: str,
    base_url: str,
    api_key: str,
    model: str = LLM_MODEL,
    temperature: float | None = None,
) -> list[dict[str, str]]:
    """
    items: [{id, text, speaker?}, ...]
    returns: [{id, text}, ...] translated
    """
    if not items:
        return []
    if source_lang == target_lang:
        return [{"id": str(it["id"]), "text": str(it.get("text") or "")} for it in items]

    system = _build_system_prompt(mode, source_lang, target_lang)
    user_payload = [
        {
            "id": str(it.get("id") or i),
            "speaker": str(it.get("speaker") or ""),
            "text": str(it.get("text") or ""),
        }
        for i, it in enumerate(items)
    ]
    # compact JSON (no indent) reduces tokens / latency
    user = (
        f"{source_lang}->{target_lang} mode={mode}\n"
        f"翻译 text 字段：\n{json.dumps(user_payload, ensure_ascii=False, separators=(',', ':'))}"
    )

    temp = 0.1 if mode == "literal" else 0.55
    if temperature is not None:
        temp = temperature

    log.info(
        "translate_batch · mode=%s · %s→%s · items=%s · model=%s",
        mode,
        source_lang,
        target_lang,
        len(items),
        model or LLM_MODEL,
    )
    raw = chat_completion(
        base_url=base_url,
        api_key=api_key,
        model=model or LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temp,
        timeout=90.0 if mode == "literal" else 120.0,
    )
    try:
        parsed = _extract_json_array(raw)
    except Exception:
        log.error("translate_batch parse fail · raw_head=%s", (raw or "")[:240])
        raise

    by_id: dict[str, str] = {}
    ordered: list[str] = []
    for entry in parsed:
        if isinstance(entry, str):
            ordered.append(entry)
            continue
        if not isinstance(entry, dict):
            continue
        eid = str(entry.get("id") or entry.get("row_id") or "")
        etext = entry.get("text") or entry.get("translation") or entry.get("translated") or ""
        if eid:
            by_id[eid] = str(etext)
        else:
            ordered.append(str(etext))

    results: list[dict[str, str]] = []
    for i, it in enumerate(items):
        rid = str(it.get("id") or i)
        if rid in by_id:
            text = by_id[rid]
        elif i < len(ordered):
            text = ordered[i]
        else:
            raise RuntimeError(f"模型未返回第 {i + 1} 条翻译（id={rid}）")
        results.append({"id": rid, "text": text.strip()})
    return results


def translate_rows(
    rows: list[dict[str, Any]],
    *,
    mode: TranslateMode = "literal",
    source_lang: str,
    target_lang: str,
    base_url: str,
    api_key: str,
    model: str = LLM_MODEL,
    only_enabled: bool = True,
) -> list[dict[str, str]]:
    """Translate enabled rows that have source text. Returns list of {id, tts_text}."""
    work: list[dict[str, str]] = []
    for row in rows:
        if only_enabled and not row.get("enabled", True):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        work.append(
            {
                "id": str(row.get("id") or ""),
                "speaker": str(row.get("speaker") or ""),
                "text": text,
            }
        )
    if not work:
        return []

    all_results: list[dict[str, str]] = []
    for start in range(0, len(work), BATCH_SIZE):
        chunk = work[start : start + BATCH_SIZE]
        translated = translate_batch(
            chunk,
            mode=mode,
            source_lang=source_lang,
            target_lang=target_lang,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        for item in translated:
            all_results.append({"id": item["id"], "tts_text": item["text"]})
    return all_results
