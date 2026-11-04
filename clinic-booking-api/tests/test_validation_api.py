import psycopg
import pytest

from tests.helpers import new_booking, slot

VALID = new_booking()


def _without(key):
    return {k: v for k, v in VALID.items() if k != key}


INVALID = {
    "no body": {},
    "empty object": {"json": {}},
    "list body": {"json": [VALID]},
    "string body": {"json": "hello"},
    "malformed json": {"content": "{oops", "headers": {"Content-Type": "application/json"}},
    "missing slot_id": {"json": _without("slot_id")},
    "missing name": {"json": _without("name")},
    "missing email": {"json": _without("email")},
    "blank slot_id": {"json": {**VALID, "slot_id": "  "}},
    "blank name": {"json": {**VALID, "name": ""}},
    "blank email": {"json": {**VALID, "email": ""}},
    "name is a number": {"json": {**VALID, "name": 123}},
    "slot_id is a number": {"json": {**VALID, "slot_id": 1}},
    "name too long": {"json": {**VALID, "name": "x" * 201}},
    "email without an at sign": {"json": {**VALID, "email": "ada.example.com"}},
    "email without a domain dot": {"json": {**VALID, "email": "ada@example"}},
    "email with a space": {"json": {**VALID, "email": "ada @example.com"}},
    "email with nothing before the at": {"json": {**VALID, "email": "@example.com"}},
    "email with two at signs": {"json": {**VALID, "email": "a@b@c.com"}},
}


@pytest.mark.parametrize("kwargs", INVALID.values(), ids=INVALID.keys())
def test_invalid_bookings_are_rejected_and_create_nothing(
    client, api_headers, reset_slots, migrated_database, kwargs
):
    reset_slots([slot("s1")])
    kwargs = dict(kwargs)
    headers = {**api_headers, **kwargs.pop("headers", {})}
    response = client.post("/bookings", headers=headers, **kwargs)
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)
    with psycopg.connect(migrated_database) as conn:
        assert conn.execute("SELECT count(*) FROM bookings").fetchone()[0] == 0


@pytest.mark.parametrize(
    "email", ["ada@example.com", "a.b+tag@mail.example.co.uk", "user@example.test"]
)
def test_ordinary_emails_are_accepted(client, api_headers, reset_slots, email):
    reset_slots([slot("s1")])
    response = client.post("/bookings", json=new_booking(email=email), headers=api_headers)
    assert response.status_code == 201


def test_error_messages_do_not_repeat_what_was_sent(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    body = new_booking(name="Zed Unique", email="zed-not-an-email")
    response = client.post("/bookings", json=body, headers=api_headers)
    assert response.status_code == 400
    assert "zed" not in response.text.lower()
