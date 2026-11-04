"""SQL for bookings. No business rules live here."""

from psycopg import Connection

_COLUMNS = "id, slot_id, name, email, status, created_at"


def insert(conn: Connection, booking_id: str, slot_id: str, name: str, email: str) -> dict:
    """Insert a confirmed booking. The database rejects a second confirmed booking per slot."""
    return conn.execute(
        "INSERT INTO bookings (id, slot_id, name, email, status) "
        f"VALUES (%s, %s, %s, %s, 'confirmed') RETURNING {_COLUMNS}",
        (booking_id, slot_id, name, email),
    ).fetchone()


def get(conn: Connection, booking_id: str) -> dict | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM bookings WHERE id = %s", (booking_id,)).fetchone()


def cancel(conn: Connection, booking_id: str) -> dict | None:
    """Cancel a confirmed booking. Returns the row only if this call changed it.

    Returns None when the booking does not exist or was already cancelled.
    """
    return conn.execute(
        "UPDATE bookings SET status = 'cancelled' "
        f"WHERE id = %s AND status = 'confirmed' RETURNING {_COLUMNS}",
        (booking_id,),
    ).fetchone()
