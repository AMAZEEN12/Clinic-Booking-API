"""POST /bookings, GET /bookings/{id} (Level 1) and DELETE /bookings/{id} (Level 3)."""

from typing import Annotated

from fastapi import APIRouter, Header

from app.errors import BadRequestError
from app.schemas import Booking, NewBooking
from app.services import bookings as booking_service

router = APIRouter()

MAX_IDEMPOTENCY_KEY_LENGTH = 255


def _clean_key(raw: str | None) -> str | None:
    """A blank Idempotency-Key header counts as no key; an overlong one is a bad request."""
    key = (raw or "").strip()
    if len(key) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise BadRequestError("Idempotency-Key is too long")
    return key or None


@router.post("/bookings", status_code=201, response_model=Booking)
def create_booking(
    new_booking: NewBooking,
    idempotency_key: Annotated[str | None, Header()] = None,
):
    return booking_service.create_booking(new_booking, _clean_key(idempotency_key))


@router.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: str):
    return booking_service.get_booking(booking_id)


@router.delete("/bookings/{booking_id}", response_model=Booking)
def cancel_booking(booking_id: str):
    return booking_service.cancel_booking(booking_id)
