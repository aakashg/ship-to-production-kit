# ENG-PLAN: Per-API-key monthly request quotas
Version: v1 (2026-11-20)

No LLM is called by this feature, so there is no eval gate (section 9).

## 1. Assumptions
A1 Stack and layout: the repo is an empty template. I assume a Python service under `app/` and pytest under `tests/`. M0 confirms the language, framework, auth middleware and key table, and rewrites paths here if not. (DECISIONS #1)
A2 A key table exists with an owner and a revoked flag, and an auth step identifies the key before our code runs. M0 confirms.
A3 Redis is available or can be added. M0 confirms. (DECISIONS #5)
A4 Traffic: assumed 2,000 req/s peak, hottest key 20%. M0 replaces with real numbers from logs.
A5 Idempotency keys may not exist in the API. M0 confirms; if absent, example #7 is dropped.

## 2. Architecture
```
request -> auth (key id, owner) -> quota middleware
              |                     1. read key limit (cached 60 s, from DB)
              |                     2. no limit -> count only, allow
              |                     3. INCR redis quota:{key}:{YYYYMM}
              |                     4. n > limit -> DECR, 429 + reset headers
              |                     5. else allow, add X-Quota-* headers
              v
         handler
Redis counters --(flush every 5 s, batch)--> DB key_usage_monthly
GET /v1/keys/{id}/usage -> authz owner check -> Redis count (fallback DB) -> JSON
```
Atomic INCR gives correct behavior for concurrent requests (example #6): the 1,000th returns 1000 (allowed), the 1,001st returns 1001 (denied and decremented).

## 3. Data model
- `api_keys.monthly_quota` BIGINT NULL, additive, no backfill. NULL means unlimited. Check: 1 or more.
- `key_usage_monthly(key_id, period CHAR(6) 'YYYYMM', request_count BIGINT, updated_at)`, primary key (key_id, period), additive. Flush uses upsert with `GREATEST(existing, redis_value)`.
- Redis key `quota:{key_id}:{YYYYMM}`, expires 40 days after period end.
- Rebuild on Redis loss: seed counter from the DB value on first INCR if the key is missing.

## 4. Interfaces and APIs
- Middleware `check_quota(key_id, now) -> Allow(remaining, reset_at) | Deny(limit, used, reset_at)`.
- Over quota: `429` JSON `{"error":"quota_exceeded","limit":1000,"used":1000,"reset_at":"2026-12-01T00:00:00Z"}`, headers `Retry-After` (seconds), `X-Quota-Limit`, `X-Quota-Remaining`, `X-Quota-Reset`.
- `GET /v1/keys/{key_id}/usage` (owner only): 200 `{key_id, period, limit, used, remaining, reset_at, as_of}`; 404 for a key not owned by the caller; 503 plus `Retry-After` if the counter store is down.
- `PUT /v1/admin/keys/{key_id}/quota` body `{"monthly_quota": 1000 | null}` (admin only): 400 on negative, zero, non-integer; 404 unknown key. (Per DECISIONS #2.)
- Client mistakes are 4xx, only our own failures 5xx (rule `10-code-standards`).

## 5. Files touched
| Path | New or changed | Why |
|---|---|---|
| app/quota/period.py | new | UTC month period and reset time |
| app/quota/counter.py | new | Redis INCR/DECR, flush, seed from DB |
| app/quota/enforce.py | new | middleware decision, response headers |
| app/quota/usage_api.py | new | usage endpoint |
| app/quota/admin_api.py | new | set/clear quota endpoint |
| app/<auth middleware, path from M0> | changed | register middleware after auth |
| migrations/<path from M0> | new | the two additive schema changes (HIGH, human owner) |
| tests/quota/test_period.py, test_counter.py, test_enforce.py, test_usage_api.py, test_admin_api.py | new | one per module |
| docs/OBSERVABILITY.md | changed | add the logs, metrics, alarms below |
| docs/features/api-key-monthly-quotas/experiment/m0-notes.md | new | M0 findings |
| docs/features/api-key-monthly-quotas/ROLLOUT.md | new | M6 stage log and rollback record |
| tests/quota/test_migration.py, tests/quota/test_enforce_429.py | new | M2 and M6 tests |

## 6. Edge cases and semantics
- Boundaries: used == limit - 1 allowed; used == limit denied. 429s never count.
- Month rollover at 00:00:00 UTC; clock from the server, not the client. Redis key is per period so rollover needs no reset job.
- Concurrency: atomic INCR; never above limit in stored state (denied requests DECR).
- Lowered quota below usage: new limit read within 60 s; requests denied. Raised: unblocked within 60 s.
- Limit cache staleness is the only lag; quoted as "up to 60 s".
- Dependency down: Redis down fails open and alarms; DB down for the limit lookup uses the last cached limit, or fail open if none.
- Huge: a 2^40 limit is fine for BIGINT. Request count above the limit is impossible by design.
- Revoked or unauthenticated requests never reach the middleware.

## 7. Security and privacy
- Authz on every new endpoint: usage requires owner of the key; admin endpoint requires the admin role. Unowned keys return 404 so key ids are not enumerable.
- No PII stored. Logs carry `key_id`, never the key secret.
- Abuse: a client cannot raise its own quota; the usage endpoint is itself rate limited with the existing per-IP limit (assumption, M0 confirms one exists).

## 8. Observability
Logs (JSON, with `request_id`, `trace_id`, `key_id`): `quota_exceeded` (limit, used), `quota_shadow_exceeded`, `quota_store_error`, `quota_changed` (admin id, old, new).
Metrics: `quota_rejections_total` (counter; a sudden jump across many keys is bad), `quota_check_latency_ms` (histogram; p95 over 5 ms is bad), `quota_store_errors_total`.
Alarms: `quota_store_unavailable` when store errors persist for 2 minutes (page on-call); `quota_false_429` when a reconcile job finds a rejected key whose DB usage is under limit (page).
Add each to docs/OBSERVABILITY.md in the milestone that ships it.

## 9. Evals
Not applicable: the feature does not call an LLM.

## 10. Failure modes
| Failure | User sees | Detection | Mitigation |
|---|---|---|---|
| Redis down | requests succeed, usage endpoint 503 | `quota_store_unavailable` | fail open (DECISIONS #7), restore Redis, counters reseed from DB |
| Redis restart loses counts | undercount up to 5 s of requests | flush lag metric | DB value seeds counter |
| Bug returns false 429 | customer blocked under quota | `quota_false_429`, support | flag off, shadow mode |
| Admin sets wrong quota | key blocked early | `quota_changed` log | set it back, takes effect in 60 s |
| Hot key | latency | `quota_check_latency_ms` | INCR is O(1); no DB write per request |

## 11. Rollout
Flag `quota_enforcement` with modes `off`, `shadow`, `enforce`, plus an allowlist of key ids. Stages: shadow for 1 week, then enforce at 1% of keys with quotas, 10%, 50%, 100% (order per DECISIONS #11). Watch false 429 rate and added p95 latency. Rollback if false 429s exceed 0.01% of requests, error rate rises 0.5 points over control, or p95 rises 20% (thresholds from `docs/OBSERVABILITY.md`). Rollback: set the flag to `off`.

## Changelog
- v1 2026-11-20: first draft, headless
