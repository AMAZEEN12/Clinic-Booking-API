"""Settings read from environment variables. Secrets are never stored in code or files."""

import os
from dataclasses import dataclass


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
