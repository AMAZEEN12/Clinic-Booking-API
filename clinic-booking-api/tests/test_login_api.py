"""Login (extra): the two seeded accounts, signed tokens, and the staff/patient split."""

import time

import psycopg
import pytest

from app.auth import hash_password, issue_token, read_token, verify_password
from app.ratelimit import SlidingWindowLimiter
from app.services.auth import PATIENT_EMAIL, STAFF_EMAIL
from tests.conftest import AUTH_SECRET, PATIENT_PASSWORD, STAFF_PASSWORD


def _login(client, api_headers, email, password):
    return client.post(
        "/auth/login", json={"email": email, "password": password}, headers=api_headers
    )


# --- the endpoint -------------------------------------------------------------------------------


def test_staff_can_sign_in(client, api_headers):
    response = _login(client, api_headers, STAFF_EMAIL, STAFF_PASSWORD)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"token", "role", "name", "expires_at"}
    assert body["role"] == "staff"
    assert body["token"]


def test_a_patient_can_sign_in(client, api_headers):
    response = _login(client, api_headers, PATIENT_EMAIL, PATIENT_PASSWORD)
    assert response.status_code == 200
    assert response.json()["role"] == "patient"


def test_the_email_is_not_case_sensitive(client, api_headers):
    response = _login(client, api_headers, f"  {STAFF_EMAIL.upper()} ", STAFF_PASSWORD)
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (STAFF_EMAIL, "wrong"),
        (STAFF_EMAIL, PATIENT_PASSWORD),
        ("nobody@beeclinic.test", STAFF_PASSWORD),
    ],
)
def test_a_wrong_login_is_a_401_with_one_message(client, api_headers, email, password):
    response = _login(client, api_headers, email, password)
    assert response.status_code == 401
    assert response.json() == {"error": "wrong email or password"}


def test_an_empty_email_is_a_400(client, api_headers):
    assert _login(client, api_headers, "", "x").status_code == 400


def test_login_needs_the_api_key(client):
    response = client.post("/auth/login", json={"email": STAFF_EMAIL, "password": STAFF_PASSWORD})
    assert response.status_code == 401
    assert response.json() == {"error": "missing or invalid API key"}


def test_login_is_rate_limited_per_client(client, api_headers):
    original = client.app.state.login_limiter
    client.app.state.login_limiter = SlidingWindowLimiter(3)
    try:
        for _ in range(3):
            assert _login(client, api_headers, STAFF_EMAIL, "wrong").status_code == 401
        blocked = _login(client, api_headers, STAFF_EMAIL, STAFF_PASSWORD)
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) >= 1
    finally:
        client.app.state.login_limiter = original


def test_a_signed_in_patient_can_still_book(client, patient_headers, reset_slots):
    reset_slots(
        [
            {
                "id": "s1",
                "provider": "Dr Ade",
                "start": "2099-12-10T09:00:00Z",
                "end": "2099-12-10T09:30:00Z",
            }
        ]
    )
    response = client.post(
        "/bookings",
        json={"slot_id": "s1", "name": "Ada Obi", "email": "ada@example.com"},
        headers=patient_headers,
    )
    assert response.status_code == 201


def test_passwords_are_stored_only_as_hashes(migrated_database, client):
    with psycopg.connect(migrated_database) as conn:
        hashes = [row[0] for row in conn.execute("SELECT password_hash FROM users")]
    assert hashes
    for stored in hashes:
        assert stored.startswith("scrypt$")
        assert STAFF_PASSWORD not in stored
        assert PATIENT_PASSWORD not in stored


# --- passwords and tokens (no database needed) --------------------------------------------------


def test_a_password_hash_checks_out_only_for_the_right_password():
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong horse", stored)
    assert hash_password("correct horse") != stored  # a fresh salt each time


@pytest.mark.parametrize("stored", ["", "nonsense", "scrypt$1$2", "md5$a$b$c$d$e"])
def test_a_malformed_hash_is_a_failed_check_not_an_error(stored):
    assert verify_password("anything", stored) is False


def test_a_token_carries_the_role():
    token, _ = issue_token(AUTH_SECRET, "user_staff", "staff")
    claims = read_token(AUTH_SECRET, token)
    assert claims is not None
    assert (claims["sub"], claims["role"]) == ("user_staff", "staff")


def test_a_token_signed_with_another_secret_is_refused():
    token, _ = issue_token("some-other-secret-that-is-long-enough!!", "user_staff", "staff")
    assert read_token(AUTH_SECRET, token) is None


def test_a_changed_payload_is_refused():
    token, _ = issue_token(AUTH_SECRET, "user_patient", "patient")
    _, signature = token.split(".")
    forged_token, _ = issue_token(AUTH_SECRET, "user_patient", "staff")
    forged_payload, _ = forged_token.split(".")
    assert read_token(AUTH_SECRET, f"{forged_payload}.{signature}") is None


def test_an_expired_token_is_refused():
    token, expires = issue_token(AUTH_SECRET, "user_staff", "staff", now=time.time() - 10**6)
    assert expires < time.time()
    assert read_token(AUTH_SECRET, token) is None
