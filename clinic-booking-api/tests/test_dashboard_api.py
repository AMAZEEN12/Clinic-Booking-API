"""Dashboard extra (R15, R16, N10): read-only, masked names, never an email or a full name."""

from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from app.services.dashboard import mask_name
from tests.helpers import new_booking

DAY = "2026-12-10"
NEXT_DAY = "2026-12-11"
SUMMARY_FIELDS = {"date", "booked", "cancelled", "open_slots", "total_slots"}
APPOINTMENT_FIELDS = {
    "booking_id",
    "slot_id",
    "provider",
    "start",
    "end",
    "patient",
    "status",
    "payment",
}


def _slot_at(slot_id: str, day: str, hhmm: str, provider: str = "Dr Ade") -> dict:
    """A 30-minute slot starting at the given UTC day and time."""
    start = datetime.fromisoformat(f"{day}T{hhmm}:00+00:00")
    return {
        "id": slot_id,
        "provider": provider,
        "start": start.isoformat(),
        "end": (start + timedelta(minutes=30)).isoformat(),
    }


def _book(client, api_headers, slot_id, name="Ada Obi", email="ada@example.com"):
    response = client.post("/bookings", json=new_booking(slot_id, name, email), headers=api_headers)
    assert response.status_code == 201
    return response.json()


def _cancel(client, api_headers, booking_id):
    assert client.delete(f"/bookings/{booking_id}", headers=api_headers).status_code == 200


def _pay(client, api_headers, booking_id):
    assert client.post(f"/bookings/{booking_id}/payment", headers=api_headers).status_code == 200


def _summary(client, api_headers, day=DAY):
    return client.get("/dashboard/summary", params={"date": day}, headers=api_headers)


def _appointments(client, api_headers, day=DAY):
    return client.get("/dashboard/appointments", params={"date": day}, headers=api_headers)


@pytest.fixture
def three_slots(reset_slots):
    """Three slots on DAY (09:00, 10:00, 11:00) and one on the next day."""
    reset_slots(
        [
            _slot_at("s1", DAY, "09:00"),
            _slot_at("s2", DAY, "10:00"),
            _slot_at("s3", DAY, "11:00"),
            _slot_at("s4", NEXT_DAY, "09:00"),
        ]
    )


# --- the summary (R15) --------------------------------------------------------------------------


def test_the_summary_counts_follow_bookings_and_cancellations(client, api_headers, three_slots):
    before = _summary(client, api_headers)
    assert before.status_code == 200
    assert before.json() == {
        "date": DAY,
        "booked": 0,
        "cancelled": 0,
        "open_slots": 3,
        "total_slots": 3,
    }

    _book(client, api_headers, "s1")
    second = _book(client, api_headers, "s2", email="bola@example.com")
    _cancel(client, api_headers, second["id"])

    after = _summary(client, api_headers).json()
    assert set(after) == SUMMARY_FIELDS
    assert after == {"date": DAY, "booked": 1, "cancelled": 1, "open_slots": 2, "total_slots": 3}
    assert after["booked"] + after["open_slots"] == after["total_slots"]


def test_a_rebooked_slot_counts_once_as_booked_and_once_as_cancelled(
    client, api_headers, three_slots
):
    first = _book(client, api_headers, "s1")
    _cancel(client, api_headers, first["id"])
    _book(client, api_headers, "s1", name="Bola Eze", email="bola@example.com")

    summary = _summary(client, api_headers).json()
    assert (summary["booked"], summary["cancelled"], summary["open_slots"]) == (1, 1, 2)


def test_other_days_are_not_counted(client, api_headers, three_slots):
    _book(client, api_headers, "s4")
    assert _summary(client, api_headers).json()["booked"] == 0
    assert _summary(client, api_headers, NEXT_DAY).json() == {
        "date": NEXT_DAY,
        "booked": 1,
        "cancelled": 0,
        "open_slots": 0,
        "total_slots": 1,
    }


def test_a_day_with_no_slots_is_all_zeros(client, api_headers, three_slots):
    assert _summary(client, api_headers, "2027-01-01").json() == {
        "date": "2027-01-01",
        "booked": 0,
        "cancelled": 0,
        "open_slots": 0,
        "total_slots": 0,
    }


def test_the_day_runs_from_midnight_to_midnight_utc(client, api_headers, reset_slots):
    reset_slots([_slot_at("late", DAY, "23:30"), _slot_at("early", NEXT_DAY, "00:00")])
    assert _summary(client, api_headers, DAY).json()["total_slots"] == 1
    assert _summary(client, api_headers, NEXT_DAY).json()["total_slots"] == 1
    assert _appointments(client, api_headers, DAY).json() == []


def test_the_default_day_is_today_in_utc(client, api_headers, reset_slots, migrated_database):
    today = datetime.now(UTC).date()
    reset_slots([_slot_at("today", today.isoformat(), "00:00")])
    # This slot has already started, so the API refuses to book it: insert the booking directly.
    with psycopg.connect(migrated_database) as conn:
        conn.execute(
            "INSERT INTO bookings (id, slot_id, name, email, status) "
            "VALUES ('b-today', 'today', 'Ada Obi', 'ada@example.com', 'confirmed')"
        )

    summary = client.get("/dashboard/summary", headers=api_headers)
    assert summary.status_code == 200
    body = summary.json()
    # The date can roll over at midnight UTC while this test runs.
    assert body["date"] in {today.isoformat(), datetime.now(UTC).date().isoformat()}
    if body["date"] == today.isoformat():
        assert (body["booked"], body["total_slots"]) == (1, 1)

    listed = client.get("/dashboard/appointments", headers=api_headers)
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)


def test_a_bad_date_is_a_400_for_both_endpoints(client, api_headers, three_slots, bad_date):
    for path in ("/dashboard/summary", "/dashboard/appointments"):
        response = client.get(path, params={"date": bad_date}, headers=api_headers)
        assert response.status_code == 400
        assert response.json() == {"error": "date must be YYYY-MM-DD"}


# --- the appointments (R16) ---------------------------------------------------------------------


def test_appointments_are_sorted_by_start_time_with_the_expected_fields(
    client, api_headers, three_slots
):
    _book(client, api_headers, "s3", name="Chidi Nwosu", email="chidi@example.com")
    _book(client, api_headers, "s1")
    _book(client, api_headers, "s2", name="Bola Eze", email="bola@example.com")

    response = _appointments(client, api_headers)
    assert response.status_code == 200
    items = response.json()
    assert [item["slot_id"] for item in items] == ["s1", "s2", "s3"]
    assert [item["patient"] for item in items] == ["Ada O.", "Bola E.", "Chidi N."]
    for item in items:
        assert set(item) == APPOINTMENT_FIELDS
        assert item["status"] == "confirmed"
        assert item["payment"] == "unpaid"
        assert item["provider"] == "Dr Ade"
        assert item["start"].endswith("Z") and item["end"].endswith("Z")
    assert items[0]["start"] == "2026-12-10T09:00:00Z"


def test_appointments_show_the_payment_state(client, api_headers, three_slots):
    paid = _book(client, api_headers, "s1")
    _book(client, api_headers, "s2", email="bola@example.com")
    _pay(client, api_headers, paid["id"])

    items = _appointments(client, api_headers).json()
    assert [item["payment"] for item in items] == ["paid", "unpaid"]


def test_cancelled_bookings_are_listed_as_cancelled(client, api_headers, three_slots):
    booking = _book(client, api_headers, "s1")
    _cancel(client, api_headers, booking["id"])

    items = _appointments(client, api_headers).json()
    assert [(item["booking_id"], item["status"]) for item in items] == [
        (booking["id"], "cancelled")
    ]


def test_a_rebooked_slot_lists_the_cancelled_booking_then_the_new_one(
    client, api_headers, three_slots
):
    first = _book(client, api_headers, "s1")
    _cancel(client, api_headers, first["id"])
    second = _book(client, api_headers, "s1", name="Bola Eze", email="bola@example.com")

    items = _appointments(client, api_headers).json()
    assert [(item["booking_id"], item["status"]) for item in items] == [
        (first["id"], "cancelled"),
        (second["id"], "confirmed"),
    ]


def test_other_days_are_not_listed(client, api_headers, three_slots):
    _book(client, api_headers, "s4")
    assert _appointments(client, api_headers).json() == []
    assert len(_appointments(client, api_headers, NEXT_DAY).json()) == 1


# --- privacy (N10, D36) -------------------------------------------------------------------------


def test_no_email_and_no_full_name_appears_in_any_dashboard_response(
    client, api_headers, three_slots
):
    _book(client, api_headers, "s1", name="Ada Obi", email="ada@example.com")
    _book(client, api_headers, "s2", name="Chidi Nwosu-Bellamy", email="chidi@example.com")
    # Someone typed an email address into the name box: it must not come back either.
    _book(client, api_headers, "s3", name="bola@example.com", email="bola@example.com")

    summary = _summary(client, api_headers)
    appointments = _appointments(client, api_headers)
    for response in (summary, appointments):
        assert response.status_code == 200
        assert "@" not in response.text
        for private in ("example.com", "Obi", "Nwosu", "Bellamy", "Ada Obi"):
            assert private not in response.text
    assert [item["patient"] for item in appointments.json()] == ["Ada O.", "Chidi N.", "Patient"]


# --- the key is required ------------------------------------------------------------------------


def test_both_dashboard_endpoints_need_the_api_key(client, api_headers, three_slots):
    for path in ("/dashboard/summary", "/dashboard/appointments"):
        for headers in ({}, {"X-API-Key": "wrong"}):
            response = client.get(path, params={"date": DAY}, headers=headers)
            assert response.status_code == 401
            assert response.json() == {"error": "missing or invalid API key"}


def test_the_dashboard_cannot_change_anything(client, api_headers, three_slots):
    for path in ("/dashboard/summary", "/dashboard/appointments"):
        response = client.post(path, headers=api_headers)
        assert response.status_code == 405


# --- masking (D36) ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("full_name", "shown"),
    [
        ("Ada Obi", "Ada O."),
        ("  Ada   Obi  ", "Ada O."),
        ("Ada Chioma Obi", "Ada O."),
        ("Chidi Nwosu-Bellamy", "Chidi N."),
        ("ada obi", "ada O."),
        ("Ada", "Ada"),
        ("bola@example.com", "Patient"),
        ("Ada O@bi", "Patient"),
        ("   ", "Patient"),
        ("A" * 100 + " Obi", "A" * 30 + " O."),
    ],
)
def test_mask_name(full_name, shown):
    assert mask_name(full_name) == shown
