"""Supported languages for translation / localization / TTS."""

from __future__ import annotations

from typing import Any

# code -> display name (native + Chinese label)
LANGUAGES: list[dict[str, str]] = [
    {"code": "zh-CN", "name": "简体中文", "native": "简体中文", "tts_hint": "Natural Mandarin Chinese"},
    {"code": "zh-TW", "name": "繁體中文", "native": "繁體中文", "tts_hint": "Natural Traditional Chinese"},
    {"code": "en-US", "name": "英语（美式）", "native": "English (US)", "tts_hint": "Natural American English"},
    {"code": "en-GB", "name": "英语（英式）", "native": "English (UK)", "tts_hint": "Natural British English"},
    {"code": "ja-JP", "name": "日语", "native": "日本語", "tts_hint": "Natural Japanese"},
    {"code": "ko-KR", "name": "韩语", "native": "한국어", "tts_hint": "Natural Korean"},
    {"code": "es-ES", "name": "西班牙语", "native": "Español", "tts_hint": "Natural Spanish"},
    {"code": "fr-FR", "name": "法语", "native": "Français", "tts_hint": "Natural French"},
    {"code": "de-DE", "name": "德语", "native": "Deutsch", "tts_hint": "Natural German"},
    {"code": "pt-BR", "name": "葡萄牙语（巴西）", "native": "Português (BR)", "tts_hint": "Natural Brazilian Portuguese"},
    {"code": "ru-RU", "name": "俄语", "native": "Русский", "tts_hint": "Natural Russian"},
    {"code": "it-IT", "name": "意大利语", "native": "Italiano", "tts_hint": "Natural Italian"},
    {"code": "th-TH", "name": "泰语", "native": "ไทย", "tts_hint": "Natural Thai"},
    {"code": "vi-VN", "name": "越南语", "native": "Tiếng Việt", "tts_hint": "Natural Vietnamese"},
    {"code": "id-ID", "name": "印尼语", "native": "Bahasa Indonesia", "tts_hint": "Natural Indonesian"},
    {"code": "ar-SA", "name": "阿拉伯语", "native": "العربية", "tts_hint": "Natural Arabic"},
    {"code": "hi-IN", "name": "印地语", "native": "हिन्दी", "tts_hint": "Natural Hindi"},
    {"code": "ms-MY", "name": "马来语", "native": "Bahasa Melayu", "tts_hint": "Natural Malay"},
    {"code": "tr-TR", "name": "土耳其语", "native": "Türkçe", "tts_hint": "Natural Turkish"},
    {"code": "pl-PL", "name": "波兰语", "native": "Polski", "tts_hint": "Natural Polish"},
    {"code": "nl-NL", "name": "荷兰语", "native": "Nederlands", "tts_hint": "Natural Dutch"},
]

_BY_CODE = {item["code"]: item for item in LANGUAGES}


def list_languages() -> list[dict[str, str]]:
    return list(LANGUAGES)


def get_language(code: str) -> dict[str, str]:
    code = (code or "").strip()
    if code in _BY_CODE:
        return _BY_CODE[code]
    # allow bare language tags like "en" / "zh"
    for item in LANGUAGES:
        if item["code"].split("-")[0].lower() == code.lower():
            return item
    return {
        "code": code or "unknown",
        "name": code or "未知",
        "native": code or "unknown",
        "tts_hint": "Natural speech",
    }


def language_label(code: str) -> str:
    item = get_language(code)
    return f"{item['name']} ({item['native']})" if item.get("native") != item.get("name") else item["name"]


def resolve_tts_style(base_style: str, target_lang: str) -> str:
    """Append language guidance so VoiceClone stays on-language."""
    lang = get_language(target_lang)
    hint = lang.get("tts_hint") or "Natural speech"
    base = (base_style or "").strip()
    lang_line = f"Speak in {lang.get('native') or lang['code']}. {hint}."
    if not base:
        return lang_line
    if lang.get("native") and lang["native"] in base:
        return base
    return f"{base} {lang_line}"


def public_language_payload() -> dict[str, Any]:
    return {"languages": list_languages()}
