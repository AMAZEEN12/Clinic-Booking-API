"""Dashboard logic (R15, R16): one UTC day at a time, with masked patient names (D36)."""

import re
from datetime import UTC, date, datetime, timedelta

from app import db
from app.errors import BadRequestError
from app.repositories import dashboard as dashboard_repository
from app.schemas import DashboardAppointment, DashboardSummary

_DAY_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Only so one very long first name cannot fill the dashboard.
MAX_FIRST_NAME_LENGTH = 30
_UNKNOWN_PATIENT = "Patient"


def mask_name(full_name: str) -> str:
    """First name plus the last name's initial ("Ada Obi" -> "Ada O."), never the full name.

    A name with an "@" in it (someone typed an email address there) is replaced entirely, so
    an email can never leave through this endpoint (N10).
    """
    if "@" in full_name:
        return _UNKNOWN_PATIENT
    parts = full_name.split()
    if not parts:
        return _UNKNOWN_PATIENT
    first = parts[0][:MAX_FIRST_NAME_LENGTH]
    if len(parts) == 1:
        return first
    return f"{first} {parts[-1][0].upper()}."


def parse_day(raw: str | None) -> date:
    """The requested UTC day. Missing means today; anything but YYYY-MM-DD is a 400."""
    if raw is None:
        return datetime.now(UTC).date()
    try:
        if not _DAY_SHAPE.match(raw):
            raise ValueError(raw)
        return date.fromisoformat(raw)
    except ValueError:
        raise BadRequestError("date must be YYYY-MM-DD") from None


def _window(day: date) -> tuple[datetime, datetime]:
    """Midnight to midnight UTC."""
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    return start, start + timedelta(days=1)


def get_summary(raw_day: str | None) -> DashboardSummary:
    day = parse_day(raw_day)
    with db.get_pool().connection() as conn:
        row = dashboard_repository.summary(conn, *_window(day))
    return DashboardSummary(date=day, **row)


def get_appointments(raw_day: str | None) -> list[DashboardAppointment]:
    day = parse_day(raw_day)
    with db.get_pool().connection() as conn:
        rows = dashboard_repository.appointments(conn, *_window(day))
    return [
        DashboardAppointment(
            booking_id=row["booking_id"],
            slot_id=row["slot_id"],
            provider=row["provider"],
            start=row["start_at"],
            end=row["end_at"],
            patient=mask_name(row["name"]),
            status=row["status"],
            payment="paid" if row["paid"] else "unpaid",
        )
        for row in rows
    ]
