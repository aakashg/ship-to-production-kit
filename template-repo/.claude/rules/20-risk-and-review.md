# Risk and review
LOW risk (AI review may approve and auto-merge): docs, tests, UI copy and styling, small bug fixes inside one module, internal refactors with tests.
HIGH risk (human review required): auth, payments and billing, database migrations and schema, `infra/`, secrets and config for prod, public API contract changes, data deletion, security-sensitive dependencies.
When unsure, treat it as HIGH. Say in the PR description which bucket you chose and why.
Rollout: ship partial (1 percent) first, even for a critical fix, whenever traffic allows.
Check the bucket with `python3 .claude/skills/ops-agent/scripts/risk_check.py --git main` (exit 0 LOW, exit 2 HIGH). It uses the same path list as `.github/workflows/auto-merge-low-risk.yml`; change both together. The script can only raise the bucket: a clean path list does not make an untested or cross-service change LOW.
