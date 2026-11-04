import threading
from concurrent.futures import ThreadPoolExecutor

import psycopg

from tests.helpers import new_booking, slot


def _fire(client, api_headers, slot_ids):
    """One booking request per entry, all released at the same moment. Returns the responses."""
    start_together = threading.Barrier(len(slot_ids))

    def attempt(number):
        body = new_booking(
            slot_id=slot_ids[number], name=f"Person {number}", email=f"p{number}@example.com"
        )
        start_together.wait(timeout=30)
        return client.post("/bookings", json=body, headers=api_headers)

    with ThreadPoolExecutor(max_workers=len(slot_ids)) as workers:
        return list(workers.map(attempt, range(len(slot_ids))))


def test_fifty_simultaneous_requests_book_the_slot_exactly_once(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    responses = _fire(client, api_headers, ["s1"] * 50)

    statuses = [response.status_code for response in responses]
    assert statuses.count(201) == 1
    assert statuses.count(409) == 49
    losers = [response for response in responses if response.status_code == 409]
    assert all(response.json() == {"error": "slot already booked"} for response in losers)

    winner = next(response.json() for response in responses if response.status_code == 201)
    with psycopg.connect(migrated_database) as conn:
        rows = conn.execute("SELECT id FROM bookings WHERE slot_id = 's1'").fetchall()
    assert [row[0] for row in rows] == [winner["id"]]


def test_the_race_has_exactly_one_winner_every_time(client, api_headers, reset_slots):
    for _ in range(5):
        reset_slots([slot("s1")])
        statuses = [r.status_code for r in _fire(client, api_headers, ["s1"] * 20)]
        assert statuses.count(201) == 1
        assert statuses.count(409) == 19


def test_simultaneous_bookings_of_different_slots_all_succeed(client, api_headers, reset_slots):
    slots = [slot(f"s{number}", hour=number) for number in range(20)]
    reset_slots(slots)
    responses = _fire(client, api_headers, [s["id"] for s in slots])

    assert [response.status_code for response in responses] == [201] * 20
    assert len({response.json()["id"] for response in responses}) == 20


def test_the_database_has_the_partial_unique_index(migrated_database):
    with psycopg.connect(migrated_database) as conn:
        definition = conn.execute(
            "SELECT indexdef FROM pg_indexes WHERE indexname = 'bookings_one_confirmed_per_slot'"
        ).fetchone()[0]
    assert "UNIQUE" in definition
    assert "confirmed" in definition
