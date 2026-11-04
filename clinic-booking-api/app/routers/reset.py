"""POST /reset (Level 1): replace all slots and clear all bookings."""

from typing import Annotated, Any

from fastapi import APIRouter, Body

from app.services import slots as slot_service

router = APIRouter()


@router.post("/reset")
def reset(payload: Annotated[Any, Body()]):
    return {"slots": slot_service.replace_slots(payload)}
