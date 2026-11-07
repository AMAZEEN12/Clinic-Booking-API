"""Checks a running Clinic Booking API against the Koya spec, level by level.

    python scripts/verify_live.py --url https://YOUR-API.onrender.com --key YOUR_KEY --yes

URL and key can also come from the API_URL and API_KEY environment variables.

WARNING: it calls POST /reset, which deletes every booking and replaces all slots. That is why
--yes is required. At the end it puts the normal demo slots back (scripts/make_slots.py), unless
you pass --no-reseed. Run it BEFORE you submit, never after.

Uses only the Python standard library. Exit code 0 = every check passed, 1 = something failed.
"""

# ruff: noqa
# fmt: off

import argparse
import itertools
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

TIMEOUT = 90  # a sleeping free host can take about a minute to wake up
results: list[tuple[bool, str, str]] = []
BASE = ""
KEY = ""
_client_numbers = itertools.count(1)


def call(method, path, body=None, headers=None, key=True):
    """One request. Returns (status, parsed JSON or None, response headers)."""
    sent = {"Content-Type": "application/json", **(headers or {})}
    # The booking limit is per client IP, and every request here comes from this one machine. So
    # each request claims a different client address (X-Forwarded-For), except in level 5, which
    # pins one address on purpose to test the limit itself.
    if "X-Forwarded-For" not in sent:
        sent["X-Forwarded-For"] = f"2001:db8:1::{next(_client_numbers):x}"
    if key:
        sent["X-API-Key"] = KEY
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=sent)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw, status, response_headers = response.read(), response.status, response.headers
    except urllib.error.HTTPError as error:
        raw, status, response_headers = error.read(), error.code, error.headers
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        parsed = None
    return status, parsed, {k.lower(): v for k, v in response_headers.items()}


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def section(title):
    print(f"\n== {title}")


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def slot(slot_id, days_ahead=30, hour=9, provider="Dr Ade"):
    start = (datetime.now(UTC) + timedelta(days=days_ahead)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return {
        "id": slot_id,
        "provider": provider,
        "start": iso(start),
        "end": iso(start + timedelta(minutes=30)),
    }


def book(slot_id, email, name="Test Patient", key=None, headers=None):
    headers = {**(headers or {}), **({"Idempotency-Key": key} if key else {})}
    return call("POST", "/bookings", {"slot_id": slot_id, "name": name, "email": email}, headers)


def run_together(calls):
    """Run every call at the same moment, each in its own thread. Returns the results."""
    out = [None] * len(calls)
    barrier = threading.Barrier(len(calls))

    def worker(index):
        barrier.wait(timeout=60)
        try:
            out[index] = calls[index]()
        except OSError:  # a dropped connection counts as a failed request, not a crash
            out[index] = (0, None, {})

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(calls))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return out


def run_id():
    return uuid.uuid4().hex[:8]


def level_1_and_auth(tag):
    section("Level 1 + API key")
    status, _, _ = call("GET", "/slots", key=False)
    check("GET /slots without a key is 401", status == 401, f"got {status}")
    status, _, _ = call("GET", "/slots", headers={"X-API-Key": "wrong"}, key=False)
    check("GET /slots with a wrong key is 401", status == 401, f"got {status}")
    status, _, _ = call("POST", "/reset", {"slots": []}, key=False)
    check("POST /reset without a key is 401", status == 401, f"got {status}")

    slots = [
        slot("s1", hour=9),
        slot("s2", hour=10, provider="Dr Bisi"),
        slot("s3", hour=11),
        slot("s4", hour=12),
        slot("s5", hour=13),
        slot("p1", hour=14),
        slot("p2", hour=15),
        slot("p3", hour=16),
        {**slot("old"), "start": "2020-01-01T09:00:00Z", "end": "2020-01-01T09:30:00Z"},
    ]
    status, _, _ = call("POST", "/reset", {"slots": slots})
    check("POST /reset with slots (including a past one) is 200", status == 200, f"got {status}")

    status, body, _ = call("GET", "/slots")
    ids = [item["id"] for item in body or []]
    check("GET /slots lists every slot, earliest first", status == 200 and ids[0] == "old", str(ids))
    check("every slot has 'available'", all("available" in item for item in body or []))
    status, body, _ = call("GET", "/slots?provider=Dr%20Bisi")
    check("GET /slots?provider= filters (exact match)", [i["id"] for i in body or []] == ["s2"])

    status, created, _ = book("s1", f"  Ada.{tag}@Example.COM ", name="  Ada Obi  ")
    check("POST /bookings is 201", status == 201, f"got {status}")
    created = created or {}
    check("status is confirmed", created.get("status") == "confirmed")
    check("email trimmed and lower-cased", created.get("email") == f"ada.{tag}@example.com".lower())
    check("name trimmed", created.get("name") == "Ada Obi")
    status, fetched, _ = call("GET", f"/bookings/{created.get('id')}")
    check("GET /bookings/{id} returns it", status == 200 and fetched == created)
    status, body, _ = call("GET", "/bookings/does-not-exist")
    check("unknown booking is 404 with {'error': ...}", status == 404 and "error" in (body or {}))


def level_2(tag):
    section("Level 2: validation")
    cases = {
        "missing name": {"slot_id": "s2", "email": f"v1.{tag}@example.com"},
        "empty name": {"slot_id": "s2", "name": "  ", "email": f"v2.{tag}@example.com"},
        "missing slot_id": {"name": "A", "email": f"v3.{tag}@example.com"},
        "missing email": {"slot_id": "s2", "name": "A"},
        "invalid email": {"slot_id": "s2", "name": "A", "email": "not-an-email"},
    }
    for label, body in cases.items():
        status, response, _ = call("POST", "/bookings", body)
        check(f"{label} is 400", status == 400 and "error" in (response or {}), f"got {status}")
    status, _, _ = book("no-such-slot", f"v4.{tag}@example.com")
    check("unknown slot is 404", status == 404, f"got {status}")
    status, _, _ = book("old", f"v5.{tag}@example.com")
    check("slot that already started is 400", status == 400, f"got {status}")


def level_3(tag):
    section("Level 3: double booking and cancel")
    status, first, _ = book("s2", f"first.{tag}@example.com")
    check("first booking of s2 is 201", status == 201, f"got {status}")
    status, body, _ = book("s2", f"second.{tag}@example.com")
    check("another person booking s2 is 409", status == 409, f"got {status}")
    status, body, _ = book("s2", f"first.{tag}@example.com")
    check("same person booking s2 again (no key) is 409", status == 409, f"got {status}")

    first = first or {}
    status, cancelled, _ = call("DELETE", f"/bookings/{first.get('id')}")
    check("DELETE cancels (200, status cancelled)", status == 200 and cancelled["status"] == "cancelled")
    _, listing, _ = call("GET", "/slots")
    available = {item["id"]: item["available"] for item in listing or []}
    check("cancelling frees the slot", available.get("s2") is True)
    status, _, _ = call("DELETE", f"/bookings/{first.get('id')}")
    check("cancelling twice is 409", status == 409, f"got {status}")
    status, _, _ = call("DELETE", "/bookings/does-not-exist")
    check("cancelling an unknown booking is 404", status == 404, f"got {status}")
    status, _, _ = book("s2", f"third.{tag}@example.com")
    check("a freed slot can be booked again (201)", status == 201, f"got {status}")

    calls = [(lambda i=i: book("s3", f"race{i}.{tag}@example.com")) for i in range(20)]
    statuses = sorted(result[0] for result in run_together(calls))
    check(
        "20 simultaneous bookings of one slot: exactly one 201, the rest 409",
        statuses.count(201) == 1 and statuses.count(409) == 19,
        f"201 x{statuses.count(201)}, 409 x{statuses.count(409)}",
    )


def level_4(tag):
    section("Level 4: idempotency")
    email = f"idem.{tag}@example.com"
    key = f"key-{uuid.uuid4()}"
    status1, booking1, _ = book("s4", email, key=key)
    status2, booking2, _ = book("s4", email, key=key)
    print(f"      request 1 with key {key[:12]}... -> {status1} id={(booking1 or {}).get('id')}")
    print(f"      request 2 (same key, same body) -> {status2} id={(booking2 or {}).get('id')}")
    check("first request is 201", status1 == 201, f"got {status1}")
    check("same key + same body: same status code", status2 == status1, f"{status1} vs {status2}")
    check("same key + same body: same booking id", booking1 == booking2)
    _, listing, _ = call("GET", f"/bookings?email={email}")
    count = len((listing or {}).get("bookings", []))
    check("no second booking was created", count == 1, f"{count} booking(s) for this email")

    status3, _, _ = book("s4", email, name="Someone Else", key=key)
    print(f"      request 3 (same key, DIFFERENT body) -> {status3}")
    check("same key + different body is 422", status3 == 422, f"got {status3}")

    email2 = f"idem2.{tag}@example.com"
    key2 = f"key-{uuid.uuid4()}"
    calls = [(lambda: book("s5", email2, key=key2)) for _ in range(4)]
    outcomes = run_together(calls)
    ids = {(body or {}).get("id") for _, body, _ in outcomes}
    codes = {status for status, _, _ in outcomes}
    check("4 simultaneous retries with one key: all 201, one booking id", codes == {201} and len(ids) == 1, f"{sorted(codes)}, {len(ids)} id(s)")

    section("Level 4: paging a person's bookings")
    page_email = f"Page.{tag}@Example.com"
    booked = []
    for slot_id in ("p1", "p2", "p3"):
        status, body, _ = book(slot_id, page_email)
        booked.append((body or {}).get("id"))
    status, page1, _ = call("GET", f"/bookings?email={page_email.upper()}&limit=2")
    page1 = page1 or {}
    check("page 1 has 2 bookings, oldest first", [b["id"] for b in page1.get("bookings", [])] == booked[:2])
    check("page 1 has a next_cursor", bool(page1.get("next_cursor")))
    cursor = page1.get("next_cursor") or ""
    status, page2, _ = call("GET", f"/bookings?email={page_email}&limit=2&cursor={cursor}")
    page2 = page2 or {}
    check("page 2 has the last booking", [b["id"] for b in page2.get("bookings", [])] == booked[2:])
    check("last page has next_cursor null", "next_cursor" in page2 and page2["next_cursor"] is None)
    for label, query in {
        "limit 0": f"email={page_email}&limit=0",
        "limit 51": f"email={page_email}&limit=51",
        "no email": "limit=5",
        "garbage cursor": f"email={page_email}&cursor=%21%21%21",
    }.items():
        status, _, _ = call("GET", f"/bookings?{query}")
        check(f"{label} is 400", status == 400, f"got {status}")


def level_5(tag):
    section("Level 5: rate limit (5 attempts per client IP per minute)")
    ip = {"X-Forwarded-For": f"2001:db8:5::{tag[:4]}:{tag[4:]}"}
    other_ip = {"X-Forwarded-For": f"2001:db8:6::{tag[:4]}:{tag[4:]}"}
    statuses = [book("no-such-slot", f"spam{n}.{tag}@example.com", headers=ip)[0] for n in range(5)]
    check("attempts 1-5 from one IP are not limited (failed ones count too)", 429 not in statuses, str(statuses))
    status, body, headers = book("no-such-slot", f"spam.{tag}@example.com", headers=ip)
    check("6th attempt from the same IP is 429, even with a new email", status == 429, f"got {status}")
    retry = headers.get("retry-after", "")
    check("Retry-After is whole seconds", retry.isdigit() and int(retry) >= 1, f"Retry-After: {retry!r}")
    check("429 body is {'error': ...}", "error" in (body or {}))
    status, _, _ = book("no-such-slot", f"spam0.{tag}@example.com", headers=other_ip)
    check("another IP is not affected", status != 429, f"got {status}")
    status, _, _ = call("POST", "/bookings", {"slot_id": "s1", "name": "A", "email": f"spam.{tag}@example.com"}, headers=ip, key=False)
    check("wrong/missing key is still 401 when limited", status == 401, f"got {status}")


def reseed():
    section("Putting the demo slots back")
    script = Path(__file__).with_name("make_slots.py")
    output = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, check=True)
    body = json.loads(output.stdout)
    status, _, _ = call("POST", "/reset", body)
    check(f"re-seeded {len(body['slots'])} slots", status == 200, f"got {status}")


def main():
    global BASE, KEY
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("API_URL", ""))
    parser.add_argument("--key", default=os.environ.get("API_KEY", ""))
    parser.add_argument("--yes", action="store_true", help="I understand this resets the data")
    parser.add_argument("--no-reseed", action="store_true", help="leave the test slots in place")
    args = parser.parse_args()
    if not args.url or not args.key:
        sys.exit("Give --url and --key (or set API_URL and API_KEY).")
    if not args.yes:
        sys.exit("This calls POST /reset and wipes all bookings. Re-run with --yes to confirm.")
    BASE, KEY = args.url.rstrip("/"), args.key

    tag = run_id()
    print(f"Checking {BASE} (run {tag})")
    try:
        status, _, _ = call("GET", "/health", key=False)
    except OSError as error:
        sys.exit(f"Could not reach {BASE}: {error}")
    if status != 200:
        sys.exit(f"/health returned {status}: is the API up?")
    try:
        level_1_and_auth(tag)
        level_2(tag)
        level_3(tag)
        level_4(tag)
        level_5(tag)
    finally:
        if not args.no_reseed:
            try:
                reseed()
            except Exception as error:  # report it, but still show the results
                check("re-seed demo slots", False, type(error).__name__)

    failed = [name for ok, name, _ in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    for name in failed:
        print(f"  FAILED: {name}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
