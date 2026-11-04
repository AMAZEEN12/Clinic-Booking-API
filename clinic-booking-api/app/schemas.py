"""Request and response models."""

from datetime import UTC, datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Slot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: NonEmptyStr
    provider: NonEmptyStr
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def _as_utc(cls, value: datetime) -> datetime:
        """Store and return every time in UTC; a time without a zone is taken as UTC."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class SlotWithAvailability(Slot):
    available: bool
