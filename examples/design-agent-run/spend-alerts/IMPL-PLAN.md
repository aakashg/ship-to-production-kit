Status: DRAFT - awaiting human approval

# IMPL-PLAN: Usage-based spend alerts

Version: v1 (headless draft, 2026-11-20). Do not start until the status line above is changed by a human **and** every `needs you` row in DECISIONS.md is answered (guardrail: stop and ask on unanswered `needs you`). One PR per milestone, each under about 400 changed lines; if a milestone grows past that, split it. Paths are proposals from ENG-PLAN (assumptions A1 to A5).

Total estimate: about 41 agent hours, plus human review time and a one-week shadow soak.

## M0. Confirm stack and wire the test harness (3h) - LOW risk
- **Goal:** replace guesses with facts. Fill CLAUDE.md commands, confirm the cost-estimate source, event channel, DB and email provider; make CI run a real test.
- **Files:** `CLAUDE.md`, `scripts/setup.sh`, `docs/features/spend-alerts/ENG-PLAN.md` (update A1 to A5), `tests/spend_alerts/conftest.py`.
- **Tests:** existing smoke test stays green; one fixture test that starts the test DB.
- **Human check:** read the updated ENG-PLAN assumptions section; confirm they match reality.

## M1. Pure crossing logic (4h) - LOW risk
- **Goal:** the correctness core, no I/O.
- **Files:** `app/spend_alerts/crossing.py`, `tests/spend_alerts/test_crossing.py`.
- **Tests:** property tests (boundary inclusive, integer math, jumps, budget raised and lowered, month boundary, leap-year February, UTC edge at 23:59:59 and 00:00:00).
- **Human check:** review a table of worked examples in the PR description against DECISIONS #7.

## M2. Schema migration (3h) - HIGH, human owner required
- **Goal:** additive tables `key_budgets`, `key_period_spend`, `processed_usage_events`, `spend_alert_events` with constraints and indexes.
- **Files:** `app/migrations/<ts>_spend_alerts.sql` (path per tool), `app/spend_alerts/repo.py` (skeleton), `tests/spend_alerts/test_migration.py`.
- **Tests:** up and down migration; UNIQUE constraint rejects duplicates; CHECK rejects non-positive budget.
- **Human check:** apply to staging DB; run `\d` on the tables; confirm down migration. DBA or CODEOWNER approves.

## M3. Usage event emit and aggregator, shadow mode (7h) - HIGH (hot path plus billing-adjacent)
- **Goal:** emit usage events behind a flag; aggregator applies idempotent increments and writes `suppressed/shadow` crossing rows. Nothing is sent.
- **Files:** gateway completion hook (path set in M0), `app/spend_alerts/aggregator.py`, `app/spend_alerts/repo.py`, `app/spend_alerts/config.py`, `tests/spend_alerts/test_aggregator.py`.
- **Tests:** duplicate delivery; two concurrent aggregators; out-of-order timestamps; month boundary; flag off means zero behaviour change; latency test shows no measurable change in hot path.
- **Human check (staging):** send 1,000 synthetic requests to a test key with a $1 budget; query `spend_alert_events` and see rows for 50/80/100 in shadow state and counters matching the sum of costs.

## M4. Budget API (5h) - HIGH (public API contract)
- **Goal:** PUT/GET/DELETE budget and the alerts-history endpoint, with authz and validation.
- **Files:** `app/spend_alerts/api.py`, `schemas.py`, router registration file, `tests/spend_alerts/test_api.py`, API docs (`docs/api/` if present).
- **Tests:** admin vs non-admin vs other org; validation edges ($0.99, $1, $1,000,000, 3 decimals, 6 recipients, bad email); 4xx vs 5xx; budget change semantics from ENG-PLAN section 6.
- **Human check (staging):** create, read, change, delete a budget with curl; change the budget below current spend and see the `budget_changed` row.

## M5. Notifier and email delivery (7h) - HIGH (external communication, customer data)
- **Goal:** outbox worker sends email, retries, handles bounce and suppression; templates with masked key and "estimated" labelling.
- **Files:** `app/spend_alerts/notifier.py`, `templates/spend_alert.txt`, `templates/spend_alert.html`, provider adapter, `tests/spend_alerts/test_notifier.py`.
- **Tests:** retry with backoff; max 24h then `failed`; hard bounce no retry; idempotency key per event; disabled budget suppresses; no full email or key secret in logs (log-capture test).
- **Human check (staging):** trigger 50/80/100 on a test key to internal mailboxes; read the three emails; confirm they render in two mail clients and contain no secret.

## M6. Observability, reconciler, runbook (6h) - LOW for docs and code, HIGH for `infra/` alarms (human owner)
- **Goal:** metrics, alarms, nightly reconciliation, dashboard, runbook, OBSERVABILITY.md updated.
- **Files:** `app/spend_alerts/reconcile.py`, metrics wiring, `docs/OBSERVABILITY.md`, `docs/runbooks/spend-alerts.md`, `infra/sandbox/` alarm definitions (prod via human PR), `tests/spend_alerts/test_reconcile.py`.
- **Tests:** seeded drift is detected; metric names match ENG-PLAN; alarm definitions validated by `terraform plan` in CI (paste plan in PR).
- **Human check (staging):** stop the aggregator for 3 minutes and see the lag alarm fire; restart and see catch-up.

## M7. Staged rollout (6h agent, mostly waiting) - HIGH
- **Goal:** shadow soak, internal pilot, pilot customers, 1%, 10%, 50%, 100%.
- **Files:** flag config only, `docs/features/spend-alerts/ROLLOUT-LOG.md` (new, optional).
- **Tests:** shadow vs reconcile comparison report must show zero missed and zero duplicate crossings before enabling send.
- **Human check:** a human flips each flag step. Rollback is `spend_alerts.send_enabled=false`. At each step compare gateway error rate and p95 latency to control (thresholds in OBSERVABILITY.md).

## Deferred (not in this plan)
Signed webhooks (unless DECISIONS #6 says v1), custom thresholds, hard cap, forecast alerts, recipient verification, org or team budgets.

## Changelog
- v1 (2026-11-20): initial headless draft. Not approved. No code written.
