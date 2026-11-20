# Guardrails (org-wide, every agent, every repo)
- Never push to `main`. Always work on a branch and open a PR.
- Never read, print, commit or log secrets. Use the secret manager; `.env` files are never committed.
- Never run commands against production. Production changes go through a reviewed PR and the deploy pipeline.
- Never run destructive commands (`rm -rf`, `DROP`, `terraform destroy`, force-push) without a human saying so in this session.
- Do not edit `infra/prod/`, auth, billing or migration code without a human owner on the PR (see CODEOWNERS). You may draft the change and say it needs review.
- Do not disable, skip or delete tests to make a build pass.
- If a plan has unanswered `needs you` decisions, stop and ask.
