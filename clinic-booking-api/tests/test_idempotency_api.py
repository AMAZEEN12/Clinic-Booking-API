import psycopg

from tests.helpers import new_booking, run_together, slot


def _book(client, api_headers, key=None, **overrides):
    headers = dict(api_headers)
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post("/bookings", json=new_booking(**overrides), headers=headers)


def _booking_rows(database_url):
    with psycopg.connect(database_url) as conn:
        return conn.execute("SELECT id, status FROM bookings ORDER BY created_at").fetchall()


def _availability(client, api_headers):
    items = client.get("/slots", headers=api_headers).json()
    return {item["id"]: item["available"] for item in items}


# --- With an Idempotency-Key header -------------------------------------------------------


def test_same_key_and_body_returns_the_original_response(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    first = _book(client, api_headers, key="key-1")
    second = _book(client, api_headers, key="key-1")
    assert first.status_code == 201
    assert second.status_code == first.status_code
    assert second.json() == first.json()
    assert len(_booking_rows(migrated_database)) == 1


def test_same_key_with_a_different_slot_is_a_conflict(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    _book(client, api_headers, key="key-2", slot_id="s1")
    second = _book(client, api_headers, key="key-2", slot_id="s2")
    assert second.status_code == 409
    assert isinstance(second.json()["error"], str)
    assert _availability(client, api_headers) == {"s1": False, "s2": True}


def test_same_key_with_a_different_email_is_a_conflict(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers, key="key-3").json()
    second = _book(client, api_headers, key="key-3", email="bola@example.com")
    assert second.status_code == 409
    still = client.get(f"/bookings/{first['id']}", headers=api_headers).json()
    assert still["email"] == "ada@example.com"


def test_different_keys_for_the_same_person_and_slot_share_one_booking(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    first = _book(client, api_headers, key="key-4a").json()
    second = _book(client, api_headers, key="key-4b").json()
    assert second["id"] == first["id"]
    assert len(_booking_rows(migrated_database)) == 1


def test_a_replay_after_cancelling_does_not_book_again(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    first = _book(client, api_headers, key="key-5").json()
    client.delete(f"/bookings/{first['id']}", headers=api_headers)

    replay = _book(client, api_headers, key="key-5")
    assert replay.json()["id"] == first["id"]
    assert _availability(client, api_headers) == {"s1": True}
    assert len(_booking_rows(migrated_database)) == 1


def test_a_failed_request_does_not_use_up_the_key(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    missing = _book(client, api_headers, key="key-6", slot_id="no-such-slot")
    assert missing.status_code == 404
    retry = _book(client, api_headers, key="key-6", slot_id="s1")
    assert retry.status_code == 201


def test_a_reset_forgets_old_keys(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers, key="key-7").json()
    reset_slots([slot("s1")])
    again = _book(client, api_headers, key="key-7")
    assert again.status_code == 201
    assert again.json()["id"] != first["id"]


def test_a_blank_key_is_ignored(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    first = _book(client, api_headers, key="   ", slot_id="s1")
    second = _book(client, api_headers, key="   ", slot_id="s2")
    assert first.status_code == 201
    assert second.status_code == 201


def test_a_key_that_is_too_long_is_rejected(client, api_headers, reset_slots, migrated_database):
    reset_slots([slot("s1")])
    response = _book(client, api_headers, key="k" * 256)
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)
    assert _booking_rows(migrated_database) == []


# --- Without a key: the same person asking for the same slot ----------------------------


def test_repeating_the_same_request_returns_the_existing_booking(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    first = _book(client, api_headers)
    second = _book(client, api_headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    assert len(_booking_rows(migrated_database)) == 1


def test_the_email_is_compared_ignoring_capital_letters(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers).json()
    second = _book(client, api_headers, email="ADA@Example.com")
    assert second.status_code == 201
    assert second.json()["id"] == first["id"]


def test_a_different_person_still_gets_a_conflict(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers).json()
    second = _book(client, api_headers, name="Bola Eze", email="bola@example.com")
    assert second.status_code == 409
    assert second.json() == {"error": "slot already booked"}
    still = client.get(f"/bookings/{first['id']}", headers=api_headers).json()
    assert still["email"] == "ada@example.com"


def test_after_a_cancel_the_same_request_makes_a_new_booking(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    first = _book(client, api_headers).json()
    client.delete(f"/bookings/{first['id']}", headers=api_headers)
    second = _book(client, api_headers)
    assert second.status_code == 201
    assert second.json()["id"] != first["id"]
    assert second.json()["status"] == "confirmed"


# --- Simultaneous retries -----------------------------------------------------------------


def test_simultaneous_requests_with_one_key_make_one_booking(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    results = run_together([lambda: _book(client, api_headers, key="key-par-1")] * 20)
    assert [response.status_code for response in results] == [201] * 20
    assert len({response.json()["id"] for response in results}) == 1
    assert len(_booking_rows(migrated_database)) == 1


def test_simultaneous_identical_requests_without_a_key_make_one_booking(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    results = run_together([lambda: _book(client, api_headers)] * 20)
    assert [response.status_code for response in results] == [201] * 20
    assert len({response.json()["id"] for response in results}) == 1
    assert len(_booking_rows(migrated_database)) == 1


def test_simultaneous_requests_with_one_key_but_two_bodies_make_one_booking(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1")])
    calls = [lambda: _book(client, api_headers, key="key-par-2")] * 10 + [
        lambda: _book(client, api_headers, key="key-par-2", email="bola@example.com")
    ] * 10
    results = run_together(calls)
    statuses = [response.status_code for response in results]
    assert set(statuses) == {201, 409}
    assert len({r.json()["id"] for r in results if r.status_code == 201}) == 1
    assert len(_booking_rows(migrated_database)) == 1
