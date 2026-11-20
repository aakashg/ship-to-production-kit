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
