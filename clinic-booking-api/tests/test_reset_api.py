import psycopg
import pytest

from tests.helpers import slot


def _ids(client, api_headers):
    return [item["id"] for item in client.get("/slots", headers=api_headers).json()]


def test_accepts_an_object_with_a_slots_list(client, api_headers):
    response = client.post(
        "/reset", json={"slots": [slot("s1"), slot("s2", hour=10)]}, headers=api_headers
    )
    assert response.status_code == 200
    assert response.json() == {"slots": 2}
    assert _ids(client, api_headers) == ["s1", "s2"]


def test_accepts_a_bare_list_of_slots(client, api_headers):
    response = client.post("/reset", json=[slot("a1"), slot("a2", hour=10)], headers=api_headers)
    assert response.status_code == 200
    assert _ids(client, api_headers) == ["a1", "a2"]


def test_replaces_the_previous_slots(client, api_headers, reset_slots):
    reset_slots([slot("old1"), slot("old2", hour=10)])
    reset_slots([slot("new1")])
    assert _ids(client, api_headers) == ["new1"]


def test_an_empty_list_removes_every_slot(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    response = client.post("/reset", json={"slots": []}, headers=api_headers)
    assert response.status_code == 200
    assert _ids(client, api_headers) == []


def test_reset_removes_existing_bookings(client, api_headers, reset_slots, migrated_database):
    reset_slots([slot("s1")])
    with psycopg.connect(migrated_database) as conn:
        conn.execute(
            "INSERT INTO bookings (id, slot_id, name, email, status) "
            "VALUES ('b1', 's1', 'Ada', 'a@x.com', 'confirmed')"
        )
    reset_slots([slot("s1")])
    with psycopg.connect(migrated_database) as conn:
        count = conn.execute("SELECT count(*) FROM bookings").fetchone()[0]
    assert count == 0
    assert client.get("/slots", headers=api_headers).json()[0]["available"] is True


def test_a_time_without_a_zone_is_taken_as_utc(client, api_headers):
    body = {
        "slots": [
            {
                "id": "s1",
                "provider": "Dr Ade",
                "start": "2026-12-10T09:00:00",
                "end": "2026-12-10T09:30:00",
            }
        ]
    }
    assert client.post("/reset", json=body, headers=api_headers).status_code == 200
    item = client.get("/slots", headers=api_headers).json()[0]
    assert item["start"] == "2026-12-10T09:00:00Z"
    assert item["end"] == "2026-12-10T09:30:00Z"


INVALID_BODIES = {
    "missing id": {"slots": [{k: v for k, v in slot("s1").items() if k != "id"}]},
    "blank id": {"slots": [{**slot("s1"), "id": "  "}]},
    "end before start": {"slots": [{**slot("s1"), "end": "2026-12-10T08:00:00Z"}]},
    "bad date": {"slots": [{**slot("s1"), "start": "not a date"}]},
    "duplicate ids": {"slots": [slot("s1"), slot("s1", hour=10)]},
    "slots is not a list": {"slots": "nope"},
    "wrong shape": {"something": []},
}


@pytest.mark.parametrize("body", INVALID_BODIES.values(), ids=INVALID_BODIES.keys())
def test_invalid_bodies_are_rejected(client, api_headers, body):
    response = client.post("/reset", json=body, headers=api_headers)
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)


def test_an_invalid_reset_changes_nothing(client, api_headers, reset_slots):
    reset_slots([slot("keep")])
    client.post("/reset", json={"slots": [slot("x"), slot("x")]}, headers=api_headers)
    assert _ids(client, api_headers) == ["keep"]


def test_malformed_json_is_rejected(client, api_headers):
    response = client.post(
        "/reset",
        content="{not json",
        headers={**api_headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)
