# ENG-PLAN: weekly email digest

Status: v1. Written against an empty template repo. No existing module could be inspected, so every path below is proposed, not existing, and assumes Python/pytest (DECISIONS #11). The design also assumes the answers recommended in DECISIONS.md (#1 to #3, #9): owner-only, opt-in, inline HTML.

## Architecture
```
settings UI/API --> digest_subscription (DB)
                         ^
scheduler tick (every 15 min) -- selects due rows, claims them
         |
         v
   per-subscription send job
     1. re-check owner still has access to dashboard (else disable + skip)
     2. build snapshot: run the dashboard's widget queries as the owner
     3. compare to previous week's stored snapshot summary
     4. if empty/unchanged and policy = skip --> record "skipped"
     5. render HTML + plain text, escape all values
     6. send via email provider (idempotency key: subscription_id + period_start)
     7. write digest_send row, set next_send_at, reset/increment failure count
```
The snapshot is built with the owner's permissions at send time, never with a service account that can see more. Nothing is cached across users.

## Data model (additive only, HIGH risk migration, DECISIONS #6)
`digest_subscription`
- id (uuid, pk), user_id, dashboard_id, enabled (bool), weekday (0-6), hour_local (0-23), tz (IANA string), next_send_at (utc, indexed with enabled), last_sent_at, consecutive_failures (int), unsubscribed_at (nullable), created_at, updated_at
- unique (user_id, dashboard_id)

`digest_send`
- id (uuid, pk), subscription_id (fk), period_start (date), status (sent, skipped_empty, skipped_no_access, failed), provider_message_id (nullable), error_code (nullable), summary_hash (for the unchanged check; a hash, not the values), created_at
- unique (subscription_id, period_start)  <- the double-send guard

No dashboard values and no email body are stored. Recipient address is read from the user record at send time, not copied.

## Interfaces
(Paths, auth and error shapes follow existing API conventions once known; 4xx for client mistakes, 5xx only for our failures, per `.claude/rules/10-code-standards.md`.)
- `GET /api/dashboards/{id}/digest` returns the caller's subscription or 404.
- `PUT /api/dashboards/{id}/digest` body `{enabled, weekday, hour_local, tz}`; creates or updates; 400 on invalid tz/weekday/hour; 403 if the caller cannot view the dashboard.
- `DELETE /api/dashboards/{id}/digest` disables.
- `POST /api/dashboards/{id}/digest/preview` sends one email to the caller now; rate limit 3 per hour per user; returns 202.
- `GET /digest/unsubscribe?token=...` confirmation page; `POST /digest/unsubscribe` one-click (RFC 8058). Token is a signed, single-purpose, expiring-not-required token scoped to one subscription; it can only disable.
These are additions, not changes to an existing public contract. Confirm that against the real API (a public API contract change would be HIGH risk).

## Files that will be touched (proposed)
New:
- `app/digest/__init__.py`
- `app/digest/models.py` (subscription, send records)
- `app/digest/schedule.py` (next_send_at math, DST-safe)
- `app/digest/snapshot.py` (build summary, compare to last week)
- `app/digest/render.py` (HTML and text)
- `app/digest/templates/weekly_digest.html`, `app/digest/templates/weekly_digest.txt`
- `app/digest/sender.py` (provider adapter behind an interface; fake adapter for tests)
- `app/digest/unsubscribe.py` (token sign/verify)
- `app/digest/api.py` (routes above)
- `app/digest/jobs.py` (tick and send job)
- `app/migrations/<timestamp>_create_digest_tables.sql` (location depends on the real migration tool)
- `tests/digest/test_schedule.py`, `test_snapshot.py`, `test_render.py`, `test_sender.py`, `test_unsubscribe.py`, `test_api.py`, `test_jobs.py`
- `docs/runbooks/weekly-digest.md`

Existing, modified:
- The dashboard settings UI and API router (unknown; real file names needed, DECISIONS #11)
- `docs/OBSERVABILITY.md` (add the digest metrics, alarms and queries below)
- Config loading in `app/` for provider settings (names only; values from the secret manager)

Drafted only, human-reviewed, not touched by the design or by agent-built milestones without a human owner:
- `infra/sandbox/` and `infra/prod/` (scheduler trigger, DNS records for the sending domain, provider credentials wiring)

## Security and privacy
- Recipient is always the owner's own account email. No free-text recipient field in v1.
- Access re-checked at every send. Removed users or deleted dashboards produce `skipped_no_access` and auto-disable.
- Email contains dashboard numbers: this is data leaving the product. Decide what is allowed (DECISIONS #3). Provide an admin kill switch per workspace/tenant if the product has tenants.
- HTML-escape every dashboard-derived string. Plain-text part always included.
- Unsubscribe token: HMAC-signed with a key from the secret manager, support key rotation, scope = subscription id + purpose. Human-owner review required (DECISIONS #10).
- Logs never contain email addresses, dashboard values or email bodies. Use ids.
- Preview endpoint is rate limited so it cannot be used as a mail cannon.
- Provider API key only via secret manager. Never in `.env`, repo or logs.
- Consent: opt-in only (DECISIONS #9). Record `created_at` of the opt-in. Legal review of requirements by region is needed and not done here.

## Rollout and observability
Flag `weekly_digest` (per user, percentage ramp 1% -> 10% -> 50% -> 100%, one full weekly cycle between steps; sandbox first with a human present). Because the cadence is weekly, a 1% ramp yields little data in the first days, so staging uses accelerated schedules (send every 10 minutes) with the fake or sandbox provider only.

Logs (JSON, `request_id`, `trace_id`, `subscription_id`): `digest.scheduled`, `digest.sent`, `digest.skipped` (reason), `digest.failed` (error_code), `digest.unsubscribed`, `digest.tick` (due_count, claimed_count, duration_ms).

Metrics: digests_due, digests_sent, digests_skipped{reason}, digests_failed{error_code}, provider_bounces, provider_complaints, unsubscribes, tick_lag_seconds (now minus oldest due next_send_at), send_latency_ms, provider_cost.

Alarms (starting values, tune with data):
- tick_lag_seconds > 1800 for 2 ticks: scheduler stuck.
- no `digest.tick` event for 60 minutes.
- failed / (sent + failed) > 2% over 1 hour.
- complaints / sent > 0.1% in any day: page, and set flag to 0%.
- unsubscribes / sent > 2% in a week: review content.
Rollback: set `weekly_digest` to 0%. Already-queued jobs check the flag before sending. Additive tables stay in place; dropping them is a separate reviewed migration.

## Failure modes
| Failure | Effect | Handling |
|---|---|---|
| Tick runs twice or job retried | Double email | Unique `(subscription_id, period_start)` plus provider idempotency key; second insert fails and the job exits |
| Provider outage | Missed sends | Retry with backoff within a 6 hour window, then mark failed; never send a stale digest later than the window; next week proceeds normally |
| Persistent failure for one user | Wasted work, bad reputation | Auto-disable after 5 consecutive failures (the threshold Tableau uses by default); show it in settings |
| Hard bounce or complaint | Reputation damage | Disable that subscription on first hard bounce or complaint |
| Owner lost access | Data leak risk | Re-check at send; skip and disable |
| Dashboard query slow or erroring | Late or empty email | Per-send timeout; on error mark failed, do not send a partial email |
| DST change or bad tz data | Wrong hour | Compute from local wall clock; test around DST dates |
| Huge dashboard | Large email | Cap to N widgets (proposed 10) with "see all" link |
| Sudden volume spike (ramp) | Provider throttling | Spread sends: jitter within the chosen hour, cap sends per tick |
| Flag misconfigured to 100% early | Bulk email to everyone | Opt-in only, so only users who enabled it receive it |

## Changelog
- v1 (2026-11-20): first draft, headless.
