from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import ConflictError, install_error_handlers


def test_unknown_path_returns_a_json_error(client, api_headers):
    response = client.get("/no-such-path", headers=api_headers)
    assert response.status_code == 404
    assert isinstance(response.json()["error"], str)
    assert "Traceback" not in response.text


def test_wrong_method_returns_a_json_error(client):
    response = client.post("/health")
    assert response.status_code == 405
    assert isinstance(response.json()["error"], str)


def _small_app() -> FastAPI:
    small = FastAPI()
    install_error_handlers(small)

    @small.get("/conflict")
    def conflict():
        raise ConflictError("slot already booked")

    @small.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail about Ada Obi")

    return small


def test_deliberate_errors_use_their_status_and_message():
    response = TestClient(_small_app()).get("/conflict")
    assert response.status_code == 409
    assert response.json() == {"error": "slot already booked"}


def test_unexpected_errors_hide_all_details():
    test_client = TestClient(_small_app(), raise_server_exceptions=False)
    response = test_client.get("/boom")
    assert response.status_code == 500
    assert response.json() == {"error": "internal server error"}
    assert "Ada" not in response.text
    assert "Traceback" not in response.text
