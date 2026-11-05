"""POST /bookings/{id}/payment and GET /bookings/{id}/payment (R13, extra).

Separate from the core booking endpoints on purpose: the Booking response never changes (D6).
The POST takes no body; anything sent with it is ignored and never stored.
"""

from fastapi import APIRouter

from app.schemas import Payment
from app.services import payments as payment_service

router = APIRouter()


@router.post("/bookings/{booking_id}/payment", response_model=Payment)
def pay_for_booking(booking_id: str):
    return payment_service.pay(booking_id)


@router.get("/bookings/{booking_id}/payment", response_model=Payment)
def get_booking_payment(booking_id: str):
    return payment_service.get_payment(booking_id)
