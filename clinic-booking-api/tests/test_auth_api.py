import pytest

PROTECTED = [
    ("POST", "/reset"),
    ("GET", "/slots"),
    ("POST", "/bookings"),
    ("GET", "/bookings"),
    ("GET", "/bookings/abc"),
    ("DELETE", "/bookings/abc"),
    ("GET", "/dashboard/summary"),
    ("GET", "/dashboard/appointments"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_missing_key_is_rejected(client, method, path):
    response = client.request(method, path)
    assert response.status_code == 401
    assert isinstance(response.json()["error"], str)


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_wrong_key_is_rejected(client, method, path):
    response = client.request(method, path, headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert isinstance(response.json()["error"], str)


def test_empty_key_is_rejected(client):
    response = client.get("/slots", headers={"X-API-Key": ""})
    assert response.status_code == 401


def test_correct_key_passes_the_key_check(client, api_headers):
    # Whatever the endpoint answers, it must not be 401 once the key is right.
    response = client.get("/slots", headers=api_headers)
    assert response.status_code != 401
