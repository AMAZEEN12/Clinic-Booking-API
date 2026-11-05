"""SQL for slots. No business rules live here."""

from psycopg import Connection

from app.schemas import Slot

# Arbitrary constant: makes two simultaneous resets run one after the other.
_RESET_LOCK_ID = 727_275


def list_with_availability(conn: Connection, provider: str | None = None) -> list[dict]:
    """Every slot, earliest first; available is false while it has a confirmed booking.

    With `provider`, only that provider's slots (exact match).
    """
    where = "WHERE s.provider = %s " if provider is not None else ""
    params = (provider,) if provider is not None else ()
    return conn.execute(
        "SELECT s.id, s.provider, s.start_at, s.end_at, "
        "NOT EXISTS ("
        "SELECT 1 FROM bookings b WHERE b.slot_id = s.id AND b.status = 'confirmed'"
        ") AS available "
        f"FROM slots s {where}ORDER BY s.start_at, s.id",
        params,
    ).fetchall()


def get(conn: Connection, slot_id: str) -> dict | None:
    return conn.execute(
        "SELECT id, provider, start_at, end_at FROM slots WHERE id = %s", (slot_id,)
    ).fetchone()


def exists(conn: Connection, slot_id: str) -> bool:
    return conn.execute("SELECT 1 FROM slots WHERE id = %s", (slot_id,)).fetchone() is not None


def replace_all(conn: Connection, slots: list[Slot]) -> None:
    """Replace every slot. Deleting slots also removes their bookings, keys and payments."""
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (_RESET_LOCK_ID,))
    conn.execute("DELETE FROM slots")
    with conn.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO slots (id, provider, start_at, end_at) VALUES (%s, %s, %s, %s)",
            [(slot.id, slot.provider, slot.start, slot.end) for slot in slots],
        )
