# Spec: Clinic booking API and booking web page

Derived from: intent.md (accepted 2026-10-31) · Status: accepted (user, 2026-10-31)
Product owner: user (self-approve) · Technical sign-off (if high risk): not required (D5)
Policies applied: assumed baseline (authentication on every endpoint, input validation, no sensitive data in logs, audit events on state changes, accessibility for the web page)
Supporting skills: none
Stack: Java on JDK 25, Spring Boot (version verified in plan.md), PostgreSQL on Neon, Render via Docker (D7-D10)

## Summary
A Spring Boot service exposes the Koya clinic booking contract (slots, bookings, cancel, reset) backed by PostgreSQL, and serves a simple web page from the same service so a patient can see slots, book one and see a confirmation. Safety rules (API key, validation, no double-booking, idempotent retries, rate limiting) are enforced in the API and the database, not the web page. A simulated payment is added afterwards as a separate, optional endpoint that never changes the core contract.

## Functional requirements
Items marked (A) were decided by the user in D12-D15 because the full Koya spec was not available; they are decided but still unverified against the Koya spec.

| ID | Requirement | Acceptance criterion (measurable) |
|----|-------------|-----------------------------------|
| R1 | GET /slots returns every slot with `id, provider, start, end, available`; `available` is false while the slot has a confirmed booking | After booking s1, GET /slots shows s1 `available:false` and others true; response is 200 JSON array |
| R2 | POST /reset accepts either {"slots": [...]} or a bare array [...], replaces all slots with the supplied list and clears all bookings (A, D15) | After reset with N slots, GET /slots returns exactly N, all available, and no old booking id resolves |
| R3 | POST /bookings with `slot_id, name, email` creates a booking with status `confirmed` and a generated unique `id` and `created_at` | Returns 201 with a Booking object matching the schema; the slot then shows `available:false` |
| R4 | GET /bookings/{id} returns the booking | 200 with the Booking for a known id; 404 `{"error":...}` for unknown |
| R5 | Every endpoint requires the `X-API-Key` header | Missing or wrong key returns 401 `{"error":...}` on all six endpoints; correct key proceeds |
| R6 | Bookings with missing, empty, wrongly typed or invalid details are rejected | Missing/blank `slot_id`, `name`, `email` or an invalid email returns 400 and creates nothing; unknown `slot_id` returns 404 |
| R7 | A slot can never have two confirmed bookings, even at the same moment | 50 simultaneous POSTs for one slot produce exactly one 201 and 49 409; GET /slots shows one confirmed booking |
| R8 | DELETE /bookings/{id} cancels a booking, setting status `cancelled` and freeing the slot | 200 with status `cancelled`; slot becomes `available:true` and can be booked again; unknown id returns 404; cancelling twice returns the same cancelled booking (A) |
| R9 | A retried booking request never creates a duplicate (A, D12): with an `Idempotency-Key` header, the same key and body returns the original response (same status and booking id) and the same key with a different body returns 409; without a header, a repeat of the same slot_id + email already confirmed returns the existing booking with the same response | Sending the same request twice (with and without a key) returns the same booking id, and a single row exists |
| R10 | A person can page through their bookings: GET /bookings?email=&page=&limit= (A, D13) | page starts at 1, `limit` default 10, max 100; response `{items, page, limit, total}`; paging through all pages returns every booking once, newest first; missing email returns 400 |
| R11 | Spamming bookings is limited (A, D14): 10 POST /bookings per minute per key+IP, configurable in one value | The 11th request inside a minute returns 429 with `Retry-After` and `{"error":...}`; normal use is unaffected |
| R12 | A web page (design: docs/design/web-reference.jpeg, phone booking flow only) lets a patient pick a day and time from the slots, enter name and email, book, and see the confirmation | In a browser on the deployed URL: day chips and time grid reflect GET /slots, taken slots are disabled and labelled, booking confirmation shows booking id, slot and status; errors (taken slot, invalid email) show a clear message |
| R13 | Extra (first): simulated payment, separate from the core contract. POST /bookings/{id}/payment marks a confirmed booking paid with a fake reference; GET /bookings/{id}/payment returns its state. No real money, no card data | Paying a confirmed booking returns 200 paid; paying a cancelled booking returns 409; the Booking schema returned by core endpoints is unchanged |
| R14 | All error responses use `{"error": "<message>"}` | Every non-2xx response in the test suite parses to an object with a string `error` |

Deferred extras (not in this spec pass, see intent.md out of scope): accounts/login on the web page, in-app notifications, email notifications, the clinic dashboard and insurance row from the reference design (D16).

## Non-functional requirements
| ID | Category | Requirement | Acceptance criterion |
|----|----------|-------------|----------------------|
| N1 | Security | One API key read from an environment variable, compared in constant time, never logged or committed; injected into the web page at runtime (D11) | Repo scan finds no key; wrong key returns 401 in constant-time comparison test |
| N2 | Reliability (concurrency) | Double-booking prevented by a database constraint, not only application checks | A partial unique index on confirmed bookings per slot exists; concurrency test passes against a real Postgres |
| N3 | Reliability (persistence) | Data survives restarts and redeploys | Create a booking, restart the service, GET /bookings/{id} still returns it |
| N4 | Privacy | Names and emails never appear in logs or error messages | Log output from the test run contains none of the test names or emails |
| N5 | Auditability | State changes (booking created, cancelled, paid, reset) write an audit log line with ids and timestamp only | One audit line per state change in tests; lines contain no PII |
| N6 | Performance | Typical request under 500 ms; first request after Render idle sleep succeeds | p95 under 500 ms on a warm instance; cold request returns a valid response within 60 s |
| N7 | Accessibility | Web page usable by keyboard and screen reader | Form fields have labels, visible focus, contrast at least 4.5:1, status messages announced (aria-live) |
| N8 | Robustness | Invalid JSON, oversized bodies and unexpected errors return JSON errors without stack traces | Malformed body returns 400 `{"error":...}`; no stack trace in any response |
| N9 | Operability | A public health check `GET /health` (no key, returns only `{"status":"ok"}`, runs `SELECT 1` so it also wakes the database) for the host and the external keep-alive monitor (D31) | `/health` returns 200 without a key and 503 if the database is unreachable; the monitor pings it every 5 minutes |

## Design
### Components and responsibilities
- **Web layer (Spring MVC):** controllers for slots, bookings and payment; a filter that checks `X-API-Key` and rate limits; a global exception handler that returns `{"error":...}`.
- **Service layer:** booking logic, idempotency handling, cancellation, payment simulation, audit logging.
- **Persistence (Spring Data JDBC or JPA, Flyway migrations):** PostgreSQL on Neon.
- **Web page:** static HTML, CSS and JS served by the same Spring Boot app (same origin, one deploy).
- **Docker image** built for Render; configuration via environment variables.

### Data flow (booking)
1. Request reaches the key filter (401 if wrong) then the rate limiter (429 if over).
2. Controller validates the body (400 on failure).
3. Service checks the idempotency key; a known key returns the stored booking.
4. In one transaction: confirm the slot exists (404), insert the booking with status `confirmed`. The partial unique index rejects a second confirmed booking for the slot, which maps to 409.
5. Store the idempotency record, write an audit line, return 201.

### Interfaces and contracts
| Method and path | Level | Success | Errors |
|---|---|---|---|
| POST /reset | 1 | 200 | 401, 400 |
| GET /slots | 1 | 200 array of SlotWithAvailability | 401 |
| POST /bookings | 1-5 | 201 Booking | 400, 401, 404, 409, 429 |
| GET /bookings?email=&page=&limit= | 4 | 200 `{items,page,limit,total}` (A) | 400, 401 |
| GET /bookings/{id} | 1 | 200 Booking | 401, 404 |
| DELETE /bookings/{id} | 3 | 200 Booking (cancelled) | 401, 404 |
| POST /bookings/{id}/payment (extra) | extra | 200 | 401, 404, 409 |
| GET /bookings/{id}/payment (extra) | extra | 200 | 401, 404 |

### Data model
- `slots(id text pk, provider text, start_at timestamptz, end_at timestamptz)`
- `bookings(id text pk, slot_id text fk, name text, email text, status text check in (confirmed, cancelled), created_at timestamptz)` with a unique index on `slot_id` where `status = 'confirmed'`.
- `idempotency_keys(key text pk, request_hash text, booking_id text, created_at timestamptz)`
- `payments(booking_id text pk fk, status text, reference text, paid_at timestamptz)` for the extra only.

### UI / UX
Visual reference: `docs/design/web-reference.jpeg` (user-supplied; D16). Style taken from it: near-white cards on a light ground, navy text and selected state, amber accent, small uppercase amber eyebrow labels, rounded corners. A rough 3-screen mock is at https://claude.ai/artifact/LP8Vh1yPD14v2i4ggZTEF6 (superseded by the reference where they differ).

Phone-first booking flow (works on wider screens too):
1. **Choose a time:** clinic card (static placeholder text), day chips built from the dates in GET /slots, a grid of time buttons for the chosen day (provider shown on each slot). Slots with `available:false` are disabled and labelled "Taken". The selected slot is highlighted and named on the button: "Confirm booking, Tue 10:30".
2. **Your details:** name and email (the reference has no such fields but the API requires them), inline validation, clear error messages (invalid email, slot just taken).
3. **Confirmation:** booking id, slot, provider, status, a Cancel button, and (extra, R13) "Pay now (demo)".

From the reference, deliberately NOT built in this change (parked as next steps, D16): the clinic dashboard (booked today, reminders sent, reschedule requests, appointment list with Visited / Reminder sent badges) and the Insurance "Verified" row. They need data or features outside the Koya contract (no endpoint lists all bookings, no reminders, no rescheduling, no insurance field).

Accessibility adjustments to the reference: taken times use a visible "Taken" label plus `disabled`, not only pale grey; text and button colours meet 4.5:1 (the white-on-amber button text is darkened or the amber deepened); selected state is shown by more than colour; touch targets at least 44 px.

### Integration with the existing system
Not applicable: greenfield. The only external contract is the Koya spec.

## Policy compliance
| Policy | How the design satisfies it | Status |
|--------|-----------------------------|--------|
| Authentication on every external endpoint | Key filter in front of all routes (R5, N1) | met in design |
| Input validation | Bean validation plus explicit checks (R6) | met in design |
| No sensitive data in logs | N4, audit lines carry ids only | met in design |
| Audit events on state changes | N5 | met in design |
| Accessibility | N7 | met in design |

## Areas of concern
| # | Concern (contradiction, risk or unmet intent) | Policy owner | Resolution | Status |
|---|----|----|----|----|
| C1 | Spec gaps: paging shape, idempotency signal, rate-limit thresholds and response, /reset body were not in the pasted schema | user | Decided with the user in D12-D15. Each lives in one config value or class so it is a one-line change; re-check against the full Koya spec if it becomes available | decided, unverified |
| C2 | Render free tier sleeps after idle (~50 s cold start) and has small memory; a grader request could time out | user | Keep-alive ping of the public /health (D31), lean JVM and Spring settings, small Docker image; verify cold start time before submitting | open |
| C3 | The web page is public but the API needs a key; one key is used everywhere (D11), so it is visible in the page source and anyone who finds it could call /reset and wipe bookings | user | Risk accepted by user. Mitigations: the key is injected into the page at runtime from the environment variable and never committed to Git; the repo and Loom must not show it; rotate it after Koya finishes | accepted risk (D11) |
| C4 | In-memory rate limiting resets on restart and does not share across instances | user | Acceptable on a single Render instance; document the limit | accepted pending confirmation |
| C5 | The payment extra must not alter core responses | user | Separate endpoints and table; Booking schema untouched (R13) | resolved in design |
| C7 | The reference design includes a dashboard, reminders, rescheduling and an insurance row that the Koya contract does not support, and its grey/amber colours risk low contrast | user | Out of scope this change, parked as next steps (D16); contrast fixed in the UI section | resolved in design |
| C6 | POST /reset is destructive and protected only by the key; with one shared key (C3) the web page can reach it | user | Needed by Koya checks; the page itself never calls /reset; accepted with C3 | accepted risk (D11) |

## Open questions carried from intent.md
- [x] Spec gaps (paging, idempotency, rate limit, /reset body) · answered: D12-D15, unverified against the full Koya spec (C1)
- [x] Language, framework, database, host · answered: Java 25, Spring Boot, PostgreSQL on Neon, Render (D8-D10)
- [x] Which extra first · answered: simulated payment (R13)
- [x] Web page visual reference · answered: docs/design/web-reference.jpeg (D16)

## Measurement
- Leading: time from the intent.md commit to the spec.md commit.
- Lagging: commits to spec.md made after plan.md was first committed (requirements rework).
