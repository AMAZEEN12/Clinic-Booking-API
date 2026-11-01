# Monitoring: Clinic booking API and booking web page

Derived from: intent.md success criteria, release.md · Status: accepted (user, 2026-10-31)
Service owner: user · On call: user (only responder, email alerts, D33)
Supporting skills: none

## Principle
Detection stays deterministic: the external uptime monitor applies fixed thresholds, with no model involved. The agent is invoked only after an alert fires, and the tier sets what it may do. The agent holds no production credentials (release.md), so it works from the evidence the user pastes in and from the public `/health` check.

## Metrics
Thresholds below are assumed starting values (UNRESOLVED until measured on the live service).
| Metric | Source | Baseline / target | Why it matters |
|--------|--------|-------------------|----------------|
| Availability: `/health` returns 200 | external uptime monitor (every 5 min) | 100% of checks | The brief says to keep it running; a down service fails Koya's checks |
| `/health` latency | uptime monitor | under 2 s warm; first ping after sleep may exceed it | Slow responses can time out a grader request (N6, C2) |
| 5xx error count | Render metrics (checked by hand, no alert, D32) | 0 | Shows broken endpoints or database trouble |
| Memory use | Render metrics (checked by hand) | under 80% of the instance limit | A small free instance can run out of memory and restart |
| Database reachability | `/health` returns 503 when `SELECT 1` fails | always 200 | Neon sleeping or unavailable would break every booking |

## Alert thresholds and response tiers
Fixed thresholds replace statistical bands: a one-week, single-instance service has no 30-day baseline to learn from. Revisit once real traffic exists.
```yaml
metric: health_availability
threshold: 2 consecutive failed checks (~10 min)
tiers:
  warn:  { action: log }                                   # 1 failed check
  alert: { action: diagnose, tools: "read-only", notify: email }   # 2 consecutive failures
metric: health_latency
threshold: over 2 s on 2 consecutive checks (first ping after a sleep ignored)
tiers:
  alert: { action: diagnose, tools: "read-only", notify: email }
  persistent: { action: propose, routes: [pull_request] }  # repeats for more than 1 hour
```
Error spikes and memory are reviewed by hand in Render metrics, not alerted (D32). Check the inbox and the Render dashboard daily until Koya contacts you (D33).

## Trigger layer
- Source: the free uptime monitor emails the user when a threshold is crossed (D31, D32).
- The agent does not run on a schedule. The user opens a session and pastes the alert, the relevant Render logs and metrics; the agent runs stateless, in a sandbox, with no production credentials.
- Read-only tools available to the agent: `GET /health`, the pasted logs, the repository and CI results.

## Closing the loop
1. The agent writes its diagnosis as a new `sdlc/<new-slug>/intent.md` (anomaly, evidence, proposed outcome, affected systems, open questions) and, where a code fix is warranted, prepares it as a pull request (D34).
2. The user triages: fix now, schedule, or dismiss. Dismissals tune the thresholds.
3. The user approves and triggers any deploy manually (release.md); a rollback is the user's action in the Render dashboard.
4. When the fix ships, add an eval for the incident (test-plan.md, D25).

## Pre-approved runbooks
| Runbook | When the agent may trigger it | Approved by |
|---------|-------------------------------|-------------|
| None | The agent may diagnose and prepare a fix as a pull request only (D34). Rollback, redeploy and any production change stay with the user | user |

## Incident channel
- Channel: email alerts to the user, plus the working conversation with the agent · The agent participates under its own identity: no (it has no channel access).
- Post-mortems: `lessons/<YYYY-MM>-<slug>.md`

## Open questions
- [ ] Which free uptime monitor, and whether its free plan allows a 5-minute interval and email alerts · UNRESOLVED (owner: user, when setting it up)
- [ ] Real baselines for latency and memory after the first days live · UNRESOLVED (owner: user)

## Measurement
- Leading: time from alert to an intent.md in the triage queue.
- Lagging: share of findings that become merged fixes; repeat incidents of the same class.
