# Test plan: Clinic booking API and booking web page

Derived from: spec.md (2026-10-31), plan.md (2026-10-31) · Status: accepted (user, 2026-10-31)
Supporting skills: none
Decisions applied: D19 (Neon test branch), D20 (Spotless), D22 (GitHub Actions on every push), D23 (every requirement has a test), D24 (manual checklist plus browser test), D25 (small eval suite as a stretch goal)

## Feedback loop
The agent runs these itself and iterates until they pass, before any human reviews the work.
| Check | Command | Passing looks like |
|-------|---------|--------------------|
| Build | `./mvnw -q -DskipTests package` | exits 0, `target/*.jar` exists |
| Test | `./mvnw test` (needs `TEST_DATABASE_URL`, a Neon test branch) | exits 0, all tests pass, none skipped |
| Lint | `./mvnw spotless:check` | exits 0, no violations |
| Visual (UI only) | `WebPageBrowserTest` (Playwright for Java, run inside `./mvnw test`) plus the manual checklist below | happy path passes; page matches `docs/design/web-reference.jpeg` as adjusted in spec.md UI / UX |

CI (GitHub Actions, every push) runs the same three commands on JDK 25 with `TEST_DATABASE_URL` as an encrypted secret and a browser-install step for Playwright.

## Done-targets
- Every `*ApiTest` class listed under Traceability passes.
- `ConcurrencyApiTest`: 50 parallel POSTs for one slot give exactly one 201 and 49 409, and GET /slots shows one confirmed booking.
- No test run can reach the production database: `PostgresTestBase` fails fast when `TEST_DATABASE_URL` is missing or equals `DATABASE_URL`.
- After deploy, the same API checks pass against the live https URL, and a booking survives a service restart.
- Cold start check: the first request after Render idle sleep returns a valid response within 60 s.

## Traceability
| Requirement | Test(s) | Type |
|-------------|---------|------|
| R1 | `SlotsApiTest` | integration |
| R2 | `ResetApiTest` (object body, bare array body, bookings cleared) | integration |
| R3, R4 | `BookingApiTest` | integration |
| R5 | `AuthApiTest` (all six endpoints, missing and wrong key) | integration |
| R6 | `ValidationApiTest` | integration |
| R7 | `ConcurrencyApiTest` | integration (real Postgres) |
| R8 | `CancelApiTest` | integration |
| R9 | `IdempotencyApiTest` (same key, no key, different body, parallel same key) | integration |
| R10 | `PagingApiTest` | integration |
| R11 | `RateLimitApiTest` | integration |
| R12 | `WebPageBrowserTest` plus manual checklist | e2e + manual |
| R13 | `PaymentApiTest` | integration |
| R14 | `ErrorFormatApiTest` | integration |
| N1 | `AuthApiTest`; repository scan for secrets in CI | integration + static |
| N2 | `ConcurrencyApiTest`; migration test that the partial unique index exists | integration |
| N3 | restart check on the deployed service | manual |
| N4, N5 | `LogPrivacyTest` (captured logs contain no test names or emails; one audit line per state change) | integration |
| N6 | timing check warm and cold on the deployed service | manual |
| N7 | manual checklist (keyboard, labels, 4.5:1 contrast, phone width, "Taken" label) | manual |
| N8 | `ErrorFormatApiTest` (malformed JSON, no stack traces) | integration |
| N9 | `HealthApiTest` (200 without a key, 503 when the database is down); uptime monitor configured | integration + manual |

Manual web page checklist (run on the live URL): matches the design look; day chips and time grid follow GET /slots; taken slots disabled and labelled; Tab reaches every control with visible focus; error messages announced; works at 390 px width; no key in the screen recording.

## Bug fixes: test first
1. Reproduce the bug as a failing test; confirm it fails for the expected reason.
2. Commit the test.
3. Fix the code without editing the test.

## Protecting the loop
- Review rule (REVIEW.md): reject diffs that delete, skip or weaken tests; during a fix task, test files change only in the test-first commit.
- Safety guard: `PostgresTestBase` refuses to run against the production database (D19).

## Evals (ongoing agent work)
Stretch goal (D25), done after Levels 1-5 and the first extra are solid.
- Suite location: `evals/`
- Cases: 10 small tasks with accepted outcomes, taken from real work in this project (for example add a validation rule, fix a seeded paging bug, change the rate limit); the exact list is written after Levels 1-5 (current count: 0).
- Runs: manually, and on any change to AGENTS.md, REVIEW.md or guardrails. No scheduled runs, because the repository stays frozen after submission.
- Gate: pass rate at least 80% to merge configuration changes.
- Rule: every incident adds one eval.
- Constraint: nothing in `evals/` may change the deployed service, because the brief says not to change it after submission.

## Open questions
- [ ] Exact list of the 10 eval tasks · UNRESOLVED (owner: user, after Levels 1-5)
- [ ] Playwright version and the CI browser-install step · UNRESOLVED (owner: agent, verified when writing the pom and ci.yml)

## Measurement
- Leading: first-pass CI success rate for agent-written changes; eval pass rate over time.
- Lagging: review time per PR; change failure rate; regressions caught in CI vs. in production.
