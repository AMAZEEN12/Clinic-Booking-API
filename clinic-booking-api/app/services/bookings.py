"""Booking business logic."""

import base64
import binascii
import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

import psycopg.errors

from app import audit, db
from app.errors import BadRequestError, ConflictError, NotFoundError, UnprocessableError
from app.repositories import bookings as booking_repository
from app.repositories import idempotency as idempotency_repository
from app.repositories import slots as slot_repository
from app.schemas import Booking, BookingPage, NewBooking

_ONE_CONFIRMED_PER_SLOT = "bookings_one_confirmed_per_slot"


def _fingerprint(new: NewBooking) -> str:
    """A short digest of the request body, to tell a true retry from a different request."""
    body = json.dumps([new.slot_id, new.name, new.email], separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def create_booking(new: NewBooking, idempotency_key: str | None = None) -> Booking:
    """Book a slot, safely when the same request arrives more than once (Levels 3 and 4).

    The unique index, not this code, is what stops a double booking: when two requests race
    for one slot, the database lets one in and the other gets a 409. Retrying safely is done
    with the Idempotency-Key header: the same key and body gives back the original booking.
    """
    try:
        booking, created = _create_once(new, idempotency_key, _fingerprint(new))
    except psycopg.errors.UniqueViolation as error:
        if error.diag.constraint_name == _ONE_CONFIRMED_PER_SLOT:
            raise ConflictError("slot already booked") from error
        raise  # anything else (for example a clash on the random booking id) is a real fault
    except psycopg.errors.ForeignKeyViolation as error:
        # The slot was removed (a reset) between the check and the insert.
        raise NotFoundError("slot not found") from error
    if created:
        audit.record("booking_created", booking_id=booking.id, slot_id=booking.slot_id)
    return booking


def _create_once(new: NewBooking, key: str | None, fingerprint: str) -> tuple[Booking, bool]:
    """One attempt, in one transaction. Returns the booking and whether this call created it."""
    with db.get_pool().connection() as conn:
        if key:
            idempotency_repository.lock(conn, key)
            stored = idempotency_repository.get(conn, key)
            if stored is not None:
                if stored["request_hash"] != fingerprint:
                    raise UnprocessableError(
                        "idempotency key was already used for a different request"
                    )
                row = booking_repository.get(conn, stored["booking_id"])
                if row is None:
                    raise NotFoundError("booking not found")
                return Booking(**row), False

        slot = slot_repository.get(conn, new.slot_id)
        if slot is None:
            raise NotFoundError("slot not found")
        if slot["start_at"] <= datetime.now(UTC):
            raise BadRequestError("slot has already started")

        row = booking_repository.insert(conn, f"bk_{uuid4().hex}", new.slot_id, new.name, new.email)
        if key:
            idempotency_repository.insert(conn, key, fingerprint, row["id"])
    return Booking(**row), True


def get_booking(booking_id: str) -> Booking:
    with db.get_pool().connection() as conn:
        row = booking_repository.get(conn, booking_id)
    if row is None:
        raise NotFoundError("booking not found")
    return Booking(**row)


def _encode_cursor(row: dict) -> str:
    raw = f"{row['created_at'].isoformat()}|{row['id']}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created_at, booking_id = base64.urlsafe_b64decode(padded).decode().split("|", 1)
        moment = datetime.fromisoformat(created_at)
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise BadRequestError("invalid cursor") from error
    if moment.tzinfo is None or not booking_id:
        raise BadRequestError("invalid cursor")
    return moment, booking_id


def list_bookings(email: str, limit: int, cursor: str | None = None) -> BookingPage:
    """One page of a person's bookings, oldest first, with a cursor for the next page."""
    email = email.strip()
    if not email:
        raise BadRequestError("email is required")
    after = _decode_cursor(cursor) if cursor else None
    with db.get_pool().connection() as conn:
        rows = booking_repository.list_page(conn, email, limit + 1, after)
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1]) if len(rows) > limit else None
    return BookingPage(bookings=[Booking(**row) for row in page], next_cursor=next_cursor)


def cancel_booking(booking_id: str) -> Booking:
    """Cancel a booking and free its slot (Level 3). Cancelling twice is a 409."""
    with db.get_pool().connection() as conn:
        row = booking_repository.cancel(conn, booking_id)
        existing = row if row is not None else booking_repository.get(conn, booking_id)
    if existing is None:
        raise NotFoundError("booking not found")
    if row is None:
        raise ConflictError("booking already cancelled")
    audit.record("booking_cancelled", booking_id=booking_id, slot_id=row["slot_id"])
    return Booking(**row)
