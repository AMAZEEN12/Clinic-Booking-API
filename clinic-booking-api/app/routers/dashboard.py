"""GET /dashboard/summary and GET /dashboard/appointments (R15, R16, extra).

Read-only and additive: the Koya endpoints are untouched (D6). The API key is public in the web
page (D11), so these never return emails or full names (D36, N10). They also need a staff login
(Authorization: Bearer <token> from POST /auth/login): a patient's token is a 403. `date` is a
UTC day, YYYY-MM-DD, and defaults to today.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth import require_staff
from app.schemas import DashboardAppointment, DashboardSummary
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", dependencies=[Depends(require_staff)])

# A plain string, checked by the service: the framework's own date parsing would also accept
# forms such as a timestamp, and the spec asks for exactly YYYY-MM-DD.
DayQuery = Annotated[str | None, Query(alias="date")]


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(day: DayQuery = None):
    return dashboard_service.get_summary(day)


@router.get("/appointments", response_model=list[DashboardAppointment])
def dashboard_appointments(day: DayQuery = None):
    return dashboard_service.get_appointments(day)
