import os
from collections.abc import Callable, Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from tests.guard import GuardError, check_test_database

API_KEY = "test-key-not-a-secret"


@pytest.fixture(scope="session")
def database_url() -> str:
    """The test database URL, after the production-safety guard (D19)."""
    try:
        return check_test_database(
            os.environ.get("TEST_DATABASE_URL"), os.environ.get("DATABASE_URL")
        )
    except GuardError as error:
        pytest.exit(str(error), returncode=2)


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    """The test database with every migration applied."""
    db.run_migrations(database_url)
    return database_url


@pytest.fixture
def clean_db(migrated_database: str) -> str:
    """The migrated test database with all data removed, for tests that need a clean start."""
    with psycopg.connect(migrated_database) as conn:
        conn.execute("TRUNCATE slots, bookings, idempotency_keys, payments CASCADE")
    return migrated_database


@pytest.fixture(scope="session")
def client(migrated_database: str) -> Iterator[TestClient]:
    """The app running against the test database (one shared instance for the whole run)."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", migrated_database)
        patch.setenv("API_KEY", API_KEY)
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture(scope="session")
def api_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


@pytest.fixture
def reset_slots(client: TestClient, api_headers: dict[str, str]) -> Callable[[list[dict]], None]:
    """Replace all slots through the API (this also clears every booking)."""

    def _reset(slots: list[dict]) -> None:
        response = client.post("/reset", json={"slots": slots}, headers=api_headers)
        assert response.status_code == 200

    return _reset
