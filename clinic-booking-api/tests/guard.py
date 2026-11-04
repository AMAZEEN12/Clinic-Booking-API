"""Safety guard (D19): tests wipe data, so they must never run against the production database."""

from psycopg.conninfo import conninfo_to_dict


class GuardError(Exception):
    """Raised when the test database setting is unsafe."""


def _identity(url: str) -> tuple[str | None, str | None, str | None]:
    info = conninfo_to_dict(url)
    return info.get("host"), str(info.get("port") or 5432), info.get("dbname")


def check_test_database(test_url: str | None, production_url: str | None) -> str:
    """Return the test URL if it is safe to use; otherwise raise GuardError."""
    test_url = (test_url or "").strip()
    production_url = (production_url or "").strip()

    if not test_url:
        raise GuardError(
            "TEST_DATABASE_URL is not set. Tests only run against a separate Neon test branch."
        )
    if production_url and (
        test_url == production_url or _identity(test_url) == _identity(production_url)
    ):
        raise GuardError(
            "TEST_DATABASE_URL points at the same database as DATABASE_URL. "
            "Refusing to run tests against production."
        )
    return test_url
