# Answers to the `needs you` rows (stand-in PM, 2026-11-20)

This is a test of the build step, so the PM answers were written by the test operator acting as the PM (`test-pm`), not by a customer team. Each answer is the one a PM at a small API company would most likely pick, with the reason. The same answers are written into the "Decided by" column of DECISIONS.md as `answered by test-pm: <choice>`, which is the convention in the skill.

| # | Decision | Answer | Why |
|---|----------|--------|-----|
| 1 | Stack, build vs configure | (a) Build in our service. Python 3 standard library, tests with pytest (`python3 -m pytest -q`). No gateway sits in front of the API. | The repo is a fresh template with no gateway. M0 is waived: this row confirms the stack, so the build starts at M1. |
| 2 | Who sets quotas, who reads usage | (a) Admins set quotas, owners read their own keys. Cross-owner reads return 404. | Smallest authz surface. Self-serve limits can come later. |
| 3 | Keys with no quota | (a) Unlimited, still counted. | No existing customer gets a surprise 429 on launch day. |
| 4 | Quota 0 | (b) Rejected as invalid (400 `invalid_quota`). To block a key, revoke it. | One way to disable a key. Example #13 becomes a 400. |
| 5 | Counter store | (a) Redis INCR, flushed to the DB every 5 s. | The experiment showed a per-request row update would serialize on the hottest key. |
| 6 | What counts, the period | (a) Allowed requests count, 429s do not, UTC calendar month. Idempotency dedupe only if M4 finds idempotency keys in the API. | Simplest to explain to a customer and to test. |
| 7 | Counter store down | (a) Fail open, alarm fires, usage endpoint returns 503. | A quota outage should not become a customer outage. |
| 8 | Quota changed mid-month | (a) Applies within 60 s, no refund. | Matches what an admin expects when they click save. |
| 9 | Data model | (a) Nullable `monthly_quota` column plus `key_usage_monthly` table. | Additive only. M2 still needs the migration owner's review. |
| 10 | Public contract | (a) 429 body and the four headers as written. Names are final. | Clients can self-throttle. Frozen before M4. |
| 11 | Rollout | (a) One week of shadow mode, then 1%, 10%, 50%, 100% of keys that have a quota. Internal and test keys go first. | A false 429 is an outage; measure it before enforcing. |
| 12 | Success metric | (b) as the primary metric: 0 billing incidents caused by a single runaway key in the 60 days after 100% rollout. (a) as secondary: 40% of active keys have a quota within 60 days. | Ties the feature to the cost problem it exists for. The 40% is a stated target now, not a placeholder. |

Acceptance example labels updated in PRD.md to match: #5, #7, #10, #11 now `pass`; #13 now expects a 400.

Approval: line 1 of IMPL-PLAN.md set to `Status: APPROVED by test-pm 2026-11-20`. Scope asked of the build agent: milestone M1 only.
