"""SQL for simulated payments. No business rules live here."""

from psycopg import Connection

_COLUMNS = "booking_id, status, reference, paid_at"


def booking_status(conn: Connection, booking_id: str) -> str | None:
    """The booking's status, or None when there is no such booking."""
    row = conn.execute("SELECT status FROM bookings WHERE id = %s", (booking_id,)).fetchone()
    return None if row is None else row["status"]


def lock_booking_status(conn: Connection, booking_id: str) -> str | None:
    """Like booking_status, but holds a shared lock on the row until the transaction ends.

    A cancel running at the same moment has to wait for this transaction, or this one waits for
    the cancel and then sees "cancelled". Either way a payment is never added to a booking
    that was already seen as cancelled.
    """
    row = conn.execute(
        "SELECT status FROM bookings WHERE id = %s FOR SHARE", (booking_id,)
    ).fetchone()
    return None if row is None else row["status"]


def get(conn: Connection, booking_id: str) -> dict | None:
    return conn.execute(
        f"SELECT {_COLUMNS} FROM payments WHERE booking_id = %s", (booking_id,)
    ).fetchone()


def insert_if_missing(conn: Connection, booking_id: str, reference: str) -> dict | None:
    """Record a payment. Returns the new row, or None when the booking was already paid."""
    return conn.execute(
        "INSERT INTO payments (booking_id, status, reference) VALUES (%s, 'paid', %s) "
        f"ON CONFLICT (booking_id) DO NOTHING RETURNING {_COLUMNS}",
        (booking_id, reference),
    ).fetchone()
