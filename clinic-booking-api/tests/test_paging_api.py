import pytest

from app.ratelimit import SlidingWindowLimiter
from tests.helpers import new_booking, slot

EMAIL = "ada@example.com"


@pytest.fixture(autouse=True)
def _roomy_limit(client):
    """These tests book many slots for one email; the limit has its own tests."""
    original = client.app.state.rate_limiter
    client.app.state.rate_limiter = SlidingWindowLimiter(10_000)
    yield
    client.app.state.rate_limiter = original


def _make_slots(count):
    return [slot(f"s{number}", hour=number % 24) for number in range(count)]


def _book_many(client, api_headers, reset_slots, count, email=EMAIL):
    """Reset to `count` slots and book them all for one person, oldest first. Returns the ids."""
    reset_slots(_make_slots(count))
    ids = []
    for number in range(count):
        body = new_booking(slot_id=f"s{number}", email=email)
        response = client.post("/bookings", json=body, headers=api_headers)
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return ids


def _list(client, api_headers, **params):
    return client.get("/bookings", params=params, headers=api_headers)


def _walk(client, api_headers, limit, email=EMAIL):
    """Follow next_cursor to the end. Returns the ids seen and the size of each page."""
    seen, sizes, cursor = [], [], None
    for _ in range(100):
        params = {"email": email, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        body = _list(client, api_headers, **params).json()
        sizes.append(len(body["bookings"]))
        seen += [item["id"] for item in body["bookings"]]
        cursor = body["next_cursor"]
        if cursor is None:
            return seen, sizes
    raise AssertionError("the cursor never ended")


def test_the_response_has_bookings_and_next_cursor(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 3)
    response = _list(client, api_headers, email=EMAIL)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"bookings", "next_cursor"}
    assert body["next_cursor"] is None
    assert {item["id"] for item in body["bookings"]} == set(ids)


def test_each_item_is_a_normal_booking(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 1)
    item = _list(client, api_headers, email=EMAIL).json()["bookings"][0]
    assert set(item) == {"id", "slot_id", "name", "email", "status", "created_at"}


def test_oldest_booking_comes_first(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 4)
    listed = [item["id"] for item in _list(client, api_headers, email=EMAIL).json()["bookings"]]
    assert listed == ids


def test_the_default_page_size_is_ten(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 12)
    body = _list(client, api_headers, email=EMAIL).json()
    assert len(body["bookings"]) == 10
    assert body["next_cursor"] is not None


def test_paging_through_every_page_returns_each_booking_once(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 25)
    seen, sizes = _walk(client, api_headers, limit=10)
    assert sizes == [10, 10, 5]
    assert seen == ids


def test_an_exact_multiple_ends_with_a_null_cursor_and_no_empty_page(
    client, api_headers, reset_slots
):
    ids = _book_many(client, api_headers, reset_slots, 6)
    seen, sizes = _walk(client, api_headers, limit=3)
    assert sizes == [3, 3]
    assert seen == ids


def test_the_limit_can_be_changed(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 5)
    body = _list(client, api_headers, email=EMAIL, limit=2).json()
    assert len(body["bookings"]) == 2
    assert body["next_cursor"] is not None


def test_a_cursor_that_outlives_a_reset_gives_an_empty_page(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 4)
    first = _list(client, api_headers, email=EMAIL, limit=2).json()
    client.post("/reset", json={"slots": _make_slots(4)}, headers=api_headers)  # clears all
    again = _list(client, api_headers, email=EMAIL, limit=2, cursor=first["next_cursor"])
    assert again.status_code == 200
    assert again.json() == {"bookings": [], "next_cursor": None}
    assert [b["id"] for b in first["bookings"]] == ids[:2]


def test_only_that_persons_bookings_are_listed(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    client.post("/bookings", json=new_booking("s1"), headers=api_headers)
    client.post("/bookings", json=new_booking("s2", email="bola@example.com"), headers=api_headers)
    body = _list(client, api_headers, email="bola@example.com").json()
    assert [item["email"] for item in body["bookings"]] == ["bola@example.com"]


def test_an_unknown_email_gives_an_empty_page(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 2)
    response = _list(client, api_headers, email="nobody@example.com")
    assert response.status_code == 200
    assert response.json() == {"bookings": [], "next_cursor": None}


def test_the_email_is_matched_ignoring_capitals_and_spaces(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 2)
    body = _list(client, api_headers, email="  ADA@Example.COM ").json()
    assert [item["id"] for item in body["bookings"]] == ids


def test_an_email_with_a_plus_sign_works(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 1, email="ada+clinic@example.com")
    body = _list(client, api_headers, email="ada+clinic@example.com").json()
    assert len(body["bookings"]) == 1


def test_cancelled_bookings_are_listed_too(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 2)
    client.delete(f"/bookings/{ids[0]}", headers=api_headers)
    items = _list(client, api_headers, email=EMAIL).json()["bookings"]
    assert {item["id"]: item["status"] for item in items} == {
        ids[0]: "cancelled",
        ids[1]: "confirmed",
    }


def test_the_largest_allowed_limit_works(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 3)
    body = _list(client, api_headers, email=EMAIL, limit=50).json()
    assert len(body["bookings"]) == 3


BAD_QUERIES = {
    "no email": {},
    "blank email": {"email": "   "},
    "limit zero": {"email": EMAIL, "limit": 0},
    "negative limit": {"email": EMAIL, "limit": -1},
    "limit above the maximum": {"email": EMAIL, "limit": 51},
    "limit is text": {"email": EMAIL, "limit": "many"},
    "cursor is nonsense": {"email": EMAIL, "cursor": "not-a-cursor"},
    "cursor is not base64": {"email": EMAIL, "cursor": "!!!"},
}


@pytest.mark.parametrize("params", BAD_QUERIES.values(), ids=BAD_QUERIES.keys())
def test_bad_queries_are_rejected(client, api_headers, params):
    response = _list(client, api_headers, **params)
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)
    assert EMAIL not in response.text
