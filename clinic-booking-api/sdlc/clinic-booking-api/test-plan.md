# Test plan: Clinic booking API and booking web page

Derived from: spec.md (2026-10-31), plan.md (2026-10-31) · Status: accepted (user, 2026-10-31)
Supporting skills: none
Decisions applied: D19 (Neon test branch), D20 (lint tool, now Ruff via D39), D22 (GitHub Actions on every push), D23 (every requirement has a test), D24 (manual checklist plus browser tests; amended by D41: Playwright and Vitest from the web template), D25 (small eval suite as a stretch goal)

## Feedback loop
The agent runs these itself and iterates until they pass, before any human reviews the work.
| Check | Command | Passing looks like |
|-------|---------|--------------------|
| Install and import | `pip install -r requirements-dev.txt` then `python -c "import app.main"` | exits 0, no import errors |
| Test | `pytest` (needs `TEST_DATABASE_URL`, a Neon test branch) | exits 0, all tests pass, none skipped |
| Lint | `ruff check .` and `ruff format --check .` | exits 0, no violations |
| Web build | `pnpm --dir web typecheck`, `pnpm --dir web lint`, `pnpm --dir web test` (Vitest), `pnpm --dir web build` | all exit 0 |
| Visual (UI only) | `pnpm --dir web test:e2e` (Playwright happy path at phone and desktop widths) plus the manual checklist below | tests pass; page matches the Emerald template look |

CI (GitHub Actions, every push) runs the same three commands on Python 3.12 with `TEST_DATABASE_URL` as an encrypted secret and a separate `web` job (Node 22, pnpm: install, typecheck, lint, Vitest, build); the Playwright end-to-end tests run against a locally started API on the test database after `playwright install --with-deps chromium`.

## Done-targets
- Every `tests/test_*_api.py` file listed under Traceability passes.
- The dashboard returns no emails and no full names (N10), and the page works at 390 px and 1280 px (R12, R17).
- `tests/test_concurrency_api.py`: 50 parallel POSTs for one slot give exactly one 201 and 49 409, and GET /slots shows one confirmed booking.
- No test run can reach the production database: `tests/conftest.py` fails fast when `TEST_DATABASE_URL` is missing or equals `DATABASE_URL`.
- After deploy, the same API checks pass against the live https URL, and a booking survives a service restart.
- Cold start check: the first request after Render idle sleep returns a valid response within 60 s.

## Traceability
| Requirement | Test(s) | Type |
|-------------|---------|------|
| R1 | `tests/test_slots_api.py` | integration |
| R2 | `tests/test_reset_api.py` (object body, bare array body, bookings cleared) | integration |
| R3, R4 | `tests/test_booking_api.py` | integration |
| R5 | `tests/test_auth_api.py` (all six endpoints, missing and wrong key) | integration |
| R6 | `tests/test_validation_api.py` | integration |
| R7 | `tests/test_concurrency_api.py` | integration (real Postgres) |
| R8 | `tests/test_cancel_api.py` | integration |
| R9 | `tests/test_idempotency_api.py` (same key, no key, different body, parallel same key) | integration |
| R10 | `tests/test_paging_api.py` | integration |
| R11 | `tests/test_rate_limit_api.py` | integration |
| R12 | `web/e2e` Playwright test (phone 390 px and desktop 1280 px), Vitest tests for the booking form and API mapping, plus manual checklist | e2e + unit + manual |
| R13 | `tests/test_payment_api.py` | integration |
| R14 | `tests/test_error_format_api.py` | integration |
| R15, R16 | `tests/test_dashboard_api.py` | integration |
| R17 | `web/e2e` dashboard spec (desktop viewport) plus manual design match | e2e + manual |
| N1 | `tests/test_auth_api.py`; repository scan for secrets in CI | integration + static |
| N2 | `tests/test_concurrency_api.py`; migration test that the partial unique index exists | integration |
| N3 | restart check on the deployed service | manual |
| N4, N5 | `tests/test_log_privacy.py` (captured logs contain no test names or emails; one audit line per state change) | integration |
| N6 | timing check warm and cold on the deployed service | manual |
| N7 | manual checklist (keyboard, labels, 4.5:1 contrast, phone width, "Taken" label) | manual |
| N8 | `tests/test_error_format_api.py` (malformed JSON, no stack traces) | integration |
| N9 | `tests/test_health_api.py` (200 without a key, 503 when the database is down); uptime monitor configured | integration + manual |
| N10 | `tests/test_dashboard_api.py` (no emails, no full names in any dashboard response) | integration |
| D42 (CORS) | `tests/test_cors_api.py` | integration |

Manual web page checklist (run on the live URL): matches the design look on a phone (390 px) and on a desktop (1280 px); day chips and time grid follow GET /slots; taken slots disabled and labelled; Tab reaches every control with visible focus; error messages announced; no horizontal scrolling at either width; dashboard shows only masked names; no key in the screen recording.

## Bug fixes: test first
1. Reproduce the bug as a failing test; confirm it fails for the expected reason.
2. Commit the test.
3. Fix the code without editing the test.

## Protecting the loop
- Review rule (REVIEW.md): reject diffs that delete, skip or weaken tests; during a fix task, test files change only in the test-first commit.
- Safety guard: `tests/conftest.py` refuses to run against the production database (D19).

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
- [ ] Playwright and Vitest versions come from the template's `pnpm-lock.yaml`; confirm they install, and write the CI `web` job · UNRESOLVED (owner: agent, when writing ci.yml)

## Measurement
- Leading: first-pass CI success rate for agent-written changes; eval pass rate over time.
- Lagging: review time per PR; change failure rate; regressions caught in CI vs. in production.