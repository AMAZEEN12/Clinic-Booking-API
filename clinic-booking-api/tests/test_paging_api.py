import pytest

from tests.helpers import new_booking, slot

EMAIL = "ada@example.com"


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


def test_the_response_has_items_page_limit_and_total(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 3)
    response = _list(client, api_headers, email=EMAIL)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "limit", "total"}
    assert (body["page"], body["limit"], body["total"]) == (1, 10, 3)
    assert {item["id"] for item in body["items"]} == set(ids)


def test_each_item_is_a_normal_booking(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 1)
    item = _list(client, api_headers, email=EMAIL).json()["items"][0]
    assert set(item) == {"id", "slot_id", "name", "email", "status", "created_at"}


def test_newest_booking_comes_first(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 4)
    listed = [item["id"] for item in _list(client, api_headers, email=EMAIL).json()["items"]]
    assert listed == list(reversed(ids))


def test_paging_through_every_page_returns_each_booking_once(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 25)
    seen = []
    sizes = []
    for page in (1, 2, 3):
        body = _list(client, api_headers, email=EMAIL, page=page, limit=10).json()
        assert (body["page"], body["limit"], body["total"]) == (page, 10, 25)
        sizes.append(len(body["items"]))
        seen += [item["id"] for item in body["items"]]
    assert sizes == [10, 10, 5]
    assert seen == list(reversed(ids))


def test_a_page_past_the_end_is_empty_but_keeps_the_total(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 3)
    body = _list(client, api_headers, email=EMAIL, page=5).json()
    assert body["items"] == []
    assert (body["page"], body["total"]) == (5, 3)


def test_the_limit_can_be_changed(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 5)
    body = _list(client, api_headers, email=EMAIL, limit=2, page=3).json()
    assert (body["limit"], len(body["items"]), body["total"]) == (2, 1, 5)


def test_only_that_persons_bookings_are_listed(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    client.post("/bookings", json=new_booking("s1"), headers=api_headers)
    client.post("/bookings", json=new_booking("s2", email="bola@example.com"), headers=api_headers)
    body = _list(client, api_headers, email="bola@example.com").json()
    assert body["total"] == 1
    assert [item["email"] for item in body["items"]] == ["bola@example.com"]


def test_an_unknown_email_gives_an_empty_page(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 2)
    response = _list(client, api_headers, email="nobody@example.com")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "limit": 10, "total": 0}


def test_the_email_is_matched_ignoring_capitals_and_spaces(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 2)
    body = _list(client, api_headers, email="  ADA@Example.COM ").json()
    assert body["total"] == 2


def test_an_email_with_a_plus_sign_works(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 1, email="ada+clinic@example.com")
    body = _list(client, api_headers, email="ada+clinic@example.com").json()
    assert body["total"] == 1


def test_cancelled_bookings_are_listed_too(client, api_headers, reset_slots):
    ids = _book_many(client, api_headers, reset_slots, 2)
    client.delete(f"/bookings/{ids[0]}", headers=api_headers)
    items = _list(client, api_headers, email=EMAIL).json()["items"]
    assert {item["id"]: item["status"] for item in items} == {
        ids[0]: "cancelled",
        ids[1]: "confirmed",
    }


def test_the_largest_allowed_limit_works(client, api_headers, reset_slots):
    _book_many(client, api_headers, reset_slots, 3)
    body = _list(client, api_headers, email=EMAIL, limit=100).json()
    assert body["limit"] == 100


BAD_QUERIES = {
    "no email": {},
    "blank email": {"email": "   "},
    "page zero": {"email": EMAIL, "page": 0},
    "negative page": {"email": EMAIL, "page": -1},
    "page is text": {"email": EMAIL, "page": "abc"},
    "absurdly large page": {"email": EMAIL, "page": 10**30},
    "limit zero": {"email": EMAIL, "limit": 0},
    "limit above the maximum": {"email": EMAIL, "limit": 101},
    "limit is text": {"email": EMAIL, "limit": "many"},
}


@pytest.mark.parametrize("params", BAD_QUERIES.values(), ids=BAD_QUERIES.keys())
def test_bad_queries_are_rejected(client, api_headers, params):
    response = _list(client, api_headers, **params)
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)
    assert EMAIL not in response.text
