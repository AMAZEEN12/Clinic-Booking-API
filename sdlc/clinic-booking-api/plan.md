# Plan: Clinic booking API and booking web page

Derived from: intent.md (2026-10-31), spec.md (2026-10-31) · Status: accepted
Accepted by: user, 2026-10-31 · Amended 2026-11-01 for the switch from Java to Python (D38, D39) · Higher-risk sign-off: not required (D5)
Supporting skills: none
Stack (D38, D39): Python 3.12+, FastAPI (synchronous endpoints), psycopg 3 with a connection pool and plain SQL, SQL migration files with a small runner, PostgreSQL on Neon, pytest, Ruff, Render (native Python, no Docker). Repo state: greenfield with a Python scaffold (requirements, pyproject, empty `app/` package).

Source paths below are under `app/` unless they start with `tests/`, `migrations/` or are at the repo root.

## Files that change
| File | New / modified / deleted | Requirements covered |
|------|--------------------------|----------------------|
| `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` (Ruff and pytest settings) | new | all (build) |
| `.gitignore` | new | N1 (no secrets committed) |
| `main.py` (app, middleware wiring, static files, startup migrations) | new | all |
| `config.py` (settings read from environment: API key, database URL, limits) | new | R10, R11, N1 |
| `db.py` (connection pool, migration runner) | new | R7, N2, N3 |
| `migrations/V1__schema.sql` (slots, bookings + partial unique index, idempotency_keys, payments) | new | R7, N2, N3 |
| `security.py` (API key check, constant-time compare; `/health`, `/config.js` and static files exempt) | new | R5, N1 |
| `ratelimit.py` (in-memory window per key + IP, limits from config) | new | R11 |
| `errors.py` (exception types and handlers that return `{"error": ...}`) | new | R6, R14, N8 |
| `schemas.py` (Pydantic models: Slot, SlotWithAvailability, NewBooking, Booking, ResetRequest, PageResponse, Payment, DashboardSummary, DashboardAppointment) | new | R1-R4, R10, R13, R15, R16 |
| `routers/slots.py`, `routers/reset.py` | new | R1, R2 |
| `routers/bookings.py` | new | R3, R4, R6, R8, R9, R10 |
| `routers/payments.py` | new | R13 |
| `routers/dashboard.py` (read-only, masked names) | new | R15, R16, N10 (D35, D36) |
| `routers/health.py` (`GET /health`, `/config.js` with the key from env) | new | R12, N9, D11 |
| `services/slots.py`, `services/bookings.py`, `services/payments.py`, `services/dashboard.py`, `audit.py` | new | R2-R4, R7-R10, R13, R15, R16, N5 |
| `repositories/slots.py`, `repositories/bookings.py`, `repositories/idempotency.py`, `repositories/payments.py`, `repositories/dashboard.py` (SQL only) | new | R1-R4, R7-R10, R13, R15, R16 |
| `static/index.html`, `static/app.css`, `static/app.js` (responsive from phone to desktop; design: docs/design/web-reference.jpeg) | new | R12, N7 |
| `static/dashboard.html`, `static/dashboard.js` | new | R17 |
| `tests/conftest.py` (database fixtures and the guard from D19) | new | N2, N3 |
| `tests/test_*_api.py`, `tests/test_log_privacy.py` (see Proof) | new | R1-R16, N1-N10 |
| `tests/test_web_page_browser.py`, `tests/test_dashboard_page_browser.py` (pytest-playwright) | new | R12, R17, N7 (D24) |
| `.github/workflows/ci.yml` (install, lint, test on every push; test DB from encrypted secret) | new | feedback loop (D22) |
| `render.yaml` (native Python service, `autoDeploy: false`, single worker), `README.md` | new | N3, N6, N9, C2 |
| `AGENTS.md`, `REVIEW.md` | modified / new | repo policy |

## Order of work
1. Scaffold project (requirements, pyproject, `app/` package, .gitignore); install, import and lint pass. (foundation)
2. Migration V1, migration runner and `tests/conftest.py` with the safety guard: tests refuse to run unless `TEST_DATABASE_URL` is set and differs from `DATABASE_URL`. (covers R7, N2, N3)
3. Error model, key check, global exception handlers, `/health`. (covers R5, R14, N1, N8, N9)
4. Slots list and `/reset` (accepts `{"slots":[...]}` or a bare array). (covers R1, R2)
5. Create and get booking with validation. (covers R3, R4, R6)
6. Double-booking guard: unique violation maps to 409; concurrency test with 50 simultaneous requests. (covers R7, N2)
7. Cancel booking; cancelled slot can be rebooked. (covers R8)
8. Idempotency: header key (advisory lock per key) plus natural dedupe on slot+email. (covers R9)
9. Paging by email. (covers R10)
10. Rate limiter on POST /bookings (in-memory window per key+IP, limits from config). (covers R11)
11. Audit lines and log-privacy test. (covers N4, N5)
12. Web page following the reference, responsive from phone to desktop, plus `/config.js`. (covers R12, N7)
13. Checkpoint: Levels 1-5 green end to end. Only then start extras (D6).
14. Simulated payment endpoints and "Pay now (demo)" button. (covers R13)
15. Desktop dashboard extra: summary and appointments endpoints with masked names, `dashboard.html`, responsive checks at 390 px and 1280 px. (covers R15, R16, R17, N10)
16. `render.yaml`, README; deploy; keep-alive ping of /health; measure cold start; run all checks against the live URL. (covers N3, N6, N9, C2)

## Parallelization
- Independent (separate workspaces/branches, different files): web page (step 12, needs only the contract from steps 4-5), dashboard.html (step 15 front end, needs only the endpoint contract), `render.yaml` + README (step 16 files), `ratelimit.py` + its test (step 10).
- Sequential (share `services/bookings.py`, `repositories/bookings.py`, `routers/bookings.py`): steps 5 → 6 → 7 → 8 → 9 → 14 → 15 (the dashboard reads bookings and payment state, so it comes after the payment extra). Steps 1 → 2 → 3 → 4 also run in order.

## Risks
| Risk | What it could break | Mitigation |
|------|---------------------|------------|
| Concurrent bookings for one slot | double-booking (R7) | Partial unique index on confirmed bookings per slot; handle the unique violation as 409; 50-way concurrency test on real Postgres |
| Same Idempotency-Key sent twice at the same instant | duplicate booking or a 500 (R9) | `pg_advisory_xact_lock(hashtext(key))` inside the transaction, then look up the stored response |
| Same slot+email retried while another person books the slot | wrong person gets the booking | Natural dedupe returns the existing booking only when its email matches; otherwise 409 |
| Tests wipe production data | lost bookings | Guard in `tests/conftest.py` (D19); separate Neon branch; secrets never committed |
| Render cold start and Neon compute sleep | first grader request times out (C2, N6) | Keep-alive ping of the public /health (it also runs `SELECT 1`), small dependency set, small connection pool (max 5), measure cold start before submitting |
| In-memory rate limiter breaks if more than one worker process runs | spam limit not enforced (R11, C4) | Run uvicorn with exactly one worker (set in `render.yaml`); document it in AGENTS.md |
| `/config.js` exposes the key to anyone (D11) | key leaks; `/reset` reachable | Accepted risk; key from env only, never in Git or Loom, rotate after Koya finishes |
| Dashboard leaks patient details through the public key (D11) | privacy breach (N4, N10) | Masked names only, never emails; `tests/test_dashboard_api.py` asserts no `@` and no full name in responses |
| Library API drift (FastAPI, Pydantic v2, psycopg 3) from older tutorials | wasted time on removed or renamed APIs | Check current docs; pin versions with `pip freeze` after the first successful install |
| Riskiest step: step 8 (idempotency) | retries, the unique index and concurrency interact; the Koya check is unknown (C1) | Isolate the logic in one service; keep the header name and replay behaviour in one place |

## Alternatives considered
- Java and Spring Boot: replaced by Python and FastAPI (D38): faster to build in the one-week window, matches the programme, lighter to start on Render.
- ORM (SQLAlchemy): rejected because plain SQL gives exact control of locks and constraint errors (D39).
- Async endpoints with an async driver: rejected for now; synchronous endpoints with a connection pool keep transactions simple.
- Application-level locking (in-process locks, in-memory sets): rejected because it breaks across restarts or more than one instance; the database must be the guard.
- Row lock `SELECT ... FOR UPDATE` as the only guard: rejected as the sole mechanism; the unique index is simpler and always enforced, and cancelled rows stay out of it.
- SQLite or in-memory databases for tests: rejected by the user in favour of a Neon test branch (D19).
- Redis or a rate-limit library: rejected as extra infrastructure or dependency for a single worker.
- Separate frontend (React) hosted elsewhere: rejected; static page in the same service avoids CORS and a second deploy.

## Proof
| Requirement | Test or check that proves it |
|-------------|------------------------------|
| R1 | `tests/test_slots_api.py` (availability flips after booking) |
| R2 | `tests/test_reset_api.py` (both body shapes; bookings cleared) |
| R3, R4 | `tests/test_booking_api.py` (create 201, get 200, unknown 404) |
| R5, N1 | `tests/test_auth_api.py` (missing or wrong key returns 401 on all endpoints) |
| R6 | `tests/test_validation_api.py` (missing, blank, bad email, unknown slot) |
| R7, N2 | `tests/test_concurrency_api.py` (50 parallel requests: one 201, 49 409) |
| R8 | `tests/test_cancel_api.py` (cancel, rebook, double cancel, unknown id) |
| R9 | `tests/test_idempotency_api.py` (same key, no key, different body, parallel same key) |
| R10 | `tests/test_paging_api.py` (page through all items once, limits, missing email) |
| R11 | `tests/test_rate_limit_api.py` (11th request returns 429 with Retry-After) |
| R12, N7 | `tests/test_web_page_browser.py` (happy path at phone and desktop widths) plus a manual checklist on the deployed URL (design match, keyboard, contrast, phone and desktop width) |
| R13 | `tests/test_payment_api.py` (pay, pay cancelled returns 409, core schema unchanged) |
| R14, N8 | `tests/test_error_format_api.py` (every non-2xx has a string `error`, no stack traces) |
| R15, R16, N10 | `tests/test_dashboard_api.py` (counts, order, masked names, no emails, 401 without key) |
| R17 | `tests/test_dashboard_page_browser.py` (desktop viewport) plus manual design match |
| N3 | restart check on the deployed service (booking survives) |
| N4, N5 | `tests/test_log_privacy.py` (no names/emails in captured logs; one audit line per state change) |
| N6, N9 | timing check of warm and cold requests; `tests/test_health_api.py` |

## Plan maintenance
If implementation departs from this plan, update this file in the same commit as the code.

## Measurement
- Leading: share of changes that merge from the first implementation pass; time from plan acceptance to merged PR.
- Lagging: rework cycles per change; whether the merged diff still matches this plan.
