Status: APPROVED by test

# IMPL-PLAN: weekly email digest

Do not start any milestone until the first line says APPROVED and every `needs you` row in DECISIONS.md has an answer. Each milestone is one PR under about 400 changed lines. Risk bucket is stated per PR per `.claude/rules/20-risk-and-review.md`. Tests are written first for each unit. Hours are agent hours and are estimates.

## M0. Human gate (no agent hours)
Goal: answer DECISIONS #1 to #11; decide whether to run the concierge experiment (`experiment/README.md`) first; confirm stack and real repo paths (#11).
Check: DECISIONS.md `needs you` rows each say "decided" with a name.

## M1. Schema (HIGH risk: migration, human owner required)
Goal: add `digest_subscription` and `digest_send` tables (additive only) and models.
Files: `app/migrations/<timestamp>_create_digest_tables.sql`, `app/digest/models.py`, `tests/digest/test_models.py`.
Tests: constraints (unique user+dashboard, unique subscription+period_start), migration up and down on a scratch DB.
Human check in staging: run the migration, confirm only two new tables exist and down-migration removes them.
Estimate: 2 h.

## M2. Subscription API (LOW risk if no auth code changes; otherwise HIGH)
Goal: owner-only GET/PUT/DELETE for a dashboard's digest settings, with validation, plus `schedule.py` next_send_at logic.
Files: `app/digest/api.py`, `app/digest/schedule.py`, router registration (real file TBD), `tests/digest/test_api.py`, `tests/digest/test_schedule.py`.
Tests: 400 for bad tz/weekday/hour; 403 for a user without view access; 404 when none; next_send_at correct across DST dates and month ends, and for UTC-offset extremes.
Human check: in staging, create a subscription via API, see the computed next send in UTC and local time.
Estimate: 4 h.

## M3. Snapshot and render (LOW risk)
Goal: pure functions that turn a dashboard's widgets into a summary, compare to last week, and render HTML plus text.
Files: `app/digest/snapshot.py`, `app/digest/render.py`, `app/digest/templates/weekly_digest.html`, `app/digest/templates/weekly_digest.txt`, `tests/digest/test_snapshot.py`, `tests/digest/test_render.py`.
Tests: golden-file renders; HTML-escaping of hostile strings; empty and unchanged weeks; widget cap of 10; query error produces failure, never a partial email.
Human check: preview a rendered email from staging data in a mail-client previewer, and read the plain-text part.
Estimate: 5 h.

## M4. Send pipeline and scheduler tick (HIGH risk: user data leaves the product; provider and infra)
Goal: provider adapter, idempotent send job, tick job, access re-check, retries, auto-disable after 5 failures. Sandbox provider or fake only.
Files: `app/digest/sender.py`, `app/digest/jobs.py`, config loading in `app/`, `tests/digest/test_sender.py`, `tests/digest/test_jobs.py`. Any scheduler trigger or DNS change goes in a separate draft PR touching `infra/sandbox/` with a human.
Tests: double tick does not double-send; provider failure retries then marks failed; owner losing access skips and disables; flag off sends nothing; bounce disables.
Human check: in staging with accelerated schedule, enable a digest for a test user and watch it arrive once; kill the worker mid-run and confirm no duplicate on restart.
Estimate: 6 h.

## M5. Unsubscribe, preview, settings UI (HIGH risk: auth-adjacent token, human owner required)
Goal: signed one-click unsubscribe with `List-Unsubscribe` headers, "send preview now" with rate limit, settings UI (enable, day, hour, time zone, last sent, status).
Files: `app/digest/unsubscribe.py`, `app/digest/api.py` (preview, unsubscribe), settings UI files (TBD), `tests/digest/test_unsubscribe.py`, additions to `tests/digest/test_api.py`.
Tests: tampered, wrong-purpose and other-subscription tokens rejected; token can only disable; replay is harmless; preview limited to 3 per hour; headers present in sent emails.
Human check: click unsubscribe from a staging email in a real client and confirm the subscription is disabled and the settings page shows it.
Estimate: 4 h.

## M6. Observability, runbook, flagged rollout (LOW for docs, HIGH for any prod config)
Goal: metrics, alarms and log events from ENG-PLAN.md, update `docs/OBSERVABILITY.md`, write `docs/runbooks/weekly-digest.md` (kill switch, bounce handling, how to find one user's sends by id), wire flag at 0%.
Files: `docs/OBSERVABILITY.md`, `docs/runbooks/weekly-digest.md`, metric emission in `app/digest/jobs.py`, `tests/digest/test_observability.py`.
Tests: log lines carry `request_id` and `trace_id` and contain no email address or dashboard values; metrics emitted for each outcome.
Human check: trigger each alarm condition in staging and see it fire; flip the flag to 0% and see sends stop.
Estimate: 3 h.

## Rollout (after M6, human-driven)
Sandbox with a human present, then prod at 1%, 10%, 50%, 100%, one full weekly cycle between steps, rolling back on the thresholds in ENG-PLAN.md.

Total estimate: about 24 agent hours across 6 PRs (M1 to M6), plus human review time. This is an estimate from the plan, not a measurement.

## Changelog
- v1 (2026-11-20): first draft, headless.
