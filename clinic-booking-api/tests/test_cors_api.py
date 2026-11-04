ORIGIN = "https://clinic-web.example.test"
OTHER = "https://other.example.test"


def test_preflight_is_answered_without_the_key(client):
    response = client.options(
        "/slots",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-api-key",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "x-api-key" in response.headers["access-control-allow-headers"].lower()


def test_allowed_origin_gets_cors_headers_on_real_requests(client):
    response = client.get("/health", headers={"Origin": ORIGIN})
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_cors_headers_are_also_sent_on_a_401(client):
    response = client.get("/slots", headers={"Origin": ORIGIN})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_other_origins_get_no_cors_headers(client):
    response = client.get("/health", headers={"Origin": OTHER})
    assert "access-control-allow-origin" not in response.headers


def test_preflight_from_another_origin_is_refused(client):
    response = client.options(
        "/slots", headers={"Origin": OTHER, "Access-Control-Request-Method": "GET"}
    )
    assert response.status_code == 400
