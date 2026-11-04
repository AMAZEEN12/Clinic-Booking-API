import pytest

from app.config import load_settings
from app.ratelimit import TokenBucketLimiter
from tests.conftest import API_KEY
from tests.helpers import new_booking, run_together, slot

LIMIT = 10
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
    """Swap in a fresh limiter of 10 per minute for one test, then put the old one back."""
    original = client.app.state.rate_limiter
    client.app.state.rate_limiter = TokenBucketLimiter(LIMIT, clock=clock)
    yield
    client.app.state.rate_limiter = original


def _post(client, api_headers, ip=None, headers=None, body=None):
    """POST /bookings for a slot that does not exist: cheap, and still counts toward the limit."""
    sent = {**api_headers, **(headers or {})}
    if ip is not None:
        sent["X-Forwarded-For"] = ip
    body = body if body is not None else new_booking(slot_id="no-such-slot")
    return client.post("/bookings", json=body, headers=sent)


def _use_up_the_limit(client, api_headers, ip=None):
    for _ in range(LIMIT):
        assert _post(client, api_headers, ip=ip).status_code != 429


# --- The basic rule -----------------------------------------------------------------------


def test_the_eleventh_request_in_a_minute_is_refused(client, api_headers, limited):
    statuses = [_post(client, api_headers).status_code for _ in range(LIMIT + 1)]
    assert 429 not in statuses[:LIMIT]
    assert statuses[LIMIT] == 429


def test_the_refusal_says_when_to_try_again(client, api_headers, limited):
    _use_up_the_limit(client, api_headers)
    response = _post(client, api_headers)
    assert response.status_code == 429
    assert response.json() == {"error": "too many requests"}
    assert response.headers["Retry-After"] == "6"  # one request is earned back every 6 seconds


def test_after_waiting_as_told_the_next_request_is_allowed(client, api_headers, limited, clock):
    _use_up_the_limit(client, api_headers)
    retry_after = int(_post(client, api_headers).headers["Retry-After"])
    clock.advance(retry_after)
    assert _post(client, api_headers).status_code != 429
    assert _post(client, api_headers).status_code == 429  # only one request was earned back


def test_a_full_minute_of_quiet_restores_the_whole_limit(client, api_headers, limited, clock):
    _use_up_the_limit(client, api_headers)
    clock.advance(60)
    _use_up_the_limit(client, api_headers)
    assert _post(client, api_headers).status_code == 429


def test_steady_normal_use_is_never_limited(client, api_headers, limited, clock):
    for _ in range(40):
        assert _post(client, api_headers).status_code != 429
        clock.advance(7)  # about 8 a minute, under the limit


def test_a_refused_request_does_nothing(client, api_headers, reset_slots, limited):
    reset_slots([slot("s1")])
    _use_up_the_limit(client, api_headers)
    refused = _post(client, api_headers, body=new_booking("s1"))
    assert refused.status_code == 429
    slots = client.get("/slots", headers=api_headers).json()
    assert [item["available"] for item in slots] == [True]


def test_invalid_requests_count_too(client, api_headers, limited):
    for _ in range(LIMIT):
        assert _post(client, api_headers, body={"slot_id": "s1"}).status_code == 400
    assert _post(client, api_headers, body={"slot_id": "s1"}).status_code == 429


def test_simultaneous_requests_are_counted_exactly(client, api_headers, limited):
    results = run_together([lambda: _post(client, api_headers)] * 30)
    statuses = [response.status_code for response in results]
    assert statuses.count(429) == 30 - LIMIT


# --- Who and what is limited -----------------------------------------------------------


def test_each_client_address_has_its_own_limit(client, api_headers, limited):
    _use_up_the_limit(client, api_headers, ip="203.0.113.7")
    assert _post(client, api_headers, ip="203.0.113.7").status_code == 429
    assert _post(client, api_headers, ip="198.51.100.9").status_code != 429


def test_the_first_forwarded_address_is_the_client(client, api_headers, limited):
    _use_up_the_limit(client, api_headers, ip="203.0.113.7, 10.0.0.1")
    assert _post(client, api_headers, ip="203.0.113.7, 10.0.0.2").status_code == 429


def test_a_wrong_key_is_refused_before_it_is_counted(client, api_headers, limited):
    bad = {"X-API-Key": "wrong-key"}
    for _ in range(LIMIT * 2):
        response = client.post("/bookings", json=new_booking("s1"), headers=bad)
        assert response.status_code == 401
    # The wrong-key attempts used up nothing, so the real key still has its full allowance.
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


def test_the_refusal_can_be_read_by_the_web_page(client, api_headers, limited):
    _use_up_the_limit(client, api_headers)
    response = _post(client, api_headers, headers={"Origin": ORIGIN})
    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "Retry-After" in response.headers["access-control-expose-headers"]


# --- The limiter on its own, and its setting ----------------------------------------------


def test_idle_clients_are_forgotten():
    clock = FakeClock()
    limiter = TokenBucketLimiter(LIMIT, clock=clock)
    for number in range(2000):
        limiter.check(f"client-{number}")
    assert limiter.tracked_clients() == 2000
    clock.advance(120)  # everyone has earned their full allowance back
    limiter.check("someone-new")
    assert limiter.tracked_clients() < 10


@pytest.fixture
def required_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setenv("API_KEY", API_KEY)


def test_the_limit_is_ten_a_minute_unless_changed(required_settings, monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_PER_MINUTE", raising=False)
    assert load_settings().rate_limit_per_minute == 10
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "25")
    assert load_settings().rate_limit_per_minute == 25


@pytest.mark.parametrize("bad", ["0", "-3", "ten", "2.5"])
def test_a_bad_limit_setting_stops_the_app_starting(required_settings, monkeypatch, bad):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", bad)
    with pytest.raises(RuntimeError, match="RATE_LIMIT_PER_MINUTE"):
        load_settings()
