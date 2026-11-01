# Review instructions

Applied to every pull request, whether a human or an agent reviews it. Findings inform the decision; the code owner (the user) approves the merge. The agent that wrote a change never approves it.

## Passes
Run these passes and tag each finding with its pass:
- **Bugs**: logic errors, broken edge cases, subtle regressions, race conditions around booking, cancel and retry.
- **Security**: missing or bypassable API key check, injection (SQL built by string concatenation), secrets in code or logs, stack traces in responses.
- **Compliance**: the change matches `sdlc/clinic-booking-api/spec.md`, `plan.md` and the decisions in `WORKLOG.md`. Flag drift from plan.md, changes to the core Booking response for extras (D6), and edits to applied migrations.
- **Privacy**: names or emails in logs, error messages, URLs or audit lines (N4, N5); audit lines carry ids only.
- **Accessibility**: web page labels, keyboard use, visible focus, 4.5:1 contrast, "Taken" label not colour alone, touch targets of 44 px, status messages announced (N7).

## Severity
- **Important**: would break behavior, leak data, or breach a policy. Must be resolved before merge.
- **Nit**: style, naming, minor readability.

## Cap the nits
Report at most 5 nits per review; summarize the rest as a count.

## Do not report
- Generated files and caches (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`).
- Anything CI already enforces (Ruff lint and formatting, import errors, test failures).

## Weakened tests
Reject diffs that delete, skip or weaken tests. During a fix task, test files change only in the test-first commit (test-plan.md).

## Feedback into AGENTS.md
When a review flags the same mistake for the second time, add the correction to AGENTS.md in the same PR. Also flag when a change makes AGENTS.md outdated.

## Tuning
After Koya contacts the user, the user rates the findings and adjusts this file.
