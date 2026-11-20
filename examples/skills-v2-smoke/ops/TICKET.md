# POST /v1/chat returns 500 when the caller's max_tokens is smaller than the prompt

- **Service:** toy-ai-gateway (owner @platform-team; `.github/CODEOWNERS` does not exist in this repo)
- **Severity:** medium (customer-visible errors, wrong status class, no data loss; 45 requests)
- **Confidence:** high

## What we saw
Window 2026-11-18T14:19Z to 2026-11-19T14:19Z: 400 requests, 45 5xx (11.25%), all on /v1/chat (45 of 349 = 12.89%), all one cluster. 4xx: 0. No alarms fired (`logs/alarms.jsonl` empty).
Customer-visible defects: 1 this window (45 requests hit). Previous window: no data in the file, so no baseline.
Latency is not the problem: /v1/chat p50 163 ms, p95 305 ms, p99 370 ms.

## Evidence
```
{"ts": "2026-11-19T14:02:33.061755Z", "level": "ERROR", "event": "llm_call_failed", "request_id": "req_14f9b65190", "trace_id": "3986de5c3f6247fab5533c438b0c7d3f", "path": "/v1/chat", "status": 500, "latency_ms": 207, "error": "MaxTokensExceeded: completion hit max_tokens=128 (prompt_tokens=150)", ...}
```
Trace 3986de5c3f6247fab5533c438b0c7d3f: span `llm.complete` ERROR, `llm.finish_reason=length`, `exception.stacktrace: app/main.py:chat -> app/llm.py:complete (raise MaxTokensExceeded)`. Second sample: req_33cc0ebc24, trace 2ad6c31a7a8a47b1a2f8b0690ab07a28.
Every sampled failure has prompt_tokens > max_tokens (e.g. 374/128, 1094/256, 150/128).

## Root cause
`app/llm.py:complete` raises `MaxTokensExceeded` when `prompt_tokens > max_tokens`. `app/main.py:chat` did not catch it, so FastAPI returned 500. The trigger is the caller's own max_tokens value, so it is a client error (rule: 10-code-standards, client mistakes are 4xx).

## Impact
45 requests (12.89% of /v1/chat) got an opaque 500 instead of an actionable 400. Also pages on-call for a client mistake and inflates the error budget.

## Proposed fix
Catch `MaxTokensExceeded` in `chat` and return HTTP 400 with the message as detail. Alternatives: 422 (also fine); raising max_tokens server-side (rejected, changes cost/behavior silently).
Done on branch `ops/max-tokens-4xx`; test `tests/test_chat.py::test_max_tokens_exceeded_is_client_error`.

## Risk gate
LOW. `risk_check.py --git main`: 2 files, 15 changed lines, no high-risk path. One service, no auth/billing/schema/infra. Caveat: a 500 to 400 change is technically visible to clients, but no client can depend on a 500 for this input.

## Rollout plan
1. Merge after review; CI to staging. Re-run a request with a 600-char prompt and max_tokens=128; expect 400.
2. Prod 1% for at least 1 hour or 1,000 requests, whichever is longer.
3. Watch 5xx and 4xx separately: 5xx on /v1/chat should fall by about 12.89 points (baseline) and 4xx rise by about the same. Total error rate should stay flat. Roll back if total error rate rises by more than 0.5 points or p95 rises by more than 20% (baseline p95 305 ms, so the limit is about 366 ms).
4. Then 10%, 50%, 100% with the same checks.

## Status
Fix ready on branch (not pushed). Needs human review and rollout.
