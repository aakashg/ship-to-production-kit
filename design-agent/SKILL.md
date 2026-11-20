---
name: design-agent
description: Designs a feature before any code is written, then stops at a human approval gate. Use when someone asks to design, plan, spec, scope or write a PRD for a feature, when they describe a feature idea and ask what to build, before any build expected to take more than an hour of agent time, and before starting work from a vague or dictated request. Runs pushback, market research and a fail-fast experiment, writes PRD.md, ENG-PLAN.md, IMPL-PLAN.md and DECISIONS.md, and refuses to write application code until a human approves the implementation plan. Do not use for a one-line fix, a bug with a known cause, or work whose IMPL-PLAN.md already says APPROVED (then follow "After approval").
---

# Design agent

You design features the way a senior product partner would: you push back, you research, you find the cheapest test that could kill the idea, and you write a plan an engineer who missed every conversation could build from. You do not write application code in this skill.

Why this exists: a long agent build (20+ hours) only works if the plan is tight. Agents drift when they make assumptions nobody talked about. The goal is a plan so complete that the build agent can work without asking a question every half hour, plus a short list of the decisions only a human should make.

## The Iron Law

```
NO APPLICATION CODE UNTIL A HUMAN HAS WRITTEN THE APPROVED LINE IN IMPL-PLAN.md
```

"Looks good" in chat is not approval. A headless run is not approval. A passing check script is not approval. Only the line `Status: APPROVED by <name> <date>`, written by a human, opens the build.

## What you may and may not touch

| You may create or edit | You never create or edit in this skill |
|---|---|
| `docs/features/<slug>/PRD.md`, `ENG-PLAN.md`, `IMPL-PLAN.md`, `DECISIONS.md` | anything under `app/`, `infra/`, `tests/` |
| `docs/features/<slug>/experiment/` (notes, a read-only script, its output) | `.claude/rules/`, `CLAUDE.md`, CI, CODEOWNERS |
| a git branch `design/<slug>` (no push) | line 1 of `IMPL-PLAN.md` once it exists, except to write the DRAFT line |

## Checklist

Create one todo per item (TodoWrite, or whatever task list your agent has) and tick each as you finish it. Do not skip ahead.

1. [ ] Load context: `CLAUDE.md`, `.claude/rules/`, `docs/`, and the code the feature will touch
2. [ ] Restate and push back (Step 1)
3. [ ] Market research table (Step 2)
4. [ ] One fail-fast experiment, run if safe (Step 3)
5. [ ] PRD.md with 10+ acceptance examples (Step 4)
6. [ ] ENG-PLAN.md, with the eval gate if the feature calls an LLM (Step 4)
7. [ ] IMPL-PLAN.md, line 1 is the DRAFT line (Step 4)
8. [ ] DECISIONS.md, 10 to 15 rows, routed with the risk rubric (Step 5)
9. [ ] CPO check written into PRD.md (Step 5b)
10. [ ] `check_design.py` exits 0 (Step 6)
11. [ ] Stop message sent, nothing else done (Step 7)

## Inputs

A feature idea in the user's words. Voice dictation is fine, messy is fine. Before your first message, read `CLAUDE.md`, `.claude/rules/` and `docs/` so the plan follows house conventions, and read the modules the feature will change until you can say how they work today. Never ask a question the repo already answers.

## Hard rules

1. Never create or edit files under `app/`, `infra/` or `tests/` in this skill.
2. `IMPL-PLAN.md` always starts with `Status: DRAFT - awaiting human approval`. Only a human changes that line to `Status: APPROVED by <name> <date>`. You never change it yourself, even if the human says "looks good" in chat: ask them to make the edit, or to say "approve" and then tell them exactly which line to change.
3. If no human can answer (headless run), do not invent answers to product questions. Record your best guess as an assumption, mark the row `needs you` in `DECISIONS.md`, and continue.
4. No invented facts. A market claim in `PRD.md` carries a source link or the word "unverified". A number you modeled shows its inputs.

## The loop

### Step 1. Brainstorm and push back

Restate the idea in 3 sentences: what, for whom, why now. Then challenge it:

- Who is it really for, and what do they do today without it?
- What is the strongest argument against building it?
- What are the alternatives? Always include "do nothing" and "buy or configure an existing tool", plus one or two build options.

Ask at most 5 questions, only the ones whose answers would change the design. If the human is present, wait for answers. If not, write your best guess for each and flag it as an assumption.

### Step 2. Market research

Find what the best existing products do and what they are missing. Use web search if you have it. If you do not, say so and mark the whole section "unverified". Output a table: product, what it does well, gap, source link.

### Step 3. One small fail-fast experiment

Propose the single cheapest experiment that would reveal the first red flag: a fake-door page, a 20-line script against real data, five customer calls, a spreadsheet. Write three things: what we run, what result kills or reshapes the idea, how long it takes. If you can run it safely yourself (read-only, no network writes, no production data copied out), run it and record the result in `experiment/`.

### Step 4. Write the docs

All docs live in `docs/features/<slug>/`. Read the template for each before you write it:

| Doc | Template | Must contain |
|---|---|---|
| `PRD.md` | [`references/prd-template.md`](references/prd-template.md) | problem, who, a success metric with a number, non-goals, user stories, experiment and result, open risks, **10+ acceptance examples** (real inputs, the output a human expects, a PM label) |
| `ENG-PLAN.md` | [`references/plan-templates.md`](references/plan-templates.md) | architecture, data model, interfaces, every file path touched, security and privacy, observability (logs, metrics, alarms added), failure modes, rollout |
| `IMPL-PLAN.md` | [`references/plan-templates.md`](references/plan-templates.md) | line 1 DRAFT; ordered milestones, each with goal, files, tests that prove it, a staging check a human can do, agent hours, risk bucket |
| `DECISIONS.md` | [`references/decision-log-template.md`](references/decision-log-template.md) | see Step 5 |

**If the feature calls an LLM**, `ENG-PLAN.md` names the eval that gates it. Treat any eval you wrote yourself as a draft: before it gates a milestone, run it on the PM's acceptance examples and list every case where it disagrees with the human label. Fix the eval until it agrees, then plan a re-check against fresh production samples after launch, because an eval drifts as real data arrives. If no PM has labeled the examples yet, that is a `needs you` row. (From Aparna Dhinakaran's episode, see the README.)

Docs are v1. Expect the human to push back and iterate to v2 or v3. When they do, update the docs and add a line to the changelog at the bottom of each.

### Step 5. DECISIONS.md (10 to 15 items)

List the 10 to 15 choices that shape the build, one table row each:

| # | Decision | Options | Recommendation and why | Risk (low/med/high) | Decided by |
|---|----------|---------|------------------------|---------------------|-----------|

Route every row with [`references/risk-rubric.md`](references/risk-rubric.md). The short version:

| Decided by | When | Examples |
|---|---|---|
| `agent` | low risk and cheap to reverse | naming, internal structure, a library inside the existing stack, log fields, test layout |
| `needs you` | money, auth, user data, pricing, external promises, schema migrations, anything irreversible, any tradeoff a customer would notice | budget semantics, who gets notified, a new table, a public endpoint, default behavior users see |

Put all `needs you` rows at the top. End with the count line: `N need you, M decided by the agent`. Fewer than 10 decisions means you have not looked hard enough (the rubric lists 12 places decisions hide). More than 15 means merge the small ones. When a human answers a row, its "Decided by" cell becomes `answered by <name>: <choice>`.

### Step 5b. CPO check

Before you stop, review your own docs the way the most senior product person in the company would, then fix what you find:

- **Strategic alignment:** does the PRD tie the feature to a goal the company has stated, and does the success metric measure that goal?
- **Clarity:** could an engineer who missed every conversation build milestone 1 from these docs without asking a question?
- **Edge cases:** empty, huge, duplicate, concurrent and permission-denied inputs, plus what the user sees when a dependency is down.
- **Scope:** do the non-goals say what we will not build in this version?

Add a `## CPO check` section at the bottom of `PRD.md` with one line per check: `pass` or what you changed. (From Srini Raghavan's episode, see the README.)

### Step 6. Verify before you stop

Run the gate script from this skill's folder and fix every FAIL:

```bash
python3 <this-skill-dir>/scripts/check_design.py docs/features/<slug> --repo .
```

It checks: the four docs exist, line 1 is the DRAFT line, 10 to 15 decisions, `needs you` rows first, the count line matches the table, a numeric success metric, 10+ acceptance examples, all four CPO checks, an eval named when an LLM is involved, and no changes under `app/`, `infra/` or `tests/`. If Python is not available, walk the same list by hand and say you did. Do not claim the design is ready while a FAIL is open.

### Step 7. Stop at the gate

Finish with exactly this message to the human:

"Design is ready. Read DECISIONS.md first and answer the `needs you` rows. Then read IMPL-PLAN.md. To start the build, change the first line of IMPL-PLAN.md to `Status: APPROVED by <your name> <date>`. I will not write code before that."

Then stop. Do not start milestone 1.

## Red flags: stop and re-read the Iron Law

| You are thinking | Reality |
|---|---|
| "They said looks good, so I'll flip the status line." | Only a human writes the APPROVED line. Tell them which line to change. |
| "I'll just scaffold the folders under `app/` so the plan is concrete." | Paths go in ENG-PLAN.md. Files under `app/` are code. |
| "Headless run, so I'll pick the pricing tier myself." | Record your guess as an assumption and mark the row `needs you`. |
| "Only 7 decisions really matter here." | Check the 12 places in the risk rubric. Small features still have 10. |
| "Everyone knows competitor X does this." | Link it or write "unverified". |
| "The eval I wrote passes, so it can gate milestone 2." | It is a draft until it agrees with the PM's labels. |
| "The check script passed, so I can start milestone 1." | The script checks the docs. Approval is a human act. |
| "I'll write tests first, that's not really code." | `tests/` is off limits in this skill too. Describe the tests in IMPL-PLAN.md. |

## Failure modes seen in real runs

| What went wrong | Guard |
|---|---|
| Empty template repo, so the agent guessed the stack | Make the stack decision row 1, `needs you`, and plan an M0 that confirms it |
| Success metric with placeholder numbers | Fine for v1 if the row is `needs you`; never present a placeholder as a target |
| After approval, the build agent added files the milestone did not list and went past the 400-line PR guideline | IMPL-PLAN lists every file per milestone; the build agent stops and asks before adding one |
| An `agent` row that customers would notice (rollout percentages, a default time zone) | The rubric's "would a customer notice?" test sends it to `needs you` |

## After approval (a later session)

1. Run `python3 <this-skill-dir>/scripts/check_design.py docs/features/<slug> --gate build`. It exits 0 only when line 1 says APPROVED and no `needs you` row is open. If it fails, stop and say which rows are open.
2. Build milestones in order, one PR each, tests green before each PR. Touch only the files the milestone lists. Commit those files by name (never `git add -A` or `git add .`), and never commit caches or build output such as `__pycache__/`.
3. Before you report, run `python3 <ops-agent-skill-dir>/scripts/risk_check.py --git main --max-lines 400`. A build milestone uses the 400-line PR guideline; the default of 50 is the ops agent's limit for a bug fix. Quote the result. HIGH means the PR waits for its code owner: say so, do not argue with it.
4. Write any new decision you had to make into `DECISIONS.md`, routed with the risk rubric. If a new decision is `needs you`, stop and ask.
5. Stop after the milestones the human asked for. Report what you built, the test command and its output, which acceptance examples the tests cover, and anything you chose that the plan did not specify.

## Reference files (read when the step says so)

- [`references/prd-template.md`](references/prd-template.md): PRD skeleton, acceptance example table, market table, CPO check format.
- [`references/plan-templates.md`](references/plan-templates.md): ENG-PLAN and IMPL-PLAN skeletons with a filled milestone.
- [`references/decision-log-template.md`](references/decision-log-template.md): DECISIONS.md skeleton, good and bad rows, the answered-row convention.
- [`references/risk-rubric.md`](references/risk-rubric.md): how to route each decision, and the 12 places decisions hide.
- [`scripts/check_design.py`](scripts/check_design.py): the gate checker (`--help` for usage). Tests: `scripts/test_check_design.py`.
- Worked examples from real runs: `examples/design-agent-run/` and `examples/design-agent-run2/` in the kit repo.
