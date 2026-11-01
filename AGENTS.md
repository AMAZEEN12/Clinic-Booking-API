# Clinic booking API

Context for any AI agent or new team member working in this repository. Keep it under one page.

## Commands
- Setup: `python -m venv .venv`, activate it, then `pip install -r requirements-dev.txt`
- Check: `python -c "import app.main"` (healthy output: no errors)
- Test: `pytest` (needs `TEST_DATABASE_URL`, a Neon test branch, never production)
- Lint: `ruff check .` and `ruff format --check .` (fix formatting with `ruff format .`; run before pushing)
- Run: `uvicorn app.main:app --reload` with `DATABASE_URL` and `API_KEY` set. Use exactly one worker: the rate limiter is in memory. `DATABASE_URL` and `TEST_DATABASE_URL` are standard `postgresql://USER:PASSWORD@HOST/DB?sslmode=require` URLs.

## Conventions
- Python 3.12+, FastAPI with synchronous endpoints, psycopg 3 with plain SQL, SQL migration files in `migrations/`, PostgreSQL on Neon, Ruff for lint and format.
- Every error response is `{"error": "<message>"}`; never return a stack trace.
- The database is the guard against double-booking (partial unique index), not application locks.
- Every endpoint needs an integration test that runs against real Postgres.
- Names and emails are personal data: never in logs or error messages. Audit lines carry ids only.

## Architecture
- `app/routers/` HTTP endpoints, `app/services/` booking, slot, payment and dashboard logic, `app/repositories/` SQL only, `app/security.py` key check, `app/ratelimit.py`, `app/errors.py`, `app/schemas.py`.
- `migrations/` SQL migrations. `app/static/` the web page and dashboard. `tests/` pytest suite.
- `docs/design/` visual reference. `sdlc/clinic-booking-api/` lifecycle artifacts.

## Protected paths
- Applied migrations `migrations/V*.sql`: never edit; add a new version.
- `docs/design/`, `sdlc/**/` accepted artifacts: change only through the lifecycle.
- Secrets: API key, `DATABASE_URL`, `TEST_DATABASE_URL` stay in environment variables, never in Git, logs or the worklog.

## Mistakes to avoid
Rule: when an agent makes the same mistake twice, the correction goes here.
- Do not change the core Booking response for extras; payment lives on separate endpoints (D6).
- Dashboard endpoints must never return emails or full names; masked names only (D36).
- Do not point tests at the production database; the guard in `tests/conftest.py` must stay.
- Do not edit tests to make a fix pass; test-first (see test-plan.md).
- Do not guess the Koya contract: the paging, idempotency, rate-limit and `/reset` choices are D12-D15 and need re-checking if the full spec appears.

## Verifying your work
- Check: `python -c "import app.main"` (must end without errors)
- Test: `pytest` (all green, including the browser tests; never skip or delete a failing test)
- Lint: `ruff check .` and `ruff format --check .` (zero violations)

Run all three before reporting any task complete, and paste the output. If a test fails, fix the code, not the test.

## Lifecycle work in progress
Per-change artifacts live in `sdlc/<change-slug>/`. Before doing any work on a change, read its `WORKLOG.md` first: it holds the current state, the next action, every decision made so far, and the agreed conventions. Continue from its "Resume here" section, follow its decisions and conventions, and update it as you work. Then read intent.md, spec.md and plan.md before changing code for that change.

Active change: `sdlc/clinic-booking-api/`
