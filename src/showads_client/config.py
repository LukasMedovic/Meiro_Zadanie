"""Rezolver konfigurácie pre aplikáciu."""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Any, get_type_hints

# voliteľné načítanie .env
try:
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv())
except Exception:
    pass


@dataclass(frozen=True)
class Settings:
    base_url: str = "https://api.showads.example.com"
    project_key: str = ""
    min_age: int = 18
    max_age: int = 99
    request_timeout_s: float = 10.0
    max_retries: int = 3
    retry_backoff_s: float = 1.0
    bulk_batch_size: int = 1000
    log_level: str = "INFO"
    log_json: bool = False
    parallel_requests: int = 4
    dedup_window: int = 100_000


_FIELD_ENV = {
    "base_url": "SHOWADS_BASE_URL",
    "project_key": "SHOWADS_PROJECT_KEY",
    "min_age": "MIN_AGE",
    "max_age": "MAX_AGE",
    "request_timeout_s": "REQUEST_TIMEOUT_SECONDS",
    "max_retries": "MAX_RETRIES",
    "retry_backoff_s": "RETRY_BACKOFF_SECONDS",
    "bulk_batch_size": "BULK_BATCH_SIZE",
    "log_level": "LOG_LEVEL",
    "log_json": "LOG_JSON",
    "parallel_requests": "PARALLEL_REQUESTS",
    "dedup_window": "DEDUP_WINDOW",
}


def _coerce(value: str, target_type: type) -> Any:
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type is bool:
        return value.lower() == "true"
    return value


def resolve_settings(cli_overrides: dict[str, Any] | None = None) -> Settings:
    data: dict[str, Any] = {}
    type_map = get_type_hints(Settings)
    for f in fields(Settings):
        env_name = _FIELD_ENV.get(f.name)
        val = os.getenv(env_name) if env_name else None
        if val is not None:
            data[f.name] = _coerce(val, type_map[f.name])
        else:
            data[f.name] = f.default

    if cli_overrides:
        for key, val in cli_overrides.items():
            if val is not None and key in data:
                data[key] = val
    return Settings(**data)


# predvolená inštancia nastavení
settings = resolve_settings()
