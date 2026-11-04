"""The public health check (N9, D31): no key, tiny answer, 503 when the database is down."""

import logging

import psycopg
import pytest

from app import db


class _BrokenPool:
    """Stands in for the connection pool when the database cannot be reached."""

    def __init__(self, error: Exception):
        self._error = error

    def connection(self, timeout=None):
        raise self._error


def test_health_answers_without_a_key(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ignores_a_wrong_key_because_it_is_public(client):
    response = client.get("/health", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_answers_a_head_request_for_monitors_that_use_it(client):
    assert client.head("/health").status_code == 200


def test_health_returns_only_the_status(client):
    assert set(client.get("/health").json()) == {"status"}


def test_health_really_talks_to_the_database(client, monkeypatch):
    """The ping must run a query, so it also keeps the Neon database awake."""
    queries = []

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def execute(self, query):
            queries.append(query)

    class _Pool:
        def connection(self, timeout=None):
            return _Connection()

    monkeypatch.setattr(db, "get_pool", lambda: _Pool())

    assert client.get("/health").status_code == 200
    assert queries == ["SELECT 1"]


@pytest.mark.parametrize(
    "error",
    [
        psycopg.OperationalError("could not connect to server"),
        psycopg.errors.AdminShutdown("terminating connection"),
        RuntimeError("Database pool is not initialised"),
    ],
    ids=["unreachable", "shutting down", "no pool"],
)
def test_health_returns_503_when_the_database_is_down(client, monkeypatch, error):
    monkeypatch.setattr(db, "get_pool", lambda: _BrokenPool(error))

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"error": "database unavailable"}


def test_a_database_failure_does_not_leak_details_into_the_answer_or_the_log(
    client, monkeypatch, caplog
):
    secret = "password=hunter2 host=secret-db.internal"
    monkeypatch.setattr(db, "get_pool", lambda: _BrokenPool(psycopg.OperationalError(secret)))

    with caplog.at_level(logging.WARNING, logger="app.health"):
        response = client.get("/health")

    assert response.status_code == 503
    assert "hunter2" not in response.text
    assert "secret-db" not in response.text
    assert "hunter2" not in caplog.text
    assert "secret-db" not in caplog.text
    assert "OperationalError" in caplog.text


def test_health_recovers_once_the_database_is_back(client):
    down = _BrokenPool(psycopg.OperationalError("could not connect"))
    with pytest.MonkeyPatch.context() as broken:
        broken.setattr(db, "get_pool", lambda: down)
        assert client.get("/health").status_code == 503

    assert client.get("/health").status_code == 200
