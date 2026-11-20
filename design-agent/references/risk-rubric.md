# Risk rubric: who decides

Use this for every row in DECISIONS.md, and again for any new decision during the build.

## The four questions

Ask them in order. The first `yes` sends the row to `needs you`.

1. **Money, auth or user data?** Pricing, billing, plan limits, who can see or change what, personal data stored or sent.
2. **Hard to reverse?** Schema migrations, public API shapes, data deletion, an email or webhook format customers will parse, anything that needs a migration or an apology to undo.
3. **A promise outside the team?** Anything a customer, partner or the legal team will hold us to: SLAs, delivery times, retention periods, what a notification says.
4. **Would a customer notice?** A default they see, a behavior at a boundary, a rollout order that decides who gets it first, a time zone.

All four `no`: the agent decides, writes what it chose and why, and marks the row `agent: <choice>`.

When unsure, `needs you`. A wrong `needs you` costs the human a minute. A wrong `agent` row can cost a migration.

## Routing table

| Decision | Decided by | Why |
|---|---|---|
| Module and file names, internal structure | agent | invisible to users, cheap to rename |
| A library already in the stack | agent | reversible inside one PR |
| A new dependency | agent, with a one-line reason | reversible, but the PR must say why |
| Log fields, metric names | agent | internal, but follow `docs/OBSERVABILITY.md` |
| Sync vs async processing, with no user-visible latency change | agent | internal |
| Money type (integer cents vs decimal) | agent | internal and has a clear right answer; state it |
| New table or column | needs you | migration, hard to reverse |
| New or changed public endpoint | needs you | external contract |
| Who gets notified, what the message says | needs you | user data and an external promise |
| Default values users see | needs you | a customer would notice |
| Which plans get the feature | needs you | pricing |
| Rollout order and percentages | needs you | decides which customers see it first |
| The success metric and its target | needs you | PM-owned, even when low risk |
| The stack, when the repo is empty | needs you | every path in the plan depends on it |

## The 12 places decisions hide

If you have fewer than 10 rows, walk this list:

1. The stack or the existing module this builds on
2. Source of truth for each number the feature shows
3. Behavior exactly at each boundary or threshold
4. Duplicates and retries (idempotency)
5. Concurrency: two writers, two workers
6. Time: periods, time zones, late or out-of-order events
7. Who can see, set or change it (authz)
8. What the user sees when a dependency is down
9. Notifications: channel, recipients, frequency, content
10. Data model and migration shape
11. Rollout: flag, shadow mode, order, percentages
12. Success metric, guardrail metric, and how the eval gates (if an LLM is involved)
