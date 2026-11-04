"""GET /slots (Level 1)."""

from fastapi import APIRouter

from app.schemas import SlotWithAvailability
from app.services import slots as slot_service

router = APIRouter()


@router.get("/slots", response_model=list[SlotWithAvailability])
def get_slots():
    return slot_service.list_slots()
