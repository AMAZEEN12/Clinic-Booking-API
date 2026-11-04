"""Small helpers shared by the tests."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor


def slot(slot_id: str, provider: str = "Dr Ade", hour: int = 9) -> dict:
    """A slot as the API sends and returns it (30 minutes on 10 December 2026, UTC)."""
    return {
        "id": slot_id,
        "provider": provider,
        "start": f"2026-12-10T{hour:02d}:00:00Z",
        "end": f"2026-12-10T{hour:02d}:30:00Z",
    }


def new_booking(
    slot_id: str = "s1", name: str = "Ada Obi", email: str = "ada@example.com"
) -> dict:
    """A booking request body."""
    return {"slot_id": slot_id, "name": name, "email": email}


def run_together(calls: list[Callable]) -> list:
    """Run every call at the same moment (each in its own thread) and return the results."""
    start_together = threading.Barrier(len(calls))

    def wrapped(call):
        start_together.wait(timeout=30)
        return call()

    with ThreadPoolExecutor(max_workers=len(calls)) as workers:
        return list(workers.map(wrapped, calls))