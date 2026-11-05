"""No personal data in the logs (N4), and one audit line per state change (N5)."""

import logging
import re

import pytest

import app.main  # noqa: F401  (importing the app installs the access-log filter)
from tests.helpers import new_booking, slot

# Distinct, easy-to-spot personal data: any part of it showing up in a log or an error is a leak.
NAME = "Zainab Okonkwo-Pemberton"
EMAIL = "zainab.okonkwo@example.com"
OTHER_NAME = "Chidi Nwosu-Bellamy"
OTHER_EMAIL = "chidi.nwosu@example.com"
PERSONAL_DATA = ["zainab", "okonkwo", "pemberton", "chidi", "nwosu", "bellamy", "@example.com"]

# One audit line is "audit event=<name>" followed by key=value pairs, and nothing else.
AUDIT_LINE = re.compile(r"^audit event=[a-z_]+( [a-z_]+=\S+)+$")


@pytest.fixture(autouse=True)
def _capture_info_logs(caplog):
    caplog.set_level(logging.INFO)


def _log_access_line(path: str) -> None:
    # The same arguments uvicorn passes for every request it serves.
    logging.getLogger("uvicorn.access").info(
        '%s - "%s %s HTTP/%s" %d', "127.0.0.1:5000", "GET", path, "1.1", 200
    )


def _audit_lines(caplog) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "app.audit"]


def _app_log_text(caplog) -> str:
    """Everything the app logged. The test client's own request log is left out: it prints the
    full URL, including ?email=..., but it only exists in the tests, never in production."""
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if not record.name.startswith(("httpx", "httpcore"))
    )


def _book(client, api_headers, **overrides):
    return client.post("/bookings", json=new_booking(**overrides), headers=api_headers)


# --- N4: personal data stays out of the logs --------------------------------------------------


def test_the_email_in_a_query_string_is_not_logged(caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        _log_access_line("/bookings?email=ada@example.com&page=2")
    assert "ada@example.com" not in caplog.text
    assert "page=2" not in caplog.text
    assert 'GET /bookings HTTP/1.1" 200' in caplog.text


def test_paths_without_a_query_string_are_logged_as_they_are(caplog):
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        _log_access_line("/slots")
    assert 'GET /slots HTTP/1.1" 200' in caplog.text


def test_no_name_or_email_reaches_the_logs_or_an_error_message(
    client, api_headers, reset_slots, caplog
):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    caplog.clear()

    created = _book(client, api_headers, slot_id="s1", name=NAME, email=EMAIL)
    booking_id = created.json()["id"]
    failures = [
        # The slot is taken by someone else.
        _book(client, api_headers, slot_id="s1", name=OTHER_NAME, email=OTHER_EMAIL),
        # The slot does not exist.
        _book(client, api_headers, slot_id="nope", name=NAME, email=EMAIL),
        # Invalid details that contain personal data.
        _book(client, api_headers, slot_id="s2", name=NAME, email="zainab.okonkwo-no-domain"),
        _book(client, api_headers, slot_id="s2", name="", email=EMAIL),
        # A body that is not JSON at all.
        client.post(
            "/bookings",
            content="{" + NAME,
            headers={**api_headers, "Content-Type": "application/json"},
        ),
        # Unknown ids.
        client.get("/bookings/unknown", headers=api_headers),
        client.delete("/bookings/unknown", headers=api_headers),
        # A wrong key and a missing key.
        client.post("/bookings", json=new_booking(name=NAME, email=EMAIL)),
        client.get("/slots", headers={"X-API-Key": "wrong-key"}),
    ]
    # The successful paths too: read, list by email, cancel, cancel again.
    client.get(f"/bookings/{booking_id}", headers=api_headers)
    client.get("/bookings", params={"email": EMAIL}, headers=api_headers)
    client.delete(f"/bookings/{booking_id}", headers=api_headers)
    client.delete(f"/bookings/{booking_id}", headers=api_headers)

    assert all(response.status_code >= 400 for response in failures)
    log_text = _app_log_text(caplog).lower()
    for fragment in PERSONAL_DATA:
        assert fragment not in log_text, f"{fragment!r} was logged"
        for response in failures:
            assert fragment not in response.text.lower(), f"{fragment!r} was in an error"


# --- N5: one audit line per state change ------------------------------------------------------


def test_creating_a_booking_writes_one_audit_line(client, api_headers, reset_slots, caplog):
    reset_slots([slot("s1")])
    caplog.clear()

    response = _book(client, api_headers)

    assert response.status_code == 201
    booking_id = response.json()["id"]
    assert _audit_lines(caplog) == [
        f"audit event=booking_created booking_id={booking_id} slot_id=s1"
    ]


def test_cancelling_a_booking_writes_one_audit_line(client, api_headers, reset_slots, caplog):
    reset_slots([slot("s1")])
    booking_id = _book(client, api_headers).json()["id"]
    caplog.clear()

    response = client.delete(f"/bookings/{booking_id}", headers=api_headers)

    assert response.status_code == 200
    assert _audit_lines(caplog) == [
        f"audit event=booking_cancelled booking_id={booking_id} slot_id=s1"
    ]


def test_a_reset_writes_one_audit_line_with_the_slot_count(client, api_headers, caplog):
    caplog.clear()

    response = client.post(
        "/reset", json={"slots": [slot("s1"), slot("s2", hour=10)]}, headers=api_headers
    )

    assert response.status_code == 200
    assert _audit_lines(caplog) == ["audit event=slots_reset slots=2"]


def test_cancelling_again_is_a_conflict_and_writes_no_audit_line(
    client, api_headers, reset_slots, caplog
):
    reset_slots([slot("s1")])
    booking_id = _book(client, api_headers).json()["id"]
    client.delete(f"/bookings/{booking_id}", headers=api_headers)
    caplog.clear()

    response = client.delete(f"/bookings/{booking_id}", headers=api_headers)

    assert response.status_code == 409
    assert _audit_lines(caplog) == []


def test_a_repeated_request_creates_nothing_so_writes_no_second_audit_line(
    client, api_headers, reset_slots, caplog
):
    reset_slots([slot("s1")])
    caplog.clear()

    first = client.post(
        "/bookings", json=new_booking(), headers={**api_headers, "Idempotency-Key": "retry-1"}
    )
    same_key = client.post(
        "/bookings", json=new_booking(), headers={**api_headers, "Idempotency-Key": "retry-1"}
    )
    same_person_no_key = _book(client, api_headers)  # slot taken: 409

    statuses = [first.status_code, same_key.status_code, same_person_no_key.status_code]
    assert statuses == [201, 201, 409]
    assert len(_audit_lines(caplog)) == 1


def test_requests_that_fail_write_no_audit_line(client, api_headers, reset_slots, caplog):
    reset_slots([slot("s1")])
    _book(client, api_headers)
    caplog.clear()

    results = [
        _book(client, api_headers, name="Bola Eze", email="bola@example.com"),  # slot taken: 409
        _book(client, api_headers, slot_id="nope"),  # unknown slot: 404
        _book(client, api_headers, email="not-an-email"),  # invalid: 400
        client.delete("/bookings/unknown", headers=api_headers),  # unknown booking: 404
        client.post("/reset", json={"slots": "wrong"}, headers=api_headers),  # invalid: 400
        client.post("/bookings", json=new_booking()),  # no key: 401
    ]

    assert [r.status_code for r in results] == [409, 404, 400, 404, 400, 401]
    assert _audit_lines(caplog) == []


def test_audit_lines_hold_ids_and_counts_only(client, api_headers, caplog):
    client.post("/reset", json={"slots": [slot("s1")]}, headers=api_headers)
    booking_id = _book(client, api_headers, name=NAME, email=EMAIL).json()["id"]
    client.delete(f"/bookings/{booking_id}", headers=api_headers)

    lines = _audit_lines(caplog)

    assert len(lines) == 3
    for line in lines:
        assert AUDIT_LINE.match(line), line
        for fragment in PERSONAL_DATA:
            assert fragment not in line.lower()
