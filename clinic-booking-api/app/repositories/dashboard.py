"""SQL for the dashboard (read-only). No business rules live here.

Patient emails are never selected, and names are returned only so the service can mask them.
"""

from datetime import datetime

from psycopg import Connection


def summary(conn: Connection, start: datetime, end: datetime) -> dict:
    """Slot and booking counts for slots starting in [start, end). One statement, one snapshot."""
    return conn.execute(
        """
        WITH day_slots AS (
            SELECT id FROM slots WHERE start_at >= %(start)s AND start_at < %(end)s
        )
        SELECT
            (SELECT count(*) FROM day_slots) AS total_slots,
            (SELECT count(*) FROM day_slots d
              WHERE NOT EXISTS (
                  SELECT 1 FROM bookings b WHERE b.slot_id = d.id AND b.status = 'confirmed'
              )) AS open_slots,
            (SELECT count(*) FROM bookings b JOIN day_slots d ON d.id = b.slot_id
              WHERE b.status = 'confirmed') AS booked,
            (SELECT count(*) FROM bookings b JOIN day_slots d ON d.id = b.slot_id
              WHERE b.status = 'cancelled') AS cancelled
        """,
        {"start": start, "end": end},
    ).fetchone()


def appointments(conn: Connection, start: datetime, end: datetime) -> list[dict]:
    """Every booking (confirmed or cancelled) on slots starting in [start, end), by start time."""
    return conn.execute(
        """
        SELECT b.id AS booking_id, b.slot_id, s.provider, s.start_at, s.end_at,
               b.name, b.status, (p.booking_id IS NOT NULL) AS paid
          FROM bookings b
          JOIN slots s ON s.id = b.slot_id
          LEFT JOIN payments p ON p.booking_id = b.id
         WHERE s.start_at >= %(start)s AND s.start_at < %(end)s
         ORDER BY s.start_at, s.id, b.created_at, b.id
        """,
        {"start": start, "end": end},
    ).fetchall()
