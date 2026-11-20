# Observability map
This is the file the ops agent reads first. Fill every TODO. Keep it factual.

## Where things live
- Logs: TODO (tool, how to query, example query, fields: ts, level, event, request_id, trace_id, path, status, latency_ms, error)
- Metrics: TODO (dashboard URL or query endpoint, the 5 numbers that matter: request rate, error rate, p95 latency, saturation, cost)
- Traces: TODO (backend, how to open a trace by trace_id)
- Alarms: TODO (channel, which alarms exist, what each means)
- Access: TODO (read-only VPN or API token, where the agent gets it; NEVER write access)
- Log export for the summarizer: TODO (if logs can be pulled as JSON lines, the path or command; list any field names that differ from the ones above so the agent passes `--field-*` to `log_summary.py`)

## Services and owners
| Service | Owner team | CODEOWNERS handle | On-call |
|---|---|---|---|
| TODO | TODO | TODO | TODO |

## Rollout and rollback
- Staging URL: TODO
- Partial rollout: TODO (feature flag or traffic split; how to set 1%)
- Rollback thresholds: error rate +0.5 points over control, or p95 latency +20%. Adjust to your traffic.
- Rollback command: TODO
- Defect count baseline: TODO (customer-visible defects per week last month; the ops agent reports the count against this, not only the error rate)
