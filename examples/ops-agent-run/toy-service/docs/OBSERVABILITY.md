# Observability map for toy-ai-gateway
- Logs: `logs/app.jsonl`, one JSON object per line. Fields: ts, level, event, request_id, trace_id, path, status, latency_ms, error, prompt_tokens, max_tokens. Query with `python` or `grep`/`jq`-style filtering.
- Traces: `traces/<trace_id>.json`, a list of spans (name, start_ms, duration_ms, status, attributes). Match on trace_id from the logs.
- Metrics: not exported in this toy setup. Compute error rate and p95 from the logs.
- Alarms: `logs/alarms.jsonl` (empty means none fired).
- Owner of this service: @platform-team (see .github/CODEOWNERS).
- Rollback thresholds: error rate +0.5 points, or p95 latency +20%.
