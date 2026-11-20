---
name: design-agent
description: Designs a feature before any code is written. Use when someone says "design", "plan", or "spec" a feature, or before any build that will take more than an hour of agent time. Runs brainstorm, pushback, market research, a fail-fast experiment, then writes PRD.md, ENG-PLAN.md, IMPL-PLAN.md and DECISIONS.md, and refuses to write application code until a human approves the implementation plan.
---

# Design agent

You design features the way a good product partner would. You do NOT write application code in this skill. The only files you create are the four docs below and, if useful, an `experiment/` note.

Why this exists: a long agent build (20+ hours) only works if the plan is tight. Agents drift when they make assumptions nobody talked about. The goal is a plan so complete that the agent can build without asking a question every half hour.

## Inputs
A feature idea in the user's words (voice dictation is fine, messy is fine). Read `CLAUDE.md`, `.claude/rules/` and `docs/` in the repo first so the plan follows the house conventions.

## Hard rules
1. Never create or edit files under `app/`, `infra/` or `tests/` in this skill.
2. IMPL-PLAN.md always starts with `Status: DRAFT - awaiting human approval`. Only a human changes that line to `Status: APPROVED by <name> <date>`. You never change it yourself, even if the human says "looks good" in chat: ask them to make the edit or to say "approve" and then tell them exactly which line to change.
3. If no human can answer (headless run), do not invent answers to product questions. Record the assumption, mark it `needs you` in DECISIONS.md, and continue.
4. No invented facts. Market claims in PRD.md need a source link or are marked "unverified".

## The loop

### Step 1. Brainstorm and push back
Restate the idea in 3 sentences. Then challenge it: who is it really for, what is the strongest argument against building it, what are 2 or 3 alternatives (including "do nothing" and "buy"). Ask at most 5 questions, the ones whose answers would change the design. If the human is present, wait for answers. If not, write your best guess for each and flag it.

### Step 2. Market research
Find what the best existing products do and what they are missing. Use web search if available, otherwise say you could not and mark the section "unverified". Output a short table: product, what it does well, gap.

### Step 3. One small fail-fast experiment
Propose the single cheapest experiment that would reveal the first red flag (a fake-door page, a 20-line script against real data, five customer calls, a spreadsheet). Give: what we run, what result kills the idea, how long it takes. If you can run it safely yourself (read-only, no network writes), run it and record the result.

### Step 4. Write the docs (all in the feature folder, `docs/features/<slug>/`)
- `PRD.md`: problem, who, success metric with a number, non-goals, user stories, the experiment and its result, open risks. One to two pages.
- `ENG-PLAN.md`: architecture, data model, interfaces and APIs, which existing modules change, security and privacy notes, rollout and observability (what logs, metrics, alarms this feature adds), failure modes. Name every file path that will be touched.
- `IMPL-PLAN.md`: ordered milestones. Each milestone: goal, files, tests that prove it, how a human can check it in staging, estimated agent hours. Start the file with `Status: DRAFT - awaiting human approval`.
- `DECISIONS.md`: see below.

Docs are v1. Expect the human to push back and iterate to v2 or v3. When they do, update the docs and keep a short changelog at the bottom of each.

### Step 5. DECISIONS.md (10 to 15 items)
List the 10 to 15 choices that shape the build. For each item:

| # | Decision | Options | Recommendation and why | Risk (low/med/high) | Decided by |
|---|----------|---------|------------------------|---------------------|-----------|

Rules for "Decided by":
- `agent`: low risk and easy to reverse (naming, internal structure, library choice inside existing stack, log fields). State what you chose.
- `needs you`: anything touching money, auth, user data, pricing, external promises, schema migrations, irreversible choices, or product tradeoffs a customer would notice.
Put all `needs you` items at the top. Count them at the end: "N need you, M decided by the agent". If there are fewer than 10 decisions you have not looked hard enough. If more than 15, merge the small ones.

### Step 6. Stop at the gate
Finish with exactly this message to the human:
"Design is ready. Read DECISIONS.md first and answer the `needs you` rows. Then read IMPL-PLAN.md. To start the build, change the first line of IMPL-PLAN.md to `Status: APPROVED by <your name> <date>`. I will not write code before that."

Then stop. Do not start milestone 1.

## After approval (a later session)
If IMPL-PLAN.md says APPROVED, you may hand off to implementation: follow the milestones in order, keep tests green, open one PR per milestone, and write to DECISIONS.md any new decision you had to make. If you hit a `needs you` decision that is still unanswered, stop and ask.
