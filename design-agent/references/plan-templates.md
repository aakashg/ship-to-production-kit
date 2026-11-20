# ENG-PLAN and IMPL-PLAN templates

## ENG-PLAN.md

```markdown
# ENG-PLAN: <feature name>
Version: v1 (<date>)

## 1. Assumptions
A1 <stack, existing module, data source>: <what you assumed and how M0 confirms it>

## 2. Architecture
<ASCII diagram of the new flow: request path, async jobs, stores, external calls>

## 3. Data model
<tables or documents, fields with types, keys, constraints, indexes; mark each change additive or not>

## 4. Interfaces and APIs
<endpoints, events, function signatures; request and response shapes; error codes, client errors are 4xx>

## 5. Files touched
| Path | New or changed | Why |
|---|---|---|

## 6. Edge cases and semantics
<boundaries, duplicates, concurrency, ordering, time zones, what happens when a dependency is down>

## 7. Security and privacy
<authz on every new endpoint, PII stored or sent, secrets, abuse cases>

## 8. Observability
Logs: <event names and fields, with request_id and trace_id>
Metrics: <name, type, what a bad value looks like>
Alarms: <condition, threshold, who is paged>
Add each to docs/OBSERVABILITY.md in the milestone that ships it.

## 9. Evals (only if the feature calls an LLM)
Eval: <name, what it scores, where it runs>
Agreement with PM labels on the acceptance examples: <N of M agree; list each disagreement>
Gate: <which milestone it blocks, and the pass threshold>
Drift re-check: <when, on how many fresh production samples>

## 10. Failure modes
| Failure | User sees | Detection | Mitigation |
|---|---|---|---|

## 11. Rollout
<flag name, stages (1% then 10/50/100), metric to watch at each stage, rollback trigger>

## Changelog
```

## IMPL-PLAN.md

Line 1 is always the DRAFT line. A human, never the agent, changes it.

```markdown
Status: DRAFT - awaiting human approval

# IMPL-PLAN: <feature name>
Version: v1 (<date>). Do not start until line 1 is changed by a human and every `needs you` row in DECISIONS.md is answered.
Total estimate: <N> agent hours, plus human review time.

## M0. <confirm assumptions> (<h>) - LOW risk
- Goal: <one sentence>
- Files: <every path>
- Tests: <test names and what each proves>
- Human check: <what a person does in staging to see it work>

## M1. ...
```

### A milestone that passes review

```markdown
## M1. Pure crossing logic (4h) - LOW risk
- Goal: decide which thresholds a spend change crosses. No I/O.
- Files: app/spend_alerts/crossing.py, tests/spend_alerts/test_crossing.py
- Tests: boundary inclusive (79.99 to 80.00 fires), integer micro-USD math, one jump across 50 and 80 fires only 80,
  budget raised mid-month re-arms only thresholds above current spend, month boundary in UTC.
- Human check: read the worked-example table in the PR description against DECISIONS #7.
```

### Milestone rules

- One PR per milestone, under about 400 changed lines. Split if bigger.
- Every milestone names its risk bucket. A milestone that touches a HIGH path (auth, billing, migrations, infra, public API) says `HIGH, human owner required` and names the owner from CODEOWNERS.
- Every milestone lists every file it creates or changes. The build agent stops and asks before touching an unlisted file.
- Put risky, reversible work behind a flag, and ship a shadow mode (compute but do not act) before the user-visible step when you can.
- The last milestone is rollout: 1% first, with the metric and threshold that trigger a rollback.
