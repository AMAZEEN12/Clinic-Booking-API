"""Database access: a small connection pool and a forward-only SQL migration runner."""

import logging
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

log = logging.getLogger("app.db")

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

# Arbitrary constant: stops two app instances from running migrations at the same moment.
_MIGRATION_LOCK_ID = 727_274

_pool: ConnectionPool | None = None


def init_pool(database_url: str, max_size: int = 5) -> ConnectionPool:
    """Open the shared connection pool (D39: small pool, max 5). Rows come back as dicts."""
    global _pool
    _pool = ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=max_size,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    _pool.open(wait=True, timeout=30)
    return _pool


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialised")
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _version_number(path: Path) -> int:
    # "V12__add_something.sql" -> 12
    return int(path.name.split("__", 1)[0].removeprefix("V"))


def run_migrations(database_url: str) -> list[str]:
    """Apply every migrations/V<n>__*.sql file not yet applied, in order.

    Returns the file names applied by this call (empty when already up to date).
    All pending migrations run in one transaction, so a failure leaves nothing half-applied.
    """
    applied: list[str] = []
    with psycopg.connect(database_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("V*__*.sql"), key=_version_number):
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            applied.append(path.name)
    if applied:
        log.info("applied migrations: %s", ", ".join(applied))
    return applied
