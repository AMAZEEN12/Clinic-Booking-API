# Execution: Clinic booking API and booking web page

The runbook for taking this change from its current state to production and into maintenance. Any human or agent can follow it. Generated from the artifacts below; update it whenever one of them changes. Progress against these steps, plus all decisions and conventions, is tracked in `WORKLOG.md` in this folder. Log each completed step there.

Change slug: `clinic-booking-api` · Last updated: 2026-10-31 · Current stage: Build (all lifecycle artifacts accepted; no code written yet)

## Artifact chain
| Stage | Artifact | Status | Owner | Approved by / date |
|-------|----------|--------|-------|--------------------|
| Plan | intent.md | accepted | user | user, 2026-10-31 |
| Design | spec.md | accepted | user | user, 2026-10-31 |
| Build | plan.md | accepted | user | user, 2026-10-31 |
| Build | AGENTS.md (repo) | accepted | user | user, 2026-10-31 |
| Test | test-plan.md | accepted | user | user, 2026-10-31 |
| Deploy | REVIEW.md (repo) | accepted | user | user, 2026-10-31 |
| Deploy | release.md | accepted | user | user, 2026-10-31 |
| Maintain | monitoring.md | accepted | user | user, 2026-10-31 |

Source document: Koya Cohort 4 assessment Task 1 brief + OpenAPI 1.0 schema (pasted in chat). Visual reference: `docs/design/web-reference.jpeg`. Decisions D1-D34 are in `WORKLOG.md`.

## Supporting skills
| Skill | Location (folder or link) | Version / date | Stages it shaped |
|-------|---------------------------|----------------|------------------|
| none | | | |

Candidate skills to write (conventions found during the interview):
- Additive-only database migrations (so rollback of the app stays safe, D28) · owner: user · also needs a hard guardrail: yes (CI check on new migration files)
- No names or emails in logs (N4) · owner: user · also needs a hard guardrail: yes (already partly covered by `LogPrivacyTest`; add a log-scan step in CI)

## Setup before automation starts
- [ ] GitHub repository created (public, or invite `quadri40`); branch protection on main: pull request plus passing CI required, code owner is the user (D26); confirm it works on a solo repo
- [ ] Neon project with two branches: production and test; connection strings stored only as secrets (`TEST_DATABASE_URL` in GitHub Actions; `DATABASE_URL` in Render)
- [ ] Render web service created with `autoDeploy: false`; env vars `DATABASE_URL`, `API_KEY` set (D27, D29)
- [ ] `.github/workflows/ci.yml` running build, test, lint with the test-DB secret (D22)
- [ ] Free external uptime monitor pinging `/health` every 5 minutes, email alerts on (D31-D33)
- [ ] Eval suite skeleton in `evals/` (stretch, D25)
- [ ] Rollback rehearsed once on the live service and the date recorded in release.md (D28; no staging exists)

## Steps
Each step: actor · input → action → output · gate before the next step. "Plan step N" means the numbered steps in plan.md.

1. **Set up accounts and secrets** · human (user) · release.md setup list → create repo, Neon branches, Render service, GitHub secret · Gate: user confirms the setup checklist above (secrets never pasted into chat or files).
2. **Scaffold project** · agent · plan.md step 1, AGENTS.md → pom, Maven wrapper (pin latest Boot 4.0.x), app class, config, .gitignore · Gate: `./mvnw -q -DskipTests package` passes.
3. **Schema and test guard** · agent · plan step 2 → Flyway V1, `PostgresTestBase` with the prod-database guard · Gate: guard test passes; migration applies to the test branch.
4. **Error model, key filter, health** · agent · plan step 3 → R5, R14, N1, N8, N9 · Gate: `AuthApiTest`, `ErrorFormatApiTest`, `HealthApiTest` green.
5. **Slots and reset** · agent · plan step 4 → R1, R2 · Gate: `SlotsApiTest`, `ResetApiTest` green.
6. **Create and get booking** · agent · plan step 5 → R3, R4, R6 · Gate: `BookingApiTest`, `ValidationApiTest` green.
7. **Double-booking guard** · agent · plan step 6 → R7, N2 · Gate: `ConcurrencyApiTest` green (one 201, 49 409); review the SQL.
8. **Cancel, idempotency, paging** · agent · plan steps 7-9 → R8, R9, R10 (in this order, they share `BookingService`) · Gate: `CancelApiTest`, `IdempotencyApiTest`, `PagingApiTest` green.
9. **Rate limit, audit and privacy** · agent · plan steps 10-11 → R11, N4, N5 · Gate: `RateLimitApiTest`, `LogPrivacyTest` green.
10. **Web page** · agent · plan step 12, design reference → R12, N7 · Gate: `WebPageBrowserTest` green plus the manual checklist (user).
11. **Levels 1-5 checkpoint** · human (user) · all tests, local run → decide to start extras (D6) · Gate: user confirms every level is solid before the payment extra starts.
12. **Simulated payment extra** · agent · plan step 14 → R13 · Gate: `PaymentApiTest` green and core Booking schema unchanged.
13. **Package and deploy** · agent prepares, human deploys · plan step 15, release.md → Dockerfile, render.yaml, README, pre-release checklist · Gate: CI green on main, user triggers the Render deploy (production gate, D26/D27).
14. **Verify live service** · human + agent · test-plan.md done-targets → run API checks against the https URL, restart check, cold-start timing, rollback rehearsal, uptime monitor on · Gate: all pass; user signs off.
15. **Submit** · human (user) · Koya form → API base URL, API key, page URL, repo link, Loom (5 min or less, key not shown), short note (how far, two biggest decisions, next steps) · Gate: user submits; the service then stays frozen (release.md Freeze).
16. **Maintain** · human + agent · monitoring.md → watch alerts and Render metrics daily; agent diagnoses and prepares fix PRs only · Gate: user triages every finding.

## Commands
```
build:    ./mvnw -q -DskipTests package
test:     ./mvnw test                      # needs TEST_DATABASE_URL (Neon test branch)
lint:     ./mvnw spotless:check            # fix: ./mvnw spotless:apply
run:      DATABASE_URL=... API_KEY=... ./mvnw spring-boot:run
deploy:   Render dashboard, manual deploy   # production requires user (release manager)
rollback: Render dashboard, redeploy previous successful deploy   # user only
```

## Parallel work
- Run at the same time (separate isolated workspaces): web page (step 10, needs only the contract from steps 5-6), Dockerfile + render.yaml + README (step 13 files), rate limiter and its test (step 9).
- Run in order: steps 2-9 (they build on each other and share `BookingService`, `BookingRepository`, `BookingController`), then 11 → 12 → 13 → 14 → 15.

## Human decision points
| Decision | Approver | Evidence they review |
|----------|----------|----------------------|
| Merge each pull request | user (code owner) | green CI, REVIEW.md findings |
| Start the extras after Levels 1-5 (D6) | user | all level tests green, local demo |
| Production deploy | user (release manager) | pre-release checklist, CI on main |
| Rollback | user | alert, Render logs and metrics |
| Re-check the guessed Koya contract (D12-D15) | user | full Koya spec if it becomes available |
| Submit to Koya, then keep the service frozen | user | live checks, Loom, README |
| Rotate the API key (only after Koya finishes) | user | confirmation from Koya |
| Triage monitoring findings | user | agent's diagnosis intent.md |

## Automation roadmap
| Trigger | Starts | Automated now? |
|---------|--------|----------------|
| intent.md accepted | spec pass | no (manual) |
| spec.md accepted | planning | no (manual) |
| PR opened or pushed | build, test, lint in GitHub Actions | yes, once `ci.yml` exists (step 1-2) |
| PR merged | pipeline up to a ready release | partial: CI only; deploy stays manual (D27) |
| alert threshold crossed | new intent.md | no (user pastes the alert into a session, monitoring.md) |

## Measurement
| Stage | Leading indicator | Lagging indicator |
|-------|-------------------|-------------------|
| Plan | time from first conversation to accepted intent.md | intent.md edits after spec.md is first committed |
| Design | time from intent.md commit to spec.md commit | spec.md commits after plan.md was first committed |
| Build | share of changes that merge on the first implementation pass; time from plan acceptance to merged PR | rework cycles per change; merged diff vs plan.md |
| Test | first-pass CI success rate; eval pass rate | regressions caught in CI vs production |
| Deploy | time to first review; time waiting on each gate | defects escaping to production; gate violations; DORA measures |
| Maintain | time from alert to intent.md in the triage queue | share of findings that become merged fixes; repeat incidents |

## Unresolved questions
| Question | From artifact | Owner | Needed by step |
|----------|---------------|-------|----------------|
| Paging, idempotency, rate-limit and /reset choices are decided but unverified against the full Koya spec (C1, D12-D15) | spec.md | user | before step 15 (submit) |
| Exact list of the 10 eval tasks | test-plan.md | user | after step 11 (stretch) |
| Playwright version and CI browser-install step | test-plan.md | agent | step 4 (ci.yml) and step 10 |
| Exact latest Spring Boot 4.0.x patch to pin (checked online when the pom is written) | plan.md | agent | step 2 |
| Neon and Render free-plan limits for "keep it running" (sleep, retention, hours) | release.md | user | step 13 |
| Whether GitHub branch protection can require passing CI on a solo repo without a second approver | release.md | user | step 1 |
| Which free uptime monitor; confirm 5-minute interval and email alerts | monitoring.md | user | step 14 |
| Real latency and memory baselines after the service is live | monitoring.md | user | step 16 |
| Submission values (API base URL, API key, page URL, repo, Loom link): not recorded in any file | intent.md | user | step 15 |
