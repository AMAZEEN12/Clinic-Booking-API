from tests.helpers import new_booking, slot


def _book(client, api_headers, **overrides):
    return client.post("/bookings", json=new_booking(**overrides), headers=api_headers)


def test_creates_a_confirmed_booking(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    response = _book(client, api_headers)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "slot_id", "name", "email", "status", "created_at"}
    assert body["slot_id"] == "s1"
    assert body["name"] == "Ada Obi"
    assert body["email"] == "ada@example.com"
    assert body["status"] == "confirmed"
    assert isinstance(body["id"], str) and body["id"]
    assert body["created_at"].endswith("Z")


def test_the_booked_slot_becomes_unavailable(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    _book(client, api_headers)
    available = {i["id"]: i["available"] for i in client.get("/slots", headers=api_headers).json()}
    assert available == {"s1": False, "s2": True}


def test_get_returns_the_same_booking(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    created = _book(client, api_headers).json()
    response = client.get(f"/bookings/{created['id']}", headers=api_headers)
    assert response.status_code == 200
    assert response.json() == created


def test_unknown_booking_is_404(client, api_headers):
    response = client.get("/bookings/does-not-exist", headers=api_headers)
    assert response.status_code == 404
    assert isinstance(response.json()["error"], str)


def test_unknown_slot_is_404(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    response = _book(client, api_headers, slot_id="no-such-slot")
    assert response.status_code == 404
    assert response.json() == {"error": "slot not found"}


def test_a_booked_slot_cannot_be_booked_again(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers).json()
    second = _book(client, api_headers, name="Bola Eze", email="bola@example.com")
    assert second.status_code == 409
    assert second.json() == {"error": "slot already booked"}
    still_there = client.get(f"/bookings/{first['id']}", headers=api_headers).json()
    assert still_there["status"] == "confirmed"


def test_each_booking_gets_its_own_id(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    first = _book(client, api_headers, slot_id="s1").json()
    second = _book(client, api_headers, slot_id="s2").json()
    assert first["id"] != second["id"]


def test_surrounding_spaces_are_trimmed(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    body = _book(client, api_headers, name="  Ada Obi  ", email="  ada@example.com ").json()
    assert body["name"] == "Ada Obi"
    assert body["email"] == "ada@example.com"


def test_the_email_is_stored_in_lower_case(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    body = _book(client, api_headers, email="  Ada.Obi@Example.COM ").json()
    assert body["email"] == "ada.obi@example.com"


def test_a_slot_that_has_already_started_is_a_bad_request(client, api_headers, reset_slots):
    past = {**slot("old"), "start": "2020-01-01T09:00:00Z", "end": "2020-01-01T09:30:00Z"}
    reset_slots([past])
    response = _book(client, api_headers, slot_id="old")
    assert response.status_code == 400
    assert response.json() == {"error": "slot has already started"}
    available = [i["available"] for i in client.get("/slots", headers=api_headers).json()]
    assert available == [True]


def test_the_same_person_booking_a_taken_slot_again_is_a_conflict(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    assert _book(client, api_headers).status_code == 201
    second = _book(client, api_headers)
    assert second.status_code == 409
    assert second.json() == {"error": "slot already booked"}
