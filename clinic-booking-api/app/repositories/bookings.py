"""SQL for bookings. No business rules live here."""

from datetime import datetime

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


def list_page(
    conn: Connection,
    email: str,
    limit: int,
    after: tuple[datetime, str] | None = None,
) -> list[dict]:
    """Up to `limit` of a person's bookings, oldest first, starting after `after`.

    `after` is the (created_at, id) of the last booking already seen. Emails match ignoring
    capital letters. The id breaks ties so pages never overlap or skip a booking.
    """
    where = "lower(email) = lower(%s)"
    params: list = [email]
    if after is not None:
        where += " AND (created_at, id) > (%s, %s)"
        params += [after[0], after[1]]
    params.append(limit)
    return conn.execute(
        f"SELECT {_COLUMNS} FROM bookings WHERE {where} ORDER BY created_at, id LIMIT %s",
        params,
    ).fetchall()


def get_confirmed_for_slot(conn: Connection, slot_id: str) -> dict | None:
    """The confirmed booking holding a slot, if any (at most one can exist, R7)."""
    return conn.execute(
        f"SELECT {_COLUMNS} FROM bookings WHERE slot_id = %s AND status = 'confirmed'",
        (slot_id,),
    ).fetchone()


def cancel(conn: Connection, booking_id: str) -> dict | None:
    """Cancel a confirmed booking. Returns the row only if this call changed it.

    Returns None when the booking does not exist or was already cancelled.
    """
    return conn.execute(
        "UPDATE bookings SET status = 'cancelled' "
        f"WHERE id = %s AND status = 'confirmed' RETURNING {_COLUMNS}",
        (booking_id,),
    ).fetchone()
