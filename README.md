# Clinic booking API

A small appointment-booking service for a clinic: an HTTP API (FastAPI + PostgreSQL) and a web page (React) where a patient picks a day and time, books, looks a booking up by its ID or email, and cancels it. There is also a simple clinic dashboard and a simulated payment step.

Built for the Koya Cohort 4 assessment, Task 1.

## Live

| What | Address |
|------|---------|
| API | `https://clinic-booking-api-ayhl.onrender.com` |
| Web page | `https://clinic-booking-api-mocha.vercel.app/` |
| Health check | `https://clinic-booking-api-ayhl.onrender.com/health` |

The API key is not in this repository. It was given to Koya in the submission form.

The API runs on a free host that sleeps when idle, so the first request after a quiet spell can take up to a minute.

## API

Every endpoint except `/health` needs the header `X-API-Key` (a missing or wrong key is a 401). Every error is `{"error": "<message>"}`. All times are ISO 8601 in UTC.

### Core endpoints

| Method and path | What it does | Answers |
|-----------------|--------------|---------|
| `GET /slots` | All slots, earliest first, each with `available` true or false. Optional `?provider=` shows one provider's slots | 200 |
| `POST /reset` | Replace all slots and clear all bookings. Body is `{"slots":[...]}` or a bare list; each slot is `{id, provider, start, end}` | 200 `{"slots": N}`, 400 |
| `POST /bookings` | Book a slot: `{slot_id, name, email}`. Optional `Idempotency-Key` header | 201 booking, 400, 404, 409 (slot taken), 422 (key reused with a different body), 429 |
| `GET /bookings/{id}` | One booking | 200, 404 |
| `GET /bookings?email=&limit=&cursor=` | A person's bookings, oldest first: `{bookings, next_cursor}` | 200, 400 |
| `DELETE /bookings/{id}` | Cancel a booking and free the slot. Returns the booking with `status: "cancelled"` | 200, 404, 409 (already cancelled) |
| `GET /health` | Public. `{"status":"ok"}` after a database check | 200, 503 |

A booking looks like `{id, slot_id, name, email, status, created_at}` with `status` either `confirmed` or `cancelled`.

### Extra endpoints

These are additive. They never change the core booking response.

| Method and path | What it does | Answers |
|-----------------|--------------|---------|
| `POST /bookings/{id}/payment` | Pretend to pay for a confirmed booking (demo, no money, no body). Paying again returns the same payment | 200 `{booking_id, status, reference, paid_at}`, 404, 409 (cancelled) |
| `GET /bookings/{id}/payment` | Payment state, `paid` or `unpaid` | 200, 404 |
| `GET /dashboard/summary?date=YYYY-MM-DD` | Counts for one UTC day (default today): `{date, booked, cancelled, open_slots, total_slots}` | 200, 400 |
| `GET /dashboard/appointments?date=YYYY-MM-DD` | That day's appointments as a list, with the patient name masked (`Ada O.`), never emails | 200, 400 |

Interactive docs are at `/docs`.

## How it works

- **No double booking.** The database refuses it: a partial unique index allows one confirmed booking per slot. A test fires 50 requests at one slot at the same time and expects exactly one 201 and 49 409. A cancelled slot can be booked again.
- **Safe retries.** Send an `Idempotency-Key` header and the same request returns the same booking (201) without booking again. The same key with a different body returns 422. A blank key is ignored and a key over 255 characters is a 400. Without a key, a repeat of an already booked slot returns 409.
- **Paging.** `GET /bookings` needs `email` (matched ignoring capitals). `limit` is 1 to 50 (default 10); anything else is a 400. Each response has `next_cursor`; pass it back as `cursor` for the next page. `next_cursor` is `null` on the last page. Cancelled bookings are listed too.
- **Rate limit.** 5 booking attempts per minute per client IP address (a sliding 60-second window), whatever email is in the body, then 429 with a `Retry-After` header in seconds. Attempts that fail with 400, 404 or 409 count; refused ones (429) do not; a request with a wrong API key is not counted. The client address is the first address in `X-Forwarded-For` (set by Render's proxy), or the direct connection address when that header is missing or not an IP. `POST /reset` clears the counters. Set `RATE_LIMIT_PER_MINUTE` to change the limit. The limiter is in memory, so run exactly one worker.
- **Validation.** `name` is 1 to 200 characters. `email` must look like `something@something.something` (a lenient check, so addresses on test domains are accepted). A slot that has already started cannot be booked (400). Bad input is a 400.
- **Privacy.** Names and emails never appear in logs or error messages. Audit lines carry ids only. The access log hides query strings, because `GET /bookings?email=` carries an email. The dashboard returns masked names only.
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

Migrations run when the app starts. To load slots, generate a body and send it to `POST /reset`:

```
python scripts/make_slots.py 90 > slots.json
```

The web page:

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
| `RATE_LIMIT_PER_MINUTE` | API | Booking attempts a minute per client IP address (default 5) |
| `TEST_DATABASE_URL` | tests | A separate test database. Tests refuse to run against `DATABASE_URL` |
| `VITE_API_BASE_URL` | web | The API address, set at build time |
| `VITE_API_KEY` | web | The same key, set at build time |

## Tests

```
cd clinic-booking-api
export TEST_DATABASE_URL="postgresql://USER:PASSWORD@HOST/TESTDB"
pytest                       # API tests against real PostgreSQL
ruff check . && ruff format --check .

pnpm --dir web typecheck && pnpm --dir web lint && pnpm --dir web test && pnpm --dir web build
pnpm --dir web exec playwright install chromium   # once
pnpm --dir web test:e2e      # page tests at 390 px and 1280 px, against a fake API
```

GitHub Actions runs both on every push.

The manual workflow `verify-live.yml` **resets the live data**. Do not run it after submission.

## Decisions worth knowing

The full list is in `clinic-booking-api/sdlc/clinic-booking-api/WORKLOG.md`. These are the main ones:

- **Assumptions.** The brief did not say exactly how paging, retries, rate limiting and `/reset` should look, so I chose sensible shapes and wrote tests for them. I could not check them against the full Koya specification.
- **The API key is public in the web page.** The page is a static site, so its key can be read by anyone. I accepted that (D11): the key is never committed, and it should be rotated once Koya has finished.
- **Lenient email check** (D43), so addresses on test domains are accepted.

## Known limits

- Free hosting: cold starts after idle time, and a small database.
- The rate limit is per client IP address and kept in memory, so it resets when the service restarts and only works with a single worker. Several patients behind one shared connection (for example a clinic's wifi) share one allowance.
- A "day" on the dashboard is a UTC day, so slots starting between 00:00 and 01:00 Lagos time fall on the previous day.
- Payments are simulated: no money moves, and there is no refund.

## Project layout

```
clinic-booking-api/
  app/            routers, services, repositories (SQL only), security, rate limiter
  migrations/     forward-only SQL migrations
  scripts/        make_slots.py (slot generator), verify_live.py
  tests/          pytest suite (real PostgreSQL)
  web/            React + Vite page and dashboard (hosted on Vercel)
  sdlc/           intent, spec, plan, test plan, release plan, decision log
render.yaml       Render deployment settings
```