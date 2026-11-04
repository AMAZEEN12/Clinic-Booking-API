"""Request and response models."""

import re
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]

# Deliberately lenient (D43): something@something.something, no spaces. A strict checker would
# reject valid-looking addresses such as ones on .test domains.
_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _to_utc(value: datetime) -> datetime:
    """Return every time in UTC; a time without a zone is taken as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Slot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: NonEmptyStr
    provider: NonEmptyStr
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def _as_utc(cls, value: datetime) -> datetime:
        return _to_utc(value)

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class SlotWithAvailability(Slot):
    available: bool


class NewBooking(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slot_id: NonEmptyStr
    name: PersonName
    email: str

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 254 or not _EMAIL_SHAPE.match(value):
            raise ValueError("must be a valid email address")
        return value


class Booking(BaseModel):
    id: str
    slot_id: str
    name: str
    email: str
    status: Literal["confirmed", "cancelled"]
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def _created_at_utc(cls, value: datetime) -> datetime:
        return _to_utc(value)
