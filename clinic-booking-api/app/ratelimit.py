"""Limit on creating bookings (R11, D14): a token bucket per API key + client address.

Everything is kept in memory, so the limit is per process: run exactly one worker (C4).
Nothing here stores the key or the address itself, only a one-way hash of the pair (N4).
"""

import hashlib
import math
import threading
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.errors import error_response
from app.security import API_KEY_HEADER

# Once this many clients are tracked, the ones who have earned their full allowance back
# (so tracking them tells us nothing) are dropped, which keeps memory from growing.
_SWEEP_ABOVE = 1024


class TokenBucketLimiter:
    """Each client has a bucket that holds up to `limit_per_minute` tokens and refills evenly.

    A request spends one token. A client who has been quiet for a minute is back to a full
    bucket; one who spams runs dry and is told how many seconds until the next token.
    """

    def __init__(self, limit_per_minute: int, clock: Callable[[], float] = time.monotonic):
        self._capacity = float(limit_per_minute)
        self._seconds_per_token = 60.0 / limit_per_minute
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}  # client -> (tokens, last seen)
        self._lock = threading.Lock()

    def check(self, client: str) -> int:
        """Spend one token. Returns 0 when allowed, otherwise the seconds to wait (at least 1)."""
        with self._lock:
            now = self._clock()
            if len(self._buckets) > _SWEEP_ABOVE:
                self._forget_idle(now)
            tokens, last = self._buckets.get(client, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) / self._seconds_per_token)
            if tokens >= 1:
                self._buckets[client] = (tokens - 1, now)
                return 0
            self._buckets[client] = (tokens, now)
            return max(1, math.ceil((1 - tokens) * self._seconds_per_token))

    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._buckets)

    def _forget_idle(self, now: float) -> None:
        for client, (tokens, last) in list(self._buckets.items()):
            if tokens + (now - last) / self._seconds_per_token >= self._capacity:
                del self._buckets[client]


def client_address(request: Request) -> str:
    """The caller's address: the first X-Forwarded-For entry, else the connection's own."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def _is_booking_creation(request: Request) -> bool:
    return request.method == "POST" and request.url.path.rstrip("/") == "/bookings"


async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Refuse the 11th POST /bookings in a minute. Runs after the key check, so only requests
    with the right key are counted."""
    if _is_booking_creation(request):
        who = f"{request.headers.get(API_KEY_HEADER, '')}|{client_address(request)}"
        client = hashlib.sha256(who.encode()).hexdigest()
        wait = request.app.state.rate_limiter.check(client)
        if wait:
            return error_response(429, "too many requests", {"Retry-After": str(wait)})
    return await call_next(request)
