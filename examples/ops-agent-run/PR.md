# Return 400 instead of 500 when prompt exceeds max_tokens
## What
`/v1/chat` now catches `MaxTokensExceeded` and returns HTTP 400 with the error message as detail. Changes: `app/main.py`, `tests/test_chat.py`.
## Why
113 of 1,040 `/v1/chat` requests (10.9%) in the watch window were 500s, all caused by the caller's prompt being longer than their `max_tokens`. This is a client error and should not be a 5xx. See `TICKET.md`.
## Test evidence
- New test `test_chat_prompt_longer_than_max_tokens_is_client_error` failed before the fix (got 500) and passes after.
- Full suite: `.venv/bin/python -m pytest -q` -> 3 passed.
## Rollout
Staging, then 1% for at least 1 hour / 1,000 requests, then 10/50/100%. Expect 5xx down and 4xx up by about the same amount; roll back on error rate +0.5 points or p95 +20%.
## Rollback
`git revert` this commit.
