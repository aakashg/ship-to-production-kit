# Return 400 instead of 500 when max_tokens is below the prompt size

**What:** `/v1/chat` catches `MaxTokensExceeded` and returns 400 with the message.
**Why:** 45 caller-caused 5xx in 24h (see TICKET.md). Client mistakes must be 4xx.

## Test evidence
- Red (before fix): `tests/test_chat.py:18: assert 500 == 400` (`1 failed, 2 passed`)
- Green (after fix): `3 passed`

## Risk
LOW. `risk_check.py --git main`: 15 changed lines, no high-risk path, single service.

## Rollback
Revert the commit. Roll out at 1% first; watch 5xx fall and 4xx rise by about the same amount.

## Rule to add (a human adds this to `.claude/rules/`)
- When an upstream or provider exception is caused by request parameters, map it to a 4xx at the handler; do not let it escape as a 500.
