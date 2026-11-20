# PRD: Per-API-key monthly request quotas
Version: v1 (2026-11-20, headless: no human to answer questions; every answer below is a recorded assumption)

## 1. The idea, restated
Each API key gets an optional monthly request quota. Once a key has used its quota, further requests get HTTP 429 with a reset time. Key owners can see usage so far this month. For API owners who need to contain runaway clients and cost, and who today have no per-key ceiling.

## 2. Pushback
- Strongest argument against: the repo has no application code, no stack, no key model and no stated traffic. A quota enforced on the hot path adds a stateful lookup and counter write to every request, and a bug in it turns into an outage for paying customers (false 429s). If the real pain is a few abusive clients, a per-second rate limit at the gateway plus manual key revocation is cheaper and safer. Monthly quotas also do not stop bursts.
- Alternatives:
  - Do nothing: abuse and cost spikes continue, found only after the invoice. Cost depends on traffic we cannot see (assumption A1).
  - Buy or configure: gateway-native plans and quotas (Kong, Apigee, AWS API Gateway usage plans, Tyk are the usual candidates; unverified). Good if we already run one of them; the decision is `needs you` (DECISIONS #1).
  - Build A: counters in Redis (atomic INCR keyed by key and month), persisted to the DB by batch flush. Fast, approximate on a Redis loss.
  - Build B: counters in the primary DB, one row per key per month. Exact and simple, but hot-key row contention (see experiment).
- Questions that would change the design (assumed answers):
  1. What is the stack and do we already have a gateway? Assumption: unknown; M0 confirms.
  2. Are the quotas set by us (per plan) or by the key owner? Assumption: set by our staff/admin API per key, with a plan default; owners read only.
  3. Does a 429 count against the quota? Assumption: no, only requests that were allowed count.
  4. Which requests count (all, or only 2xx)? Assumption: every allowed request counts, regardless of the response status.
  5. Is a month the UTC calendar month? Assumption: yes, resets 00:00:00 UTC on the 1st.

## 3. Market research
No web access in this run. Every row is unverified, from prior knowledge; verify before relying on any of it.

| Product | What it does well | Gap | Source |
|---|---|---|---|
| AWS API Gateway usage plans | Per-key quota (day/week/month) with throttling, 429 on exceed | Reset time not in the response body; usage visible via a separate API call | unverified |
| Kong rate-limiting / Advanced | Per-consumer limits incl. month window, rate limit headers | Month window counters are approximate in some modes; usage UI is limited in OSS | unverified |
| Stripe / GitHub public APIs | Return limit, remaining and reset headers; clients can self-throttle | Per-second/hour windows, not owner-set monthly quotas | unverified |
| Apigee quota policy | Per-app quotas, analytics dashboards | Heavy platform to adopt for one feature | unverified |

Pattern worth copying (unverified): `Retry-After` plus `X-RateLimit-Limit/Remaining/Reset` headers on every response, so clients see the quota before they hit it.

## 4. Problem
API owners cannot cap what one key consumes. A buggy or abusive client can burn through capacity or cost with no ceiling, and owners cannot see per-key usage. Frequency and cost: unknown, no data in this repo (unverified; the M0 query and the experiment note ask for real numbers).

## 5. Who
- Primary: API owners (the humans who own keys) who want a ceiling and visibility.
- Secondary: API client developers, who need a clear 429 and a reset time.
- Not the user: anonymous or unauthenticated callers (they are not keyed) and per-second burst control.

## 6. Success metric
Within 60 days of GA, 40% of active keys have a quota set, and 100% of over-quota requests return 429 with a correct reset time. Target is a placeholder: `needs you` (DECISIONS #12).
Guardrail metrics: added p95 latency on authenticated requests under +5 ms; false 429 rate (429s on keys whose true usage is under quota) at 0.01% or less of requests; no more than 1 customer-visible quota defect per week.

## 7. Non-goals (this version)
- Per-second or burst rate limiting (different problem, different mechanism).
- Billing or overage charges, plan upgrades on exceed.
- Owner-editable quotas through a self-serve UI.
- Per-endpoint or per-method quotas.
- Usage alerts at 80%/100% (a natural v2 once counters exist).
- Org-level pooled quotas.
- Historical usage charts beyond the current and previous month.

## 8. User stories
- As an API owner, I want to cap a key at N requests per month so that a runaway client cannot exceed it.
- As an API owner, I want to see requests used, quota and reset time for each of my keys so that I can plan.
- As a client developer, I want a 429 that says when I can call again so that I can stop retrying blindly.
- As an admin, I want to set, change or remove a key's quota so that plans are enforced.

## 9. Experiment
What we run: `experiment/reset_time_check.py`, a read-only script that checks reset-time math at month, year and leap-year boundaries and models the counter write load on a hot key.
Kill result: reset math ambiguity or a modeled hot-key rate above what the chosen store sustains. Reshape: the stack's real peak per-key rate from logs may force Redis counters.
Time: 15 minutes, plus M0 (about 2 hours) to replace assumed traffic with real numbers.
Result: ran it. Reset math is correct at all five boundaries (Dec 31 to Jan 1, Feb 28, leap day 2028-02-29). Modeled hot key at 400 incr/s (assumed 2,000 req/s peak, 20% on one key; assumed inputs, not measured) argues against per-request DB row updates. Output in `experiment/output.txt`. Nothing red enough to kill the idea; it reshaped the design toward atomic counters with batched persistence.

## 10. Acceptance examples
Quota limit L, "used" is requests already counted this UTC month. A request is allowed if used < L and then counts.

| # | Input (real, concrete) | Expected output | PM label |
|---|---|---|---|
| 1 | Key `k_42`, quota 1,000, used 10, `GET /v1/items` on 2026-11-20T13:05Z | 200, header `X-Quota-Remaining: 989`, used becomes 11 | pass |
| 2 | Key `k_42`, quota 1,000, used 999, one request | 200 and used becomes 1,000 (the 1,000th request is allowed) | pass |
| 3 | Key `k_42`, quota 1,000, used 1,000, request at 2026-11-20T13:05:00Z | 429, `Retry-After: 903300`, header `X-Quota-Reset: 2026-12-01T00:00:00Z`, JSON `{"error":"quota_exceeded","limit":1000,"used":1000,"reset_at":"2026-12-01T00:00:00Z"}`; used stays 1,000 | pass |
| 4 | Key `k_42` quota 1,000 used 1,000, request at 2026-12-01T00:00:00Z | 200; counter is a new month, used becomes 1 | pass |
| 5 | Key `k_7` with no quota set, 5 million requests in a month | all 200, no quota headers, usage still recorded | pass (answered, DECISIONS #3) |
| 6 | Key `k_42` quota 1,000 used 998, 5 concurrent requests at once | exactly 2 return 200, 3 return 429; final used 1,000, never above 1,000 | pass |
| 7 | Client retries request with `Idempotency-Key: abc` after a timeout, quota 1,000, used 500 | counts once; used 501 (assumes idempotency keys exist in the API) | pass (answered, DECISIONS #6) |
| 8 | Owner A calls `GET /v1/keys/k_42/usage` for a key owned by owner B | 404, no usage disclosed | pass |
| 9 | Owner calls `GET /v1/keys/k_42/usage` on own key mid-month | 200 `{"key_id":"k_42","period":"2026-11","limit":1000,"used":412,"remaining":588,"reset_at":"2026-12-01T00:00:00Z","as_of":"2026-11-20T13:05:02Z"}` | pass |
| 10 | Admin lowers `k_42` quota from 1,000 to 300 when used is 412 | takes effect within 60 s; next request is 429 with limit 300, used 412 | pass (answered, DECISIONS #8) |
| 11 | Counter store (Redis) is unreachable for 20 minutes | requests are allowed (fail open), `quota_store_unavailable` alarm fires; usage endpoint returns 503 with `Retry-After`, not stale zeros | pass (answered, DECISIONS #7) |
| 12 | Request at 2026-12-31T23:59:59Z for exceeded key | 429, `Retry-After: 1`, `X-Quota-Reset: 2027-01-01T00:00:00Z` | pass |
| 13 | Admin sets quota to 0 | 400 `{"error":"invalid_quota"}`, nothing changes; to block a key, revoke it | pass (answered, DECISIONS #4) |
| 14 | Admin sets quota to -5 or 1.5 or "abc" | 400 `{"error":"invalid_quota"}`, nothing changes | pass |
| 15 | Revoked key `k_9` with quota remaining | 401 from auth before quota is consulted; usage not incremented | pass |

## 11. Open risks
- False 429s from counter bugs or a hot-key race: caught by the shadow mode (compute, log would-be 429s, do not enforce) and the false-429 guardrail.
- Fail-open vs fail-closed on counter outage: a business call, `needs you`.
- Unknown stack and traffic: M0 confirms before any path is trusted.
- Approximate counts if Redis loses data between flushes: bounded by flush interval; the stated accuracy is a decision (#5).
- Clients not expecting a new 429 body: a public contract change, human review required.

## CPO check
- Strategic alignment: changed. No company goal is stated in the repo, so the metric is tied to an assumed goal (cost containment and fairness for API owners); flagged in DECISIONS #12 as `needs you` rather than presented as settled.
- Clarity: changed. Added explicit "counts when allowed" semantics, the 429 body and header names, and M0 for the unknown stack so milestone 1 does not rest on a guess.
- Edge cases: changed. Added examples for concurrency (#6), no quota (#5), quota lowered below usage (#10), store outage (#11), year boundary (#12), zero and invalid quotas (#13, #14), revoked key (#15), cross-owner access (#8).
- Scope: pass. Non-goals exclude burst limiting, billing, alerts, self-serve UI, per-endpoint and pooled quotas.

## Changelog
- v1 2026-11-20: first draft, headless
