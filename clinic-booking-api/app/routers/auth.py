"""POST /auth/login: sign in as staff or patient (extra, additive)."""

from fastapi import APIRouter, Depends, Request

from app.ratelimit import enforce_login_rate_limit
from app.schemas import LoginRequest, LoginResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth")


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(enforce_login_rate_limit)],
)
def login(credentials: LoginRequest, request: Request):
    return auth_service.login(credentials, request.app.state.settings)
