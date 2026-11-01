# Plan: Clinic booking API and booking web page

Derived from: intent.md (2026-10-31), spec.md (2026-10-31) · Status: accepted
Accepted by: user, 2026-10-31 · Higher-risk sign-off: not required (D5)
Supporting skills: none
Stack (D8-D10, D17-D20): Java 25, Spring Boot 4.0.x, Maven wrapper, PostgreSQL on Neon, Flyway, plain SQL via JdbcClient, Spotless, Render (Docker). Repo state: empty greenfield (only AGENTS.md, docs/design/, sdlc/ exist).

Base package `com.clinic.booking`. Source paths below are under `src/main/java/com/clinic/booking/` unless they start with `src/` or are at the repo root.

## Files that change
| File | New / modified / deleted | Requirements covered |
|------|--------------------------|----------------------|
| `pom.xml`, `mvnw`, `mvnw.cmd`, `.mvn/wrapper/*` | new | all (build, N3) |
| `.gitignore`, `.dockerignore` | new | N1 (no secrets committed) |
| `BookingApplication.java` | new | all |
| `src/main/resources/application.properties` | new | N1, N3, N6 (env-based config, small Hikari pool) |
| `src/main/resources/db/migration/V1__schema.sql` | new | R7, N2, N3 (slots, bookings + partial unique index, idempotency_keys, payments) |
| `config/AppProperties.java` | new | R10, R11, N1 (api key, limits as config) |
| `web/ApiKeyFilter.java` (enforces the key on /slots, /bookings, /reset; `/health`, `/config.js` and static files exempt) | new | R5, N1 |
| `web/RateLimitFilter.java` | new | R11 |
| `web/ApiError.java`, `web/GlobalExceptionHandler.java` | new | R6, R14, N8 |
| `web/SlotController.java`, `web/ResetController.java` | new | R1, R2 |
| `web/BookingController.java` | new | R3, R4, R6, R8, R9, R10 |
| `web/PaymentController.java` | new | R13 |
| `web/ConfigController.java` (serves `/config.js` with the key from env) and `GET /health` | new | R12, N9, D11 |
| `web/dto/*.java` (records: Slot, SlotWithAvailability, NewBooking, Booking, ResetRequest, PageResponse, PaymentResponse) | new | R1-R4, R10, R13 |
| `service/SlotService.java`, `service/BookingService.java`, `service/PaymentService.java`, `service/AuditLog.java` | new | R2-R4, R7-R10, R13, N5 |
| `repo/SlotRepository.java`, `repo/BookingRepository.java`, `repo/IdempotencyRepository.java`, `repo/PaymentRepository.java` | new | R1-R4, R7-R10, R13 |
| `exception/NotFoundException.java`, `ConflictException.java`, `BadRequestException.java` | new | R4, R6, R7, R14 |
| `src/main/resources/static/index.html`, `app.css`, `app.js` | new | R12 (design: docs/design/web-reference.jpeg) |
| `src/test/java/.../support/PostgresTestBase.java` | new | N2, N3 (guard from D19) |
| `src/test/java/.../*ApiTest.java` (see Proof) | new | R1-R14, N1-N8 |
| `src/test/java/.../WebPageBrowserTest.java` (Playwright for Java, happy path) | new | R12, N7 (D24) |
| `.github/workflows/ci.yml` (build, test, lint on every push; test DB from encrypted secret) | new | R1-R14 feedback loop (D22) |
| `Dockerfile`, `render.yaml` | new | N3, N6, N9, C2 |
| `README.md` | new | N9, Loom walkthrough |
| `AGENTS.md`, `REVIEW.md` | modified / new | repo policy |

## Order of work
1. Scaffold project (pom, wrapper, app class, properties, .gitignore); build passes. (foundation)
2. Migration V1 and `PostgresTestBase` with the safety guard: tests refuse to run unless `TEST_DATABASE_URL` is set and differs from `DATABASE_URL`. (covers R7, N2, N3)
3. Error model, key filter, global exception handler, `/health`. (covers R5, R14, N1, N8)
4. Slots list and `/reset` (accepts `{"slots":[...]}` or a bare array). (covers R1, R2)
5. Create and get booking with validation. (covers R3, R4, R6)
6. Double-booking guard: unique-violation maps to 409; concurrency test with 50 simultaneous requests. (covers R7, N2)
7. Cancel booking; cancelled slot can be rebooked. (covers R8)
8. Idempotency: header key (advisory lock per key) plus natural dedupe on slot+email. (covers R9)
9. Paging by email. (covers R10)
10. Rate limiter on POST /bookings (in-memory window per key+IP, limits from config). (covers R11)
11. Audit lines and log-privacy test. (covers N4, N5)
12. Web page following the reference, plus `/config.js`. (covers R12, N7)
13. Checkpoint: Levels 1-5 green end to end. Only then start extras (D6).
14. Simulated payment endpoints and "Pay now (demo)" button. (covers R13)
15. Dockerfile, render.yaml, README; deploy; keep-alive ping; measure cold start; run all checks against the live URL. (covers N3, N6, N9, C2)

## Parallelization
- Independent (separate workspaces/branches, different files): web page (step 12, needs only the contract from steps 4-5), `Dockerfile` + `render.yaml` + README (step 15 files), `RateLimitFilter` + its test (step 10).
- Sequential (share `BookingService`, `BookingRepository`, `BookingController`): steps 5 → 6 → 7 → 8 → 9 → 14. Steps 1 → 2 → 3 → 4 also run in order.

## Risks
| Risk | What it could break | Mitigation |
|------|---------------------|------------|
| Concurrent bookings for one slot | double-booking (R7) | Partial unique index on confirmed bookings per slot; handle the unique violation as 409; 50-way concurrency test on real Postgres |
| Same Idempotency-Key sent twice at the same instant | duplicate booking or a 500 (R9) | `pg_advisory_xact_lock(hashtext(key))` inside the transaction, then look up the stored response |
| Same slot+email retried while another person books the slot | wrong person gets the booking | Natural dedupe returns the existing booking only when its email matches; otherwise 409 |
| Tests wipe production data | lost bookings | Guard in `PostgresTestBase` (D19); separate Neon branch; secrets never committed |
| Render cold start and small memory; Neon compute also sleeps | first grader request times out (C2, N6) | Keep-alive ping of the public /health, `-XX:MaxRAMPercentage`, serial GC, small Hikari pool (max 5), measure cold start before submitting |
| `/config.js` exposes the key to anyone (D11) | key leaks; `/reset` reachable | Accepted risk; key from env only, never in Git or Loom, rotate after Koya finishes |
| Boot 4.0 / Spring Framework 7 differences from older tutorials | wasted time on removed or renamed APIs | Check the current Boot 4.0 docs; fall back to Boot 3.5.x only through a new decision |
| In-memory rate limiter resets on restart (C4) | spam limit briefly resets | Accepted for a single instance |
Riskiest step: step 8 (idempotency), because it combines retries, the unique index and concurrency, and the Koya check for it is unknown (C1).

## Alternatives considered
- JPA/Hibernate: rejected because plain SQL gives exact control of locks and constraint errors (D21).
- Application-level locking (`synchronized`, in-memory sets): rejected because it breaks across restarts or more than one instance; the database must be the guard.
- Row lock `SELECT ... FOR UPDATE` as the only guard: rejected as the sole mechanism; the unique index is simpler and always enforced, and cancelled rows stay out of it.
- H2 or Testcontainers for tests: rejected by the user in favour of a Neon test branch (D19).
- Redis or Bucket4j for rate limiting: rejected as extra infrastructure or dependency for a single instance.
- Separate frontend (React) hosted elsewhere: rejected; static page in the same service avoids CORS and a second deploy.

## Proof
| Requirement | Test or check that proves it |
|-------------|------------------------------|
| R1 | `SlotsApiTest` (availability flips after booking) |
| R2 | `ResetApiTest` (both body shapes; bookings cleared) |
| R3, R4 | `BookingApiTest` (create 201, get 200, unknown 404) |
| R5, N1 | `AuthApiTest` (missing or wrong key returns 401 on all endpoints) |
| R6 | `ValidationApiTest` (missing, blank, bad email, unknown slot) |
| R7, N2 | `ConcurrencyApiTest` (50 parallel requests: one 201, 49 409) |
| R8 | `CancelApiTest` (cancel, rebook, double cancel, unknown id) |
| R9 | `IdempotencyApiTest` (same key, no key, different body, parallel same key) |
| R10 | `PagingApiTest` (page through all items once, limits, missing email) |
| R11 | `RateLimitApiTest` (11th request returns 429 with Retry-After) |
| R12, N7 | `WebPageBrowserTest` (automated happy path) plus a manual checklist on the deployed URL (design match, keyboard, contrast, phone width) |
| R13 | `PaymentApiTest` (pay, pay cancelled returns 409, core schema unchanged) |
| R14, N8 | `ErrorFormatApiTest` (every non-2xx has a string `error`, no stack traces) |
| N3 | restart check on the deployed service (booking survives) |
| N4, N5 | `LogPrivacyTest` (no names/emails in captured logs; one audit line per state change) |
| N6, N9 | timing check of warm and cold requests; `/health` returns 200 |

## Plan maintenance
If implementation departs from this plan, update this file in the same commit as the code.

## Measurement
- Leading: share of changes that merge from the first implementation pass; time from plan acceptance to merged PR.
- Lagging: rework cycles per change; whether the merged diff still matches this plan.
