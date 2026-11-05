"""Simulated payments (R13). No money moves and no card details are ever read or stored."""

from uuid import uuid4

from app import audit, db
from app.errors import ConflictError, NotFoundError
from app.repositories import payments as payment_repository
from app.schemas import Payment


def _new_reference() -> str:
    """An obviously fake reference, so nobody mistakes it for a real transaction."""
    return f"DEMO-{uuid4().hex[:10].upper()}"


def pay(booking_id: str) -> Payment:
    """Mark a confirmed booking as paid. Paying again returns the same payment (200).

    A cancelled booking cannot be paid (409), even if it was paid before it was cancelled.
    """
    with db.get_pool().connection() as conn:
        status = payment_repository.lock_booking_status(conn, booking_id)
        if status is None:
            raise NotFoundError("booking not found")
        if status != "confirmed":
            raise ConflictError("booking is cancelled")
        row = payment_repository.insert_if_missing(conn, booking_id, _new_reference())
        created = row is not None
        if row is None:  # paid already, possibly a moment ago by a request that ran alongside
            row = payment_repository.get(conn, booking_id)
    if created:
        audit.record("payment_recorded", booking_id=booking_id)
    return Payment(**row)


def get_payment(booking_id: str) -> Payment:
    """The payment state of a booking: paid, or unpaid when nothing was recorded."""
    with db.get_pool().connection() as conn:
        if payment_repository.booking_status(conn, booking_id) is None:
            raise NotFoundError("booking not found")
        row = payment_repository.get(conn, booking_id)
    if row is None:
        return Payment(booking_id=booking_id, status="unpaid")
    return Payment(**row)
