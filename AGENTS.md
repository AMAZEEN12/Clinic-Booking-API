# Clinic booking API

Context for any AI agent or new team member working in this repository. Keep it under one page.

## Commands
- Build: `./mvnw -q -DskipTests package` (healthy output: no errors, `target/*.jar` created)
- Test: `./mvnw test` (needs `TEST_DATABASE_URL`, a Neon test branch, never production)
- Lint: `./mvnw spotless:check` (fix with `./mvnw spotless:apply`; run before pushing)
- Run: `DATABASE_URL=... API_KEY=... ./mvnw spring-boot:run`

## Conventions
- Java 25, Spring Boot 4.0.x, Maven wrapper, plain SQL via `JdbcClient`, Flyway migrations, PostgreSQL on Neon.
- Every error response is `{"error": "<message>"}`; never return a stack trace.
- The database is the guard against double-booking (partial unique index), not application locks.
- Every endpoint needs an integration test that runs against real Postgres.
- Names and emails are personal data: never in logs or error messages. Audit lines carry ids only.

## Architecture
- `web/` controllers, filters (API key, rate limit), error handling, DTO records.
- `service/` booking, slot and payment logic, audit log. `repo/` SQL only.
- `src/main/resources/db/migration/` Flyway SQL. `src/main/resources/static/` the web page.
- `docs/design/` visual reference. `sdlc/clinic-booking-api/` lifecycle artifacts.

## Protected paths
- Applied migrations `db/migration/V*.sql`: never edit; add a new version.
- `docs/design/`, `sdlc/**/` accepted artifacts: change only through the lifecycle.
- Secrets: API key, `DATABASE_URL`, `TEST_DATABASE_URL` stay in environment variables, never in Git, logs or the worklog.

## Mistakes to avoid
Rule: when an agent makes the same mistake twice, the correction goes here.
- Do not change the core Booking response for extras; payment lives on separate endpoints (D6).
- Do not point tests at the production database; the guard in `PostgresTestBase` must stay.
- Do not edit tests to make a fix pass; test-first (see test-plan.md).
- Do not guess the Koya contract: the paging, idempotency, rate-limit and `/reset` choices are D12-D15 and need re-checking if the full spec appears.

## Verifying your work
- Build: `./mvnw -q -DskipTests package` (must end without errors)
- Test: `./mvnw test` (all green, including the browser test; never skip or delete a failing test)
- Lint: `./mvnw spotless:check` (zero violations)

Run all three before reporting any task complete, and paste the output. If a test fails, fix the code, not the test.

## Lifecycle work in progress
Per-change artifacts live in `sdlc/<change-slug>/`. Before doing any work on a change, read its `WORKLOG.md` first: it holds the current state, the next action, every decision made so far, and the agreed conventions. Continue from its "Resume here" section, follow its decisions and conventions, and update it as you work. Then read intent.md, spec.md and plan.md before changing code for that change.

Active change: `sdlc/clinic-booking-api/`
