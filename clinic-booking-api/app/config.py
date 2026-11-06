"""Settings read from environment variables. Secrets are never stored in code or files."""

import os
from dataclasses import dataclass

# Paging for GET /bookings (Level 4): the only place these numbers live.
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

# Booking attempts per client IP address per minute (Level 5, R11).
DEFAULT_RATE_LIMIT_PER_MINUTE = 5

# Login attempts per client IP address per minute. Slows down password guessing.
LOGIN_ATTEMPTS_PER_MINUTE = 10

# A login lasts this long, then the person signs in again.
TOKEN_LIFETIME_SECONDS = 8 * 60 * 60

# The signing secret must be long enough that guessing it is not realistic.
MIN_AUTH_SECRET_LENGTH = 32


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_key: str
    # Signs login tokens. Must NOT be the API key: that key is public in the web page.
    auth_secret: str
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE
    # Passwords for the two seeded demo accounts. When one is not set, that account is not created.
    staff_password: str | None = None
    patient_password: str | None = None


def load_settings() -> Settings:
    """Read required settings; fail clearly (and closed) when any is missing."""
    database_url = os.environ.get("DATABASE_URL", "").strip()
    api_key = os.environ.get("API_KEY", "").strip()
    auth_secret = os.environ.get("AUTH_SECRET", "").strip()
    missing = [
        name
        for name, value in (
            ("DATABASE_URL", database_url),
            ("API_KEY", api_key),
            ("AUTH_SECRET", auth_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
    if len(auth_secret) < MIN_AUTH_SECRET_LENGTH:
        raise RuntimeError(f"AUTH_SECRET must be at least {MIN_AUTH_SECRET_LENGTH} characters")
    if auth_secret == api_key:
        raise RuntimeError("AUTH_SECRET must be different from API_KEY")
    return Settings(
        database_url=database_url,
        api_key=api_key,
        auth_secret=auth_secret,
        rate_limit_per_minute=_rate_limit_from_env(),
        staff_password=os.environ.get("STAFF_PASSWORD", "").strip() or None,
        patient_password=os.environ.get("PATIENT_PASSWORD", "").strip() or None,
    )


def _rate_limit_from_env() -> int:
    """RATE_LIMIT_PER_MINUTE, or 10 when unset. Anything but a whole number of 1+ is an error."""
    raw = os.environ.get("RATE_LIMIT_PER_MINUTE", "").strip()
    if not raw:
        return DEFAULT_RATE_LIMIT_PER_MINUTE
    if not raw.isdecimal() or int(raw) < 1:
        raise RuntimeError("RATE_LIMIT_PER_MINUTE must be a whole number of 1 or more")
    return int(raw)


def cors_origins_from_env() -> list[str]:
    """Web origins allowed to call the API from a browser (D42), from CORS_ORIGINS.

    Comma-separated, for example "https://clinic.vercel.app". Empty means no browser origin.
    """
    raw = os.environ.get("CORS_ORIGINS", "")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
