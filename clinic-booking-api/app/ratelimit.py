"""Limit on booking attempts (Level 5, R11): at most N per email per minute.

A sliding window: an attempt is allowed when fewer than N attempts from that email happened in
the last 60 seconds. Failed attempts (400, 404, 409 ...) count too; refused ones (429) do not,
so waiting the time in Retry-After is always enough.

Everything is kept in memory, so the limit is per process: run exactly one worker (C4).
Only a one-way hash of the email is kept (N4).
"""

import hashlib
import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

from app.errors import TooManyRequestsError
from app.schemas import normalize_email

WINDOW_SECONDS = 60.0

# Once this many emails are tracked, the ones with no attempt in the last window are dropped,
# which keeps memory from growing.
_SWEEP_ABOVE = 1024


class SlidingWindowLimiter:
    def __init__(
        self,
        limit_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
        window: float = WINDOW_SECONDS,
    ):
        self._limit = limit_per_minute
        self._window = window
        self._clock = clock
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, client: str) -> int:
        """Record one attempt. Returns 0 when allowed, otherwise the whole seconds to wait."""
        with self._lock:
            now = self._clock()
            if len(self._attempts) > _SWEEP_ABOVE:
                self._forget_idle(now)
            times = self._attempts.setdefault(client, deque())
            while times and now - times[0] >= self._window:
                times.popleft()
            if len(times) >= self._limit:
                return max(1, math.ceil(times[0] + self._window - now))
            times.append(now)
            return 0

    def reset(self) -> None:
        """Forget every attempt (used by POST /reset)."""
        with self._lock:
            self._attempts.clear()

    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._attempts)

    def _forget_idle(self, now: float) -> None:
        for client, times in list(self._attempts.items()):
            if not times or now - times[-1] >= self._window:
                del self._attempts[client]


async def enforce_booking_rate_limit(request: Request) -> None:
    """Dependency for POST /bookings: refuse the attempt after the limit, before validation.

    It runs after the API key check (a wrong key is a 401 and is never counted). A body with no
    usable email cannot be tied to anyone, so it is not counted.
    """
    try:
        payload = await request.json()
    except ValueError:
        return
    raw = payload.get("email") if isinstance(payload, dict) else None
    email = normalize_email(raw) if isinstance(raw, str) else None
    if email is None:
        return
    client = hashlib.sha256(email.encode()).hexdigest()
    wait = request.app.state.rate_limiter.check(client)
    if wait:
        raise TooManyRequestsError("too many requests", headers={"Retry-After": str(wait)})
