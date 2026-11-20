# Code standards
- Follow the existing style in the folder you are editing. Match naming and structure before inventing new ones.
- Every behavior change has a test. Every bug fix has a test that failed before the fix.
- Errors: client mistakes are 4xx with a clear message. Only our own failures are 5xx.
- Log in JSON with `request_id` and `trace_id` on every line. Never log secrets or full user content.
- Keep PRs small: one concern, under about 400 changed lines. Split bigger work into milestones.
- No new dependency without a one-line reason in the PR description.
