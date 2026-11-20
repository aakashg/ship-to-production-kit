#!/usr/bin/env python3
"""Summarize a JSON-lines request log into the numbers the ops agent needs.

Deterministic, read-only, standard library only. It does the counting so the
agent spends its turns on root cause, not arithmetic.

What it prints:
  * requests, error rate and p50/p95/p99 latency per endpoint
  * error clusters: (path, status, normalized error) with counts, first and last
    seen, and sample request_id / trace_id pairs to quote in a ticket
  * a CLIENT-CAUSED? flag on 5xx clusters whose error text looks like a caller
    mistake (token limits, validation, missing fields), the classic 5xx that
    should be a 4xx
  * customer-visible defects (distinct 5xx clusters) and requests hit, for this
    window and the previous window of the same length

The window ends at the newest timestamp in the file, not at "now", so the same
file always gives the same answer.

Expected fields per line (names are configurable): ts (ISO 8601), path,
status, latency_ms, request_id, trace_id, error (optional).

Examples:
  python3 log_summary.py logs/app.jsonl
  python3 log_summary.py logs/app.jsonl --window-hours 1 --traces traces/
  python3 log_summary.py logs/app.jsonl --json > summary.json
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import sys
from collections import defaultdict

CLIENT_CAUSED = re.compile(
    r"max[_ ]?tokens|too many tokens|context length|token limit|prompt too long|"
    r"validation|invalid (input|request|parameter|argument|json)|missing (field|parameter)|"
    r"required field|payload too large|unsupported media|malformed|schema|"
    r"bad request|unprocessable|out of range|must be (positive|between|less|greater)",
    re.IGNORECASE,
)


def parse_ts(value):
    if value is None:
        return None
    s = str(value).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t


def normalize_error(text):
    """Collapse ids and numbers so one root cause becomes one cluster."""
    if not text:
        return "(no error text)"
    s = str(text)
    s = re.sub(r"\b[0-9a-f]{8,}\b", "<id>", s, flags=re.IGNORECASE)
    s = re.sub(r"\d+", "N", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120]


def percentile(values, pct):
    """Nearest-rank percentile. Returns None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[rank - 1]


def load(path, f):
    rows, bad = [], 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            t = parse_ts(d.get(f["ts"]))
            try:
                status = int(d.get(f["status"]))
            except (TypeError, ValueError):
                status = None
            if t is None or status is None:
                bad += 1
                continue
            rows.append({
                "t": t,
                "path": d.get(f["path"], "(no path)"),
                "status": status,
                "latency": d.get(f["latency"]),
                "request_id": d.get(f["request_id"]),
                "trace_id": d.get(f["trace_id"]),
                "error": d.get(f["error"]),
            })
    return rows, bad


def failing_span(traces_dir, trace_id):
    """Return 'span: exception' for the deepest ERROR span in a trace file, if any."""
    if not traces_dir or not trace_id:
        return None
    p = os.path.join(traces_dir, f"{trace_id}.json")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            spans = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(spans, dict):
        spans = spans.get("spans", [])
    errors = [s for s in spans if str(s.get("status", "")).upper() == "ERROR"]
    if not errors:
        return None
    s = errors[-1]
    attrs = s.get("attributes", {}) or {}
    exc = attrs.get("exception.type") or attrs.get("exception.message") or ""
    where = attrs.get("exception.stacktrace", "")
    out = f"{s.get('name', '?')}: {exc}".strip()
    return f"{out} ({where})" if where else out


def summarize_window(rows, traces_dir=None, samples=2):
    by_path = defaultdict(list)
    for r in rows:
        by_path[r["path"]].append(r)
    endpoints = []
    for path, rs in sorted(by_path.items(), key=lambda kv: -len(kv[1])):
        lats = [r["latency"] for r in rs if isinstance(r["latency"], (int, float))]
        n5 = sum(1 for r in rs if r["status"] >= 500)
        n4 = sum(1 for r in rs if 400 <= r["status"] < 500)
        endpoints.append({
            "path": path, "requests": len(rs), "5xx": n5, "4xx": n4,
            "error_rate_5xx_pct": round(100.0 * n5 / len(rs), 2),
            "p50_ms": percentile(lats, 50), "p95_ms": percentile(lats, 95), "p99_ms": percentile(lats, 99),
        })
    clusters = defaultdict(list)
    for r in rows:
        if r["status"] >= 400:
            clusters[(r["path"], r["status"], normalize_error(r["error"]))].append(r)
    out_clusters = []
    for (path, status, sig), rs in sorted(clusters.items(), key=lambda kv: (-(kv[0][1] >= 500), -len(kv[1]))):
        rs.sort(key=lambda r: r["t"])
        # Prefer samples that have a trace file, so the ticket can quote the failing span.
        cands = [{"request_id": r["request_id"], "trace_id": r["trace_id"], "error": r["error"],
                  "failing_span": failing_span(traces_dir, r["trace_id"])} for r in rs]
        ex = ([c for c in cands if c["failing_span"]] + [c for c in cands if not c["failing_span"]])[:samples]
        out_clusters.append({
            "path": path, "status": status, "signature": sig, "count": len(rs),
            "first_seen": rs[0]["t"].isoformat(), "last_seen": rs[-1]["t"].isoformat(),
            "client_caused_suspect": status >= 500 and bool(CLIENT_CAUSED.search(sig)),
            "examples": ex,
        })
    five = [c for c in out_clusters if c["status"] >= 500]
    return {
        "requests": len(rows),
        "5xx": sum(1 for r in rows if r["status"] >= 500),
        "4xx": sum(1 for r in rows if 400 <= r["status"] < 500),
        "endpoints": endpoints,
        "clusters": out_clusters,
        "defects": len(five),
        "defect_requests": sum(c["count"] for c in five),
    }


def build(rows, window_hours, traces_dir):
    if not rows:
        return None
    end = max(r["t"] for r in rows)
    if window_hours:
        start = end - dt.timedelta(hours=window_hours)
        prev_start = start - dt.timedelta(hours=window_hours)
        cur = [r for r in rows if start < r["t"] <= end]
        prev = [r for r in rows if prev_start < r["t"] <= start]
    else:
        start = min(r["t"] for r in rows)
        cur, prev = rows, []
    return {
        "window": {"start": start.isoformat(), "end": end.isoformat(), "hours": window_hours},
        "current": summarize_window(cur, traces_dir),
        "previous": summarize_window(prev) if prev else None,
    }


def fmt_ms(v):
    return "-" if v is None else f"{v:.0f}" if isinstance(v, float) else str(v)


def render(report, bad):
    c, p = report["current"], report["previous"]
    w = report["window"]
    out = [f"# Log summary  {w['start']} .. {w['end']}" + (f"  ({w['hours']} h window)" if w["hours"] else "  (whole file)")]
    rate = 100.0 * c["5xx"] / c["requests"] if c["requests"] else 0.0
    out.append(f"requests {c['requests']}  5xx {c['5xx']} ({rate:.2f}%)  4xx {c['4xx']}  unparsed lines {bad}")
    out.append("")
    out.append("## Endpoints")
    out.append("| path | requests | 5xx | 4xx | 5xx rate | p50 ms | p95 ms | p99 ms |")
    out.append("|---|---|---|---|---|---|---|---|")
    for e in c["endpoints"]:
        out.append(f"| {e['path']} | {e['requests']} | {e['5xx']} | {e['4xx']} | {e['error_rate_5xx_pct']}% | "
                   f"{fmt_ms(e['p50_ms'])} | {fmt_ms(e['p95_ms'])} | {fmt_ms(e['p99_ms'])} |")
    out.append("")
    out.append("## Error clusters (5xx first)")
    if not c["clusters"]:
        out.append("none")
    for cl in c["clusters"]:
        flag = "  CLIENT-CAUSED? (5xx whose error reads like a caller mistake: check if it should be a 4xx)" if cl["client_caused_suspect"] else ""
        out.append(f"- {cl['status']} {cl['path']} x{cl['count']}  `{cl['signature']}`{flag}")
        out.append(f"  first {cl['first_seen']}  last {cl['last_seen']}")
        for ex in cl["examples"]:
            line = f"  sample request_id={ex['request_id']} trace_id={ex['trace_id']}"
            if ex["failing_span"]:
                line += f"  span: {ex['failing_span']}"
            out.append(line)
    out.append("")
    out.append("## Customer-visible defects (distinct 5xx clusters)")
    out.append(f"this window: {c['defects']} defects, {c['defect_requests']} requests hit")
    if p is None:
        out.append("previous window: no data in the file (say so in the ticket, do not guess a baseline)")
    else:
        prate = 100.0 * p["5xx"] / p["requests"] if p["requests"] else 0.0
        out.append(f"previous window: {p['defects']} defects, {p['defect_requests']} requests hit, 5xx rate {prate:.2f}%")
        if rate <= prate + 0.05 and c["5xx"] > p["5xx"]:
            out.append("FLAT RATE, MORE ERRORS: same rate but more customers hit. Report it as a finding.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logfile", help="JSON-lines log file, one request per line")
    ap.add_argument("--window-hours", type=float, default=24.0,
                    help="window length ending at the newest log line (default 24). 0 = whole file, no comparison")
    ap.add_argument("--traces", help="folder of <trace_id>.json span lists; adds the failing span to each sample")
    ap.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    for name, default in [("ts", "ts"), ("path", "path"), ("status", "status"), ("latency", "latency_ms"),
                          ("request-id", "request_id"), ("trace-id", "trace_id"), ("error", "error")]:
        ap.add_argument(f"--field-{name}", default=default, help=f"field name for {name} (default {default})")
    a = ap.parse_args(argv)
    fields = {"ts": a.field_ts, "path": a.field_path, "status": a.field_status, "latency": a.field_latency,
              "request_id": a.field_request_id, "trace_id": a.field_trace_id, "error": a.field_error}
    if not os.path.isfile(a.logfile):
        print(f"error: no such file: {a.logfile}", file=sys.stderr)
        return 2
    rows, bad = load(a.logfile, fields)
    report = build(rows, a.window_hours or 0, a.traces)
    if report is None:
        print(f"error: no parseable request lines in {a.logfile} ({bad} unparsed). Check the field names.", file=sys.stderr)
        return 2
    if a.json:
        report["unparsed_lines"] = bad
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render(report, bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
