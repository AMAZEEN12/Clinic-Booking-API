"""Settings read from environment variables. Secrets are never stored in code or files."""

import os
from dataclasses import dataclass

# Paging for GET /bookings (D13): the only place these numbers live.
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
MAX_PAGE_NUMBER = 1_000_000


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_key: str


def load_settings() -> Settings:
    """Read required settings; fail clearly (and closed) when any is missing."""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    api_key = os.environ.get("API_KEY", "").strip()
    missing = [
        name for name, value in (("DATABASE_URL", database_url), ("API_KEY", api_key)) if not value
    ]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
    return Settings(database_url=database_url, api_key=api_key)


def cors_origins_from_env() -> list[str]:
    """Web origins allowed to call the API from a browser (D42), from CORS_ORIGINS.

    Comma-separated, for example "https://clinic.vercel.app". Empty means no browser origin.
    """
    raw = os.environ.get("CORS_ORIGINS", "")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
