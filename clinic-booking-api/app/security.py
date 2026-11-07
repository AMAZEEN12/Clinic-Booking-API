"""API key check (R5, N1): every Koya endpoint needs the X-API-Key header.

Also counts booking attempts for the rate limit (Level 5, R11), right after the key check."""

import hmac
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.errors import error_response
from app.ratelimit import booking_attempt_wait

API_KEY_HEADER = "X-API-Key"


def requires_api_key(path: str) -> bool:
    """True for the API endpoints. /health, /config.js and the web page files are public."""
    path = path.rstrip("/") or "/"
    return path in ("/slots", "/reset", "/auth/login") or path.startswith(
        ("/bookings", "/dashboard/")
    )


def key_matches(provided: str | None, expected: str) -> bool:
    """Constant-time comparison so response timing does not reveal the key."""
    if not provided:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


async def api_key_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if requires_api_key(request.url.path):
        expected = request.app.state.settings.api_key
        if not key_matches(request.headers.get(API_KEY_HEADER), expected):
            return error_response(401, "missing or invalid API key")
        if request.method == "POST" and request.url.path.rstrip("/") == "/bookings":
            wait = booking_attempt_wait(request)
            if wait:
                return error_response(429, "too many requests", {"Retry-After": str(wait)})
    return await call_next(request)
