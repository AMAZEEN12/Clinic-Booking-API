"""Simulated payment (R13): separate endpoints, no real money, core Booking untouched (D6)."""

import logging
import re

import pytest

from tests.helpers import new_booking, run_together, slot

BOOKING_FIELDS = {"id", "slot_id", "name", "email", "status", "created_at"}
PAYMENT_FIELDS = {"booking_id", "status", "reference", "paid_at"}
FAKE_CARD = "4242424242424242"


def _book(client, api_headers, **overrides):
    return client.post("/bookings", json=new_booking(**overrides), headers=api_headers)


def _pay(client, api_headers, booking_id, **kwargs):
    return client.post(f"/bookings/{booking_id}/payment", headers=api_headers, **kwargs)


def _payment(client, api_headers, booking_id):
    return client.get(f"/bookings/{booking_id}/payment", headers=api_headers)


def _cancel(client, api_headers, booking_id):
    return client.delete(f"/bookings/{booking_id}", headers=api_headers)


@pytest.fixture
def booking(client, api_headers, reset_slots):
    """A confirmed, unpaid booking for slot s1."""
    reset_slots([slot("s1"), slot("s2", hour=10)])
    return _book(client, api_headers).json()


# --- paying ------------------------------------------------------------------------------------


def test_paying_a_confirmed_booking_returns_200_and_paid(client, api_headers, booking):
    response = _pay(client, api_headers, booking["id"])
    assert response.status_code == 200
    body = response.json()
    assert set(body) == PAYMENT_FIELDS
    assert body["booking_id"] == booking["id"]
    assert body["status"] == "paid"
    assert body["paid_at"].endswith("Z")


def test_the_reference_is_obviously_fake(client, api_headers, booking):
    reference = _pay(client, api_headers, booking["id"]).json()["reference"]
    assert re.fullmatch(r"DEMO-[0-9A-F]{10}", reference)


def test_a_booking_starts_unpaid(client, api_headers, booking):
    response = _payment(client, api_headers, booking["id"])
    assert response.status_code == 200
    assert response.json() == {
        "booking_id": booking["id"],
        "status": "unpaid",
        "reference": None,
        "paid_at": None,
    }


def test_the_payment_can_be_read_after_paying(client, api_headers, booking):
    paid = _pay(client, api_headers, booking["id"]).json()
    assert _payment(client, api_headers, booking["id"]).json() == paid


def test_paying_twice_returns_the_same_payment(client, api_headers, booking):
    first = _pay(client, api_headers, booking["id"])
    second = _pay(client, api_headers, booking["id"])
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()


def test_simultaneous_payments_make_one_payment(client, api_headers, booking):
    results = run_together([lambda: _pay(client, api_headers, booking["id"])] * 10)
    assert [response.status_code for response in results] == [200] * 10
    assert len({response.json()["reference"] for response in results}) == 1


def test_paying_one_booking_does_not_pay_another(client, api_headers, booking):
    other = _book(client, api_headers, slot_id="s2", email="bola@example.com").json()
    _pay(client, api_headers, booking["id"])
    assert _payment(client, api_headers, other["id"]).json()["status"] == "unpaid"


def test_a_body_is_ignored_and_card_details_are_never_kept(client, api_headers, booking, caplog):
    caplog.set_level(logging.INFO)
    response = _pay(client, api_headers, booking["id"], json={"card_number": FAKE_CARD})
    assert response.status_code == 200
    assert FAKE_CARD not in response.text
    assert FAKE_CARD not in _payment(client, api_headers, booking["id"]).text
    assert FAKE_CARD not in caplog.text


# --- cancelled and unknown bookings -------------------------------------------------------------


def test_paying_a_cancelled_booking_returns_409(client, api_headers, booking):
    _cancel(client, api_headers, booking["id"])
    response = _pay(client, api_headers, booking["id"])
    assert response.status_code == 409
    assert response.json() == {"error": "booking is cancelled"}
    assert _payment(client, api_headers, booking["id"]).json()["status"] == "unpaid"


def test_a_paid_booking_that_is_then_cancelled_still_shows_its_payment(
    client, api_headers, booking
):
    paid = _pay(client, api_headers, booking["id"]).json()
    _cancel(client, api_headers, booking["id"])
    assert _payment(client, api_headers, booking["id"]).json() == paid
    assert _pay(client, api_headers, booking["id"]).status_code == 409


def test_a_rebooked_slot_starts_unpaid(client, api_headers, booking):
    _pay(client, api_headers, booking["id"])
    _cancel(client, api_headers, booking["id"])
    again = _book(client, api_headers, name="Bola Eze", email="bola@example.com").json()
    assert again["id"] != booking["id"]
    assert _payment(client, api_headers, again["id"]).json()["status"] == "unpaid"


def test_pay_and_cancel_at_the_same_moment_never_disagree(client, api_headers, booking):
    results = run_together(
        [
            lambda: _pay(client, api_headers, booking["id"]),
            lambda: _cancel(client, api_headers, booking["id"]),
        ]
    )
    pay_response, cancel_response = results
    assert cancel_response.status_code == 200
    assert pay_response.status_code in (200, 409)
    state = _payment(client, api_headers, booking["id"]).json()["status"]
    assert state == ("paid" if pay_response.status_code == 200 else "unpaid")


def test_an_unknown_booking_is_404_for_pay_and_read(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    for response in (
        _pay(client, api_headers, "does-not-exist"),
        _payment(client, api_headers, "does-not-exist"),
    ):
        assert response.status_code == 404
        assert response.json() == {"error": "booking not found"}


def test_a_reset_removes_payments_with_their_bookings(client, api_headers, reset_slots, booking):
    _pay(client, api_headers, booking["id"])
    reset_slots([slot("s1")])
    assert _payment(client, api_headers, booking["id"]).status_code == 404


# --- the core contract stays as it was (D6, C5) -------------------------------------------------


def test_the_core_booking_responses_do_not_change_when_a_booking_is_paid(
    client, api_headers, booking
):
    assert set(booking) == BOOKING_FIELDS
    before = client.get(f"/bookings/{booking['id']}", headers=api_headers).json()
    _pay(client, api_headers, booking["id"])
    after = client.get(f"/bookings/{booking['id']}", headers=api_headers).json()
    assert set(after) == BOOKING_FIELDS
    assert after == before

    listed = client.get("/bookings", params={"email": booking["email"]}, headers=api_headers)
    assert listed.json()["bookings"]
    assert all(set(item) == BOOKING_FIELDS for item in listed.json()["bookings"])


# --- the key is required ------------------------------------------------------------------------


def test_both_payment_endpoints_need_the_api_key(client, api_headers, booking):
    path = f"/bookings/{booking['id']}/payment"
    for response in (
        client.post(path),
        client.get(path),
        client.post(path, headers={"X-API-Key": "wrong"}),
        client.get(path, headers={"X-API-Key": "wrong"}),
    ):
        assert response.status_code == 401
        assert response.json() == {"error": "missing or invalid API key"}


# --- audit and privacy (N4, N5) -----------------------------------------------------------------


def test_one_audit_line_per_payment_and_no_personal_data(client, api_headers, booking, caplog):
    caplog.set_level(logging.INFO)
    caplog.clear()
    _pay(client, api_headers, booking["id"])
    _pay(client, api_headers, booking["id"])  # a repeat changes nothing, so it is not audited

    lines = [r.getMessage() for r in caplog.records if r.name == "app.audit"]
    assert lines == [f"audit event=payment_recorded booking_id={booking['id']}"]
    # Whole strings, not "ada": booking ids are hex and could contain it by chance.
    for private in ("ada obi", "ada@example.com"):
        assert private not in caplog.text.lower()
