# DECISIONS: Per-API-key monthly request quotas
Version: v1 (2026-11-20, headless: every `needs you` row carries my recommendation as a recorded assumption)

`needs you` rows come first.

| # | Decision | Options | Recommendation and why | Risk | Decided by |
|---|----------|---------|------------------------|------|-----------|
| 1 | Stack, and build vs configure | (a) Build in our service. (b) Use quota feature of an existing gateway if we have one. (c) Adopt a new gateway. | (a) unless M0 finds a gateway already in front of the API, then (b). The repo is empty, so every path in ENG-PLAN is an assumption (Python-style layout under `app/`). Picking (b) removes M2 to M4. | high | needs you |
| 2 | Who sets quotas and who can read usage | (a) Admin/staff set quotas, owners read their own keys. (b) Owners set their own. (c) Plan-driven defaults, admin override. | (a). Smallest authz surface; owners cannot raise their own cap. Cost of (b): a self-serve write path and abuse cases. Cross-owner reads return 404. | high | needs you |
| 3 | Keys with no quota | (a) Unlimited, still counted. (b) A default quota for all keys. | (a). No existing customer starts getting 429s on rollout. (b) is a surprise breaking change and a pricing call. | high | needs you |
| 4 | Meaning of quota 0 | (a) Allowed, blocks all calls. (b) Rejected as invalid, use key revocation. | (b). Two ways to disable a key invites confusion. Example #13 flips to a 400 if you agree. | med | needs you |
| 5 | Counter store and accuracy | (a) Redis INCR, batch-flushed to DB, may undercount after a Redis loss. (b) DB row per key per month, exact, hot-key contention. | (a) given the experiment. Overshoot is bounded by the flush interval (assumed 5 s) on a crash, never a false 429. Needs Redis in the stack (decision #1). | high | needs you |
| 6 | What counts, and the period | (a) Every allowed request counts; 429s do not; retries with the same Idempotency-Key count once; month is UTC calendar. (b) Count only 2xx. (c) Per-owner time zone. | (a). Simplest to explain and to test. Idempotency dedupe only if the API already has idempotency keys (M0 checks). UTC avoids per-customer reset confusion. | med | needs you |
| 7 | Behavior when the counter store is down | (a) Fail open (allow, alarm). (b) Fail closed (503). | (a). A quota outage should not become a customer outage; the cost is unbounded usage during the outage. Usage endpoint returns 503, never zeros. | high | needs you |
| 8 | Quota lowered below current usage, or raised after exceed | (a) Applies within 60 s, takes effect immediately, no refund. (b) Applies next month. | (a). Matches what the admin expects; raising a quota un-blocks within 60 s. Cache TTL of 60 s is the stated promise. | med | needs you |
| 9 | Data model | (a) Add `monthly_quota` (nullable) to the keys table and a `key_usage_monthly` table (key_id, period, count). (b) Separate quotas table. | (a). Additive only, nullable column, no backfill. Both are schema migrations, so human review on the PR. | high | needs you |
| 10 | Public contract | (a) 429 JSON `{"error":"quota_exceeded","limit","used","reset_at"}`, headers `Retry-After`, `X-Quota-Limit`, `X-Quota-Remaining`, `X-Quota-Reset` on all keyed responses, `GET /v1/keys/{id}/usage`. (b) Only 429 and the usage endpoint, no headers. | (a). Headers let clients self-throttle. Once clients parse them they cannot change, so confirm names before M4. | high | needs you |
| 11 | Rollout order | (a) Shadow mode (log would-be 429s) for 1 week, then enforce at 1% of keys that have quotas, then 10/50/100. (b) Enforce at once for new keys only. | (a). A false 429 is a customer-visible outage; shadow mode measures it first. Which customers go first is your call. | high | needs you |
| 12 | Success metric and target | (a) 40% of active keys with a quota within 60 days. (b) Reduction in cost or incidents from runaway keys. | (b) is closer to the goal but needs a baseline we do not have; the stated 40% is a placeholder, not a target. Company goal is not in the repo. | med | needs you |
| 13 | Reset header and field formats | (a) `Retry-After` in seconds, `X-Quota-Reset` and `reset_at` ISO-8601 UTC. (b) HTTP-date. | (a), matches RFC 9110 `Retry-After` seconds form and the examples. Part of the contract in #10, so it moves if #10 does. | low | agent: seconds plus ISO-8601 UTC |
| 14 | Log and metric names | `quota_exceeded`, `quota_shadow_exceeded`, `quota_store_error`; metrics `quota_rejections_total`, `quota_check_latency_ms`, `quota_store_errors_total` | Follow `docs/OBSERVABILITY.md`; JSON logs with `request_id`, `trace_id`, `key_id` (never the secret). | low | agent: names listed |
| 15 | Internal structure and flush interval | module `app/quota/` split into period, counter, enforcement; 5 s flush | Internal and cheap to change; the flush interval can be retuned by a flag. | low | agent: as listed |

12 need you, 3 decided by the agent.

## Changelog
- v1 2026-11-20: first draft, headless
