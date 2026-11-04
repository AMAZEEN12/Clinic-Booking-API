import psycopg
import pytest

from app import db

SLOT = ("s1", "Dr Ade", "2026-12-10T09:00:00Z", "2026-12-10T09:30:00Z")


def _insert_slot(conn):
    conn.execute(
        "INSERT INTO slots (id, provider, start_at, end_at) VALUES (%s, %s, %s, %s)",
        SLOT,
    )


def _insert_booking(conn, booking_id, status="confirmed"):
    conn.execute(
        "INSERT INTO bookings (id, slot_id, name, email, status) "
        "VALUES (%s, 's1', 'Ada', 'a@x.com', %s)",
        (booking_id, status),
    )


def test_all_tables_exist(migrated_database):
    with psycopg.connect(migrated_database) as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchall()
    names = {row[0] for row in rows}
    assert {"slots", "bookings", "idempotency_keys", "payments", "schema_migrations"} <= names


def test_running_migrations_again_applies_nothing(migrated_database):
    assert db.run_migrations(migrated_database) == []


def test_second_confirmed_booking_for_a_slot_is_rejected(clean_db):
    with psycopg.connect(clean_db) as conn:
        _insert_slot(conn)
        _insert_booking(conn, "b1")
    with pytest.raises(psycopg.errors.UniqueViolation):
        with psycopg.connect(clean_db) as conn:
            _insert_booking(conn, "b2")


def test_cancelled_booking_does_not_block_rebooking(clean_db):
    with psycopg.connect(clean_db) as conn:
        _insert_slot(conn)
        _insert_booking(conn, "b1", status="cancelled")
        _insert_booking(conn, "b2", status="confirmed")
        count = conn.execute("SELECT count(*) FROM bookings WHERE slot_id = 's1'").fetchone()[0]
    assert count == 2


def test_status_must_be_confirmed_or_cancelled(clean_db):
    with psycopg.connect(clean_db) as conn:
        _insert_slot(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(clean_db) as conn:
            _insert_booking(conn, "b1", status="pending")
