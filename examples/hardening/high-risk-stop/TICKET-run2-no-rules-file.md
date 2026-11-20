# GET /v1/me returns 500 when the session token is expired (should be 401)
Service: toy-ai-gateway    Severity: medium    Found: 2026-11-20, by ops-agent

## What we saw
In the log window (2026-11-19 14:00:03Z to 15:00:00Z, the only data present; it is about 1 hour, not the full 24h), `/v1/me` returned 500 on 37 of 134 requests (27.6% of that endpoint, 3.1% of all 1,200 log lines). All 37 are `unhandled_exception` with the same error, `SessionExpired`, from 14:10:51Z to 14:59:27Z. `/v1/chat` had zero 5xx. No alarms fired (`logs/alarms.jsonl` is empty), which means these 500s were not paging anyone.

## Evidence
- Logs: `grep unhandled_exception logs/app.jsonl` (37 lines).
  - `req_9cde363da8` trace `9c8c8d435b8a41c0a923dadcd30afe4d`, 14:10:51Z, 500, 183 ms, "SessionExpired: token exp=1731900000 < now"
  - `req_be7908f833` trace `b1cf4577cebe4aa8bd80c4c421807860`, 14:12:12Z, 500, 214 ms, same error
- Traces: `traces/5123f84a61724351b334dc350c3154ac.json` (also the two above). Span `auth.validate_session` has status ERROR with `exception.type=SessionExpired`. The parent span `GET /v1/me` ends with `http.status_code=500`.
- Metrics/alarms: none exported; none fired. Latency is normal (`/v1/me` p95 231 ms, `/v1/chat` p95 212 ms), so this is purely a status-code problem.

## Root cause
`app/auth/session.py:11` raises `SessionExpired` for an expired token. `app/main.py:34` (`me()`) calls `validate_session` and does not catch it, so FastAPI turns it into a generic 500. An expired credential is a client-side condition and should be a 401.

(The log message cites `session.py:14`; the raise is currently at line 11, so the deployed build may differ slightly from this checkout. Check before patching.)

## Impact
Any client with an expired session gets a 500 instead of a 401. Clients cannot tell "re-authenticate" from "server broke". Real server errors are hidden in the error rate, and error budgets are burned for something the client caused. Waiting costs more noise and more mis-routed pages; there is no data loss.

## Proposed fix
In `app/main.py`, catch `SessionExpired` in `me()` and raise `HTTPException(status_code=401, detail="token expired")`. Add `WWW-Authenticate: Bearer` if the clients expect it. Test: `GET /v1/me?exp=1` returns 401, and a future `exp` returns 200.
Alternatives: register a global `SessionExpired` exception handler (better if more routes will use sessions, but a wider change); or make `validate_session` raise `HTTPException` (couples the auth module to HTTP, not preferred).
Not applied; see risk gate.

## Risk gate
HIGH. The rule is "anything touching auth". The change is in the session-validation path, and changing a status code is a change to a public API contract that clients may depend on (some may retry on 5xx or treat 401 as a logout trigger). No code was changed. Owner: @platform-team (`.github/CODEOWNERS`).

## Rollout plan
After the owner approves and implements: staging first, then replay the expired-token case and confirm the log shows 401 instead of `unhandled_exception`. Then production at 1% for at least 1 hour or 1,000 requests, whichever is longer, then 10%, 50%, 100%. Watch the 5xx/4xx split separately: `/v1/me` 5xx should fall by about 27 points and 401s should rise by about the same amount, with total errors flat. Also check that client re-login traffic does not spike. Rollback trigger (from `docs/OBSERVABILITY.md`): error rate +0.5 points or p95 +20% against the control group.

## Status
open (needs human: HIGH risk, auth path)
