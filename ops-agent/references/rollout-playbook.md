# Rollout playbook

Every fix rolls out partially, including critical ones. The agent writes this plan into the ticket with real numbers. A human or the deploy pipeline runs it.

## Stages

| Stage | Traffic | Minimum watch | Advance when |
|---|---|---|---|
| Staging | 0% prod | until the failing case is re-run | the original failing request now gets the new behavior, and logs show it |
| Canary | 1% | 1 hour or 1,000 requests, whichever is longer | every metric is green against control |
| Ramp | 10% | same as canary | green |
| Ramp | 50% | same as canary | green |
| Full | 100% | 24 hours of normal monitoring | ticket closed |

If traffic is too low to reach 1,000 requests at 1% in a day, say so in the ticket and propose a time-based window instead. Do not skip the stage.

## Advance, hold or roll back

Thresholds come from `docs/OBSERVABILITY.md`. The defaults below apply when that file sets none. Compare canary to control in the same window, not to last week.

| Metric | Advance | Hold and look | Roll back |
|---|---|---|---|
| Total error rate (4xx + 5xx), canary minus control | within +0.25 points | +0.25 to +0.5 points | more than +0.5 points |
| 5xx rate | flat or down | up, under the roll back line | up more than +0.5 points |
| p95 latency | within +10% | +10% to +20% | more than +20% |
| New error signature not seen in control | none | one, rare | any at more than 0.1% of canary requests |

Alert on changes, not absolutes: a signature that was in control at the same rate is not new. Confirm a red reading on two consecutive checks before rolling back, unless data is wrong or a security issue shows up, which roll back at once.

## When the fix changes a status code

A 5xx to 4xx fix moves errors between buckets. Watch the buckets separately:

- 5xx on the endpoint should fall by about the share that was misclassified (10.9 points in the max-tokens example).
- 4xx should rise by about the same amount.
- Total error rate should stay within +0.5 points of control.

If 5xx falls but 4xx rises by much more than 5xx fell, the fix is catching requests it should not. Roll back.

## Rollback

Write these four lines in the ticket before the canary starts:

1. Trigger: the roll back column above, or any data integrity or security finding.
2. Action: revert the PR (or flip the flag off), the command or button, and who can do it.
3. Time to roll back: how long the revert takes to reach 100% of hosts.
4. Data: whether the change wrote anything that a revert leaves behind. If yes, the fix was HIGH risk.

After a rollback, set the ticket status back to `open`, add what the canary showed, and stop.
