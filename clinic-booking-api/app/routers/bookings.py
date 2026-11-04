"""POST /bookings, GET /bookings/{id} (Level 1) and DELETE /bookings/{id} (Level 3)."""

from fastapi import APIRouter

from app.schemas import Booking, NewBooking
from app.services import bookings as booking_service

router = APIRouter()


@router.post("/bookings", status_code=201, response_model=Booking)
def create_booking(new_booking: NewBooking):
    return booking_service.create_booking(new_booking)


@router.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: str):
    return booking_service.get_booking(booking_id)


@router.delete("/bookings/{booking_id}", response_model=Booking)
def cancel_booking(booking_id: str):
    return booking_service.cancel_booking(booking_id)