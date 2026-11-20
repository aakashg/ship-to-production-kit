# Ship-to-production kit

Four pieces that copy the setup Shuhao Zhang (CPO, TinyFish) described on The Growth Podcast. He did not share his files, so this is our own version, built from what he said and tested on a toy service.

What is in the box:
- `design-agent/` a Claude Code skill that designs a feature and will not start coding until a human approves the plan
- `template-repo/` the starter repo every project begins from (rules, skills, infra stubs, tests)
- `.coderabbit.yaml` + `.github/` the AI review rules, the owners file, and an auto-merge workflow for low-risk PRs
- `ops-agent/` a Claude Code skill that watches production, writes tickets and fixes low-risk bugs
- `examples/` real outputs from our test runs

You need: a PM, one engineer, a GitHub repo, Claude Code, and a CodeRabbit account (paid plan, see Step 4). One afternoon is enough for steps 1 to 5. Step 6 is a second session.

## Setup, in order

**Step 1 (engineer). Make the template repo.**
Copy `template-repo/` into a new GitHub repo called something like `starter`. Mark it as a template repository in GitHub settings. Replace the placeholder text in `CLAUDE.md` and add your real test command. Copy the two skill folders `design-agent/` and `ops-agent/` into `.claude/skills/` as real folders (the links inside the kit only work when the kit stays together).

**Step 2 (PM and engineer). Write your rules.**
Open `.claude/rules/`. Keep the guardrails, then edit the code standards and the risk list so they match how your team really works. Decide together what is LOW risk (docs, tests, small fixes) and what is HIGH risk (auth, money, database changes, infra). Short beats long. Agents follow ten clear rules better than a hundred vague ones.

**Step 3 (engineer). Add the owners file.**
Copy `.github/CODEOWNERS` into the repo and replace the team handles. In GitHub, go to Settings, Branches, and add a rule for `main`: require 1 approval, require review from Code Owners, require status checks (your CI and `CodeRabbit`), and turn on "Allow auto-merge" in the general repo settings.

**Step 4 (engineer). Turn on the AI reviewer.**
Install the CodeRabbit GitHub app on the repo. Copy `.coderabbit.yaml` to the repo root. Automatic approvals need a paid CodeRabbit plan (Essentials or above at the time of writing). Open a test PR that changes one doc line, and a second that touches `infra/`. The first should get approved by CodeRabbit, the second should not.

**Step 5. Add the merge workflow.**
Copy `.github/workflows/` into the repo. The auto-merge workflow switches on GitHub auto-merge for PRs that touch no high-risk path. GitHub then merges once CodeRabbit has approved and CI is green. Check with the doc-only PR from Step 4.

**Step 6 (second session, PM leads). Run your first design.**
In Claude Code, say: "Use the design-agent skill to design <your feature>". Answer its questions. Push back on the docs until they are v2. Open `DECISIONS.md` and answer every row marked `needs you`. When you are happy, change the first line of `IMPL-PLAN.md` to `Status: APPROVED by <your name>` and let the agent build.

**Step 7 (when you have real logs). Switch on the ops agent.**
Fill in `docs/OBSERVABILITY.md` with where your logs, metrics, traces and alarms live. Give the agent read-only access. Run: "Use the ops-agent skill, watch the last 24 hours." Read its first tickets yourself for a week before you let it open PRs on its own.

## Rules of thumb
- If your agent asks you a question every half hour, the plan was too thin. Go back to the design step.
- High-risk paths always get a human. Do not loosen this in the first month.
- Roll out to 1 percent first, even for a critical fix.
- Read `NOTES.md` for what each piece is based on, what CodeRabbit can and cannot do alone, and how we tested it.
