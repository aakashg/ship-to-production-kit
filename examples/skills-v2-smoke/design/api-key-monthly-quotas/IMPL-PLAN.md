Status: DRAFT - awaiting human approval

# IMPL-PLAN: Per-API-key monthly request quotas
Version: v1 (2026-11-20). Do not start until line 1 is changed by a human and every `needs you` row in DECISIONS.md is answered.
Total estimate: 30 agent hours, plus human review time (migration and public contract need a human owner).

## M0. Confirm the stack and numbers (2h) - LOW risk
- Goal: confirm assumptions A1 to A5 and replace assumed traffic with real numbers.
- Files: docs/features/api-key-monthly-quotas/ENG-PLAN.md (path corrections only), docs/features/api-key-monthly-quotas/experiment/m0-notes.md
- Tests: none (read-only); notes list language, auth middleware, key table, Redis, idempotency keys, real peak and hottest-key rate.
- Human check: read m0-notes.md; confirm DECISIONS #1 still holds.

## M1. Period and reset math (3h) - LOW risk
- Goal: pure UTC month period and reset time, no I/O.
- Files: app/quota/period.py, tests/quota/test_period.py
- Tests: Nov 20 gives 2026-12-01 and 903300 s; Dec 31 23:59:59 gives 2027-01-01 and 1 s; Feb and leap day; exactly 00:00:00 starts a new period.
- Human check: compare the PR's table against PRD examples #3, #4 and #12.

## M2. Schema (3h) - HIGH, human owner required (migration owner from CODEOWNERS)
- Goal: add `api_keys.monthly_quota` and `key_usage_monthly`, additive only.
- Files: migrations/<path from M0>, tests/quota/test_migration.py
- Tests: migration applies and rolls back on an empty and a populated DB; existing rows get NULL; check constraint rejects 0 and negatives.
- Human check: run the migration on staging and confirm existing keys behave identically.

## M3. Counter (6h) - LOW risk
- Goal: atomic INCR/DECR counting with seed-from-DB and batched flush, behind no user-visible change.
- Files: app/quota/counter.py, tests/quota/test_counter.py
- Tests: 50 concurrent increments at limit 10 yields exactly 10 allowed and state 10 (example #6); missing Redis key seeds from DB; flush is idempotent and monotonic; Redis error raises a typed error.
- Human check: run the concurrency test in staging and read the result.

## M4. Enforcement in shadow mode (5h) - HIGH, human owner required (public API contract, auth middleware)
- Goal: middleware computes allow or deny and logs `quota_shadow_exceeded`; headers added; nothing is blocked.
- Files: app/quota/enforce.py, app/<auth middleware path from M0>, tests/quota/test_enforce.py, docs/OBSERVABILITY.md
- Tests: examples #1, #2, #3 and #5 (in shadow: 200 plus log), fail-open on store error (#11), revoked key untouched (#15), p95 overhead under 5 ms in a local benchmark.
- Human check: in staging, set a quota of 5 on a test key, send 8 requests, see 3 `quota_shadow_exceeded` log lines and no 429s.

## M5. Usage and admin endpoints (5h) - HIGH, human owner required (authz, public endpoint)
- Goal: owner usage read and admin quota write.
- Files: app/quota/usage_api.py, app/quota/admin_api.py, tests/quota/test_usage_api.py, tests/quota/test_admin_api.py
- Tests: examples #8, #9, #13 or its 400 form per DECISIONS #4, #14; cross-owner 404; non-admin 403; store down 503.
- Human check: call both endpoints in staging as an owner, an admin and a stranger.

## M6. Enforce mode and rollout (6h) - HIGH, human owner required
- Goal: turn on 429 behind the `quota_enforcement` flag with the allowlist, alarms and rollback.
- Files: app/quota/enforce.py, tests/quota/test_enforce_429.py, docs/OBSERVABILITY.md, docs/features/api-key-monthly-quotas/ROLLOUT.md
- Tests: examples #3, #4, #6, #10, #12 in enforce mode; flag off restores the old behavior; false-429 reconcile alarm fires in a fault-injection test.
- Human check: after a week of shadow data, review the shadow false-positive count, then enable at 1% of keys with quotas. Roll back if false 429s exceed 0.01% of requests, error rate rises 0.5 points or p95 rises 20%. Then 10%, 50%, 100%.

## Changelog
- v1 2026-11-20: first draft, headless
