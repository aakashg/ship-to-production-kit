# Notes: what each piece is grounded in, and what is honest about it

Source: transcript of The Growth Podcast with Shuhao Zhang (`source/transcript.txt`). Timestamps are as printed there.

## Grounding

| Kit piece | What Shuhao said | Timestamp |
|---|---|---|
| design-agent: brainstorm, challenge, alternatives, small experiment | Encourages the agent to challenge his idea, propose alternatives, and run a small-scale experiment to fail fast | 19:53 |
| design-agent: PRD, ENG-PLAN, IMPL-PLAN, v2s | "PRD, the engineering plan, the implementation plan", goes back and forth until v2 | 20:27 to 20:59 |
| design-agent: DECISIONS.md, 10 to 15 items, agent decides low risk | "I always ask it to list the 10, 15 decisions need my attention and I also encourage it to make decisions on the low-risk ones" | 20:59 |
| design-agent: approval gate before a long build | Frontloads designs so the agent can go off on a "20 plus hours or multi-day" build | 21:32 |
| design-agent: plan review with recommendations and status | Reviews the plan, agent gives recommendations on bigger design decisions | 8:50 |
| template-repo layout | Starts from a template: `infra/` with sandbox and production Terraform, `app/` for logic, tests, same setup across projects | 14:56 to 16:35 |
| template-repo `.claude/rules`, org best practices | `.claude` folder holds org-wide best practices and "the guardrails that agent must follow", shared so everyone has the same coding agent style | 17:40 |
| agent-agnostic skills | Skills and plugins can be migrated between Claude Code and Codex | 18:12 |
| .coderabbit.yaml: loop, risk sort, auto-merge, tagging engineers | CodeRabbit requests changes, the coding agent responds, they loop. High risk: agent tags the right engineers. Low risk: auto-approved and auto-merged | 11:05 to 11:37 |
| .coderabbit.yaml: constitution | The reviewer has context on codebase, coding standards, and strictness (conventions plus how strict) | 12:42 |
| ops-agent: VPN, observability skill | VPN on the dev server, plus a skill that explains how the observability system works, where things are and formats | 33:31 |
| ops-agent: the max-tokens bug | LLM call hits max tokens, returns a server error; really a client error; found from logs and traces | 34:04 |
| ops-agent: ticket, then fix | Opens a ticket first like an engineer would, documents findings and potential fixes, then fixes | 34:39 |
| ops-agent: 1 percent rule | "Always do this partial rollout, always, even for a critical fix", and it used to be too costly for humans to watch | 37:58 to 38:29 |

Not in the transcript, so our own additions (marked so you can drop them): the exact risk path list, `max_merge_risk: low`, the rollback thresholds (+0.5 points error rate, +20% p95), the three-issue cap per ops run, the `Status: APPROVED` line mechanic, and the custom pre-merge checks.

## CodeRabbit: what it does natively and what it does not

Verified against the live JSON schema (`https://coderabbit.ai/integrations/schema.v2.json`, fetched 2026-11-20) and the docs.
`.coderabbit.yaml` here validates against that schema with `jsonschema` (0 errors; a deliberately broken copy gives 2 errors, so the check is real).

Native to CodeRabbit:
- Strictness: `reviews.profile` (quiet, chill, assertive).
- Conventions: `reviews.path_instructions` per glob, and `knowledge_base.code_guidelines.filePatterns` to read `CLAUDE.md` and `.claude/rules/`.
- Request changes and approve: `reviews.auto_approvals.enabled`. It requests changes for blocking findings and approves when threads are resolved, the latest commit is reviewed, pre-merge checks pass, and risk limits are met. `min_blocking_severity` sets what blocks. Paid plan feature (Essentials and above).
- Risk limits: `auto_approvals.max_merge_risk`, `merge_risk_instructions`, and `auto_approvals.overrides` with `paths` to withhold approval for infra, auth, billing and migrations.
- Custom checks: `pre_merge_checks.custom_checks` in `warning` or `error` mode.
- Re-review on each push, so the coding agent and the reviewer can loop.

Not native (needs GitHub):
- Merging. The docs say plainly: "An approval is not a merge." Automatic Approvals "does not merge the pull request". Merging is done by GitHub auto-merge, or by CodeRabbit Triage rules (Team plan and above, configured in the CodeRabbit web app, not in `.coderabbit.yaml`). We used GitHub auto-merge via `.github/workflows/auto-merge-low-risk.yml`.
- Making a named human review. CodeRabbit withholds approval on high-risk paths, but it does not guarantee the right engineer reviews. That is GitHub `CODEOWNERS` plus branch protection "Require review from Code Owners". `auto_assign_reviewers` only assigns suggested reviewers.
- Required status check and approval counts are branch-protection settings, not YAML in this repo.

Honest gaps: we did not run CodeRabbit on a live repo (no account or GitHub repo in this build), so the YAML is schema-valid and doc-aligned but untested end to end. The GitHub workflow is YAML-valid but never ran on GitHub. The `request_changes_workflow` key is a deprecated legacy alias in the schema; it is kept for older installs and can be deleted.

Docs used:
- https://docs.coderabbit.ai/pr-reviews/automatic-approvals
- https://docs.coderabbit.ai/pr-reviews/approval-risk-limits
- https://docs.coderabbit.ai/pr-reviews/approval-policies
- https://docs.coderabbit.ai/triage/rules
- https://docs.coderabbit.ai/llms.txt (index)
