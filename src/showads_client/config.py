"""Nastavenia aplikacie

- Bezpecne nacitanie konfiguracie z prostredia (.env) ak je dostupne.
- Ziadne tajne hodnoty sa necommituju do repozitara (.env je v .gitignore).
- Vsetky hodnoty maju rozumne defaulty pre lokalny beh a testy.
"""

from dataclasses import dataclass
import os

# Volitelne nacitanie .env (bez tvrdej zavislosti pocas testov)
try:
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv())
except Exception:
    # Ak python-dotenv nie je nainstalovany alebo .env neexistuje,
    # pokracujeme s OS env a default hodnotami.
    pass


@dataclass(frozen=True)
class Settings:
    """Imutabilna konfiguracia aplikacie.

    Poznamky:
      - base_url: zakladna URL ShowAds API
      - project_key: tajny kluc pre /auth (NELOGOVAT!)
      - min_age, max_age: validacne limity mena/veku nastavitelne bez redeployu
      - request_timeout_s: HTTP timeout v sekundach
      - max_retries, retry_backoff_s: strategia retry pre 429/5xx
      - bulk_batch_size: max 1000 (podla API limitu)
      - log_level: INFO/DEBUG
    """

    base_url: str = os.getenv("SHOWADS_BASE_URL", "https://api.showads.example.com")
    project_key: str = os.getenv("SHOWADS_PROJECT_KEY", "")
    min_age: int = int(os.getenv("MIN_AGE", "18"))
    max_age: int = int(os.getenv("MAX_AGE", "99"))
    request_timeout_s: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_backoff_s: float = float(os.getenv("RETRY_BACKOFF_SECONDS", "1.0"))
    bulk_batch_size: int = int(os.getenv("BULK_BATCH_SIZE", "1000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


# Globalna instancia nastaveni
settings = Settings()
