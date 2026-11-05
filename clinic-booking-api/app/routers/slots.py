"""GET /slots (Level 1)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas import SlotWithAvailability
from app.services import slots as slot_service

router = APIRouter()


@router.get("/slots", response_model=list[SlotWithAvailability])
def get_slots(provider: Annotated[str | None, Query()] = None):
    return slot_service.list_slots(provider)
