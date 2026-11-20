# DECISIONS.md template

```markdown
# DECISIONS: <feature name>
Version: v1 (<date>, <human present | headless: every `needs you` row carries my recommendation as a recorded assumption>)

`needs you` rows come first.

| # | Decision | Options | Recommendation and why | Risk | Decided by |
|---|----------|---------|------------------------|------|-----------|
| 1 | ... | (a) ... (b) ... (c) ... | (a), because ... What changes if you pick (b): ... | high | needs you |
| ... |
| 12 | ... | ... | ... | low | agent: <what I chose> |

N need you, M decided by the agent.

## Changelog
```

## Rules the checker enforces

`scripts/check_design.py` reads this file. It expects:

- Rows numbered in the first cell (`| 3 |`), "Decided by" as the last cell.
- "Decided by" starts with `needs you`, `agent` or, once a human answers, `answered by <name>: <choice>`.
- Every `needs you` (or answered) row above every `agent` row.
- 10 to 15 rows.
- The count line `N need you, M decided by the agent`, matching the table (answered rows count as need you).

## A good row and a weak row

Good:

| # | Decision | Options | Recommendation and why | Risk | Decided by |
|---|---|---|---|---|---|
| 2 | Does 100% of budget block traffic? | (a) Alert only. (b) Block at 100%. (c) Per-key setting, default alert only. | (a). The request was for alerts. Blocking production traffic is a different promise and a different failure mode. The counter is built so a cap can be added later. Emails say "requests are not blocked". | high | needs you |

Why it works: concrete options, a recommendation with the reason, the cost of the other choice, and the customer-facing consequence.

Weak:

| # | Decision | Options | Recommendation and why | Risk | Decided by |
|---|---|---|---|---|---|
| 2 | Blocking | yes/no | TBD | ? | needs you |

Why it fails: the human has to reconstruct the whole question before they can answer it. Every `needs you` row should be answerable in under a minute by someone who read only this table.

## Answering rows

When the human answers, replace the cell, do not delete the row:

`needs you` becomes `answered by Priya 2026-11-21: (a), alert only`

If the answer changes the plan, update PRD.md, ENG-PLAN.md and IMPL-PLAN.md in the same pass and add a changelog line to each.
