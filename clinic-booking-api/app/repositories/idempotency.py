"""SQL for Idempotency-Key records. No business rules live here."""

from psycopg import Connection

# Arbitrary constant: the first half of a two-part advisory lock, so these locks can never
# collide with the migration lock or the reset lock (which use the one-number form).
_KEY_LOCK_NAMESPACE = 727_276


def lock(conn: Connection, key: str) -> None:
    """Make requests with the same key run one after the other until this transaction ends."""
    conn.execute("SELECT pg_advisory_xact_lock(%s, hashtext(%s))", (_KEY_LOCK_NAMESPACE, key))


def get(conn: Connection, key: str) -> dict | None:
    return conn.execute(
        "SELECT key, request_hash, booking_id FROM idempotency_keys WHERE key = %s", (key,)
    ).fetchone()


def insert(conn: Connection, key: str, request_hash: str, booking_id: str) -> None:
    conn.execute(
        "INSERT INTO idempotency_keys (key, request_hash, booking_id) VALUES (%s, %s, %s)",
        (key, request_hash, booking_id),
    )
