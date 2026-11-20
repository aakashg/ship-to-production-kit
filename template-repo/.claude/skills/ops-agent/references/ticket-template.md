# Ticket template

Use exactly these sections, in this order. One ticket per root cause.

```
# <short title: what is wrong, in plain words>
Service: <name>    Severity: <low|medium|high>    Found: <date, by ops-agent>
## What we saw
<2-4 sentences, with counts: how many requests, what time window, what % of traffic>
## Evidence
- Logs: <query or file, 2 sample lines with request ids>
- Traces: <trace id and the span that failed>
- Metrics/alarms: <if any>
## Root cause
<where in the code, file:line, and why>
## Impact
<who is affected, what they see, cost of waiting>
## Proposed fix
<the smallest change; list alternatives considered>
## Risk gate
<LOW or HIGH, and which rule below decided it>
## Rollout plan
<stages, what to watch, rollback trigger>
## Status
<open | fix in PR | in staging | 1% | 100% | closed>
```

## Filled example (from the kit's test run, shortened)

```
# /v1/chat returns 500 when the caller's prompt is longer than their max_tokens
Service: toy-ai-gateway    Severity: medium    Found: 2026-11-20, by ops-agent
## What we saw
113 of 1,040 /v1/chat requests (10.9%) returned 500 between 14:00 and 15:00Z. All 113 are MaxTokensExceeded,
and in every one prompt_tokens > max_tokens. No alarms fired. /healthz is clean.
## Evidence
- Logs (logs/app.jsonl): req_800fb9c057 trace 559bb386...: `MaxTokensExceeded: completion hit max_tokens=128 (prompt_tokens=374)`
- Traces: span llm.complete ERROR, exception.type=MaxTokensExceeded, finish_reason=length; parent POST /v1/chat 500
- Metrics/alarms: none exported; no alarms fired
## Root cause
app/main.py:23 calls complete() without catching MaxTokensExceeded, raised at app/llm.py:21, so the framework returns a generic 500.
The trigger is the caller's own prompt and max_tokens, so it is a client error.
## Impact
Callers get a 500 with no message and retry the same request, which fails again. On-call is paged for a client mistake.
## Proposed fix
Catch MaxTokensExceeded in the handler and return 400 with a message naming max_tokens and prompt_tokens.
Alternatives: raise max_tokens automatically (changes billing, HIGH); truncate the prompt (silent data loss, rejected).
## Risk gate
LOW: one file in app/ plus its test, under 50 changed lines, no HIGH path (risk_check.py: LOW).
## Rollout plan
Staging re-run of a long prompt returns 400. Then 1% for 1 hour or 1,000 requests: 5xx on /v1/chat should fall by
about 10.9 points and 4xx rise by about the same. Roll back if total error rate rises more than 0.5 points or p95 rises 20%.
Then 10%, 50%, 100%.
## Status
fix in PR (tests/test_chat.py::test_chat_prompt_longer_than_max_tokens_is_client_error)
```

## Writing rules

- Title says what is wrong in plain words, not the exception name alone.
- Every count comes from a query or `log_summary.py`. Write the window.
- Evidence lines are quoted from the data, with request ids. Never paraphrase a log line.
- Root cause names file:line. If you cannot, the root cause says "unconfirmed" and there is no fix.
- Proposed fix lists at least one alternative and why it lost.
- A HIGH ticket ends with the owner from CODEOWNERS tagged and `Status: open`.
