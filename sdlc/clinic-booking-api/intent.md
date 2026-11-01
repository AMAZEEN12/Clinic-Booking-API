# Intent: Clinic booking API and booking web page

Author: user (candidate, Koya Cohort 4 assessment) · Product owner: user (self-approve) · Status: accepted
Created: 2026-10-31 · Accepted: 2026-10-31 by user
Source document: Koya Cohort 4 assessment Task 1 brief + Clinic booking API OpenAPI 1.0 schema (pasted in chat) · Entry route: idea (brief)
Requester: Koya Academy (reviews only the final submission)
Source of truth: repository
Supporting skills: none (assumed baseline policy)

> Amended 2026-10-31 (D35, D36): booking page responsive on mobile and desktop; clinic dashboard added as a desktop extra. See WORKLOG.md.

## Problem
A clinic has no way for patients to book appointment slots online. It needs an API that lets patients list available slots, book one and look it up, plus a simple web page that uses the API so a patient can see available slots, book one and see the confirmation. Both must be deployed at an https URL and keep their data between requests.

## Proposed outcome
A patient opens the web page, sees which slots are free, books one with name and email, and sees a confirmation. The API behind it only accepts requests with the API key, rejects bad input, never double-books a slot (even under simultaneous requests), supports cancellation, never creates duplicates when a request is retried, lets a person page through their bookings, and limits spam bookings. The exact endpoints and responses follow the technical spec: POST /reset, GET /slots, POST /bookings, GET /bookings, GET /bookings/{id}, DELETE /bookings/{id}; errors look like {"error": "<message>"}.

## Affected users and systems
- Users: patients booking slots; clinic staff viewing the day's appointments on a desktop dashboard (extra); Koya Academy assessors running automated checks against the API; the candidate recording a Loom walkthrough.
- Systems: a new API service, a database, a static or server-rendered web page, a public GitHub repo, and a hosting platform (Render, Vercel, Supabase, Neon or similar).

## Constraints
- Contract: follow the Koya technical spec closely; every request needs the X-API-Key header (missing or wrong key returns 401).
- Deployment: https URL; bookings must persist across requests (use a database if serverless); keep it running and unchanged after submission until Koya makes contact.
- Cost: free tiers only.
- Data: names and emails are personal data; keep them out of logs.
- Timeline: submit within one week of 2026-10-31.
- Submission needs: API base URL, API key (not recorded in repo or worklog), web page URL, public GitHub repo (or invite quadri40), Loom of 5 minutes or less, and a short note on how far it got, the two biggest decisions and next steps.
- Any language, framework, database and host; AI assistance allowed.

## Out of scope
- Changing or breaking the core API contract for any extra feature: POST /bookings must keep working with only slot_id, name, email and the X-API-Key.
- Extras are optional and additive and are built only after Levels 1-5 are solid (decision D6). Candidates: login and user accounts on the web page, simulated payments (no real money), in-app notifications, and email notifications (stretch). The clinic dashboard from the reference design is now an in-scope desktop extra (D35, D36).
- Real payment processing and admin tooling beyond /reset.

## Success criteria
- All 5 levels pass the Koya checks: list/book/look up; API key and validation; no double-booking under concurrency plus cancellation; idempotent retries plus paging; spam protection.
- The web page works end to end (see slots, book, see confirmation) on its deployed URL.
- At least one extra (for example a simulated payment) works without affecting the core contract; the booking page works on phone and desktop; the desktop clinic dashboard shows the day's appointments with masked patient names.
- Submission complete within one week, with a Loom of 5 minutes or less.

## Open questions
- [ ] Spec gaps not in the pasted schema: GET /bookings query parameters and paging shape, how idempotent retries are signalled, rate-limit response and thresholds, /reset request body (owner: user, can paste the full spec from koyaacademy.com/assessment-api) · UNRESOLVED
- [ ] Language, framework, database and host (owner: user, decided at Design) · UNRESOLVED
- [ ] Which extra to deliver first (owner: user) · UNRESOLVED

## Measurement
- Leading: time from first conversation to accepted intent.md (git timestamps).
- Lagging: whether this intent is accepted into Design, and how many edits it gets after spec.md is first committed.
