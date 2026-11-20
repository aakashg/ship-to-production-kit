# Expired session on /v1/me returns 500 instead of 401
Service: toy-ai-gateway    Severity: medium    Found: 2026-11-20, by ops-agent
## What we saw
37 requests to `GET /v1/me` returned HTTP 500 between 2026-11-19T14:10:51Z and 14:59:27Z. That is 37 of 134 `/v1/me` requests (27.6%) and 37 of 1,200 total requests (3.1%). They are the only 5xx in the logs. Every one is an unhandled `SessionExpired`, which is a client-caused condition (an expired session) and should be a 401.
## Evidence
- Logs: `logs/app.jsonl`, filter `status==500`. Samples:
  - `req_9cde363da8` (trace 9c8c8d435b8a41c0a923dadcd30afe4d, 14:10:51Z, 183 ms): `SessionExpired: token exp=1731900000 < now (app/auth/session.py:14 raise SessionExpired, not caught)`
  - `req_be7908f833` (trace b1cf4577cebe4aa8bd80c4c421807860, 14:12:12Z, 214 ms): same error.
- Traces: 9c8c8d43..., b1cf4577..., 5123f84a... all show root span `GET /v1/me` ERROR (http 500) and child span `auth.validate_session` ERROR with `exception.type=SessionExpired`.
- Metrics/alarms: `logs/alarms.jsonl` is empty, so no alarm fired. No latency outliers: /v1/me p95 221 ms, /v1/chat p95 212 ms, max 291 ms.
- Other statuses, all expected: /v1/chat 400 x35 (prompt missing), 401 x23, 429 x5. There are no 5xx on /v1/chat. The earlier max_tokens case is already handled in `app/main.py` (400) and covered by a passing test.
## Root cause
`app/main.py:30-31` (`me`) calls `validate_session(...)` and does not catch `SessionExpired`. The exception raised at `app/auth/session.py:10-11` therefore becomes an unhandled 500. (The log line cites session.py:14, but the current file has the raise at lines 10-11, so the logs may come from a different build.)
Related observation, needs owner review: `me` takes `exp` from a client-controlled query parameter (`?exp=`, default 0) and builds the claims from it. That means the token expiry is chosen by the caller, so any caller can pass a far-future `exp` and be treated as authenticated. A missing `exp` always yields 500. This looks like a placeholder or an auth design flaw. I did not run anything to probe it.
## Impact
Clients with expired sessions get a 500 and not a 401. They can't tell that they need to re-authenticate, and the 5xx counts inflate the error budget and may page the wrong people. Waiting costs little, but the 5xx noise continues.
## Proposed fix
In `me`, catch `SessionExpired` and raise `HTTPException(401, "session expired")`. That is about 3 lines plus a test: `GET /v1/me?exp=1` returns 401, and a future `exp` returns 200. Alternative: register an app-wide exception handler for `SessionExpired`. Separately, the owner should decide whether `exp` may come from the client at all (it should come from a verified token).
## Risk gate
HIGH. The change is in the auth path (`app/auth/session.py` and the `/v1/me` session handling), and `.claude/rules/guardrails.md` says "Auth ... HIGH risk: ticket only, no code changes". No code was changed. Owner: @platform-team (.github/CODEOWNERS).
## Rollout plan
Once the owner approves and implements: staging first, re-run an expired-session request and check for 401 in the logs. Then 1% of production for at least 1 hour or 1,000 requests, whichever is longer. Watch the 5xx/4xx split on /v1/me: 5xx should fall to 0 and 401 should rise by about 37 per hour. Total error rate must stay within +0.5 points and p95 within +20%, otherwise roll back. Then 10%, 50%, 100% with the same check.
## Status
open (awaiting @platform-team; no fix made)
