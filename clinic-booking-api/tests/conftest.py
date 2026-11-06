import os
from collections.abc import Callable, Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.ratelimit import SlidingWindowLimiter
from app.services.auth import PATIENT_EMAIL, STAFF_EMAIL
from tests.guard import GuardError, check_test_database

API_KEY = "test-key-not-a-secret"
AUTH_SECRET = "test-auth-secret-not-a-secret-0123456789"
STAFF_PASSWORD = "staff-test-password"
PATIENT_PASSWORD = "patient-test-password"


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
        patch.setenv("AUTH_SECRET", AUTH_SECRET)
        patch.setenv("STAFF_PASSWORD", STAFF_PASSWORD)
        patch.setenv("PATIENT_PASSWORD", PATIENT_PASSWORD)
        with TestClient(app) as test_client:
            # The shared run signs in often; the login-limit tests swap in their own limiter.
            test_client.app.state.login_limiter = SlidingWindowLimiter(100_000)
            yield test_client


@pytest.fixture(scope="session")
def api_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def _sign_in(client: TestClient, api_headers: dict[str, str], email: str, password: str) -> dict:
    response = client.post(
        "/auth/login", json={"email": email, "password": password}, headers=api_headers
    )
    assert response.status_code == 200
    return {**api_headers, "Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture(scope="session")
def staff_headers(client: TestClient, api_headers: dict[str, str]) -> dict[str, str]:
    """API key plus a signed-in staff member's token (for the dashboard)."""
    return _sign_in(client, api_headers, STAFF_EMAIL, STAFF_PASSWORD)


@pytest.fixture(scope="session")
def patient_headers(client: TestClient, api_headers: dict[str, str]) -> dict[str, str]:
    """API key plus a signed-in patient's token."""
    return _sign_in(client, api_headers, PATIENT_EMAIL, PATIENT_PASSWORD)


@pytest.fixture
def reset_slots(client: TestClient, api_headers: dict[str, str]) -> Callable[[list[dict]], None]:
    """Replace all slots through the API (this also clears every booking)."""

    def _reset(slots: list[dict]) -> None:
        response = client.post("/reset", json={"slots": slots}, headers=api_headers)
        assert response.status_code == 200

    return _reset
