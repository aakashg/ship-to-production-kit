# <Project name>
One paragraph: what this service does and who uses it.

## Layout
- `app/` application code
- `tests/` tests (CI runs all of them; no code merges without a passing suite)
- `infra/` Terraform. `infra/sandbox/` is safe to experiment in. `infra/prod/` is human-reviewed only.
- `scripts/` helper scripts (setup, local run, seed data)
- `docs/` features (`docs/features/<slug>/`), runbooks, `docs/OBSERVABILITY.md`
- `.claude/rules/` guardrails every agent must follow. `.claude/skills/` the org skills.

## How to work here
1. New feature: run the `design-agent` skill first. Do not write code until `IMPL-PLAN.md` says `Status: APPROVED by <name>`.
2. Build in small milestones, one PR each. Tests first for bug fixes.
3. Open a PR. The AI reviewer (CodeRabbit, see `.coderabbit.yaml`) reviews. Fix what it blocks on, then wait for approval.
4. Low-risk PRs merge automatically when approved. Anything under a path in `.github/CODEOWNERS` needs that team's human review.
5. Production watch is the `ops-agent` skill.
6. When an agent gets something wrong, fix the repo, not only the output: add the test, lint or rule line that stops it happening again, in the same PR or the next one.

## Gates (each one has a check you can run)
| Gate | Who opens it | Check |
|---|---|---|
| Plan approved before code | a human edits line 1 of `IMPL-PLAN.md` | `python3 .claude/skills/design-agent/scripts/check_design.py docs/features/<slug> --gate build` exits 0 |
| Design docs complete | the design agent, before it stops | `python3 .claude/skills/design-agent/scripts/check_design.py docs/features/<slug> --repo .` exits 0 |
| Change is LOW risk | rules in `.claude/rules/20-risk-and-review.md` | `python3 .claude/skills/ops-agent/scripts/risk_check.py --git main` exits 0 (exit 2 = HIGH) |
| High-risk PR reviewed | the code owner in `.github/CODEOWNERS` | branch protection: "Require review from Code Owners" |
| Fix rolled out partially | a human or the deploy pipeline | rollout plan in the ticket, per `.claude/skills/ops-agent/references/rollout-playbook.md` |

A passing check opens nothing by itself where a human is named. It tells you the docs or the diff are in shape.

## Done means
- The test command below ran in this session and you quote its pass count.
- A bug fix has a test you saw fail before the fix.
- The PR description says LOW or HIGH and why.
- Nothing you were not asked to touch changed (`git status` is clean outside the files you named).

## Stop and ask a human when
- A plan has an unanswered `needs you` row.
- A change touches a HIGH path, or you cannot test it.
- Tests fail after one retry.
- Anything looks like a security issue or a data leak. Say so first, run nothing.
- A step needs credentials, network access or a push you do not have.

## Commands
- Run tests: `<fill in, e.g. pytest -q>`
- Run locally: `<fill in>`
- Test the agent scripts: `python3 -m unittest discover -s .claude/skills/design-agent/scripts -p 'test_*.py'` and the same for `ops-agent`
