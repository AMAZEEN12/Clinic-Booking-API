"""Booking business logic."""

import hashlib
import json
from uuid import uuid4

import psycopg.errors

from app import audit, db
from app.errors import ConflictError, NotFoundError
from app.repositories import bookings as booking_repository
from app.repositories import idempotency as idempotency_repository
from app.repositories import slots as slot_repository
from app.schemas import Booking, NewBooking

_BOOKING_ID_CONSTRAINT = "bookings_pkey"


def _fingerprint(new: NewBooking) -> str:
    """A short digest of the request body, to tell a true retry from a different request."""
    body = json.dumps([new.slot_id, new.name, new.email], separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def create_booking(new: NewBooking, idempotency_key: str | None = None) -> Booking:
    """Book a slot, safely when the same request arrives more than once (R7, R9).

    The unique index, not this code, is what stops a double booking. If two requests for the
    same slot race and the loser turns out to be the same person, the second pass below finds
    the winner's booking and returns it instead of an error.
    """
    fingerprint = _fingerprint(new)
    for attempt in (1, 2):
        try:
            booking, created = _create_once(new, idempotency_key, fingerprint)
        except psycopg.errors.UniqueViolation as error:
            if error.diag.constraint_name == _BOOKING_ID_CONSTRAINT:
                raise  # a clash on the random booking id: a genuine fault, not a taken slot
            if attempt == 2:
                raise ConflictError("slot already booked") from error
        except psycopg.errors.ForeignKeyViolation as error:
            # The slot was removed (a reset) between the check and the insert.
            raise NotFoundError("slot not found") from error
        else:
            if created:
                audit.record("booking_created", booking_id=booking.id, slot_id=booking.slot_id)
            return booking
    raise AssertionError("unreachable")  # pragma: no cover


def _create_once(new: NewBooking, key: str | None, fingerprint: str) -> tuple[Booking, bool]:
    """One attempt, in one transaction. Returns the booking and whether this call created it."""
    with db.get_pool().connection() as conn:
        if key:
            idempotency_repository.lock(conn, key)
            stored = idempotency_repository.get(conn, key)
            if stored is not None:
                if stored["request_hash"] != fingerprint:
                    raise ConflictError("idempotency key was already used for a different request")
                row = booking_repository.get(conn, stored["booking_id"])
                if row is None:
                    raise NotFoundError("booking not found")
                return Booking(**row), False

        if not slot_repository.exists(conn, new.slot_id):
            raise NotFoundError("slot not found")

        row = booking_repository.get_confirmed_for_slot(conn, new.slot_id)
        created = row is None or row["email"].lower() != new.email.lower()
        if created:
            row = booking_repository.insert(
                conn, f"bk_{uuid4().hex}", new.slot_id, new.name, new.email
            )

        if key:
            idempotency_repository.insert(conn, key, fingerprint, row["id"])
    return Booking(**row), created


def get_booking(booking_id: str) -> Booking:
    with db.get_pool().connection() as conn:
        row = booking_repository.get(conn, booking_id)
    if row is None:
        raise NotFoundError("booking not found")
    return Booking(**row)


def cancel_booking(booking_id: str) -> Booking:
    """Cancel a booking and free its slot (R8). Cancelling twice changes nothing more."""
    with db.get_pool().connection() as conn:
        row = booking_repository.cancel(conn, booking_id)
        changed = row is not None
        if row is None:
            row = booking_repository.get(conn, booking_id)
    if row is None:
        raise NotFoundError("booking not found")
    if changed:
        audit.record("booking_cancelled", booking_id=booking_id, slot_id=row["slot_id"])
    return Booking(**row)
