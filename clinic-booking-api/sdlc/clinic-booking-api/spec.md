# Spec: Clinic booking API and booking web page

Derived from: intent.md (accepted 2026-10-31) · Status: accepted (user, 2026-10-31)
Product owner: user (self-approve) · Technical sign-off (if high risk): not required (D5)
Policies applied: assumed baseline (authentication on every endpoint, input validation, no sensitive data in logs, audit events on state changes, accessibility for the web page)
Supporting skills: none
Stack: Python 3.12+, FastAPI, psycopg 3 (plain SQL), PostgreSQL on Neon, Render (native Python) (D10, D38, D39; replaced the earlier Java stack)

## Summary
A FastAPI service exposes the Koya clinic booking contract (slots, bookings, cancel, reset) backed by PostgreSQL, and serves a simple web page from the same service so a patient can see slots, book one and see a confirmation. Safety rules (API key, validation, no double-booking, idempotent retries, rate limiting) are enforced in the API and the database, not the web page. A simulated payment is added afterwards as a separate, optional endpoint that never changes the core contract.

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
| R12 | A web page, built from the user's ClinicFlow React template (`web/`, D41) in its Emerald look, lets a patient pick a day and time from the slots, enter name and email, book, see the confirmation, look up a booking by its id and cancel it; it works on both a phone and a desktop browser | In a browser on the deployed URL at 390 px and 1280 px wide: day chips and time grid reflect GET /slots, taken slots are disabled and labelled, the confirmation shows booking id, slot and status; lookup and cancel work; no horizontal scrolling; errors (taken slot, invalid email) show a clear message |
| R13 | Extra (first): simulated payment, separate from the core contract. POST /bookings/{id}/payment marks a confirmed booking paid with a fake reference; GET /bookings/{id}/payment returns its state. No real money, no card data | Paying a confirmed booking returns 200 paid; paying a cancelled booking returns 409; the Booking schema returned by core endpoints is unchanged |
| R14 | All error responses use `{"error": "<message>"}` | Every non-2xx response in the test suite parses to an object with a string `error` |
| R15 | Extra: GET /dashboard/summary?date=YYYY-MM-DD returns counts for that day (default today, UTC) (A) | Returns 200 `{date, booked, cancelled, open_slots, total_slots}`; counts match the data after bookings and cancellations; wrong or missing key returns 401; the Koya endpoints are unchanged |
| R16 | Extra: GET /dashboard/appointments?date=YYYY-MM-DD returns that day's appointments, sorted by start time, with masked patient names (D36) | Each item has `booking_id, slot_id, provider, start, end, patient, status, payment`; `patient` is first name plus last initial (Ada O.); no email and no full name appears anywhere in the response |
| R17 | Extra: a desktop dashboard page in the same web app (built from the template's dashboard components, D41) shows summary cards and the appointment list with status badges | At 1280 px: cards Booked, Cancelled, Open slots and a list with Confirmed, Cancelled and Paid (demo) badges; loads its data from the R15 and R16 endpoints |

Deferred extras (not in this spec pass, see intent.md out of scope): accounts/login on the web page, in-app notifications, email notifications, the Insurance row from the reference design, reminders, rescheduling and the Visited / Reminder sent badges (D16, D35).

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
| N10 | Privacy (dashboard) | Dashboard endpoints and page never return or display emails or full patient names (D36) | `tests/test_dashboard_api.py` asserts no `@` and no full name in any dashboard response; `tests/test_log_privacy.py` still passes |

## Design
### Components and responsibilities
- **Web layer (FastAPI):** routers for slots, bookings, payments and the dashboard; a key check and a rate limiter that run before the handlers; exception handlers that return `{"error":...}`.
- **Service layer:** booking logic, idempotency handling, cancellation, payment simulation, audit logging.
- **Persistence (psycopg 3 with a connection pool, plain SQL, forward-only SQL migration files run at startup):** PostgreSQL on Neon.
- **Web page (`web/`):** React 19 + TypeScript + Vite single-page app adapted from the user's ClinicFlow template (D41), hosted separately on Vercel. It calls this API from the browser, so the API allows that origin through CORS (D42).
- **Configuration** comes from environment variables (database URL, API key, allowed web origin); no Docker (D39).

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
| GET /dashboard/summary?date= (extra) | extra | 200 `{date,booked,cancelled,open_slots,total_slots}` (A) | 400, 401 |
| GET /dashboard/appointments?date= (extra) | extra | 200 `{date, items:[...]}` with masked names (A) | 400, 401 |

### Data model
- `slots(id text pk, provider text, start_at timestamptz, end_at timestamptz)`
- `bookings(id text pk, slot_id text fk, name text, email text, status text check in (confirmed, cancelled), created_at timestamptz)` with a unique index on `slot_id` where `status = 'confirmed'`.
- `idempotency_keys(key text pk, request_hash text, booking_id text, created_at timestamptz)`
- `payments(booking_id text pk fk, status text, reference text, paid_at timestamptz)` for the extra only.

### UI / UX
Visual reference: the user's ClinicFlow web template (`web/`, D41), the "Emerald" look: warm paper background, white cards, deep emerald text and buttons, a lime accent (lime only on emerald or with emerald text), rounded corners; its colour pairs are already checked for WCAG AA. The earlier image `docs/design/web-reference.jpeg` and the rough mock are superseded; the flow below stays, restyled by the template. The template's staff login, queue, walk-ins, visit types and live tracking are not built (they need features outside the Koya contract).

**Mobile view (patient booking flow, R12):**
1. **Choose a time:** clinic card (static placeholder text), day chips built from the dates in GET /slots, a grid of time buttons for the chosen day (provider shown on each slot). Slots with `available:false` are disabled and labelled "Taken". The selected slot is highlighted and named on the button: "Confirm booking, Tue 10:30".
2. **Your details:** name and email (the reference has no such fields but the API requires them), inline validation, clear error messages (invalid email, slot just taken).
3. **Confirmation:** booking id, slot, provider, status, a Cancel button, and (extra, R13) "Pay now (demo)".

**Desktop view:** the same booking flow in a centred, wider layout (the time grid and day chips use the extra width; no horizontal scrolling from 390 px up to 1280 px and beyond), plus the clinic dashboard page (R15-R17): three summary cards (Booked, Cancelled, Open slots) and the day's appointment list with Confirmed, Cancelled and Paid (demo) badges and masked patient names. A date picker changes the day.

Deliberately NOT built (D16, D35): the Insurance "Verified" row, reminders sent, reschedule requests, Visited and Reminder sent badges. They need data or features outside the Koya contract.

Accessibility adjustments to the reference: taken times use a visible "Taken" label plus `disabled`, not only pale grey; text and button colours meet 4.5:1 (the white-on-amber button text is darkened or the amber deepened); selected state is shown by more than colour; touch targets at least 44 px; the dashboard list is a real table or list with headings, and status is text, not colour alone.

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
| C2 | Render free tier sleeps after idle (~50 s cold start) and has small memory; a grader request could time out | user | Keep-alive ping of the public /health (D31), small dependency set, small connection pool and a single worker; verify cold start time before submitting | open |
| C3 | The web page is public but the API needs a key; one key is used everywhere (D11), so it is visible in the page's JavaScript (baked in at build time) and anyone who finds it could call /reset and wipe bookings | user | Risk accepted by user. Mitigations: the key is injected into the page at runtime from the environment variable and never committed to Git; the repo and Loom must not show it; rotate it after Koya finishes | accepted risk (D11) |
| C4 | In-memory rate limiting resets on restart and does not share across instances | user | Acceptable on a single Render instance; document the limit | accepted pending confirmation |
| C9 | The page is hosted on a different origin from the API, so the browser needs CORS, including the preflight request that carries the key header (D42) | user | The API allows only the origin set in `CORS_ORIGINS`, answers the preflight before the key check, and exposes `Retry-After` | resolved in design |
| C10 | The template is a large project built for another API (visit types, staff login, queue, reference codes); keeping unused parts adds risk and code the user cannot explain in the Loom | user | Trim to the patient flow and the dashboard, delete the rest, rewire to this contract (D41) | open |
| C5 | The payment extra must not alter core responses | user | Separate endpoints and table; Booking schema untouched (R13) | resolved in design |
| C7 | The reference design includes reminders, rescheduling, a Visited status and an Insurance row that the Koya contract does not support, and its grey/amber colours risk low contrast | user | The dashboard and responsive page are now in scope (D35). Reminders, rescheduling, Visited / Reminder sent and the Insurance row stay out of scope; 'Reminders sent' and 'Reschedule requests' cards become Cancelled and Open slots; contrast fixed in the UI section | resolved in design |
| C8 | A dashboard lists patients, but the API key is public in the page source (D11), so anyone with the key could read dashboard data | user | Masked names only, no emails (D36, R16, N10); dashboard endpoints are read-only and additive | resolved in design |
| C6 | POST /reset is destructive and protected only by the key; with one shared key (C3) the web page can reach it | user | Needed by Koya checks; the page itself never calls /reset; accepted with C3 | accepted risk (D11) |

## Open questions carried from intent.md
- [x] Spec gaps (paging, idempotency, rate limit, /reset body) · answered: D12-D15, unverified against the full Koya spec (C1)
- [x] Language, framework, database, host · answered: Python and FastAPI, PostgreSQL on Neon, Render (D10, D38, D39)
- [x] Which extra first · answered: simulated payment (R13)
- [x] Web page visual reference · answered: the ClinicFlow React template (D41), superseding the image (D16)

## Measurement
- Leading: time from the intent.md commit to the spec.md commit.
- Lagging: commits to spec.md made after plan.md was first committed (requirements rework).