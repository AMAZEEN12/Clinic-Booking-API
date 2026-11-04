# Work log: Clinic booking API

Change slug: `clinic-booking-api` · Started: 2026-10-31 · Last updated: 2026-10-31 by Claude
Source document: Koya Cohort 4 assessment, Task 1 brief + Clinic booking API OpenAPI 1.0 schema (pasted in chat; koyaacademy.com/assessment-api could not be fetched)

> Any agent opening this project: read this file first, then the "Conventions and guidelines" and "Decisions" sections, then the artifacts in this folder. Continue from "Resume here". Don't re-ask anything already answered below.

## Resume here
- **Stage:** Build (implementation: EXECUTION step 8 done: cancel, idempotency and paging all tested)
- **Step:** EXECUTION step 9 (plan steps 10-11): rate limit (R11), then audit lines and the log-privacy test (N4, N5). Paging (plan step 9, R10, D13) is proven by `tests/test_paging_api.py` (21 tests).
- **In progress:** nothing half-done. Verified 2026-11-04 on a local Postgres 16: `pytest` 139 passed (5 runs in a row), `ruff check .` and `ruff format --check .` clean. A real uvicorn run confirmed the access log no longer shows the email (D45).
- **Next action:** user runs `python -m pytest`, `ruff check .`, `ruff format --check .` against the Neon test branch and reports. Then plan step 10: `app/ratelimit.py` and `tests/test_rate_limit_api.py` (R11, D14), test-first.
- **Waiting on:** user's pytest/ruff results on the Neon test branch (cancel, idempotency, paging, log filter).
- **Not yet built:** `app/ratelimit.py` (R11), the audit-line half of `tests/test_log_privacy.py` (N5; the access-log half exists), `tests/test_health_api.py` (N9), payment and dashboard extras, `web/`, `render.yaml`, README, CI workflow. When writing `render.yaml`, start uvicorn with exactly one worker; do not add `--no-access-log` (the filter in `app/logsafe.py` already hides query strings).

## How to continue without the sdlc skill
1. Stages run in order: Plan (intent.md), Design (spec.md), Build (plan.md + repo AGENTS.md), Test (test-plan.md), Deploy (release.md + repo REVIEW.md), Maintain (monitoring.md), then EXECUTION.md.
2. Each stage reads the accepted artifact before it. Never write a later artifact before the earlier one is accepted.
3. Fill in what is already known, then ask the user questions (the user prefers ONE question at a time with tappable options), each with a suggested default. Never invent answers. Mark gaps `UNRESOLVED` and carry them forward.
4. Show a short summary of each artifact and get the user's confirmation, then set `Status: accepted` with the approver and date.
5. Keep requirement IDs (R1, N1, ...) the same across spec.md, plan.md and test-plan.md.
6. Update this log after every round of answers, artifact change and decision.
7. Templates: `<path to sdlc skill>/templates/`. If they're not available, copy the heading structure of the artifacts already in this folder.

## Artifact status
| Artifact | Status (missing / draft / accepted) | Approved by | Date |
|----------|-------------------------------------|-------------|------|
| intent.md | accepted | user | 2026-10-31 |
| spec.md | accepted | user | 2026-10-31 |
| plan.md | accepted | user | 2026-10-31 |
| AGENTS.md (repo) | accepted (Verifying block provisional until Test stage) | user | 2026-10-31 |
| test-plan.md | accepted | user | 2026-10-31 |
| REVIEW.md (repo) | accepted | user | 2026-10-31 |
| release.md | accepted | user | 2026-10-31 |
| monitoring.md | accepted | user | 2026-10-31 |
| EXECUTION.md | draft (generated) | | |

## Conventions and guidelines
- **Stack and versions:** Python 3.12+, FastAPI, psycopg 3, PostgreSQL on Neon, Render native Python (D10, D38, D39)
- **Naming:** kebab-case slug `clinic-booking-api`; requirement IDs R1.., N1..; decisions D1..
- **Code and docs style:** UNRESOLVED
- **Source of truth:** repository (Markdown files are authoritative)
- **Policies in force:** assumed baseline (authentication on every endpoint, input validation, no sensitive data in logs, audit events on state changes, accessibility for the web page)
- **Supporting skills:** none
- **Approvers:** product owner: user (self-approve); tech lead: not required; release manager: user
- **User preferences for this workflow:** ask questions one at a time as tappable options; brainstorm together; explain jargon when asked. Names and emails are treated as personal data.
- **Never record secrets:** the API key is `<provided by user, not recorded>`.

## Decisions
| ID | Date | Decision | Reason | Decided by | Affects | Status |
|----|------|----------|--------|------------|---------|--------|
| D1 | 2026-10-31 | Change slug is `clinic-booking-api` | Clear, matches the brief | user | all | active |
| D2 | 2026-10-31 | User is both originator and product owner (self-approves); Koya Academy is the requester | No one at Koya reviews each document | user | all artifacts | active |
| D3 | 2026-10-31 | New empty repo; Markdown files are the source of truth | Greenfield project | user | all | active |
| D4 | 2026-10-31 | Use the assumed baseline policy, no supporting skills | User has no written policies | user | spec.md, REVIEW.md | active |
| D5 | 2026-10-31 | No tech-lead sign-off; names and emails treated as personal data | Low-risk assessment project that stores PII | user | spec.md, plan.md, release.md | active |
| D6 | 2026-10-31 | Extras (login/user accounts on the web page, simulated payments, in-app notifications, optional email notifications) are in scope as OPTIONAL and ADDITIVE: the core API contract stays untouched (POST /bookings needs only slot_id, name, email + X-API-Key) and extras are built only after Levels 1-5 are solid | Grader calls the API with the key only; brief says follow spec closely and finish each level properly first | user (after Claude flagged the contract risk) | intent.md, spec.md, plan.md | active |
| D7 | 2026-10-31 | Spec gaps (paging, idempotency, rate limit, /reset body) cannot be confirmed; use tolerant assumptions and mark UNRESOLVED in spec.md: GET /bookings?email=&page=1&limit=10 (max 100) returning {items,page,limit,total}; Idempotency-Key header (same key returns original booking; without key, repeat of same slot+email returns existing booking); 10 bookings/min per key+IP then 429 with Retry-After; POST /reset takes {"slots":[Slot]} and clears bookings; codes 201/400/401/404/409 | User cannot access fuller spec | user | spec.md, plan.md, test-plan.md | active |
| D8 | 2026-10-31 | Language Java on JDK 25 (LTS); database PostgreSQL hosted on Neon | User choice; Postgres row locks/unique constraints give safe concurrency | user | spec.md, plan.md | superseded (D38) |
| D9 | 2026-10-31 | Framework: Spring Boot (latest release supporting JDK 25; verify version in plan.md) | Most docs, strong reviewer signal | user | plan.md, AGENTS.md | superseded (D38) |
| D10 | 2026-10-31 | Host the Spring Boot service on Render (Docker, free tier). Known risk: free instances sleep after idle (~50s cold start) and have small memory; spec.md Areas of concern must list it with mitigation (keep-alive ping with the API key header, lean JVM settings, graceful startup) | User choice; free and simple | user | spec.md, release.md, monitoring.md | active (amended D39) |
| D11 | 2026-10-31 | One API key is used everywhere, including the web page (key visible in page source). Risk accepted: anyone who reads it could call /reset. Mitigations: key injected at runtime from env var, never committed, not shown in Loom, rotate after Koya finishes | User chose simplicity over a two-key or proxy design after being warned | user | spec.md (C3, C6, N1), plan.md, release.md | active |
| D12 | 2026-10-31 | Retry handling (C1 gap 1): support BOTH an Idempotency-Key header (same key + same body returns the original response, same status and booking id; same key + different body returns 409) AND natural dedupe (same slot_id + email already confirmed returns the existing booking with the same response) | Covers either way a grader might simulate a retry | user | spec.md R9, plan.md, test-plan.md | active |
| D13 | 2026-10-31 | Paging (C1 gap 2): GET /bookings?email=&page=&limit= ; page starts at 1, limit default 10, max 100; returns {items, page, limit, total}; newest first; missing email returns 400 | User chose recommended option | user | spec.md R10, plan.md, test-plan.md | active |
| D14 | 2026-10-31 | Rate limit (C1 gap 3): POST /bookings limited to 10 per minute per API key + client IP (in-memory token bucket, configurable); over the limit returns 429 with Retry-After and {"error":...}; threshold lives in one config value | User chose recommended option | user | spec.md R11, plan.md, test-plan.md | active |
| D15 | 2026-10-31 | /reset body (C1 gap 4): accept either {"slots": [...]} or a bare array [...]; replaces all slots and clears all bookings; returns 200 | Tolerant of either shape the grader may send | user | spec.md R2, plan.md, test-plan.md | active |
| D16 | 2026-10-31 | Web page follows the user's reference image (docs/design/web-reference.jpeg), phone booking flow only, with a name/email step added; the dashboard (stats, appointment list, reminders, reschedule) and Insurance row are parked as next steps; contrast and 'Taken' labelling fixed | Dashboard/insurance need data or features outside the Koya contract | user | spec.md R12, UI/UX, C7 | active |
| D17 | 2026-10-31 | Spring Boot 4.0.x (Spring Framework 7, Jakarta EE 11) on JDK 25; exact latest 4.0.x patch pinned in the build file when it is created (could not be checked offline). Boot 4.0 released 2025-11-20 with JDK 25 support (web search); Boot 3.5.x also supports JDK 25 and is the fallback | User chose recommended option | user | plan.md, AGENTS.md | superseded (D38) |
| D18 | 2026-10-31 | Build tool: Maven with the Maven wrapper (./mvnw) | User chose recommended option | user | plan.md, AGENTS.md, test-plan.md | superseded (D38) |
| D19 | 2026-10-31 | Automated tests run against a separate Neon test branch (real Postgres) via environment variable TEST_DATABASE_URL; no Docker/Testcontainers, no H2. Safety rule for plan.md: tests refuse to start if TEST_DATABASE_URL is missing or equals the production DATABASE_URL, because tests reset/wipe data; connection strings are never committed or logged | User chose Neon test branch; real Postgres needed to prove concurrency | user | plan.md, test-plan.md, AGENTS.md, release.md | active |
| D20 | 2026-10-31 | Lint/format: Spotless (Maven plugin, google-java-format); `./mvnw spotless:check` in the feedback loop, `spotless:apply` to fix | User chose Spotless | user | plan.md, AGENTS.md, test-plan.md | superseded (D38) |
| D21 | 2026-10-31 | Data access: plain SQL with Spring JdbcClient plus Flyway migrations (no JPA) | Exact control of locking and constraint errors | user | plan.md, AGENTS.md | superseded (D38) |
| D22 | 2026-10-31 | CI: GitHub Actions on every push runs build, test and lint (JDK 25, ./mvnw); TEST_DATABASE_URL supplied as an encrypted repository secret, never printed; new file .github/workflows/ci.yml added to plan.md Files that change | User chose recommended option | user | test-plan.md, plan.md, release.md | active (amended D39) |
| D23 | 2026-10-31 | Quality bar: every requirement (R and N IDs) maps to at least one passing test or documented check; no line-coverage percentage minimum | User chose recommended option | user | test-plan.md | active |
| D24 | 2026-10-31 | Web page checks: a manual checklist (look vs docs/design/web-reference.jpeg, keyboard, contrast, phone width) PLUS an automated browser test (Playwright for Java, happy path: see slots, pick day and time, enter details, confirm, see confirmation; taken slot disabled; runs in CI against the app on a random port with the Neon test DB). Adds a Playwright test dependency and a CI browser-install step; plan.md files list updated | User chose the fuller option | user | test-plan.md, plan.md | active (amended D39) |
| D25 | 2026-10-31 | Evals: a small suite of 10 tasks in evals/ as a STRETCH goal, built after Levels 1-5 and the first extra; run manually and on changes to AGENTS.md/REVIEW.md; gate 80%; must never change the deployed service | User chose the small suite over not-applicable | user | test-plan.md | active |
| D26 | 2026-10-31 | The user is the release manager and sole approver of production releases; the agent prepares the release and cannot deploy to production without the user's explicit go-ahead in the conversation | Solo assessment | user | release.md, REVIEW.md | active |
| D27 | 2026-10-31 | Deploys to Render are MANUAL (auto-deploy switched off in render.yaml/dashboard); a deploy happens only when the release manager triggers it after CI is green; no staging copy (Render free tier), so the dev environment is local plus the Neon test branch and production is the one live service | Brief says keep the service unchanged after submission; avoids accidental auto-deploys | user | release.md, plan.md (render.yaml autoDeploy: false) | active |
| D28 | 2026-10-31 | Rollback: redeploy the previous successful Render deploy from the Render dashboard (one action, release manager). Database migrations are forward-only and additive so the previous app version still works after a rollback. Rehearsal: roll back once on the live service before submission, record the date in release.md | User chose recommended option; no staging exists | user | release.md, plan.md (migration rule) | active |
| D29 | 2026-10-31 | Hard approval gate: production deploy only (release manager approves). Edits to applied migrations, Dockerfile, render.yaml, and anything touching secrets or the live database are NOT hard gates; they stay as written rules in AGENTS.md (Protected paths) and REVIEW.md, plus the test-database guard (D19). Residual risk noted in release.md | User chose the narrowest option; solo project | user | release.md, REVIEW.md | active |
| D30 | 2026-10-31 | REVIEW.md passes: Bugs, Security, Compliance, plus Privacy and Accessibility; nit cap 5; reject weakened tests | User chose recommended option | user | REVIEW.md | active |
| D31 | 2026-10-31 | Monitoring stack: Render built-in logs and metrics, plus a FREE external uptime monitor that pings GET /health every 5 minutes (keep-alive for Render, C2). To work with free monitors that cannot send custom headers, /health is PUBLIC (no key), returns only {"status":"ok"} and runs SELECT 1 so it also keeps the Neon compute awake; it is not one of the Koya endpoints. spec.md N9 and plan.md ApiKeyFilter updated accordingly | User chose Render logs + uptime monitor after being warned that Render logs alone cannot keep the service awake | user | spec.md N9, plan.md, release.md, monitoring.md | active |
| D32 | 2026-10-31 | Alerts: (1) service DOWN (/health fails 2 consecutive checks, ~10 min) and (2) SLOW responses (/health response over 2 s on 2 consecutive checks, excluding the first ping after a sleep). Delivered by the uptime monitor to the user's email. Error spikes are checked by hand in Render metrics, not alerted | User chose recommended option | user | monitoring.md | active |
| D33 | 2026-10-31 | Alert delivery: email only; the user is the only responder (on-call = user); no escalation path. Risk noted: an email can sit unread, so check the inbox and Render dashboard daily until Koya contacts the user | User chose email only | user | monitoring.md | active |
| D34 | 2026-10-31 | On an alert the agent may DIAGNOSE and prepare a fix as a pull request only; no pre-approved runbooks (rollback, redeploy and any production change stay with the user, who holds the credentials) | User chose recommended option | user | monitoring.md | active |
| D35 | 2026-10-31 | Design scope widened (supersedes the 'parked' part of D16): (a) the booking page must work on mobile AND desktop (responsive, part of R12); (b) the clinic dashboard from the reference design becomes a DESKTOP view built as an extra after Levels 1-5 and the payment extra, using NEW additive endpoints GET /dashboard/summary and GET /dashboard/appointments (key required, Koya contract untouched). 'Reminders sent' and 'Reschedule requests' are replaced by real numbers (Cancelled, Open slots); 'Visited' and 'Reminder sent' badges are not built; the Insurance row stays parked | User wants mobile and desktop views of the whole design | user | intent.md, spec.md (R12, R15-R17, N10, C7, C8), plan.md, test-plan.md, EXECUTION.md | active |
| D36 | 2026-10-31 | Dashboard privacy: show MASKED patient names only (first name + last initial, e.g. Ada O.), never emails or full names, so it is safe even though the key is public (D11) | User chose recommended option | user | spec.md R16, N10, C8 | active |
| D37 | 2026-11-01 | Scaffold choices (EXECUTION step 2): Spring Boot pinned to 4.0.0 for now (latest 4.0.x patch could not be checked offline; bump later); Boot 4 modular starters (webmvc, validation, jdbc, flyway, plus -test companions); flyway-database-postgresql added; DATABASE_URL / TEST_DATABASE_URL are JDBC URLs with user, password and sslmode as query parameters (no URL-parsing code); Spotless declared in the pom with unverified versions; Maven wrapper files NOT generated (no Maven or network in the sandbox): user runs `mvn -N wrapper:wrapper` once or copies mvnw files from a Spring Initializr project | Offline sandbox: no Maven, only a Java 21 runtime, no network | Claude | pom.xml, application.properties, AGENTS.md | superseded (D38) |
| D38 | 2026-11-01 | SWITCH OF STACK: Python with FastAPI replaces Java with Spring Boot (supersedes D8, D9, D17, D18, D20, D21, D37). Reasons: fits the AI automation programme, faster to build in the one-week window, lighter cold start on Render, simpler hosting. PostgreSQL on Neon, the Koya contract, the spec requirements, the lifecycle artifacts and the Neon test-branch approach are unchanged | User chose to switch after Claude compared the two | user | plan.md, spec.md, test-plan.md, AGENTS.md, REVIEW.md, release.md, EXECUTION.md | active |
| D39 | 2026-11-01 | Python stack details (proposed by Claude, accepted with the switch): Python 3.12+; FastAPI with synchronous endpoints; psycopg 3 with a connection pool (max 5) and plain SQL, no ORM; forward-only SQL migration files in migrations/ run by a small runner at startup; standard postgresql:// URLs (no JDBC conversion); pytest + httpx for tests; Ruff for lint and format; pytest-playwright for browser tests; CI on Python 3.12; Render native Python service (no Dockerfile), `autoDeploy: false`, exactly ONE uvicorn worker because the rate limiter is in memory; test file naming tests/test_<area>_api.py | Keep the plan's structure and gates, only the tools change | user (accepted) | plan.md, test-plan.md, AGENTS.md, release.md, EXECUTION.md | active |
| D40 | 2026-11-01 | POST /reset returns 200 with body {"slots": N} (N = slots now stored); times without a zone are read as UTC; every time is returned in UTC with a Z suffix; duplicate slot ids or end <= start return 400 and change nothing; two simultaneous resets are serialised with an advisory lock. The response body is a guess (unverified against the Koya spec, C1) | Spec gives no /reset response shape | Claude (assumption) | spec.md R2, plan.md | active |
| D41 | 2026-11-01 | Web page approach: use the user's ClinicFlow React template (React 19 + TypeScript + Vite + Tailwind + Redux Toolkit, uploaded as clinicflow-web-main.zip) as the web page, TRIMMED to the patient flow (home/book, confirmation, look up booking by id, cancel) and the dashboard, REWIRED to the Koya contract, in a `web/` folder of the same repo, hosted SEPARATELY on Vercel. Dropped: staff login, queue, walk-ins, visit types, reference codes/manage tokens, live tracking. Supersedes the plain static page, the image reference (D16) and the same-service/one-deploy plan; amends D24 (Playwright + Vitest from the template), D11 (key baked into the bundle as VITE_API_KEY, still public) and D27 (Vercel deploys also manual). Caution given: confirm permission to reuse the template and be able to explain it in the Loom (C10) | User chose it over a plain page and over serving the build from the API | user | spec.md, plan.md, test-plan.md, release.md, EXECUTION.md, AGENTS.md | active |
| D42 | 2026-11-01 | CORS: the API allows only the web origins listed in the CORS_ORIGINS environment variable (comma-separated; the Vercel URL in production); CORSMiddleware is added last so it is outermost and answers preflight before the key check; allowed headers X-API-Key, Content-Type, Idempotency-Key; Retry-After exposed. Tests set a fake origin in tests/__init__.py | Page and API are on different origins | Claude (follows from D41) | app/main.py, app/config.py, release.md | active |
| D43 | 2026-11-04 | Email check is deliberately lenient: `something@something.something`, no spaces, at most 254 characters (so addresses on `.test` domains are accepted). Found as a comment in `app/schemas.py`; not logged when it was made, so recorded here. Confirm this is what you want | Strict checkers reject valid-looking addresses | recorded from code (confirm with user) | app/schemas.py, tests/test_validation_api.py, spec.md R6 | active |
| D44 | 2026-11-04 | Idempotency details the spec left open (R9, D12): a replay of a key returns 201 and the booking as it is now (if it was cancelled since, that shows, and nothing is booked again); the natural repeat (same slot + same email, case-insensitive, name ignored) also returns 201 with the existing booking; a blank `Idempotency-Key` is ignored and one over 255 characters returns 400; a key is stored only when a booking is returned, so a failed request does not use it up; keys are locked with `pg_advisory_xact_lock(727276, hashtext(key))`; if two racing requests for one slot are the same person, the loser's second pass returns the winner's booking. Unverified against the Koya spec (C1) | Spec gives no replay details | Claude (assumption) | app/services/bookings.py, app/routers/bookings.py, tests/test_idempotency_api.py | active |
| D45 | 2026-11-04 | Paging details the spec left open (R10, D13): `page` below 1 or above 1,000,000, `limit` below 1 or above 100, or non-numbers return 400 (not clamped); a blank `email` returns 400; email matches ignoring capitals and surrounding spaces; cancelled bookings are listed too; a page past the end returns an empty `items` with the real `total`; ties in `created_at` break by id. Because the email travels in the URL, uvicorn's access log would have printed it, so `app/logsafe.py` cuts the query string from access-log lines (N4). Paging numbers live in `app/config.py`. Unverified against the Koya spec (C1) | Spec gives no limit-handling details; N4 forbids emails in logs | Claude (assumption) | app/routers/bookings.py, app/services/bookings.py, app/config.py, app/logsafe.py, tests/test_paging_api.py, tests/test_log_privacy.py | active |


## Questions and answers
| # | Date | Stage | Question | Answer | Status |
|---|------|-------|----------|--------|--------|
| Q1 | 2026-10-31 | Intake | Change slug? | clinic-booking-api | answered |
| Q2 | 2026-10-31 | Intake | Originator and product owner? | Me for both (self-approve), Koya Academy as requester | answered |
| Q3 | 2026-10-31 | Intake | Repository state? | New empty repo, Markdown files are the source of truth | answered |
| Q4 | 2026-10-31 | Intake | Policies or supporting skills? | None, use the assumed baseline | answered |
| Q5 | 2026-10-31 | Intake | Tech-lead sign-off? | No sign-off needed, treat names and emails as personal data | answered |
| Q7 | 2026-10-31 | Plan | What is out of scope? | Wants email notifications (in-app acceptable), simulated payments, login and user accounts. After risk flagged, chose: extras optional and additive, core contract untouched, built only after Levels 1-5 | answered |
| Q8 | 2026-10-31 | Plan | Deadline? | Within a week | answered |
| Q9 | 2026-10-31 | Plan | Success criteria? | All 5 levels plus at least one extra (e.g. simulated payment) working | answered |
| Q10 | 2026-10-31 | Design | How to close spec gaps? | Can't get more detail; propose sensible assumptions and mark UNRESOLVED | answered (see D7) |
| Q11 | 2026-10-31 | Design | Stack? | Java and PostgreSQL on Neon; JDK 25 | answered (D8) |
| Q12 | 2026-10-31 | Design | Java framework? | Spring Boot (latest supporting JDK 25) | answered (D9) |
| Q13 | 2026-10-31 | Design | Hosting? | Render (Docker), accepting cold-start trade-off | answered (D10) |
| Q14 | 2026-10-31 | Design | Which extra first? | Simulated payment | answered (R13) |
| Q15 | 2026-10-31 | Design | C3: how does the web page authenticate? | One key everywhere (simplest; key visible in page source) | answered (D11) |
| Q16 | 2026-10-31 | Design | C1 gap 1: how to recognise a retried booking? | Support both header and slot+email repeat | answered (D12) |
| Q17 | 2026-10-31 | Design | C1 gap 2: paging shape? | page + limit, returns {items,page,limit,total} | answered (D13) |
| Q18 | 2026-10-31 | Design | C1 gap 3: rate limit? | 10 per minute per key+IP, then 429 + Retry-After | answered (D14) |
| Q19 | 2026-10-31 | Design | C1 gap 4: /reset body? | Accept both {slots:[...]} and bare array; clears bookings | answered (D15) |
| Q20 | 2026-10-31 | Design | Web page look? | Uploaded image design; build phone flow now, park dashboard and insurance row | answered (D16) |
| Q21 | 2026-10-31 | Build | Spring Boot line? | 4.0.x | answered (D17) |
| Q22 | 2026-10-31 | Build | Build tool? | Maven with wrapper | answered (D18) |
| Q23 | 2026-10-31 | Build | Test database? | Neon test branch | answered (D19) |
| Q24 | 2026-10-31 | Build | Lint/format tool? | Spotless | answered (D20) |
| Q25 | 2026-10-31 | Build | Data access? | Plain SQL with JdbcClient + Flyway | answered (D21) |
| Q26 | 2026-10-31 | Test | CI? | GitHub Actions on every push | answered (D22) |
| Q27 | 2026-10-31 | Test | Quality bar? | Every requirement has a test | answered (D23) |
| Q28 | 2026-10-31 | Test | Web page checks? | Manual checklist plus an automated browser test | answered (D24) |
| Q29 | 2026-10-31 | Test | Eval suite? | Small suite (10 tasks) as a stretch goal | answered (D25) |
| Q30 | 2026-10-31 | Deploy | Who approves production releases? | Me (the release manager) | answered (D26) |
| Q31 | 2026-10-31 | Deploy | How do deploys to Render work? | Manual deploy trigger | answered (D27) |
| Q32 | 2026-10-31 | Deploy | Rollback method? | Redeploy the previous Render deploy | answered (D28) |
| Q33 | 2026-10-31 | Deploy | Which actions need explicit approval? | Production deploy only | answered (D29) |
| Q34 | 2026-10-31 | Deploy | Extra review passes? | Privacy pass and accessibility pass | answered (D30) |
| Q35 | 2026-10-31 | Maintain | Where to watch the service? | Render logs/metrics; after keep-alive conflict flagged, plus a free uptime monitor for the ping | answered (D31) |
| Q36 | 2026-10-31 | Maintain | What triggers an alert? | Down plus slow responses | answered (D32) |
| Q37 | 2026-10-31 | Maintain | How should alerts reach you? | Email only | answered (D33) |
| Q38 | 2026-10-31 | Maintain | What may the agent do on an alert? | Diagnose and prepare a fix as a PR | answered (D34) |
| Q41 | 2026-11-01 | Build | Which language: Java or Python? | Asked Claude for advice; chose to switch to Python (FastAPI) and update the documents | answered (D38, D39) |
| Q39 | 2026-10-31 | Design (reopened) | Rest of the design? | 'I want mobile and desktop view'; clarified: both the phone flow plus desktop dashboard AND a responsive booking page | answered (D35) |
| Q40 | 2026-10-31 | Design (reopened) | Dashboard patient details? | Masked names only, no emails | answered (D36) |
| Q42 | 2026-11-01 | Design (reopened) | How to use the uploaded ClinicFlow template? | React template, trimmed and rewired, hosted separately on Vercel | answered (D41) |
| Q6 | 2026-10-31 | Intake | Spec gaps: GET /bookings query params and paging shape, idempotency mechanism, rate-limit response, /reset body | Not in pasted schema; decided in D12-D15 | answered (decided, unverified against Koya spec) |

## Activity log
- 2026-10-31 · Claude · Read sdlc skill and templates; attempted to fetch koyaacademy.com/assessment-api (blocked)
- 2026-10-31 · Claude · Intake rounds Q1-Q5 completed one at a time
- 2026-10-31 · Claude · Created repo folder, minimal AGENTS.md, and this WORKLOG.md
- 2026-10-31 · Claude · Stage 1 out-of-scope discussion; logged D6 and Q7
- 2026-10-31 · Claude · Asked deadline (Q8) and success (Q9); drafted intent.md (Status: draft)
- 2026-10-31 · user · Confirmed intent.md; Claude set Status: accepted
- 2026-10-31 · Claude · Logged D7-D9 and Q10-Q12 (spec-gap assumptions, Java 25 + Postgres on Neon, Spring Boot)
- 2026-10-31 · Claude · Logged D10 and Q13 (Render hosting)
- 2026-10-31 · Claude · Drafted spec.md (R1-R14, N1-N9, concerns C1-C6), Status: draft
- 2026-10-31 · Claude · Logged D11 (one key everywhere); updated spec.md C3, C6, N1
- 2026-10-31 · Claude · User declined to accept spec.md yet; resolving UNRESOLVED items. Logged D12 (Q16)
- 2026-10-31 · Claude · Logged D13 (Q17) paging shape
- 2026-10-31 · Claude · Logged D14 (Q18) rate limit
- 2026-10-31 · Claude · Logged D15 (Q19); updated spec.md R2, R9-R11, C1, open questions
- 2026-10-31 · Claude · Published 3-screen web page mock (link above). User chose to upload their own image design instead; waiting for the upload
- 2026-10-31 · user · Uploaded image design; Claude copied it to docs/design/web-reference.jpeg. Design has a patient booking phone screen (clinic card, date chips, time grid, insurance row, amber confirm button) and a clinic dashboard (stats, appointment list, status badges)
- 2026-10-31 · Claude · Logged D16 (Q20); updated spec.md UI/UX, R12, C7 and open questions
- 2026-10-31 · user · Accepted spec.md; Claude set Status: accepted. Repo inspected: only AGENTS.md (minimal), docs/design/web-reference.jpeg and sdlc/ exist, no code (greenfield)
- 2026-10-31 · Claude · Web search confirmed Boot 4.0 and 3.5.x support JDK 25; logged D17 (Q21)
- 2026-10-31 · Claude · Logged D18 (Q22) Maven
- 2026-10-31 · Claude · Logged D19 (Q23) Neon test branch (shortened option labels after user said text was cut off)
- 2026-10-31 · Claude · Logged D20 (Q24) Spotless
- 2026-10-31 · Claude · Logged D21 (Q25); drafted plan.md (15 steps, risks, proof) and full AGENTS.md
- 2026-10-31 · user · Accepted plan.md and AGENTS.md; Claude set status accepted
- 2026-10-31 · Claude · Logged D22 (Q26) GitHub Actions CI
- 2026-10-31 · Claude · Logged D23 (Q27) quality bar
- 2026-10-31 · Claude · Logged D24 (Q28) browser test; plan.md files list updated
- 2026-10-31 · Claude · Logged D25 (Q29); drafted test-plan.md; updated AGENTS.md Verifying block (no longer provisional)
- 2026-10-31 · user · Accepted test-plan.md; Claude set status accepted
- 2026-10-31 · Claude · Logged D26 (Q30) release manager
- 2026-10-31 · Claude · Logged D27 (Q31) manual Render deploys
- 2026-10-31 · Claude · Logged D28 (Q32) rollback method
- 2026-10-31 · Claude · Logged D29 (Q33) approval gate scope
- 2026-10-31 · Claude · Logged D30 (Q34); drafted REVIEW.md and release.md
- 2026-10-31 · user · Accepted REVIEW.md and release.md; Claude set status accepted
- 2026-10-31 · Claude · Logged D31 (Q35); amended accepted spec.md N9 and plan.md for public /health (user-approved via D31)
- 2026-10-31 · Claude · Logged D32 (Q36) alert triggers
- 2026-10-31 · Claude · Logged D33 (Q37) email-only alerts
- 2026-10-31 · Claude · Logged D34 (Q38); drafted monitoring.md
- 2026-10-31 · user · Accepted monitoring.md; Claude set status accepted
- 2026-10-31 · Claude · Wrote EXECUTION.md (16 steps, unresolved questions collected); lifecycle artifact chain complete

- 2026-10-31 · user · Asked about the incomplete design; clarified Claude has written no application code (only docs and a throwaway mock). Chose mobile + desktop views
- 2026-10-31 · Claude · Logged D35, D36 (Q39, Q40); amended accepted artifacts intent.md, spec.md, plan.md, test-plan.md, EXECUTION.md (dashboard as desktop extra, responsive page, masked names)
- 2026-11-01 · Claude · EXECUTION step 2 started: wrote pom.xml, BookingApplication.java, application.properties, .gitignore, empty db/migration. BUILD NOT VERIFIED: sandbox has no Maven, no network, Java 21 runtime only. Gate (`./mvnw -q -DskipTests package` passes) still needs the user to run it
- 2026-11-01 · user · Fixed scaffold locally (src folder had been nested under api/); `mvn clean package -DskipTests` returns BUILD SUCCESS. Step 2 gate met. Maven wrapper still not generated
- 2026-11-01 · user · Asked whether Java or Python is better; chose to switch to Python (FastAPI)
- 2026-11-01 · Claude · Logged D38, D39 (Q41); marked D8, D9, D17, D18, D20, D21, D37 superseded; rewrote plan.md; amended spec.md, test-plan.md, release.md, EXECUTION.md, AGENTS.md, REVIEW.md; removed Java scaffold, created Python scaffold
- 2026-11-01 · user · Scaffold gate passed on Python 3.14 (install, import app.main, ruff check)
- 2026-11-01 · Claude · Wrote step 3 files (schema V1, migration runner, test guard with host+database identity check, migration tests); unverified against a real database
- 2026-11-01 · user · Guard tests 5/5 passed; asked that every new or edited file be pasted in chat with its path (no more zips)
- 2026-11-01 · Claude · Wrote plan step 3 (errors, key check, /health, startup wiring) and its tests; pasted in chat
- 2026-11-01 · user · Neon test branch set up; migration, guard, auth, health and error-format tests all passed
- 2026-11-01 · Claude · Wrote plan step 4 (slots list, /reset, schemas, audit, db dict rows); logged D40; pasted files in chat
- 2026-11-01 · user · Uploaded clinicflow-web-main.zip and chose to use it (trimmed, rewired, separate Vercel deploy) instead of the earlier image
- 2026-11-01 · Claude · Read the template (React/Vite, ~9,000 lines, ClinicFlow API contract); logged D41, D42; amended documents; wrote CORS code and tests
- 2026-11-04 · Claude · Read the whole repo. Code was ahead of this log: create/get booking, cancel, the 50-way concurrency test and the lenient email rule (D43) already existed; `test_cancel_api.py` was missing. Ran everything on a local Postgres 16: 92 tests passed before changes
- 2026-11-04 · Claude · Wrote `tests/test_cancel_api.py` (8 tests, R8); fixed one over-long docstring in `app/services/bookings.py` and ran `ruff format` on four files (missing end-of-file newlines, one long signature); logged D43. Result: 100 passed, Ruff clean
- 2026-11-04 · Claude · Plan step 8: wrote `tests/test_idempotency_api.py` first (9 of 16 failed for the expected reason), then `app/repositories/idempotency.py`, `get_confirmed_for_slot`, the new `create_booking` and the `Idempotency-Key` header; logged D44. Result: 116 passed, 15 repeat runs of the concurrent tests green, Ruff clean
- 2026-11-04 · Claude · Plan step 9: wrote `tests/test_paging_api.py` first (all 21 failed: GET /bookings answered 405), then `PageResponse`, `list_for_email`, `list_bookings`, the `GET /bookings` route and paging limits in config. Found that uvicorn's access log printed the email from the URL; added `app/logsafe.py` and `tests/test_log_privacy.py` (access-log half of N4) and checked on a real server. Logged D45. Result: 139 passed, Ruff clean
