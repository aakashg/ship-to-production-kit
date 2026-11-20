# Risk and review
LOW risk (AI review may approve and auto-merge): docs, tests, UI copy and styling, small bug fixes inside one module, internal refactors with tests.
HIGH risk (human review required): auth, payments and billing, database migrations and schema, `infra/`, secrets and config for prod, public API contract changes, data deletion, security-sensitive dependencies.
When unsure, treat it as HIGH. Say in the PR description which bucket you chose and why.
Rollout: ship partial (1 percent) first, even for a critical fix, whenever traffic allows.
