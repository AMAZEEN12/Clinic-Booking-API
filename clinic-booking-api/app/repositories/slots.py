"""SQL for slots. No business rules live here."""

from psycopg import Connection

from app.schemas import Slot

# Arbitrary constant: makes two simultaneous resets run one after the other.
_RESET_LOCK_ID = 727_275


def list_with_availability(conn: Connection) -> list[dict]:
    """Every slot, earliest first; available is false while it has a confirmed booking."""
    return conn.execute(
        "SELECT s.id, s.provider, s.start_at, s.end_at, "
        "NOT EXISTS ("
        "SELECT 1 FROM bookings b WHERE b.slot_id = s.id AND b.status = 'confirmed'"
        ") AS available "
        "FROM slots s ORDER BY s.start_at, s.id"
    ).fetchall()


def replace_all(conn: Connection, slots: list[Slot]) -> None:
    """Replace every slot. Deleting slots also removes their bookings, keys and payments."""
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (_RESET_LOCK_ID,))
    conn.execute("DELETE FROM slots")
    with conn.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO slots (id, provider, start_at, end_at) VALUES (%s, %s, %s, %s)",
            [(slot.id, slot.provider, slot.start, slot.end) for slot in slots],
        )
