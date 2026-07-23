"""Daily rotating application logs under data/log (keep 7 days)."""

from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime, timedelta
from logging.handlers import BaseRotatingHandler
from pathlib import Path

from .paths import LOG_DIR

LOG_RETENTION_DAYS = 7
_LOGGER_NAME = "voicegen"
_configured = False
_config_lock = threading.Lock()


class DailyFileHandler(BaseRotatingHandler):
    """One log file per day: voicegen-YYYY-MM-DD.log"""

    def __init__(self, log_dir: Path, encoding: str = "utf-8"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        filename = self.log_dir / f"voicegen-{self._current_date}.log"
        super().__init__(str(filename), mode="a", encoding=encoding, delay=False)

    def shouldRollover(self, record: logging.LogRecord) -> bool:  # noqa: N802
        today = datetime.now().strftime("%Y-%m-%d")
        return today != self._current_date

    def doRollover(self) -> None:  # noqa: N802
        if self.stream:
            self.stream.close()
            self.stream = None  # type: ignore[assignment]
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self.baseFilename = str(self.log_dir / f"voicegen-{self._current_date}.log")
        self.stream = self._open()
        cleanup_old_logs(self.log_dir, LOG_RETENTION_DAYS)


def cleanup_old_logs(log_dir: Path | None = None, keep_days: int = LOG_RETENTION_DAYS) -> int:
    """Delete voicegen-*.log older than keep_days. Returns removed count."""
    directory = Path(log_dir or LOG_DIR)
    if not directory.is_dir():
        return 0
    cutoff = datetime.now().date() - timedelta(days=max(1, int(keep_days)))
    removed = 0
    for path in directory.glob("voicegen-*.log"):
        # voicegen-YYYY-MM-DD.log
        stem = path.stem  # voicegen-2026-07-23
        parts = stem.split("-", 1)
        if len(parts) != 2:
            continue
        try:
            file_date = datetime.strptime(parts[1], "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < cutoff:
            try:
                path.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
    return removed


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root voicegen logger once (console + daily file)."""
    global _configured
    with _config_lock:
        logger = logging.getLogger(_LOGGER_NAME)
        if _configured:
            return logger

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        cleanup_old_logs(LOG_DIR, LOG_RETENTION_DAYS)

        logger.setLevel(level)
        logger.propagate = False

        fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = DailyFileHandler(LOG_DIR)
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

        console = logging.StreamHandler(sys.stderr)
        console.setLevel(level)
        console.setFormatter(fmt)
        logger.addHandler(console)

        _configured = True
        logger.info(
            "日志系统已启动 · 目录=%s · 保留=%s 天",
            LOG_DIR,
            LOG_RETENTION_DAYS,
        )
        return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return child logger; ensures setup_logging has run."""
    setup_logging()
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)
