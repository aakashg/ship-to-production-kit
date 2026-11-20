# Test log (2026-11-20)
Tool: Claude Code 2.1.329, `claude -p --model sonnet`, permissions limited to the test folder (Read, Edit, Write, python, pytest, git, grep, ls). No network tools for the ops run. Nothing pushed.

## Ops agent on a toy FastAPI gateway that returns 500 on max-tokens
Service had 1,200 JSON log lines and 113 failing requests (10.9% of /v1/chat), plus traces. Data is synthetic, built to mimic the bug Shuhao described.
- Run 1 (first version of skill): 11 turns, 45 s wall, $0.24. Wrote TICKET.md and PR.md, branch ops/max-tokens-4xx, 500 changed to 400, added a failing-first test. Suite 3 of 3 pass (we re-ran it ourselves).
- Run 2 (after one skill edit, fresh reset): 11 turns, 52 s, $0.24. Same result, 3 of 3 pass.
- Skill edit between runs: told the agent to commit named files only (run 1 left tracked .pyc files in the repo, harmless) and to watch the 5xx and 4xx split separately when a fix changes a status code. The skill passed on the first try, so this was hygiene, not a rescue.
- Only the toy data's `docs/OBSERVABILITY.md` was needed to point the agent at the logs; without a filled map the skill tells the agent to stop.

## Design agent on "spend alerts for an AI gateway"
Template repo copy, headless, `--max-turns 25`, web search allowed.
- 16 turns, 182 s, $0.56. Wrote PRD.md, ENG-PLAN.md, IMPL-PLAN.md, DECISIONS.md (about 5,000 words total). IMPL-PLAN stayed `Status: DRAFT - awaiting human approval`. No files created under app/, infra/ or tests/ (git status showed only docs/features/).
- DECISIONS.md: 14 decisions.
- Caveat: the stand-in repo was empty, so the agent assumed a stack and flagged it as decision 1. Market claims carry links or the word unverified; we did not fact-check each link.

## Design agent runs 2 and 3: "weekly email digest of the dashboard"
Output in examples/design-agent-run2/ (run2-docs = docs as written before our answers; run3-code = app/ and tests/ the agent wrote).
- Run 2 (design, headless, web search on): 22 turns, 156 s, $0.51. 4 docs plus experiment/README.md. 15 decisions: 11 need you, 4 agent. IMPL-PLAN stayed DRAFT, git status showed only docs/ (it created branch design/weekly-email-digest, nothing committed). Six milestones, M0 is a human gate.
- Judgement calls: row 5 (success metric, placeholders) is low risk but PM-owned, so needs you is right. Row 11 (stack) is a repo question, answerable by an agent in a real repo; here it is only needs you because the template is empty. Agent rows 12 (rollout 1/10/50/100 percent) and 14 (default time zone) are customer-visible and arguably the PM's. Row 4 (run the experiment first) is the most PM-like call and was correctly flagged.
- Run 3 (approval): we answered all 11 rows, set line 1 to APPROVED by test, asked for milestone 1 only. 8 turns, 86 s, $0.34. Built only M1 files (migration, models, tests), 44 tests pass when we re-ran them, committed once on the feature branch, nothing pushed. Slight overreach: also added .gitignore and pytest.ini, and the diff was 450 lines vs the 400 PR guideline (said so itself). It listed its own unspecified choices.
- Skill edit: none needed.

## Skills v2: references, scripts and gates (2026-11-20, later the same day)
Both skills were rebuilt with an Iron Law, a checklist, red-flag tables, `references/` files and `scripts/`. Everything below was run on 2026-11-20 on macOS, Python 3.14, Claude Code 2.1.329.

### Script tests (standard library `unittest`)
- `python3 -m unittest discover -s design-agent/scripts -p 'test_*.py'`: 7 tests, OK.
- `python3 -m unittest discover -s ops-agent/scripts -p 'test_*.py'`: 9 tests, OK. One test checks that `risk_check.py` uses the exact `HIGH=` pattern from `.github/workflows/auto-merge-low-risk.yml`, so the two cannot drift apart silently.

### Scripts on the existing example data
- `log_summary.py examples/ops-agent-run/toy-service/logs/app.jsonl --traces .../traces`: 400 requests, 45 5xx (11.25%), all in one cluster `500 /v1/chat MaxTokensExceeded: completion hit max_tokens=N (prompt_tokens=N)`, flagged CLIENT-CAUSED?. /v1/chat: 349 requests, 12.89% 5xx, p95 305 ms. 1 customer-visible defect, 45 requests hit; no previous window in the file, and the script says so. The committed log is a 400-line, 20-minute excerpt of the 1,200-line file used in the first ops runs, so these counts are lower than the 113 in the original ticket.
- `check_design.py` on `examples/design-agent-run/spend-alerts` and `examples/design-agent-run2/run2-docs/weekly-email-digest`: both FAIL on two checks, 0 acceptance examples and no CPO check. Expected: those runs happened before the acceptance-example and CPO-check steps were added. Every other check passes (14 and 15 decisions, needs-you rows first, count lines match: 9/5 and 11/4).
- `risk_check.py app/main.py tests/test_chat.py`: LOW, exit 0. `risk_check.py app/auth/session.py`: HIGH, exit 2.

### Headless skill runs (`claude -p --model sonnet --max-budget-usd 0.60 --setting-sources project,local`)
Fresh copies in a scratch folder, no web access, permissions limited to Read, Write, Edit, Glob, Grep, Skill, TodoWrite, python, ls, cat, grep and local git (no push).

**Ops agent v2 on the toy gateway** (fresh copy of `examples/ops-agent-run/toy-service` plus the v2 skill and the template rules). 22 turns, 60 s, $0.22.
- Found the one real issue (45 MaxTokensExceeded 500s), wrote `TICKET.md` with the rollout numbers, branch `ops/max-tokens-4xx`, one local commit, nothing pushed.
- Red run quoted (`assert 500 == 400`, 1 failed 2 passed), then green: 3 passed. We re-ran the suite ourselves: 3 passed.
- `PR.md` has a `## Rule to add` line; `.claude/rules/` unchanged (0 diff lines, checked).
- Two deviations it reported itself: its first branch command failed, so the red test ran on `main` before it branched (nothing was committed there); and `risk_check.py --service-dir .` wrongly returned HIGH. That second one was a bug in the script. Fixed the same day (the repo root now counts as the service), a regression test was added, and Markdown files no longer count toward the 50-line code limit. After the fix, `risk_check.py --git main --service-dir .` on its branch says LOW, 15 changed code lines.
- Caveat: the ticket template's filled example comes from this same toy bug, so this run shows the v2 skill loads, follows its gates and uses the scripts. It is not a blind test of discovery; the two original runs above are.
- Output: [`skills-v2-smoke/ops/`](skills-v2-smoke/ops/).

**Design agent v2 on "per-API-key monthly request quotas"** (fresh copy of `template-repo/`). 22 turns, 139 s, $0.42.
- Wrote the four docs plus a read-only experiment script and its output (about 4,200 words). 15 decisions: 12 need you, 3 agent. 15 acceptance examples, a CPO check, market rows marked unverified (no web access).
- Ended with the exact stop message. `IMPL-PLAN.md` line 1 stayed `Status: DRAFT - awaiting human approval`. `git status` showed only new files under `docs/features/`; nothing under `app/`, `infra/` or `tests/`; nothing committed.
- We re-ran `check_design.py --repo .` ourselves: design gate PASS, 0 failed. `--gate build`: FAIL (still DRAFT, 12 open rows), which is the correct answer before a human approves.
- Output: [`skills-v2-smoke/design/`](skills-v2-smoke/design/).

Not run in this round: a design run with a human answering questions while it runs. The post-approval build and the live CodeRabbit setup were run next; see the two sections below. `.coderabbit.yaml` was re-validated against the published schema: 0 errors (a deliberately broken copy gives 1 error).

## Design agent v2 after approval: build milestone 1 only (2026-11-20)
Input: the quotas design from the v2 smoke run above, unchanged, in a fresh copy of `template-repo/` (test command filled in as `python3 -m pytest -q`, the one edit the setup step asks an engineer to make). Same `claude -p --model sonnet --setting-sources project,local` setup, `--max-budget-usd 0.80`, permissions limited to Read, Write, Edit, Glob, Grep, Skill, TodoWrite, python, ls, cat, mkdir and local git (no push). Prompt, verbatim: "The plan in docs/features/api-key-monthly-quotas is approved. Use the design-agent skill and build milestone 1 (M1) only."

**The approval step, done the way the skill says.** We acted as the PM and answered all 12 `needs you` rows, each with a reason, in [`DECISIONS-ANSWERED.md`](skills-v2-build/approved-docs/DECISIONS-ANSWERED.md). Each "Decided by" cell became `answered by test-pm: <choice>`, the PRD example labels were updated to match (example #13 now expects a 400), M0 was waived because decision 1 confirms the stack, and line 1 of `IMPL-PLAN.md` became `Status: APPROVED by test-pm 2026-11-20`. Before the run: `check_design.py --gate build` PASS (12 answered, 0 open) and the design gate still PASS. Before approval the same build gate had failed (DRAFT, 12 open rows).

**Run 1 (skill as shipped).** 23 turns, 35 s (41 s wall), $0.24.
- Ran the build gate first, built only the two M1 files (`app/quota/period.py`, `tests/quota/test_period.py`), committed once on a branch, nothing pushed, and stopped before M2 (it named M2 as HIGH, needing the migration owner).
- Tests: 7 new plus the smoke test. We re-ran them: 8 passed. They check PRD examples #3 (Nov 20 13:05 UTC resets at 2026-12-01, 903,300 s), #4 (00:00:00 on the 1st starts a new period) and #12 (Dec 31 23:59:59, 1 s), plus February, leap day and non-UTC input.
- Two problems. It ran `git add app/quota tests/quota`, which committed two `__pycache__` `.pyc` files. And it ran `risk_check.py --git main` with the default limit, got HIGH for "109 changed lines > 50", and told the PM to check the rule. The 50-line limit is the ops agent's limit for a bug fix. The auto-merge workflow only judges paths, so the two gates disagreed on a small date-math milestone.

**Fix, then run 2.** `design-agent/SKILL.md` "After approval" now tells the agent to commit the milestone's files by name and never caches, and to run `risk_check.py --git main --max-lines 400` (the 400-line PR guideline) and quote it. Its final report must also name the acceptance examples the tests cover. `template-repo/` gained a `.gitignore` (`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `.env`). Fresh copy from the same approved commit.
- 18 turns, 35 s (41 s wall), $0.19.
- Gate first, then exactly two files, 94 lines, one commit on `build/quota-m1`, clean `git status`, nothing pushed.
- Tests: 8 new plus the smoke test. We re-ran them: 9 passed. Same three PRD examples checked, plus February, leap day and fractional-second rounding.
- `risk_check.py --git main --max-lines 400`: LOW, exit 0 (2 files, no high-risk path). We re-ran it: same.
- Stopped after M1 and wrote no new decisions. It listed what it chose that the plan did not say: naive datetimes raise `ValueError`, and no `__init__.py` files because the plan listed only two files.
- 3 Bash calls were refused by the permission sandbox (shell variables in the command); it rewrote them and carried on.

Total for both runs: $0.43. Output: [`skills-v2-build/`](skills-v2-build/) (approved docs, prompt, each run's result JSON, commit and diff, our verification output; run 2 also has its full transcript with local paths replaced).

## Live CodeRabbit review: sandbox ready, review pending the app install (2026-11-20)
Sandbox: public repo [aakashg/ship-kit-demo](https://github.com/aakashg/ship-kit-demo), built from `template-repo/` plus the toy gateway from the ops run, the kit's `.coderabbit.yaml`, CI and auto-merge workflow, and a `CODEOWNERS` that names one real owner. Branch protection on `main`: 1 approval, review from Code Owners, required checks `test` and `CodeRabbit`, auto-merge allowed.

Two PRs:
- [#1](https://github.com/aakashg/ship-kit-demo/pull/1), LOW: the ops agent's fix (`examples/ops-agent-run/fix.diff`, applied unchanged). `risk_check.py`: LOW, 17 lines. 5 tests pass.
- [#2](https://github.com/aakashg/ship-kit-demo/pull/2), HIGH: an expired session on `/v1/me` now gets a 401 (it got a 500) through a new helper in `app/auth/session.py`. The two new tests fail on `main` (`assert 500 == 401`) and pass on the branch, 6 tests in all. `risk_check.py`: HIGH, high-risk path `app/auth/session.py`.

What GitHub did before any AI review, from `check_pr.sh` ([`live-review/results-before-install.md`](live-review/results-before-install.md)):
- #1: CI `test` pass, the workflow turned on auto-merge (squash, enabled by `github-actions`), state BLOCKED waiting for an approval and the `CodeRabbit` check.
- #2: CI `test` pass, the workflow labeled it `needs-human-review` and left auto-merge off, state BLOCKED.

One bug found by the first push: CI ran bare `pytest`, which does not put the repo root on the import path, so both test files failed to import `app`. The kit's `.github/workflows/ci.yml` now runs `python -m pytest -q`. The fix went to the sandbox's `main` as a direct owner push (an admin bypass of branch protection, used for setup; one more such push later changed only the sandbox README wording), and both PR branches were rebased onto the CI fix.

Not run yet: the CodeRabbit review itself. The app is not installed on this account, and installing a third-party GitHub App is the account owner's call. After the install, `bash examples/live-review/check_pr.sh` records each PR's reviews, CodeRabbit comments, checks, labels and merge state in one command.
