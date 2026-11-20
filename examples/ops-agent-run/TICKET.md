# /v1/chat returns 500 when the caller's prompt is longer than their max_tokens
Service: toy-ai-gateway    Severity: medium    Found: 2026-11-20, by ops-agent
## What we saw
In the watch window (whole logs/app.jsonl, 2026-11-19 14:00-15:00Z) 113 of 1,040 `/v1/chat` requests (10.9%; 9.4% of all 1,200 log lines) returned 500. All 113 are `MaxTokensExceeded`; in every one `prompt_tokens > max_tokens`, and no 200 response has that property. Failures are spread across the hour, mostly max_tokens=128 (68), then 256 (34) and 512 (11). 5xx p95 latency is 393 ms against 232 ms for 200s. No alarms fired (`logs/alarms.jsonl` empty). Healthz is clean.
## Evidence
- Logs (`logs/app.jsonl`, event=llm_call_failed, level=ERROR):
  - `req_800fb9c057` trace 559bb3866db943da814d0de1862a57e4: `MaxTokensExceeded: completion hit max_tokens=128 (prompt_tokens=374)`
  - `req_5f089897d6` trace 428920c47fa34b4c9041639af9bf64b6: `MaxTokensExceeded: completion hit max_tokens=256 (prompt_tokens=1094)`
- Traces: 559bb3866db943da814d0de1862a57e4 (and the other 7 in `traces/`): span `llm.complete` ERROR, `exception.type=MaxTokensExceeded`, `llm.finish_reason=length`; parent `POST /v1/chat` http.status_code=500. Only 8 traces exist for 113 failures, so they are a sample.
- Metrics/alarms: none exported; no alarms fired.
## Root cause
`app/main.py:chat` (line ~22) does not catch `MaxTokensExceeded` raised by `app/llm.py:complete` (line ~21), so FastAPI turns it into a generic 500. The trigger is the caller's own prompt/`max_tokens` combination, so it should be a 4xx.
## Impact
Callers see an opaque 500 with no hint that they must raise `max_tokens` or shorten the prompt. The 113 failures count against the error budget and would page the platform team for client mistakes. Real 5xx problems are hidden in that noise. Cost of waiting: continuing ~11% fake error rate.
## Proposed fix
Catch `MaxTokensExceeded` in `chat` and raise `HTTPException(400, detail=str(e))`. 5 lines in `app/main.py` plus one test. Alternatives: 422 (also valid; 400 chosen as the error is a semantic combination of fields, easy to switch); a pre-check before calling the model (duplicates the model's logic); auto-raising max_tokens (silently changes cost, rejected).
Open question for the owner: in this toy model "wanted" tokens = prompt tokens, so prompt>max_tokens is deterministic. With a real provider, truncation (`finish_reason=length`) depends on the output length, and returning the truncated text with a flag may be preferable to an error. That is a product call and was not made here.
## Risk gate
LOW. Under 50 changed lines, single service, adds a test, touches none of the HIGH paths (no auth, billing, schema, infra, secrets, deletion). Wrong status code is the typical LOW case. Note for the owner: the status code of this error path is a visible API behaviour change (500 to 400), so clients that retry on 5xx will stop retrying, which is desired.
## Rollout plan
1. Merge after AI review approves; CI deploys to staging.
2. Staging: POST `/v1/chat` with an 800-char prompt and max_tokens=128; expect 400 with a `max_tokens` detail, and the log shows status 400.
3. Production at 1%, watch at least 1 hour or 1,000 requests, whichever is longer.
4. Watch total error rate, the 5xx/4xx split, and p95 separately. 5xx should fall by about 10.9 points of /v1/chat traffic and 4xx rise by about the same. Roll back if total error rate rises more than +0.5 points or p95 rises more than +20% vs control. Also check that 200 volume is unchanged.
5. Then 10%, 50%, 100% with the same check at each step.
Rollback: revert the commit on `ops/max-tokens-4xx`.
## Status
fix in PR (branch `ops/max-tokens-4xx`, not pushed). Fix: catch `MaxTokensExceeded` -> 400. Test: `tests/test_chat.py::test_chat_prompt_longer_than_max_tokens_is_client_error` (failed before, 3/3 pass after).
