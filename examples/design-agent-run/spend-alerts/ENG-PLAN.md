# ENG-PLAN: Usage-based spend alerts

Version: v1 (headless draft, 2026-11-20).

## 0. Assumptions this plan stands on (all **[needs you]**, see DECISIONS #1)
The repo is an empty template: `app/` is a README, `tests/` has one smoke test, `infra/*` are stubs, and CLAUDE.md commands are unfilled. I therefore assume:
- A1. Python service with pytest (the only hint is `tests/test_smoke.py`). Paths below use `app/spend_alerts/`; rename to match the real layout.
- A2. The gateway already computes a per-request cost estimate and has a request id, API key id, org id and completion timestamp for every request.
- A3. A relational database (Postgres semantics) and some async channel (queue or log stream) already exist. If not, M0 adds the smallest viable one and this plan changes.
- A4. An existing authn/authz layer can tell us "caller is admin of the org that owns this key".
- A5. An email-sending capability or provider exists or will be chosen (DECISIONS #6).

## 1. Architecture
Keep the request hot path unchanged. Spend alerting is a side-channel fed by events.

```
gateway request completes
   |  (existing cost estimate)
   v
emit usage event {request_id, key_id, org_id, cost_micro_usd, ts}   <- only change on the hot path
   |
   v   at-least-once async channel (A3)
aggregator (app/spend_alerts/aggregator.py)
   1. dedupe by request_id
   2. period = month_of(ts, UTC)
   3. UPDATE key_period_spend SET spent += cost RETURNING old, new
   4. crossing.evaluate(old, new, budget) -> thresholds crossed
   5. INSERT spend_alert_events ... ON CONFLICT DO NOTHING (outbox row, state=pending)
   |
   v
notifier worker (app/spend_alerts/notifier.py): claims pending rows, renders, sends, marks sent/failed, retries with backoff
   |
   v
email provider (and later webhook)
```
Nightly reconciler (app/spend_alerts/reconcile.py) recomputes open-period spend from the usage ledger and compares it with the counters.

Why this shape: no new latency or failure mode in the gateway; the DB unique constraint is the only dedupe source of truth; the outbox row makes "decide to alert" atomic with "counter moved", so a crash cannot lose an alert.

## 2. Pure logic (no I/O, easy to test)
`app/spend_alerts/crossing.py`
- `period_start(ts) -> date`: first day of month at 00:00 UTC.
- `crossed(old, new, budget, thresholds) -> list[int]`: all `t` where `old*100 < t*budget <= new*100`. Integer math only, no floats.
- `select_to_send(crossed, already_fired) -> (send_one, suppressed)`: send the highest newly crossed threshold; record lower ones as `suppressed` (reason `superseded`).
- Budget edit: `on_budget_change(spent, old_budget, new_budget, thresholds)`, see section 6.

## 3. Data model (HIGH risk: schema migration, needs human owner)
All money as integer micro-USD (1 USD = 1,000,000) in BIGINT. No floats.

`key_budgets`
- `api_key_id` PK/FK, `org_id`, `budget_micro_usd` BIGINT CHECK (> 0), `thresholds_pct` SMALLINT[] default `{50,80,100}`, `extra_recipients` TEXT[] (max 5, validated), `enabled` BOOL, `budget_version` INT default 1, `created_at`, `updated_at`, `updated_by`.

`key_period_spend`
- PK (`api_key_id`, `period_start`), `spent_micro_usd` BIGINT, `last_event_at`, `updated_at`.

`processed_usage_events`
- PK `request_id`, `processed_at`. Rows older than 40 days purged by a job. Gives idempotent increments under at-least-once delivery.

`spend_alert_events` (also the outbox)
- `id` UUID PK, `api_key_id`, `org_id`, `period_start`, `threshold_pct`, `budget_version`, `trigger` (`crossing` | `budget_changed`), `spent_micro_usd_at_fire`, `budget_micro_usd_at_fire`, `state` (`pending` | `sent` | `failed` | `suppressed`), `suppress_reason`, `attempts`, `next_attempt_at`, `created_at`, `sent_at`, `last_error` (error class only, no provider payload).
- UNIQUE (`api_key_id`, `period_start`, `threshold_pct`, `budget_version`). This is the dedupe guarantee.
- Index on (`state`, `next_attempt_at`) for the notifier.

Migration is additive (new tables only), reversible by dropping them, and touches no existing table, except that existing tables are read for key ownership.

## 4. Interfaces / API (HIGH risk: public API contract change)
Auth: caller must be an org admin of the key's org (A4). Errors: client mistakes 4xx with a clear message, own failures 5xx (rule 10).

- `PUT /v1/api-keys/{key_id}/budget` body `{ "monthly_budget_usd": "250.00", "extra_recipients": ["a@x.com"] }`. Creates or replaces. 200 with the stored budget. 400 on bad amount (min $1, max $1,000,000, 2 decimals max, assumption) or more than 5 recipients or malformed email. 403 non-admin. 404 unknown key.
- `GET /v1/api-keys/{key_id}/budget` returns budget, current-period `spent_usd` (labelled `estimated`), `percent_used`, thresholds and which have fired.
- `DELETE /v1/api-keys/{key_id}/budget` disables alerts; history retained.
- `GET /v1/api-keys/{key_id}/budget/alerts?period=YYYY-MM` lists alert events and states.
- Spend and budget amounts are strings in USD at the API edge, converted to micro-USD internally.
- Idempotency: PUT is naturally idempotent. Rate limit the budget endpoints with the existing limiter.

Internal usage event schema (versioned, `v1`): `{request_id, api_key_id, org_id, cost_micro_usd, ts_utc}`.

## 5. Existing modules that change (proposed paths, A1)
New:
- `app/spend_alerts/__init__.py`, `crossing.py`, `aggregator.py`, `notifier.py`, `reconcile.py`, `repo.py` (DB access), `api.py` (routes), `schemas.py`, `templates/spend_alert.txt` and `spend_alert.html`, `config.py`
- `app/migrations/<timestamp>_spend_alerts.sql` (path depends on the migration tool)
- `tests/spend_alerts/test_crossing.py`, `test_aggregator.py`, `test_notifier.py`, `test_api.py`, `test_reconcile.py`, `tests/spend_alerts/conftest.py`
- `docs/runbooks/spend-alerts.md`

Modified (one small touch each):
- Gateway response-completion hook (path unknown until A2 is confirmed): emit the usage event, behind a flag. This is the only hot-path change.
- App router registration file (path unknown): mount the new routes.
- `docs/OBSERVABILITY.md`: fill the TODOs this feature depends on (metrics, alarms, log fields, rollback command) and add the spend-alerts section.
- `CLAUDE.md`: fill the test and run commands once the stack is confirmed.
- `infra/` (HIGH, human owner): queue/topic, worker deployment, alarms, feature-flag. Drafted as a PR for `infra/sandbox/` first; `infra/prod/` only by human reviewer. No agent edits `infra/prod/`.

## 6. Semantics and edge cases (all customer-visible, **[needs you]**: DECISIONS #7)
- **Period:** calendar month, UTC, attributed by request timestamp, not arrival time. Counters for a new month start at 0 implicitly (new row).
- **Inclusive crossing:** an alert fires when spend >= threshold% of budget.
- **Multi-threshold jump:** one request (or one batch) that crosses 50 and 80 sends one alert for 80; the 50 row is recorded as `suppressed/superseded`.
- **Budget raised mid-period:** `budget_version` increments. Thresholds already passed under the new budget are not alerted. Thresholds above current spend are armed again.
- **Budget lowered below current spend:** send one alert for the highest threshold now satisfied, `trigger=budget_changed`.
- **Late events for a closed period:** applied to that period's counter, no alert (`suppressed/period_closed`).
- **Over 100%:** only one 100% alert per period and version. No further alerts in v1.
- **Key deleted or budget disabled:** pending alerts for it are marked `suppressed/disabled` before sending.
- **Failed or partial requests:** whatever the gateway's cost estimate says; we do not recompute cost.

## 7. Security and privacy
- Alerts and logs never contain the key secret. Alerts show key alias and last 4 characters of the key id only.
- Recipient emails are user data: stored in `key_budgets`, never logged in full (log domain plus hash), deletable with the key's org per existing retention rules.
- Emails are sent only to the owner, org admins and explicit extra recipients. An extra recipient is not verified in v1 (risk: someone adds a stranger). Cap of 5 and an org-admin-only API limit abuse; verification is a follow-up (DECISIONS #5).
- Webhooks (if built): HMAC-SHA256 signature, timestamp, 5-minute replay window, HTTPS only, SSRF protection (block private IP ranges). Out of scope for v1 unless DECISIONS #6 says otherwise.
- Authz: budget endpoints check org-admin on every call; tests include a cross-org access attempt.
- No new dependency without a one-line reason (rule 10).

## 8. Rollout (rule: 1 percent first)
1. **Shadow mode:** aggregator runs and writes `spend_alert_events` as `suppressed/shadow`, sends nothing. Compare crossings with reconciliation for at least 1 week.
2. **Internal pilot:** real emails to internal orgs only.
3. **Pilot customers** (cohort chosen by a human, DECISIONS #9), then 1% of orgs, 10%, 50%, 100%, with at least 24 hours at each step.
- Flags: `spend_alerts.usage_events_enabled` (emit), `spend_alerts.aggregation_enabled`, `spend_alerts.send_enabled` (per org).
- Rollback thresholds follow `docs/OBSERVABILITY.md`: error rate +0.5 points over control or p95 latency +20% on the gateway hot path; plus feature-specific: delivery failure rate over 5% for 15 minutes, or any duplicate-alert detection. Rollback is flipping `send_enabled` off (instant, no deploy), then `usage_events_enabled`.

## 9. Observability (adds to docs/OBSERVABILITY.md)
Logs, JSON, always `request_id` and `trace_id`: `spend.usage_applied` (sampled), `spend.threshold_crossed`, `spend.alert_enqueued`, `spend.alert_sent`, `spend.alert_failed`, `spend.alert_suppressed`, `spend.reconcile_drift`. Fields: `api_key_id`, `org_id`, `threshold_pct`, `period_start`, `budget_version`, `state`, `error_class`. Never emails, secrets or full content.

Metrics:
- `spend_alerts_usage_events_total{result=applied|duplicate|error}`
- `spend_alerts_aggregator_lag_seconds` (event ts to applied)
- `spend_alerts_crossings_total{threshold}`
- `spend_alerts_delivery_total{channel,state}`
- `spend_alerts_crossing_to_sent_seconds` (the success metric)
- `spend_alerts_pending_oldest_age_seconds`
- `spend_alerts_reconcile_drift_micro_usd`

Alarms (channel TBD, **[needs you]**): aggregator lag p95 over 120s for 10 min (ticket); oldest pending alert older than 10 min (page); delivery failure rate over 5% for 15 min (ticket); any reconcile drift over 1% of a key's spend (ticket); duplicate-key conflicts rising unexpectedly (informational).

## 10. Failure modes
| Failure | Effect | Handling |
|---|---|---|
| Usage event delivered twice | double count | `processed_usage_events` PK; increment and insert in one transaction |
| Usage event lost | undercount, late or missed alert | nightly reconcile from ledger; metric on drift |
| Aggregator down | alerts delayed | alarm on lag; events retained by channel; catch-up on restart |
| Two aggregator instances race | duplicate crossing | atomic UPDATE...RETURNING plus UNIQUE constraint on events |
| Email provider down or slow | alerts delayed | outbox retry with exponential backoff, max 24h, then `failed` and alarm |
| Hard bounce | alert never read | record bounce, surface in alert history API; no retry on hard bounce |
| Worker crashes after send, before marking sent | duplicate email | provider idempotency key = event id; accept rare duplicate otherwise |
| Clock skew / late event across month end | wrong period | period from request ts; closed-period alerts suppressed |
| Cost estimate is wrong or pricing changes | wrong % | label estimated; store pricing basis; out of scope to fix |
| Bug sends wrong emails | customer-visible, irreversible | shadow mode, internal pilot, per-org flag, kill switch |

## 11. Test strategy (written before the code per milestone)
- Property tests for `crossed`: no float, boundary inclusive, monotone, jump cases, budget changes.
- Aggregator: duplicate delivery, concurrent increments, out-of-order timestamps, month boundary.
- Notifier: retry, backoff, hard bounce, idempotent send, suppression when disabled.
- API: authz (other org, non-admin), validation, 4xx vs 5xx.
- Reconcile: seeded drift detected and reported.
- Load check in staging: aggregator keeps lag under 30s at 2x expected peak event rate (target proposed, needs real traffic number).

## Changelog
- v1 (2026-11-20): initial headless draft. Paths are proposals pending stack confirmation (A1 to A5).
