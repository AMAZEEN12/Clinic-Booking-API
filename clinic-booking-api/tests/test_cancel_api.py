from tests.helpers import new_booking, run_together, slot


def _book(client, api_headers, **overrides):
    return client.post("/bookings", json=new_booking(**overrides), headers=api_headers)


def _cancel(client, api_headers, booking_id):
    return client.delete(f"/bookings/{booking_id}", headers=api_headers)


def _availability(client, api_headers):
    items = client.get("/slots", headers=api_headers).json()
    return {item["id"]: item["available"] for item in items}


def test_cancelling_returns_the_booking_as_cancelled(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    created = _book(client, api_headers).json()
    response = _cancel(client, api_headers, created["id"])
    assert response.status_code == 200
    assert response.json() == {**created, "status": "cancelled"}


def test_the_cancelled_booking_is_still_readable(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    created = _book(client, api_headers).json()
    _cancel(client, api_headers, created["id"])
    fetched = client.get(f"/bookings/{created['id']}", headers=api_headers).json()
    assert fetched["status"] == "cancelled"


def test_cancelling_frees_the_slot(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    created = _book(client, api_headers, slot_id="s1").json()
    _book(client, api_headers, slot_id="s2", email="bola@example.com")
    assert _availability(client, api_headers) == {"s1": False, "s2": False}

    _cancel(client, api_headers, created["id"])
    assert _availability(client, api_headers) == {"s1": True, "s2": False}


def test_a_cancelled_slot_can_be_booked_again(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers).json()
    _cancel(client, api_headers, first["id"])

    second = _book(client, api_headers, name="Bola Eze", email="bola@example.com")
    assert second.status_code == 201
    assert second.json()["id"] != first["id"]
    assert second.json()["status"] == "confirmed"
    assert _availability(client, api_headers) == {"s1": False}

    # The old booking stays cancelled; only the new one holds the slot.
    old = client.get(f"/bookings/{first['id']}", headers=api_headers).json()
    assert old["status"] == "cancelled"


def test_cancelling_twice_is_a_conflict(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    created = _book(client, api_headers).json()
    first = _cancel(client, api_headers, created["id"])
    second = _cancel(client, api_headers, created["id"])
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json() == {"error": "booking already cancelled"}
    fetched = client.get(f"/bookings/{created['id']}", headers=api_headers).json()
    assert fetched["status"] == "cancelled"


def test_cancelling_an_old_booking_does_not_free_a_newer_one(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers).json()
    _cancel(client, api_headers, first["id"])
    second = _book(client, api_headers, email="bola@example.com").json()

    _cancel(client, api_headers, first["id"])  # a repeat of the first cancel
    assert _availability(client, api_headers) == {"s1": False}
    still = client.get(f"/bookings/{second['id']}", headers=api_headers).json()
    assert still["status"] == "confirmed"


def test_unknown_booking_is_404(client, api_headers):
    response = _cancel(client, api_headers, "does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"error": "booking not found"}


def test_simultaneous_cancels_one_succeeds_the_rest_conflict(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    created = _book(client, api_headers).json()
    results = run_together([lambda: _cancel(client, api_headers, created["id"])] * 10)
    statuses = [response.status_code for response in results]
    assert statuses.count(200) == 1
    assert statuses.count(409) == 9
    assert _availability(client, api_headers) == {"s1": True}
