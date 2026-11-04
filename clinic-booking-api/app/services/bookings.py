"""Booking business logic."""

from uuid import uuid4

import psycopg.errors

from app import audit, db
from app.errors import ConflictError, NotFoundError
from app.repositories import bookings as booking_repository
from app.repositories import slots as slot_repository
from app.schemas import Booking, NewBooking

_BOOKING_ID_CONSTRAINT = "bookings_pkey"


def create_booking(new: NewBooking) -> Booking:
    """Book a slot. The unique index, not this code, is what stops a double booking (R7)."""
    booking_id = f"bk_{uuid4().hex}"
    try:
        with db.get_pool().connection() as conn:
            if not slot_repository.exists(conn, new.slot_id):
                raise NotFoundError("slot not found")
            row = booking_repository.insert(conn, booking_id, new.slot_id, new.name, new.email)
    except psycopg.errors.UniqueViolation as error:
        if error.diag.constraint_name == _BOOKING_ID_CONSTRAINT:
            raise  # a clash on the random booking id: a genuine fault, not a taken slot
        raise ConflictError("slot already booked") from error
    except psycopg.errors.ForeignKeyViolation as error:
        # The slot was removed (a reset) between the check and the insert.
        raise NotFoundError("slot not found") from error
    audit.record("booking_created", booking_id=booking_id, slot_id=new.slot_id)
    return Booking(**row)


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
