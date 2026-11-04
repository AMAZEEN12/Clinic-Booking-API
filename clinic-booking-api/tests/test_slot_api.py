import psycopg

from tests.helpers import slot


def test_lists_every_slot_as_available(client, api_headers, reset_slots):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    response = client.get("/slots", headers=api_headers)
    assert response.status_code == 200
    assert response.json() == [
        {**slot("s1"), "available": True},
        {**slot("s2", hour=10), "available": True},
    ]


def test_slots_are_listed_earliest_first(client, api_headers, reset_slots):
    reset_slots([slot("late", hour=11), slot("early", hour=8)])
    ids = [item["id"] for item in client.get("/slots", headers=api_headers).json()]
    assert ids == ["early", "late"]


def test_each_slot_has_exactly_the_documented_fields(client, api_headers, reset_slots):
    reset_slots([slot("s1")])
    item = client.get("/slots", headers=api_headers).json()[0]
    assert set(item) == {"id", "provider", "start", "end", "available"}


def test_no_slots_gives_an_empty_list(client, api_headers, reset_slots):
    reset_slots([])
    response = client.get("/slots", headers=api_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_booked_slot_is_unavailable_until_cancelled(
    client, api_headers, reset_slots, migrated_database
):
    reset_slots([slot("s1"), slot("s2", hour=10)])
    with psycopg.connect(migrated_database) as conn:
        conn.execute(
            "INSERT INTO bookings (id, slot_id, name, email, status) "
            "VALUES ('b1', 's1', 'Ada', 'a@x.com', 'confirmed')"
        )

    available = {i["id"]: i["available"] for i in client.get("/slots", headers=api_headers).json()}
    assert available == {"s1": False, "s2": True}

    with psycopg.connect(migrated_database) as conn:
        conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = 'b1'")

    available = {i["id"]: i["available"] for i in client.get("/slots", headers=api_headers).json()}
    assert available == {"s1": True, "s2": True}
