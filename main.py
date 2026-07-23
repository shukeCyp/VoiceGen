#!/usr/bin/env python3
"""VoiceGen — multi-speaker dubbing desktop app (pywebview + Vue)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def _bootstrap_path() -> Path:
    if _is_frozen():
        meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        if str(meipass) not in sys.path:
            sys.path.insert(0, str(meipass))
        return Path(sys.executable).resolve().parent
    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


ROOT = _bootstrap_path()

from backend.api import Api, set_window
from backend.config_store import load_config
from backend.paths import FRONTEND_DIST, FRONTEND_INDEX, RESOURCE_ROOT, VOICES_DIR
from backend.version import version_info


def resolve_ui_url(dev_url: str | None) -> str:
    if dev_url:
        return dev_url
    if FRONTEND_INDEX.is_file():
        return FRONTEND_INDEX.as_uri()
    fallback = RESOURCE_ROOT / "backend" / "fallback.html"
    if fallback.is_file():
        return fallback.as_uri()
    raise SystemExit(
        "前端资源缺失。开发模式请先构建前端:\n"
        "  cd frontend && npm install && npm run build\n"
        f"期望路径: {FRONTEND_DIST}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="多人配音工具")
    parser.add_argument(
        "--dev",
        nargs="?",
        const="http://127.0.0.1:5173",
        default=None,
        help="开发模式：加载 Vite 地址（默认 http://127.0.0.1:5173）",
    )
    parser.add_argument("--debug", action="store_true", help="打开 DevTools")
    args = parser.parse_args()

    try:
        import webview
    except ImportError:
        print("请先安装依赖: pip install -r requirements.txt", file=sys.stderr)
        return 1

    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    api = Api()
    url = resolve_ui_url(args.dev)

    ver = version_info()
    # Match default lilac theme — dark #0f1419 caused a black flash before CSS/Vue mount
    window_bg = str(cfg.get("window_bg") or "#F4F2FB").strip() or "#F4F2FB"
    window = webview.create_window(
        title=ver["window_title"],
        url=url,
        js_api=api,
        width=int(cfg.get("window_width") or 1280),
        height=int(cfg.get("window_height") or 860),
        min_size=(960, 640),
        background_color=window_bg,
    )
    set_window(window)

    webview.start(debug=bool(args.debug or args.dev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
