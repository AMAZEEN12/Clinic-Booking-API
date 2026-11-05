"""POST /reset (Level 1): replace all slots and clear all bookings."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Request

from app.services import slots as slot_service

router = APIRouter()


@router.post("/reset")
def reset(request: Request, payload: Annotated[Any, Body()]):
    count = slot_service.replace_slots(payload)
    # A reset starts everything from scratch, so earlier booking attempts no longer count.
    request.app.state.rate_limiter.reset()
    return {"slots": count}
