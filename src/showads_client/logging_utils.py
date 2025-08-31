"""Pomôcka na konfiguráciu logovania s voliteľným JSON výstupom."""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

_run_id = uuid.uuid4().hex


def _now() -> str:  # pragma: no cover - simple
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class JsonFormatter(logging.Formatter):
    """Formátuje logy ako štruktúrované JSON podľa schémy."""

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting
        base: dict[str, Any] = {
            "ts": _now(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "run_id": _run_id,
        }
        for field in [
            "command",
            "batch_index",
            "size",
            "duration_s",
            "retries",
            "error_code",
            "error_msg",
        ]:
            if field in record.__dict__:
                base[field] = record.__dict__[field]
        return json.dumps(base, ensure_ascii=False)


class ColorFormatter(logging.Formatter):
    """Minimálny farebný formátovač pre logy čitateľné človekom."""

    COLORS = {"INFO": "\033[32m", "ERROR": "\033[31m", "WARNING": "\033[33m", "DEBUG": "\033[36m"}
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""
        return f"{color}{record.levelname}:{reset} {record.getMessage()}"


def setup_logging() -> None:
    """Nastaví koreňový logger podľa premenných LOG_JSON a LOG_LEVEL."""

    log_json = os.getenv("LOG_JSON", "false").lower() == "true"
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if log_json else ColorFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level, logging.INFO))
