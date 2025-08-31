"""Klient ShowAds API s autentifikáciou a logikou opakovaných pokusov."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests  # type: ignore[import-untyped]

from .config import settings
from .logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Vyvolaná, keď API aj po opakovaniach vráti HTTP 429."""


@dataclass
class AuthToken:
    """Uchováva prístupový token a čas exspirácie."""

    access_token: str
    expires_at: float


class ShowAdsClient:
    """Klient pre ShowAds API."""

    def __init__(
        self,
        base_url: str | None = None,
        project_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = base_url or settings.base_url
        self.project_key = project_key or settings.project_key
        self.timeout = timeout or settings.request_timeout_s
        self._token: AuthToken | None = None
        self.session = requests.Session()

    # Autentifikácia
    def _token_valid(self) -> bool:  # pragma: no cover - trivial
        return bool(self._token and self._token.expires_at > time.time())

    def authenticate(self) -> str:  # pragma: no cover - network
        """Získa nový prístupový token."""

        url = f"{self.base_url}/auth"
        try:
            resp = self.session.post(
                url,
                json={"ProjectKey": self.project_key},
                timeout=self.timeout,
            )
        except Exception as exc:  # pragma: no cover - network failure
            logger.error(
                "auth_error",
                extra={"event": "auth_error", "error_msg": str(exc)},
            )
            raise
        if resp.status_code != 200:
            logger.error(
                "auth_error",
                extra={"event": "auth_error", "error_code": resp.status_code},
            )
            resp.raise_for_status()
        data = resp.json()
        token = str(data["AccessToken"])
        expires_in = int(data.get("ExpiresIn", 24 * 3600))
        self._token = AuthToken(token, time.time() + expires_in)
        logger.info("auth_ok", extra={"event": "auth_ok"})
        return token

    def _ensure_token(self) -> str:  # pragma: no cover - simple wrapper
        if not self._token_valid():
            return self.authenticate()
        assert self._token is not None
        return self._token.access_token

    # Hromadné odosielanie
    def send_bulk(
        self, payload: list[dict[str, Any]], idempotency_key: Optional[str] = None
    ) -> tuple[requests.Response, int]:  # pragma: no cover - network
        """Odošle dávku záznamov s retry a spätným čakaním.

        Ak ``idempotency_key`` nie je zadaný, vygeneruje sa z hash hodnoty
        payloadu, aby boli opakovania idempotentné.
        """

        url = f"{self.base_url}/banners/show/bulk"
        attempt = 0
        start_time = time.time()
        while True:
            token = self._ensure_token()
            if idempotency_key is None:
                idempotency_key = hashlib.sha256(
                    json.dumps(payload, sort_keys=True).encode("utf-8")
                ).hexdigest()
            headers = {
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": idempotency_key,
            }
            resp = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 401 and attempt == 0:
                self.authenticate()
                attempt += 1
                continue
            if resp.status_code in {429} or 500 <= resp.status_code < 600:
                if attempt >= settings.max_retries:
                    if resp.status_code == 429:
                        raise RateLimitError("rate limited")
                    return resp, attempt
                backoff = settings.retry_backoff_s * (2**attempt)
                backoff += random.uniform(0, settings.retry_backoff_s)
                if time.time() - start_time + backoff > 60:  # pevný limit 60 s
                    if resp.status_code == 429:
                        raise RateLimitError("rate limited")
                    return resp, attempt
                time.sleep(backoff)
                attempt += 1
                continue
            if resp.status_code == 429:
                raise RateLimitError("rate limited")
            return resp, attempt
