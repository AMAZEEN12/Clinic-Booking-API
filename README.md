# Clinic booking API

A small appointment-booking service for a clinic: an HTTP API (FastAPI + PostgreSQL) and a web page (React) where a patient picks a day and time, books, looks a booking up by its ID, and cancels it.

Built for the Koya Cohort 4 assessment, Task 1.

## Live

| What | Address |
|------|---------|
| API | `<fill in: Render URL>` |
| Web page | `<fill in: Vercel URL>` |
| Health check | `<Render URL>/health` |

The API key is not in this repository. It was given to Koya in the submission form.

The API runs on a free host that sleeps when idle, so the first request after a quiet spell can take up to a minute.

## API

Every endpoint except `/health` needs the header `X-API-Key`. Every error is `{"error": "<message>"}`.

| Method and path | What it does | Answers |
|-----------------|--------------|---------|
| `GET /slots` | All slots with `available` true or false | 200 |
| `POST /reset` | Replace all slots (`{"slots":[...]}` or a bare list) and clear all bookings | 200 `{"slots": N}`, 400 |
| `POST /bookings` | Book a slot: `{slot_id, name, email}` | 201, 400, 404, 409 (slot taken), 429 |
| `GET /bookings/{id}` | One booking | 200, 404 |
| `GET /bookings?email=&page=&limit=` | A person's bookings, newest first: `{items, page, limit, total}` | 200, 400 |
| `DELETE /bookings/{id}` | Cancel a booking; the slot can be booked again | 200, 404 |
| `POST /bookings/{id}/payment` | Extra: pretend to pay for a confirmed booking (demo, no money, no body) | 200 `{booking_id, status, reference, paid_at}`, 404, 409 (cancelled) |
| `GET /bookings/{id}/payment` | Extra: payment state, `paid` or `unpaid` | 200, 404 |
| `GET /health` | Public. `{"status":"ok"}` after a database check | 200, 503 |

Interactive docs are at `/docs`.

## How it works

- **No double booking.** The database refuses it: a partial unique index allows one confirmed booking per slot. A test fires 50 requests at one slot at the same time and expects exactly one 201 and 49 409.
- **Safe retries.** Send an `Idempotency-Key` header and the same request returns the same booking. Without a key, the same slot and email returns the existing booking.
- **Rate limit.** 10 bookings a minute per key and client address, then 429 with `Retry-After`. Set `RATE_LIMIT_PER_MINUTE` to change it. The limiter is in memory, so run exactly one worker.
- **Privacy.** Names and emails never appear in logs or error messages. Audit lines carry ids only. The access log hides query strings, because `GET /bookings?email=` carries an email.
- **Times** are stored and returned in UTC. The web page shows clinic time (Lagos).

## Run it locally

You need Python 3.12 or newer and a PostgreSQL database.

```
cd clinic-booking-api
python -m venv .venv
# activate it, then:
pip install -r requirements-dev.txt

export DATABASE_URL="postgresql://USER:PASSWORD@HOST/DB?sslmode=require"
export API_KEY="pick-a-long-random-value"
export CORS_ORIGINS="http://localhost:5173"
uvicorn app.main:app --reload
```

Migrations run when the app starts. The web page:

```
cd clinic-booking-api/web
pnpm install
# create .env.local with VITE_API_BASE_URL=http://localhost:8000 and VITE_API_KEY=<the same key>
pnpm dev
```

## Settings

| Variable | Where | Meaning |
|----------|-------|---------|
| `DATABASE_URL` | API | PostgreSQL connection URL (required) |
| `API_KEY` | API | The key clients send in `X-API-Key` (required) |
| `CORS_ORIGINS` | API | Web page address(es) allowed to call the API, comma-separated |
| `RATE_LIMIT_PER_MINUTE` | API | Bookings a minute per key and address (default 10) |
| `TEST_DATABASE_URL` | tests | A separate test database. Tests refuse to run against `DATABASE_URL` |
| `VITE_API_BASE_URL` | web | The API address, set at build time |
| `VITE_API_KEY` | web | The same key, set at build time |

## Tests

```
cd clinic-booking-api
export TEST_DATABASE_URL="postgresql://USER:PASSWORD@HOST/TESTDB"
pytest                       # 178 API tests against real PostgreSQL
ruff check . && ruff format --check .

pnpm --dir web typecheck && pnpm --dir web lint && pnpm --dir web test && pnpm --dir web build
```

GitHub Actions runs both on every push.

## Decisions worth knowing

The full list is in `clinic-booking-api/sdlc/clinic-booking-api/WORKLOG.md`. These are the main ones:

- **Assumptions.** The brief did not say how paging, retries, rate limiting and `/reset` should look, so I chose sensible shapes (decisions D12 to D15, D40, D44 to D46) and wrote tests for them. I could not check them against the full Koya specification.
- **The API key is public in the web page.** The page is a static site, so its key can be read by anyone. I accepted that (D11): the key is never committed, and it should be rotated once Koya has finished.
- **Lenient email check.** `something@something.something`, so addresses on test domains are accepted (D43).

## Known limits

- Free hosting: cold starts after idle time, and a small database.
- Extras: the simulated payment endpoints are built (see the table above); the clinic dashboard is not built yet.
- The rate limit applies to every client, so a tool that books many slots in under a minute gets 429.

## Project layout

```
clinic-booking-api/
  app/            routers, services, repositories (SQL only), security, rate limiter
  migrations/     forward-only SQL migrations
  tests/          pytest suite (real PostgreSQL)
  web/            React + Vite page (hosted on Vercel)
  sdlc/           intent, spec, plan, test plan, release plan, decision log
render.yaml       Render deployment settings
```