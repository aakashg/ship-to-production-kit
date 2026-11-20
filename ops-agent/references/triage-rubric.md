# Triage rubric

## Signal or noise

| Pattern | Verdict | Why |
|---|---|---|
| Any 5xx | suspect until explained | our failure, or a client mistake we mislabel |
| 401 or 403 with a clear message, at a steady rate | noise | callers with bad keys; the system is working |
| 429 at a steady rate | noise, unless it jumped | rate limiting is doing its job |
| 400 or 422 with a clear message | noise | validation is doing its job |
| 4xx rate jumps after a deploy | signal | we may have broken a contract callers depend on |
| p95 or p99 up 20%+ against the previous interval | signal | slow is a defect customers feel |
| Errors only on one customer, key or region | signal, check config first | often a config or data problem, not code |
| A single error that does not repeat | note it, no ticket | not reproducible from one sample |

A run that finds only noise reports 0 issues and creates no ticket, no branch and no code.

## Mismatch classes (look for these, not only errors)

| Class | What it looks like | What it should be |
|---|---|---|
| Client mistake as 5xx | 500 with `MaxTokensExceeded`, `ValidationError`, `KeyError` on a request field | 400 or 422 with a message naming the field |
| Success that failed | 200 with `"error"` in the body, or an empty result where data was expected | the right 4xx or 5xx |
| Dependency failure as 500 | timeout or 503 from a provider surfaced as a bare 500 | 502 or 504, retried with backoff where safe |
| Retry storm | the same request id or idempotency key many times in a minute | capped retries with jitter |
| Swallowed error | a WARN or ERROR log with a 200 response | an error the caller can see |
| Slow success | 200 with p99 far above p95 on one code path | a latency fix or a timeout |

## Severity

Pick the higher level when torn. Re-rate in the ticket if new evidence arrives; do not argue about it mid-investigation.

| Severity | Customer impact | Examples | What you do |
|---|---|---|---|
| high | many customers cannot use a core flow, money or data is wrong, or anything that looks like a security issue | checkout 500s, wrong invoice totals, auth bypass, PII in logs | ticket, tag the owner, stop. Security: stop at once and say so first |
| medium | a feature fails for a slice of requests with a workaround or a retry | 10% of chat requests 500 on long prompts | ticket; fix if LOW risk |
| low | cosmetic, rare, or internal only | wrong error message text, noisy log line | ticket; fix if LOW risk, or batch with the next change |

## Confidence

| Level | You have | You may |
|---|---|---|
| High | a quoted log line with request id, the trace span that failed, and the file:line that explains it | ticket and, if LOW, fix |
| Medium | log lines and a plausible file, no trace or no local reproduction | ticket with "unconfirmed" in the root cause; no fix |
| Low | a pattern in counts only | note in the final report; no ticket |

## Defect count

One defect per root cause, not per request and not per error message variant. `log_summary.py` normalizes ids and numbers so `max_tokens=128` and `max_tokens=256` land in one cluster. Two clusters with the same root cause (same file:line) are one defect: merge them in the ticket and say so.

Report both numbers for this interval and the previous one: defects, and requests hit. If the file has no previous interval, say so; do not invent a baseline.
