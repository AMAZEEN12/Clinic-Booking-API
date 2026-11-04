"""Small helpers shared by the tests."""


def slot(slot_id: str, provider: str = "Dr Ade", hour: int = 9) -> dict:
    """A slot as the API sends and returns it (30 minutes on 10 December 2026, UTC)."""
    return {
        "id": slot_id,
        "provider": provider,
        "start": f"2026-12-10T{hour:02d}:00:00Z",
        "end": f"2026-12-10T{hour:02d}:30:00Z",
    }


def new_booking(slot_id: str = "s1", name: str = "Ada Obi", email: str = "ada@example.com") -> dict:
    """A booking request body."""
    return {"slot_id": slot_id, "name": name, "email": email}
