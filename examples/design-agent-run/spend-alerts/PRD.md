# PRD: Usage-based spend alerts

Version: v1 (headless draft, 2026-11-20). Items marked **[needs you]** are unconfirmed assumptions; see DECISIONS.md.

## 1. The idea, restated
Customers of the AI gateway set a monthly dollar budget on each API key. The gateway tracks each key's spend and sends an alert when spend reaches 50%, 80% and 100% of that budget. The goal is that nobody is surprised by an AI bill, without the gateway breaking their production traffic.

## 2. Pushback (Step 1)
**Who is it really for?** Two people. (a) The platform or engineering lead who owns many keys and gets blamed for runaway cost. (b) The finance or ops person who wants a predictable bill. Developers holding a single key are a distant third. Alerts therefore go to people who may not be the key creator **[needs you]**.

**Strongest argument against:** an alert is not protection. A runaway loop can spend from 80% to well past 100% in minutes, and an email at 80% arrives after the damage is done. Customers who really fear runaway cost want a hard cap. If most of them ask for a cap after we ship alerts, we shipped the wrong thing first. Also, our cost figure is an estimate from token counts and model pricing, so "100%" will not match the provider invoice exactly.

**Alternatives:**
1. Do nothing: customers watch the usage dashboard (if one exists). Cheapest, and the status quo.
2. Buy or lean on the provider: OpenAI-style project alerts exist but live per provider, so they cannot see spend across providers behind one gateway. Not a substitute.
3. Hard cap only (block at 100%), no alerts. Safer for the wallet, riskier for uptime.
4. Alerts now, hard cap later, using the same counter. **Recommended** (this plan).

**Questions I would have asked, with my best guesses (all flagged):**
1. Should 100% block traffic? Guess: no, alert only in v1. **[needs you]**
2. Where does cost come from? Guess: the gateway already computes a per-request cost estimate. **[needs you]**
3. Which month? Guess: calendar month, UTC. **[needs you]**
4. Who gets alerts, and by what channel? Guess: key owner plus org admins, by email in v1, signed webhook as fast-follow. **[needs you]**
5. Is this on all plans? Guess: yes, no packaging decision made. **[needs you]**

## 3. Market research (Step 2)
Searched 2026-11-20. Only claims backed by a source are stated; the rest are marked unverified.

| Product | What it does well | Gap |
|---|---|---|
| LiteLLM proxy ([alerting docs](https://docs.litellm.ai/docs/proxy/alerting), [email docs](https://docs.litellm.ai/docs/proxy/email.md)) | Per-key `soft_budget` (alert, requests continue) separate from `max_budget` (hard block). Alert at a percentage of max budget (docs say default 80%). | One soft threshold, not a 50/80/100 ladder. Email delivery needs an email integration; one page says budget email alerts are enterprise-licensed (unverified, check pricing page). |
| Portkey ([budget limits](https://portkey.ai/docs/product/observability/budget-limits)) | Per-key USD or token budget, alert threshold, monthly reset (1st, 12 AM UTC), notifies admins, owners and key creator plus extra recipients. | Single alert threshold. Docs say budget limits are for Enterprise and select Pro customers. |
| OpenAI projects ([Terraform guide](https://developers.openai.com/api/docs/guides/terraform/rate-limits-and-spend)) | Monthly email alert at a dollar threshold per project or org. Docs state alerts are notifications, not hard limits. | Per project, not per key; one provider only. A community thread claims project limits behave as notification-only despite the docs (unverified). |
| Cloudflare AI Gateway ([spend limits](https://developers.cloudflare.com/ai-gateway/features/spend-limits/)) | Dollar budgets with rolling or fixed windows, scoped by model, provider or metadata. Blocks with 429 or falls back to another model. Costs are estimates. | Blocks only; per the search summary alerts for these limits are planned, not shipped (unverified, re-check). |
| AWS Budgets ([notification reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-budgets-budget-notification.html), [best practices](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html)) | Multiple thresholds per budget (up to 10), actual and forecast triggers, actual alerts fire once per period. Notes billing delay. | Forecast needs about 5 weeks of history; delayed notifications. Not AI-gateway-aware. |

**What the market tells us:** a multi-step ladder (50/80/100) is a small but real differentiator. The common pattern is alert plus separate hard cap. Nobody in this sample solves "the alert arrived too late" except by hard caps. That supports shipping alerts first on a counter that can later enforce a cap.

## 4. Problem
Customers cannot tell, per key, how close they are to the spend they intended. They find out from the invoice. Today there is no per-key budget in the gateway **[needs you: confirm nothing like this exists]**.

## 5. Who
- Primary: platform/engineering leads and admins who own gateway keys for a team or product.
- Secondary: finance/ops stakeholders added as extra recipients.

## 6. Success metric (numbers are proposals, **[needs you]**)
- **Timeliness:** 95% of threshold crossings produce a sent alert within 5 minutes of the crossing request completing.
- **Correctness:** zero duplicate alerts for the same key, period and threshold; zero missed crossings found by the nightly reconciliation.
- **Adoption:** at least 30% of active keys on opted-in orgs have a budget within 60 days of launch. Baseline unknown (unverified).
- **Outcome proxy:** fewer billing-surprise support tickets. Baseline unknown; count them for 4 weeks before launch.

## 7. Non-goals (v1)
- Blocking or throttling requests at any threshold.
- Forecast ("you will exceed") alerts.
- Custom thresholds (v1 is fixed 50/80/100; storage keeps them as a list so this is cheap later).
- Org-, team-, model- or tag-level budgets. Per-key only.
- Token budgets, non-USD currency, non-monthly periods.
- Slack/PagerDuty/SMS integrations.
- Exact reconciliation to provider invoices.

## 8. User stories
1. As an admin I set a monthly USD budget on a key so that I get warned before spend gets out of hand.
2. As an admin I get one email at 50%, one at 80%, one at 100% each month, each saying current spend, budget, key alias, and that spend is an estimate.
3. As an admin I change a key's budget mid-month and the alerts adjust sensibly rather than spamming or going silent.
4. As an admin I list a key's alert history for the current and past months.
5. As finance I am added as an extra recipient and receive the same alerts.
6. As an on-call engineer I can see delivery failures and counter lag on a dashboard and have a runbook.

## 9. Experiment (Step 3): replay spend against real usage
**Question:** is a 50/80/100 email ladder useful for real usage patterns, or does spend move from 80% to 100% faster than an alert can matter?

**What we run (about 1 to 2 days, read-only):** a script over 90 days of per-request cost grouped by key. For each key-month, set a hypothetical budget of 1.0x and 1.5x last month's spend, then compute: minutes between crossing 80% and 100%; the largest single request as a share of budget; and whether any one request jumps past more than one threshold.

**Kill / redesign signals:**
- If more than 20% of key-months go from 80% to 100% in under 10 minutes, email-only alerts do not protect customers. Redesign toward a hard cap first, or alert plus cap together.
- If more than 5% of crossings skip two or more thresholds in one request, the ladder semantics need a rethink (see DECISIONS #7).
- If fewer than 20% of active keys would ever cross 50% in a month, adoption will be low and the feature is mostly insurance.

**Result:** NOT RUN. This repo is an empty template with no usage data, and this session has no read access to gateway logs. **[needs you]** someone with read-only access to usage logs runs it, or provides an export. Optional parallel check: five short customer calls asking "alert or hard cap?".

## 10. Open risks
- Estimated cost is not invoice cost; customers may dispute "100%". Mitigation: label every alert "estimated" and show the pricing basis date.
- Counter drift or lost usage events cause missed or false alerts. Mitigation: idempotent increments plus nightly reconciliation.
- Email deliverability (spam folders, bounces) silently defeats the feature. Mitigation: delivery metrics and bounce handling.
- Alert fatigue or a bug that emails customers wrongly is outward-facing and not reversible. Mitigation: shadow mode first, internal pilot, 1% rollout.
- Unknown existing stack: every file path in ENG-PLAN is a proposal until the stack is confirmed **[needs you]**.

## Changelog
- v1 (2026-11-20): initial headless draft. Experiment not run. Market research from public docs via web search.
