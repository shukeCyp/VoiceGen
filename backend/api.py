"""pywebview JS bridge — all methods are callable from window.pywebview.api."""

from __future__ import annotations

import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from . import audio_utils, config_store, languages, mimo_chat, mimo_tts, table_io, version, voices
from .paths import DATA_DIR, OUTPUT_DIR, SEGMENTS_DIR, VOICES_DIR

# Progress callbacks into the UI thread via evaluate_js
_window = None
_cancel_flag = threading.Event()
_job_lock = threading.Lock()
_job_running = False
_translate_lock = threading.Lock()
_translate_running = False
_emit_lock = threading.Lock()


def set_window(window) -> None:
    global _window
    _window = window


def _emit(event: str, payload: dict[str, Any]) -> None:
    if _window is None:
        return
    try:
        import base64

        raw = json.dumps({"event": event, "payload": payload}, ensure_ascii=False)
        b64 = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        # atob() alone is Latin-1; must re-decode as UTF-8 for Chinese text
        with _emit_lock:
            _window.evaluate_js(
                "(() => {"
                "const b64ToUtf8 = (b64) => new TextDecoder('utf-8').decode("
                "Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));"
                f"const raw = JSON.parse(b64ToUtf8('{b64}'));"
                "window.__voicegen_event && window.__voicegen_event(raw.event, raw.payload);"
                "})()"
            )
    except Exception:
        pass


def _ok(data: Any = None, **extra) -> dict[str, Any]:
    result = {"ok": True, "data": data}
    result.update(extra)
    return result


def _err(message: str, **extra) -> dict[str, Any]:
    result = {"ok": False, "error": str(message)}
    result.update(extra)
    return result


class Api:
    """Exposed to the Vue frontend via pywebview."""

    # ── version ─────────────────────────────────────────────
    def get_version(self) -> dict:
        try:
            return _ok(version.version_info())
        except Exception as exc:
            return _err(str(exc))

    # ── config ──────────────────────────────────────────────
    def get_config(self) -> dict:
        return _ok(config_store.public_config())

    def save_config(self, updates: dict) -> dict:
        try:
            # Allow setting full api_key from UI
            pub = config_store.save_config(updates or {})
            return _ok(pub)
        except Exception as exc:
            return _err(str(exc))

    def check_api(self) -> dict:
        try:
            cfg = config_store.load_config()
            key = config_store.get_api_key(cfg)
            base_url = cfg.get("base_url") or mimo_tts.DEFAULT_BASE_URL
            tts_model = cfg.get("model") or mimo_tts.MODEL_ID
            llm_model = cfg.get("llm_model") or mimo_chat.LLM_MODEL
            tts = mimo_tts.check_service(base_url, key, tts_model)
            llm = mimo_chat.check_llm(base_url, key, llm_model)
            return _ok(
                {
                    "ok": True,
                    "base_url": tts["base_url"],
                    "tts": tts,
                    "llm": llm,
                    "status": "ready",
                }
            )
        except Exception as exc:
            return _err(str(exc))

    def list_languages(self) -> dict:
        try:
            return _ok(languages.public_language_payload())
        except Exception as exc:
            return _err(str(exc))

    # ── voices ──────────────────────────────────────────────
    def list_voices(self) -> dict:
        try:
            return _ok(
                {
                    "voices": voices.list_voices(),
                    "voices_dir": voices.voices_dir(),
                }
            )
        except Exception as exc:
            return _err(str(exc))

    def import_voice(self, path: str, name: str = "") -> dict:
        try:
            item = voices.import_voice(path, name or None)
            return _ok(item)
        except Exception as exc:
            return _err(str(exc))

    def delete_voice(self, voice_id: str) -> dict:
        try:
            voices.delete_voice(voice_id)
            return _ok(True)
        except Exception as exc:
            return _err(str(exc))

    def open_voices_folder(self) -> dict:
        try:
            import subprocess
            import sys

            path = str(VOICES_DIR.resolve())
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return _ok(path)
        except Exception as exc:
            return _err(str(exc))

    def pick_voice_file(self) -> dict:
        """Native file dialog to import a voice sample."""
        try:
            import webview

            result = _window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=(
                    "Audio Files (*.wav;*.mp3;*.m4a;*.flac;*.ogg;*.opus;*.aac)",
                    "All Files (*.*)",
                ),
            ) if _window else None
            if not result:
                return _ok(None)
            path = result[0] if isinstance(result, (list, tuple)) else result
            item = voices.import_voice(str(path))
            return _ok(item)
        except Exception as exc:
            return _err(str(exc))

    # ── table import / export ───────────────────────────────
    def import_table_text(self, content: str, fmt: str = "csv") -> dict:
        try:
            fmt = (fmt or "csv").lower()
            if fmt == "json":
                parsed = table_io.import_json(content)
                return _ok(parsed)
            rows = table_io.import_csv(content)
            return _ok({"rows": rows})
        except Exception as exc:
            return _err(str(exc))

    def export_table_text(self, rows: list, fmt: str = "csv", meta: dict | None = None) -> dict:
        try:
            fmt = (fmt or "csv").lower()
            if fmt == "json":
                text = table_io.export_json(rows or [], meta=meta)
            else:
                text = table_io.export_csv(rows or [])
            return _ok({"content": text, "fmt": fmt})
        except Exception as exc:
            return _err(str(exc))

    def pick_import_file(self) -> dict:
        try:
            import webview

            result = _window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=(
                    "Table Files (*.csv;*.json;*.txt)",
                    "All Files (*.*)",
                ),
            ) if _window else None
            if not result:
                return _ok(None)
            path = Path(result[0] if isinstance(result, (list, tuple)) else result)
            content = path.read_text(encoding="utf-8")
            fmt = "json" if path.suffix.lower() == ".json" else "csv"
            if fmt == "json":
                parsed = table_io.import_json(content)
                return _ok(
                    {
                        "rows": parsed.get("rows") or [],
                        "source_lang": parsed.get("source_lang"),
                        "target_lang": parsed.get("target_lang"),
                        "path": str(path),
                        "fmt": fmt,
                    }
                )
            rows = table_io.import_csv(content)
            return _ok({"rows": rows, "path": str(path), "fmt": fmt})
        except Exception as exc:
            return _err(str(exc))

    def save_export_file(self, rows: list, fmt: str = "csv", meta: dict | None = None) -> dict:
        try:
            import webview

            fmt = (fmt or "csv").lower()
            meta = meta or {}
            content = (
                table_io.export_json(rows or [], meta=meta)
                if fmt == "json"
                else table_io.export_csv(rows or [])
            )
            if meta.get("is_template"):
                default_name = f"voicegen_template.{fmt}"
            else:
                default_name = f"voicegen_script.{fmt}"
            result = _window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=default_name,
                file_types=(
                    "CSV (*.csv)" if fmt == "csv" else "JSON (*.json)",
                    "All Files (*.*)",
                ),
            ) if _window else None
            if not result:
                return _ok(None)
            path = Path(result if isinstance(result, str) else result[0])
            path.write_text(content, encoding="utf-8")
            return _ok({"path": str(path.resolve())})
        except Exception as exc:
            return _err(str(exc))

    def save_project(self, rows: list, meta: dict | None = None) -> dict:
        try:
            path = DATA_DIR / "project.json"
            meta = meta or {}
            cfg = config_store.load_config()
            payload = {
                "version": 2,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "source_lang": meta.get("source_lang") or cfg.get("source_lang"),
                "target_lang": meta.get("target_lang") or cfg.get("target_lang"),
                "rows": rows or [],
            }
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            # persist language prefs to config as well
            config_store.save_config(
                {
                    "source_lang": payload["source_lang"],
                    "target_lang": payload["target_lang"],
                }
            )
            return _ok({"path": str(path)})
        except Exception as exc:
            return _err(str(exc))

    def load_project(self) -> dict:
        try:
            path = DATA_DIR / "project.json"
            cfg = config_store.load_config()
            if not path.is_file():
                return _ok(
                    {
                        "rows": [],
                        "source_lang": cfg.get("source_lang"),
                        "target_lang": cfg.get("target_lang"),
                    }
                )
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                rows = table_io.normalize_rows(data)
                source_lang = cfg.get("source_lang")
                target_lang = cfg.get("target_lang")
            else:
                rows = table_io.normalize_rows(data.get("rows") or [])
                source_lang = data.get("source_lang") or cfg.get("source_lang")
                target_lang = data.get("target_lang") or cfg.get("target_lang")
            return _ok(
                {
                    "rows": rows,
                    "path": str(path),
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                }
            )
        except Exception as exc:
            return _err(str(exc))

    # ── translation ─────────────────────────────────────────
    def translate_rows(
        self,
        rows: list,
        mode: str = "literal",
        source_lang: str = "",
        target_lang: str = "",
        only_enabled: bool = True,
    ) -> dict:
        """Start translation in a background thread; results via translate_* events."""
        global _translate_running
        with _translate_lock:
            if _translate_running:
                return _err("翻译任务进行中，请稍候")
            if _job_running:
                return _err("配音任务进行中，请稍候")
            _translate_running = True

        thread = threading.Thread(
            target=self._run_translate,
            args=(rows or [], mode, source_lang, target_lang, only_enabled),
            daemon=True,
        )
        thread.start()
        return _ok({"started": True})

    def _run_translate(
        self,
        rows: list,
        mode: str,
        source_lang: str,
        target_lang: str,
        only_enabled: bool,
    ) -> None:
        global _translate_running
        try:
            cfg = config_store.load_config()
            api_key = config_store.get_api_key(cfg)
            base_url = cfg.get("base_url") or mimo_tts.DEFAULT_BASE_URL
            llm_model = cfg.get("llm_model") or mimo_chat.LLM_MODEL
            src = (source_lang or cfg.get("source_lang") or "zh-CN").strip()
            tgt = (target_lang or cfg.get("target_lang") or "en-US").strip()
            mode_key = (
                "localize"
                if str(mode).lower() in {"localize", "local", "l10n", "本土化"}
                else "literal"
            )
            _emit(
                "translate_start",
                {
                    "mode": mode_key,
                    "source_lang": src,
                    "target_lang": tgt,
                    "model": llm_model,
                },
            )

            if src == tgt:
                results = []
                for row in rows or []:
                    if only_enabled and not row.get("enabled", True):
                        continue
                    text = str(row.get("text") or "").strip()
                    if not text:
                        continue
                    results.append({"id": str(row.get("id") or ""), "tts_text": text})
                _emit(
                    "translate_done",
                    {
                        "results": results,
                        "mode": mode_key,
                        "source_lang": src,
                        "target_lang": tgt,
                        "model": llm_model,
                        "count": len(results),
                        "note": "源语言与目标语言相同，已复制原文到配音文本",
                    },
                )
                return

            mimo_chat.check_llm(base_url, api_key, llm_model)
            work = []
            for row in rows or []:
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
                _emit("translate_error", {"error": "没有可翻译的原文行"})
                return

            batch_size = int(
                cfg.get("translate_batch_size") or mimo_chat.BATCH_SIZE or 8
            )
            batch_size = max(1, min(30, batch_size))
            workers = int(cfg.get("translate_workers") or 3)
            workers = max(1, min(8, workers))

            chunks: list[tuple[int, list]] = []
            for bi, start in enumerate(range(0, len(work), batch_size)):
                chunks.append((bi, work[start : start + batch_size]))
            total_batches = len(chunks)

            _emit(
                "translate_progress",
                {
                    "batch": 0,
                    "total_batches": total_batches,
                    "done": 0,
                    "total": len(work),
                    "message": f"并发翻译 {total_batches} 批 × {workers} 线程 · {llm_model}",
                },
            )

            batch_results: dict[int, list[dict]] = {}
            done_count = 0
            done_lock = threading.Lock()

            def _run_one_batch(bi: int, chunk: list) -> tuple[int, list[dict]]:
                translated = mimo_chat.translate_batch(
                    chunk,
                    mode=mode_key,  # type: ignore[arg-type]
                    source_lang=src,
                    target_lang=tgt,
                    base_url=base_url,
                    api_key=api_key,
                    model=llm_model,
                )
                return bi, [{"id": t["id"], "tts_text": t["text"]} for t in translated]

            with ThreadPoolExecutor(max_workers=min(workers, total_batches)) as pool:
                futures = [
                    pool.submit(_run_one_batch, bi, chunk) for bi, chunk in chunks
                ]
                for fut in as_completed(futures):
                    bi, items = fut.result()
                    batch_results[bi] = items
                    with done_lock:
                        done_count += len(items)
                        finished = len(batch_results)
                    # Stream partial results so UI updates as each batch finishes
                    _emit(
                        "translate_progress",
                        {
                            "batch": finished,
                            "total_batches": total_batches,
                            "done": done_count,
                            "total": len(work),
                            "message": f"翻译完成 {done_count}/{len(work)}",
                            "results": items,
                            "partial": True,
                        },
                    )

            all_results: list[dict] = []
            for bi in range(total_batches):
                all_results.extend(batch_results.get(bi) or [])

            config_store.save_config({"source_lang": src, "target_lang": tgt})
            _emit(
                "translate_done",
                {
                    "results": all_results,
                    "mode": mode_key,
                    "source_lang": src,
                    "target_lang": tgt,
                    "model": llm_model,
                    "count": len(all_results),
                    "workers": workers,
                    "batch_size": batch_size,
                },
            )
        except Exception as exc:
            _emit(
                "translate_error",
                {"error": str(exc), "trace": traceback.format_exc()[-600:]},
            )
        finally:
            with _translate_lock:
                _translate_running = False

    def apply_tts_text_from_source(self, rows: list) -> dict:
        """Copy source text into tts_text for all enabled rows (no API)."""
        try:
            results = []
            for row in rows or []:
                if not row.get("enabled", True):
                    continue
                text = str(row.get("text") or "").strip()
                if not text:
                    continue
                results.append({"id": str(row.get("id") or ""), "tts_text": text})
            return _ok({"results": results})
        except Exception as exc:
            return _err(str(exc))

    # ── generation ──────────────────────────────────────────
    def cancel_generate(self) -> dict:
        _cancel_flag.set()
        return _ok(True)

    def is_generating(self) -> dict:
        return _ok(_job_running)

    def generate_all(self, rows: list, options: dict | None = None) -> dict:
        """Start batch generation in a background thread; progress via events."""
        global _job_running
        with _job_lock:
            if _job_running:
                return _err("已有任务在运行")
            _job_running = True
            _cancel_flag.clear()

        options = options or {}
        thread = threading.Thread(
            target=self._run_generate,
            args=(rows or [], options),
            daemon=True,
        )
        thread.start()
        return _ok({"started": True})

    def _run_generate(self, rows: list, options: dict) -> None:
        global _job_running
        try:
            cfg = config_store.load_config()
            api_key = config_store.get_api_key(cfg)
            base_url = options.get("base_url") or cfg.get("base_url") or mimo_tts.DEFAULT_BASE_URL
            model = options.get("model") or cfg.get("model") or mimo_tts.MODEL_ID
            default_style = options.get("default_style") or cfg.get("default_style") or config_store.DEFAULT_STYLE
            gap_ms = int(options.get("gap_ms", cfg.get("gap_ms", 200)) or 0)
            only_enabled = options.get("only_enabled", True)
            target_lang = (
                options.get("target_lang")
                or cfg.get("target_lang")
                or config_store.DEFAULT_TARGET_LANG
            )
            workers = int(
                options.get("tts_workers")
                or cfg.get("tts_workers")
                or config_store.DEFAULT_TTS_WORKERS
            )
            workers = max(1, min(12, workers))

            try:
                mimo_tts.check_service(base_url, api_key, model)
            except Exception as exc:
                _emit("generate_error", {"error": str(exc)})
                return

            work_rows = []
            for r in rows:
                if only_enabled and not r.get("enabled", True):
                    continue
                text = table_io.row_speak_text(r)
                if not text:
                    continue
                work_rows.append(r)

            total = len(work_rows)
            if total == 0:
                _emit(
                    "generate_error",
                    {"error": "没有可配音的行（请填写原文或译文，并勾选启用）"},
                )
                return

            SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            job_dir = SEGMENTS_DIR / stamp
            job_dir.mkdir(parents=True, exist_ok=True)

            _emit(
                "generate_start",
                {
                    "total": total,
                    "job_dir": str(job_dir),
                    "workers": workers,
                },
            )

            def _synth_one(index: int, row: dict) -> tuple[int, dict, Path | None]:
                if _cancel_flag.is_set():
                    return index, {
                        "row_id": str(row.get("id") or index),
                        "status": "error",
                        "duration": None,
                        "segment_path": "",
                        "error": "已取消",
                    }, None

                row_id = str(row.get("id") or index)
                voice_id = str(row.get("voice") or "").strip()
                text = table_io.row_speak_text(row)
                speed = float(row.get("speed") or 1.0)
                style = str(row.get("style") or "").strip() or default_style
                style = languages.resolve_tts_style(style, target_lang)
                speaker = str(row.get("speaker") or "").strip()

                _emit(
                    "generate_progress",
                    {
                        "index": index,
                        "total": total,
                        "row_id": row_id,
                        "status": "running",
                        "speaker": speaker,
                        "text": text[:80],
                        "workers": workers,
                    },
                )

                try:
                    if not voice_id:
                        raise ValueError("未选择音色")
                    ref = voices.resolve_voice(voice_id)
                    raw_wav = job_dir / f"{index:04d}_{row_id}_raw.wav"
                    final_wav = job_dir / f"{index:04d}_{row_id}.wav"

                    mimo_tts.synthesize(
                        text=text,
                        reference_audio=ref,
                        output=raw_wav,
                        api_key=api_key,
                        base_url=base_url,
                        model=model,
                        style=style,
                    )
                    if _cancel_flag.is_set():
                        raise RuntimeError("已取消")
                    audio_utils.apply_speed(raw_wav, final_wav, speed)
                    duration = audio_utils.probe_duration(final_wav)
                    item = {
                        "row_id": row_id,
                        "status": "done",
                        "duration": duration,
                        "segment_path": str(final_wav),
                        "error": "",
                    }
                    _emit(
                        "generate_progress",
                        {
                            "index": index,
                            "total": total,
                            "row_id": row_id,
                            "status": "done",
                            "duration": duration,
                            "segment_path": str(final_wav),
                        },
                    )
                    return index, item, final_wav
                except Exception as exc:
                    item = {
                        "row_id": row_id,
                        "status": "error",
                        "duration": None,
                        "segment_path": "",
                        "error": str(exc),
                    }
                    _emit(
                        "generate_progress",
                        {
                            "index": index,
                            "total": total,
                            "row_id": row_id,
                            "status": "error",
                            "error": str(exc),
                        },
                    )
                    if options.get("stop_on_error"):
                        _cancel_flag.set()
                    return index, item, None

            # Concurrent TTS; keep original order for MP3 concat
            by_index: dict[int, tuple[dict, Path | None]] = {}
            max_workers = min(workers, total)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [
                    pool.submit(_synth_one, i, row) for i, row in enumerate(work_rows)
                ]
                for fut in as_completed(futures):
                    index, item, path = fut.result()
                    by_index[index] = (item, path)

            if _cancel_flag.is_set() and len(by_index) < total:
                _emit(
                    "generate_cancelled",
                    {"done": len(by_index), "total": total},
                )
                return

            results: list[dict] = []
            segment_paths: list[Path] = []
            for i in range(total):
                item, path = by_index.get(i, (
                    {
                        "row_id": str(work_rows[i].get("id") or i),
                        "status": "error",
                        "duration": None,
                        "segment_path": "",
                        "error": "未生成",
                    },
                    None,
                ))
                results.append(item)
                if path is not None and item.get("status") == "done":
                    segment_paths.append(path)

            if not segment_paths:
                _emit("generate_error", {"error": "全部行生成失败，无法合并 MP3", "results": results})
                return

            skip_merge = bool(options.get("skip_final_merge"))
            if skip_merge:
                # Single-row (or partial) regen: keep segment files, no full MP3 concat
                total_dur = sum(
                    float(by_index[i][0].get("duration") or 0)
                    for i in range(total)
                    if by_index.get(i) and by_index[i][0].get("status") == "done"
                )
                _emit(
                    "generate_done",
                    {
                        "output": None,
                        "duration": total_dur,
                        "segments": len(segment_paths),
                        "results": results,
                        "job_dir": str(job_dir),
                        "workers": workers,
                        "skip_final_merge": True,
                    },
                )
                return

            out_name = options.get("output_name") or f"dubbing_{stamp}.mp3"
            if not str(out_name).lower().endswith(".mp3"):
                out_name = f"{out_name}.mp3"
            out_path = OUTPUT_DIR / out_name

            _emit(
                "generate_progress",
                {
                    "index": total,
                    "total": total,
                    "status": "merging",
                    "workers": workers,
                },
            )
            merge = audio_utils.concat_to_mp3(segment_paths, out_path, gap_ms=gap_ms)

            _emit(
                "generate_done",
                {
                    "output": merge["path"],
                    "duration": merge["duration"],
                    "segments": merge["segments"],
                    "results": results,
                    "job_dir": str(job_dir),
                    "workers": workers,
                    "skip_final_merge": False,
                },
            )
        except Exception as exc:
            _emit(
                "generate_error",
                {"error": str(exc), "trace": traceback.format_exc()[-800:]},
            )
        finally:
            with _job_lock:
                _job_running = False

    def open_output_folder(self) -> dict:
        try:
            import subprocess
            import sys

            path = str(OUTPUT_DIR.resolve())
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", path])
            else:
                subprocess.Popen(["xdg-open", path])
            return _ok(path)
        except Exception as exc:
            return _err(str(exc))

    def reveal_file(self, path: str) -> dict:
        try:
            import subprocess
            import sys

            p = Path(path).expanduser().resolve()
            if not p.exists():
                return _err("文件不存在")
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(p)])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p.parent)])
            return _ok(str(p))
        except Exception as exc:
            return _err(str(exc))

    def get_audio_data_url(self, path: str) -> dict:
        """Return a data-URL for preview (only under project output/ or voices/)."""
        try:
            import base64

            p = Path(path).expanduser().resolve()
            if not p.is_file():
                return _err("音频文件不存在")
            allowed_roots = (OUTPUT_DIR.resolve(), VOICES_DIR.resolve())
            allowed = False
            for root in allowed_roots:
                try:
                    p.relative_to(root)
                    allowed = True
                    break
                except ValueError:
                    continue
            if not allowed:
                return _err("只能试听本项目 output 或 voices 目录下的音频")
            raw = p.read_bytes()
            if len(raw) > 25 * 1024 * 1024:
                return _err("音频过大，无法在界面内预览")
            ext = p.suffix.lower()
            mime = {
                ".wav": "audio/wav",
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".ogg": "audio/ogg",
                ".flac": "audio/flac",
                ".aac": "audio/aac",
                ".opus": "audio/opus",
            }.get(ext, "audio/wav")
            url = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
            return _ok({"url": url, "path": str(p), "mime": mime})
        except Exception as exc:
            return _err(str(exc))

    def get_paths(self) -> dict:
        return _ok(
            {
                "voices_dir": str(VOICES_DIR.resolve()),
                "output_dir": str(OUTPUT_DIR.resolve()),
                "data_dir": str(DATA_DIR.resolve()),
            }
        )

    def new_empty_row(self) -> dict:
        return _ok(table_io.new_row())
