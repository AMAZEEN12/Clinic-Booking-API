import pytest
from starlette.requests import Request

from app.config import load_settings
from app.ratelimit import SlidingWindowLimiter, client_ip
from tests.conftest import API_KEY
from tests.helpers import new_booking, run_together, slot

LIMIT = 5
ORIGIN = "https://clinic-web.example.test"  # set for every test in tests/__init__.py


class FakeClock:
    """Time that only moves when a test says so, so nothing waits for real seconds."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def limited(client, clock):
    """Swap in a fresh limiter of 5 per minute for one test, then put the old one back."""
    original = client.app.state.rate_limiter
    client.app.state.rate_limiter = SlidingWindowLimiter(LIMIT, clock=clock)
    yield
    client.app.state.rate_limiter = original


def _post(client, api_headers, email="ada@example.com", headers=None, body=None):
    """POST /bookings for a slot that does not exist: cheap, and still counts toward the limit."""
    body = body if body is not None else new_booking(slot_id="no-such-slot", email=email)
    return client.post("/bookings", json=body, headers={**api_headers, **(headers or {})})


def _from_ip(address):
    """Headers that make a request look as if it came from this client address (via the proxy)."""
    return {"X-Forwarded-For": address}


def _use_up_the_limit(client, api_headers, email="ada@example.com", headers=None):
    for _ in range(LIMIT):
        assert _post(client, api_headers, email=email, headers=headers).status_code != 429


# --- The basic rule -----------------------------------------------------------------------


def test_the_sixth_attempt_in_a_minute_is_refused(client, api_headers, limited):
    statuses = [_post(client, api_headers).status_code for _ in range(LIMIT + 1)]
    assert 429 not in statuses[:LIMIT]
    assert statuses[LIMIT] == 429


def test_the_refusal_says_when_to_try_again(client, api_headers, limited, clock):
    _use_up_the_limit(client, api_headers)
    clock.advance(20)
    response = _post(client, api_headers)
    assert response.status_code == 429
    assert response.json() == {"error": "too many requests"}
    assert response.headers["Retry-After"] == "40"  # the oldest attempt leaves the window then


def test_after_waiting_as_told_the_next_attempt_is_allowed(client, api_headers, limited, clock):
    _use_up_the_limit(client, api_headers)
    retry_after = int(_post(client, api_headers).headers["Retry-After"])
    clock.advance(retry_after)
    assert _post(client, api_headers).status_code != 429


def test_refused_attempts_do_not_extend_the_wait(client, api_headers, limited, clock):
    _use_up_the_limit(client, api_headers)
    for _ in range(20):
        assert _post(client, api_headers).status_code == 429
    clock.advance(60)
    assert _post(client, api_headers).status_code != 429


def test_never_more_than_five_in_any_minute(client, api_headers, limited, clock):
    for _ in range(LIMIT):
        assert _post(client, api_headers).status_code != 429
        clock.advance(10)  # five attempts over 50 seconds
    assert _post(client, api_headers).status_code == 429  # still inside the first minute


def test_a_refused_request_does_nothing(client, api_headers, reset_slots, limited):
    reset_slots([slot("s1")])
    _use_up_the_limit(client, api_headers)
    refused = _post(client, api_headers, body=new_booking("s1"))
    assert refused.status_code == 429
    slots = client.get("/slots", headers=api_headers).json()
    assert [item["available"] for item in slots] == [True]


def test_failed_attempts_count_too(client, api_headers, limited):
    body = {"slot_id": "s1", "email": "ada@example.com"}  # missing name: a 400 that names the email
    for _ in range(LIMIT):
        assert _post(client, api_headers, body=body).status_code == 400
    assert _post(client, api_headers).status_code == 429


def test_the_limit_applies_before_validation(client, api_headers, limited):
    _use_up_the_limit(client, api_headers)
    bad = {"slot_id": "s1", "email": "ada@example.com"}  # would be a 400
    assert _post(client, api_headers, body=bad).status_code == 429


def test_simultaneous_attempts_are_counted_exactly(client, api_headers, limited):
    results = run_together([lambda: _post(client, api_headers)] * 20)
    statuses = [response.status_code for response in results]
    assert statuses.count(429) == 20 - LIMIT


# --- Who and what is limited -----------------------------------------------------------


def test_each_ip_address_has_its_own_limit(client, api_headers, limited):
    _use_up_the_limit(client, api_headers, headers=_from_ip("203.0.113.10"))
    assert _post(client, api_headers, headers=_from_ip("203.0.113.10")).status_code == 429
    assert _post(client, api_headers, headers=_from_ip("203.0.113.11")).status_code != 429


def test_changing_the_email_does_not_avoid_the_limit(client, api_headers, limited):
    _use_up_the_limit(client, api_headers, email="ada@example.com")
    for email in ("bola@example.com", "chidi@example.com", "  ADA@Example.COM "):
        assert _post(client, api_headers, email=email).status_code == 429


def test_the_limit_is_shared_by_every_email_from_one_ip(client, api_headers, limited):
    for number in range(LIMIT):
        email = f"person{number}@example.com"
        assert _post(client, api_headers, email=email).status_code != 429
    assert _post(client, api_headers, email="another@example.com").status_code == 429


def test_the_original_client_in_x_forwarded_for_is_the_one_limited(client, api_headers, limited):
    chain = _from_ip("203.0.113.20, 10.0.0.1, 10.0.0.2")  # client, then the proxies it went through
    _use_up_the_limit(client, api_headers, headers=chain)
    assert _post(client, api_headers, headers=chain).status_code == 429
    # A different client behind the same proxy is not affected.
    assert _post(client, api_headers, headers=_from_ip("203.0.113.21, 10.0.0.1")).status_code != 429


def test_the_same_address_written_differently_is_one_client(client, api_headers, limited):
    _use_up_the_limit(client, api_headers, headers=_from_ip("2001:db8:0:0:0:0:0:1"))
    assert _post(client, api_headers, headers=_from_ip("2001:DB8::1")).status_code == 429


def test_a_body_without_an_email_still_counts(client, api_headers, limited):
    for _ in range(LIMIT):
        assert _post(client, api_headers, body={}).status_code == 400
    assert _post(client, api_headers).status_code == 429


def test_an_unreadable_body_still_counts(client, api_headers, limited):
    for _ in range(LIMIT):
        response = client.post(
            "/bookings", content=b"not json", headers={**api_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 400
    assert _post(client, api_headers).status_code == 429


def test_a_wrong_key_is_refused_before_it_is_counted(client, api_headers, limited):
    bad = {"X-API-Key": "wrong-key"}
    for _ in range(LIMIT * 2):
        response = client.post("/bookings", json=new_booking("s1"), headers=bad)
        assert response.status_code == 401
    _use_up_the_limit(client, api_headers)


def test_a_wrong_key_stays_401_when_the_limit_is_used_up(client, api_headers, limited):
    _use_up_the_limit(client, api_headers)
    bad = client.post("/bookings", json=new_booking("s1"), headers={"X-API-Key": "wrong-key"})
    assert bad.status_code == 401


def test_only_creating_a_booking_is_limited(client, api_headers, limited):
    _use_up_the_limit(client, api_headers)
    assert _post(client, api_headers).status_code == 429
    assert client.get("/health").status_code == 200
    assert client.get("/slots", headers=api_headers).status_code == 200
    listing = client.get("/bookings", params={"email": "ada@example.com"}, headers=api_headers)
    assert listing.status_code == 200
    assert client.get("/bookings/none", headers=api_headers).status_code == 404
    assert client.delete("/bookings/none", headers=api_headers).status_code == 404


def test_a_reset_clears_the_counts(client, api_headers, reset_slots, limited):
    _use_up_the_limit(client, api_headers)
    assert _post(client, api_headers).status_code == 429
    reset_slots([slot("s1")])
    assert _post(client, api_headers).status_code != 429


def test_the_refusal_can_be_read_by_the_web_page(client, api_headers, limited):
    _use_up_the_limit(client, api_headers)
    response = _post(client, api_headers, headers={"Origin": ORIGIN})
    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "Retry-After" in response.headers["access-control-expose-headers"]


# --- The limiter on its own, and its setting ----------------------------------------------


def _request(forwarded=None, peer="192.0.2.50"):
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded is not None else []
    return Request({"type": "http", "headers": headers, "client": (peer, 5000)})


def test_the_client_is_the_first_forwarded_address():
    assert client_ip(_request("203.0.113.5, 10.1.1.1")) == "203.0.113.5"
    assert client_ip(_request("  203.0.113.5  ")) == "203.0.113.5"


def test_with_no_forwarded_header_the_direct_address_is_used():
    assert client_ip(_request()) == "192.0.2.50"


@pytest.mark.parametrize("junk", ["", "unknown", "not-an-ip", "999.1.1.1", ",203.0.113.5"])
def test_a_forwarded_value_that_is_not_an_ip_is_ignored(junk):
    assert client_ip(_request(junk)) == "192.0.2.50"


def test_idle_addresses_are_forgotten():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(LIMIT, clock=clock)
    for number in range(2000):
        limiter.check(f"client-{number}")
    assert limiter.tracked_clients() == 2000
    clock.advance(120)  # nobody has a recent attempt
    limiter.check("someone-new")
    assert limiter.tracked_clients() < 10


@pytest.fixture
def required_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setenv("API_KEY", API_KEY)


def test_the_limit_is_five_a_minute_unless_changed(required_settings, monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    assert load_settings().rate_limit_per_minute == 5
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "25")
    assert load_settings().rate_limit_per_minute == 25


@pytest.mark.parametrize("bad", ["0", "-3", "ten", "2.5"])
def test_a_bad_limit_setting_stops_the_app_starting(required_settings, monkeypatch, bad):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", bad)
    with pytest.raises(RuntimeError, match="RATE_LIMIT_PER_MINUTE"):
        load_settings()