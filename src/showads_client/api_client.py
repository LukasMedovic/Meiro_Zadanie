"""ShowAds API klient."""

from dataclasses import dataclass
from typing import List, Dict, Any
from .config import settings


@dataclass
class AuthToken:
    """Drzi pristupovy token (kratkozivy)."""

    access_token: str


class ShowAdsClient:
    """Klient pre auth a bulk odosielanie (zatial stub bez siete)."""

    def __init__(
        self,
        base_url: str | None = None,
        project_key: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = base_url or settings.base_url
        self.project_key = project_key or settings.project_key
        self.timeout = timeout or settings.request_timeout_s
        self._token: AuthToken | None = None

    def authenticate(self) -> str:
        """Zabezpeci pristupovy token (stub)."""
        self._token = AuthToken(access_token="DUMMY_TOKEN")
        return self._token.access_token

    def send_bulk(self, payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Odosle batch validnych zaznamov (stub)."""
        if not self._token:
            self.authenticate()
        return {"status": "stubbed", "sent": len(payload)}
