# PRD: Weekly email digest of a user's dashboard

Status: v1, written in a headless run. No human answered the product questions, so every answer below is a labelled assumption (see DECISIONS.md).

## Idea, restated
Users can turn their dashboard into a recurring email. Once a week we send them a summary of the numbers on their dashboard, so they get the value without logging in. "Export" in the original idea is read here as "subscribe to a scheduled email", not "download a file once" (see decision 1).

## Context gap (read this first)
This repo is the empty org template. `CLAUDE.md` still says `<Project name>`, `app/` is a stub, there is no dashboard code, no user model, no email provider, and no stack declared. This design therefore cannot name real existing modules to change. Paths in ENG-PLAN.md are proposed, assume Python (the only test file is pytest style), and must be re-mapped once the real app exists. Decision 11 asks for confirmation.

## Pushback
- **Who is it really for?** Two different users hide in the idea: (a) the dashboard owner who wants a Monday-morning recap for themselves, and (b) the owner who wants to forward numbers to people without accounts (boss, client). (a) is a retention feature. (b) is a sharing feature with a data-leak risk. Assumed: (a) first, (b) later.
- **Strongest argument against:** an email digest is a substitute for opening the product. If it is good enough, usage of the dashboard can go down. It only wins if the email drives return visits or if the email is itself the value (managers who never log in). Also: digests of "nothing changed" train people to ignore or filter the sender, which hurts all our other email.
- **Alternatives:**
  1. Do nothing: tell users to screenshot or bookmark. Costs zero, tells us nothing.
  2. Buy / integrate: let users pipe the dashboard to Slack/email through an existing tool (Zapier-style) or via a CSV export plus their own scheduler.
  3. Narrower build: one-off "email me this dashboard now" button, no schedule. Smaller, tests whether the content is useful before we build scheduling and unsubscribe machinery.
  4. Build the scheduled digest (this design).
- **Questions that would change the design** (answers assumed, because no human is present):
  1. Is the recipient only the owner, or can they add other emails? Assumed: owner only in v1.
  2. Does the email contain the numbers inline (HTML), or an image/PDF snapshot, or just a link? Assumed: inline HTML summary plus a link, no attachment.
  3. Does the dashboard contain per-user or per-customer data whose sharing is restricted? Unknown. Assumed yes, which is why recipients are limited to the owner.
  4. What does the product do today for email (provider, sender domain, unsubscribe handling)? Unknown, assumed nothing exists.
  5. How many users have a dashboard they visit weekly? Unknown. It drives whether this is worth building at all (see experiment).

## Market research
Sourced from vendor docs found by web search on 2026-11-20.

| Product | What it does well | Gap |
|---|---|---|
| [Looker Studio scheduled delivery](https://support.google.com/datastudio/answer/9263641?hl=en) | PDF attachment plus a preview of the first page and a link; up to 50 recipients; uses the report's default filters and date range | Per-recipient personalisation and multiple schedules are paid-tier only; users report third-party connector data missing from the PDF ([forum thread](https://discuss.google.dev/t/issue-gbp-data-missing-from-scheduled-email-pdf/395167), user-reported) |
| [Metabase dashboard subscriptions](https://www.metabase.com/docs/latest/dashboards/subscriptions) | Hourly to monthly schedules in every edition; recipients need no account; can skip sending when results are empty; "send now" test button; admins can audit all subscriptions | Admin must set up email first; text cards may be left out of the email (per a secondary summary, verify) |
| [Amplitude dashboard subscriptions](https://www.amplitude.com/docs/analytics/dashboard-subscribe) | HTML email on a schedule, optional CSV, recipients outside the org allowed, admin management page | Plain recurring snapshot; AI "digest" is a separate agent feature, not the default subscription |
| [Tableau subscriptions](https://help.tableau.com/current/online/en-us/subscribe_user.htm) | PNG, PDF or both plus a link; recipients must have view permission; "manage my subscriptions" link in each email; auto-suspends after 5 consecutive failures | Delivery time can drift under load; large PDFs can silently fail to arrive ([troubleshooting](https://help.tableau.com/current/server/en-us/subscribe_trouble.htm)) |
| Mixpanel | Unverified. Search did not find native scheduled email reports. Do not assume either way. | Unverified |

What the market tells us: scheduled dashboard email is table stakes in BI tools. The recurring weak spots are empty/unchanged sends, permissions on forwarded data, silent failures, and heavy attachments. Our differentiator would be a digest that says what changed rather than re-sending a static snapshot. That is a hypothesis, not a finding.

## Problem
Users must remember to open the dashboard. Those who check weekly spend time on it; those who forget miss changes.

## Who
Primary: the dashboard owner, an existing logged-in user. Secondary (later, not v1): non-account recipients they nominate.

## Success metric (proposed, `needs you` to confirm)
Within 8 weeks of launch to 100% of users: at least 20% of weekly-active dashboard users turn the digest on, and of those, at least 40% still have it on after 4 weeks, with a spam-complaint rate under 0.1% and unsubscribe rate under 2% per send. These numbers are placeholders chosen to be checkable, not benchmarks. No source supports them. Replace after the experiment gives a baseline.

## Non-goals
- Real-time or daily alerts (different feature: thresholds and anomaly detection).
- Sending to people without an account (v2, privacy review first).
- PDF or image rendering of the full dashboard.
- Custom schedules (weekly only, user-chosen weekday and hour, v1).
- Building our own email delivery infrastructure.

## User stories
1. As an owner, I turn on "weekly digest" from my dashboard and pick a day and time.
2. As an owner, I receive an email with my key numbers, change vs last week, and a link back.
3. As an owner, I can pause or turn it off from the dashboard and from one click in the email.
4. As an owner, I can press "send me a preview now" to see what it will look like.
5. As an owner with an empty or unchanged week, I am not spammed (see decision 8).
6. As an admin/ops person, I can see send volume, failures and unsubscribes.

## Experiment (Step 3)
**What we run:** a concierge digest. Pick 10 to 20 active dashboard users (with consent), hand-build the same weekly email in a spreadsheet or script from their existing numbers and send it from a normal mailbox for 3 consecutive weeks. No code in this repo. Record opens, clicks back to the product, replies, and whether the product's weekly active days go up or down for that group versus a matched group.
**Kills the idea:** fewer than 3 of 10 recipients open it in weeks 2 and 3, or recipients' dashboard visits drop versus the matched group, or fewer than half say they would be unhappy if it stopped.
**Takes:** about 1 hour per week of human time for 3 weeks, plus 1 day to pick users.
**Result:** NOT RUN. This repo has no product, data or email access, so nothing could be run safely or at all. See `experiment/README.md`. The first red flag is therefore still unknown and the metric above is untested.

## Open risks
- No baseline data on how many users have a dashboard they use weekly.
- Email deliverability and sender reputation are unknown (domain, SPF/DKIM/DMARC state not visible from this repo).
- Dashboard data may contain personal or customer data; emailing it moves it out of the product's access controls.
- Cannibalising logins (see pushback).
- Time zones, DST and "weekly" semantics for a global user base.
- Cost of the email provider at volume is unknown.

## Changelog
- v1 (2026-11-20): first draft, headless.
