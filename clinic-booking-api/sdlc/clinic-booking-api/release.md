# Release: Clinic booking API and booking web page

Derived from: plan.md (2026-10-31), test-plan.md (2026-10-31) · Status: accepted (user, 2026-10-31)
Release manager: user (D26) · Change-management reference: not required
Supporting skills: none

## Governing rule
The agent may act up to the production gate and cannot pass it.

## Approval gates
Each gate is a deterministic pre-action check (allow / ask / block). A block explains the reason and the route to approval.
| Gate | Trigger (action or path) | Decision | Approver | Where enforced |
|------|--------------------------|----------|----------|----------------|
| Production deploy | any deploy to the live Render service or the Vercel production site | block without release authorization | user (release manager) | Render auto-deploy off (`autoDeploy: false` in render.yaml, D27); Vercel production deploys only by the release manager (Git auto-deploy for the production branch switched off once the site is final); the agent holds no Render or Vercel credentials or deploy hooks |
| Merge to main | pull request merge | block until CI is green and the code owner merges | user | GitHub branch protection: pull request plus passing CI required; the agent never approves or merges |
| Protected paths (rule only, D29) | edits to applied `migrations/V*.sql`, `render.yaml`, `requirements*.txt`, secrets | ask (written rule, reviewed in REVIEW.md Compliance and Security passes) | user | AGENTS.md "Protected paths"; not a hard block |

Residual risk (D29): only the production deploy is a hard gate, so an agent could change migrations, `render.yaml` or the dependency files in a pull request without being blocked. Review and CI are the safety net, and nothing reaches production without the manual deploy.

## Environments and autonomy
| Environment | What the agent may do | Human gate |
|-------------|-----------------------|------------|
| Development (local + Neon test branch) | build, test, lint, run locally, reset the test database freely | none |
| Staging | Not applicable: the Render free tier gives no separate staging service (D27) | none |
| Production (Render API + Neon main branch + Vercel web page) | prepare the release only: green CI, changelog, pre-release checklist | user authorizes and triggers the deploy |

## Pipeline
- CI/CD platform: GitHub Actions (CI on every push, D22); Render hosts the API and Vercel hosts the web page; both deploys are triggered manually.
- Read-only agent steps: triage a failed build, summarize a flaky test, draft the changelog and pre-release checklist.
- Write steps (always arrive as a PR through branch protection): fix lint (`ruff format .`), update README and docs, address review comments.
- Execution: sandboxed runner; only `TEST_DATABASE_URL` as an encrypted secret; no production credentials (`DATABASE_URL`, `API_KEY`, Render and Vercel deploy credentials) are ever given to the agent or CI.
- Tools exposed to the agent for production: read-only status check (`GET /health`). No deploy or rollback tools.
- Migrations are forward-only and additive (D28), so the previous app version keeps working after a rollback.

## Pre-release checklist (agent prepares, user confirms)
- [ ] CI green on main (build, test incl. browser test, lint).
- [ ] Production environment variables set in Render: `DATABASE_URL`, `API_KEY`; none committed to Git.
- [ ] Vercel project created from `web/`; its env vars `VITE_API_BASE_URL` (the Render API URL) and `VITE_API_KEY` set (build-time, public by nature, D11); Render has `CORS_ORIGINS` set to the exact Vercel URL (D42).
- [ ] Vercel auto-deploy of the production branch switched off once the site is final (brief: no changes after submission).
- [ ] Neon production branch separate from the test branch.
- [ ] Cold start measured (under 60 s); external uptime monitor pinging the public /health every 5 minutes (D31).
- [ ] Live API checks pass against the https URL; booking survives a restart.
- [ ] Rollback rehearsed once (below).
- [ ] Key not visible in the repo or the Loom.

## Rollback
- Command: Render dashboard, redeploy the previous successful deploy (one action by the release manager; D28).
- Web page: Vercel dashboard, promote the previous deployment (instant rollback); same rehearsal rule.
- Last rehearsed in staging: not yet (no staging; rehearse once on the live service before submission, record the date here).
- Rehearsal cadence: once before submission.

## Freeze after submission
The brief says to keep the service running and unchanged until Koya makes contact: no deploys, no key rotation, no `/reset` by anyone else, the uptime monitor stays on. Rotate the key only after Koya has finished (D11).

## Open questions
- [ ] Neon and Render free-plan limits (database sleep, retention, monthly hours) may affect "keep it running" · UNRESOLVED (owner: user; checked before submission)
- [ ] Whether GitHub branch protection can require passing CI without a second approver on a solo repo · UNRESOLVED (owner: user, checked when the repo is created)

## Measurement
- Leading: time to first review; time waiting on each gate; share of pipeline failures triaged without paging a human.
- Lagging: defects escaping to production; gate violations reaching production; DORA measures (deploy frequency, lead time, change failure rate, time to restore).