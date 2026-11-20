# PRD template

Copy this skeleton into `docs/features/<slug>/PRD.md`. One to two pages plus the acceptance examples. Delete the guidance lines in italics.

```markdown
# PRD: <feature name>
Version: v1 (<date>, <who: human present | headless>)

## 1. The idea, restated
<3 sentences: what, for whom, why now>

## 2. Pushback
- Strongest argument against: <one paragraph>
- Alternatives: do nothing (<cost of waiting>), buy or configure (<product>), build option A, build option B
- Questions that would change the design (max 5), each with the answer or `assumption: <best guess>`

## 3. Market research
| Product | What it does well | Gap | Source |
|---|---|---|---|
| <name> | <one line> | <one line> | <link or "unverified"> |

## 4. Problem
<who hurts, how often, what it costs them today; numbers with sources>

## 5. Who
<primary user, secondary user, who is explicitly not the user>

## 6. Success metric
<one metric that measures the company goal this serves, with a number and a date: "30% of active keys set a budget within 60 days of launch">
Guardrail metrics: <what must not get worse, with a threshold>

## 7. Non-goals (this version)
- <thing we will not build, and why>

## 8. User stories
- As a <user>, I want <action> so that <outcome>.

## 9. Experiment
What we run: <...>  Kill result: <...>  Time: <...>  Result: <ran it: what happened | not run: why>

## 10. Acceptance examples
| # | Input (real, concrete) | Expected output | PM label |
|---|---|---|---|
| 1 | <a real input, not "a long prompt"> | <exactly what the user sees> | pass / fail / `needs you` |

## 11. Open risks
- <risk>: <how we will know early>

## CPO check
- Strategic alignment: pass | <what changed>
- Clarity: pass | <what changed>
- Edge cases: pass | <what changed>
- Scope: pass | <what changed>

## Changelog
- v1 <date>: first draft
```

## Acceptance examples: what good looks like

The acceptance examples are the PM's definition of done and the labeled set any eval must agree with. Ten is the floor.

| Weak | Strong |
|---|---|
| "User sets a budget and gets an alert" | "Key `k_42`, budget $100.00, spend goes $79.99 to $80.01 in one request: one 80% email to the key owner within 5 minutes, subject `Key k_42 reached 80% of its $100 budget`" |
| "Handles errors" | "Email provider returns 503 for 20 minutes: alert is sent once after recovery, not 4 times" |
| "Works for big orgs" | "Org with 5,000 keys crosses 80% on 300 keys in the same minute: 300 emails, no duplicates, p95 delivery under 5 minutes" |

Cover at least: the happy path, each threshold or boundary (just under, exactly at, just over), empty input, a huge input, a duplicate event, two writers at once, a permission-denied caller, and a dependency outage. If a case needs a product call to label, label it `needs you` and add the matching row to `DECISIONS.md`.

## Market claims

Every row in the market table carries a link, or the word "unverified" if you had no web access or could not find a primary source. A vendor's own docs page beats a blog post about the vendor. Do not state pricing or plan limits you did not read on the vendor's own page.

## CPO check: how to run it

Read the four docs top to bottom as the most senior product person in the company. For each check, either write `pass` or fix the docs and write what you changed in one line. Examples of real changes: "Clarity: M1 named no test file, added `tests/spend_alerts/test_crossing.py`." "Edge cases: added the budget-lowered-below-spend example (#11)." A CPO check with four `pass` lines and no changes on a v1 draft deserves a second look.
