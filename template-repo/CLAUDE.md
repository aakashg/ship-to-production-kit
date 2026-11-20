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

## Commands
- Run tests: `<fill in, e.g. pytest -q>`
- Run locally: `<fill in>`
