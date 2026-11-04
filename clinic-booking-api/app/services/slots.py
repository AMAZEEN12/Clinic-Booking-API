"""Slot business logic: listing with availability, and replacing all slots (reset)."""

from typing import Any

from pydantic import TypeAdapter, ValidationError

from app import audit, db
from app.errors import BadRequestError, describe_validation_errors
from app.repositories import slots as slot_repository
from app.schemas import Slot, SlotWithAvailability

_SLOT_LIST = TypeAdapter(list[Slot])


def list_slots() -> list[SlotWithAvailability]:
    with db.get_pool().connection() as conn:
        rows = slot_repository.list_with_availability(conn)
    return [
        SlotWithAvailability(
            id=row["id"],
            provider=row["provider"],
            start=row["start_at"],
            end=row["end_at"],
            available=row["available"],
        )
        for row in rows
    ]


def parse_slots(payload: Any) -> list[Slot]:
    """Accept {"slots": [...]} or a bare list (D15); reject anything invalid."""
    raw = payload.get("slots") if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise BadRequestError('body must be {"slots": [...]} or a list of slots')
    try:
        slots = _SLOT_LIST.validate_python(raw)
    except ValidationError as error:
        raise BadRequestError(describe_validation_errors(error.errors())) from error
    seen: set[str] = set()
    for slot in slots:
        if slot.id in seen:
            raise BadRequestError(f"duplicate slot id: {slot.id}")
        seen.add(slot.id)
    return slots


def replace_slots(payload: Any) -> int:
    """Replace all slots (and so clear all bookings). Returns how many slots now exist."""
    slots = parse_slots(payload)
    with db.get_pool().connection() as conn:
        slot_repository.replace_all(conn, slots)
    audit.record("slots_reset", slots=len(slots))
    return len(slots)
