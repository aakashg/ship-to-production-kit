"""Tests for log_summary.py and risk_check.py. Standard library only.

Run: python3 -m unittest discover -s ops-agent/scripts -p 'test_*.py'
"""
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import log_summary  # noqa: E402
import risk_check  # noqa: E402


def line(ts, path, status, lat=100, err=None, rid="r", tid="t"):
    d = {"ts": ts, "path": path, "status": status, "latency_ms": lat, "request_id": rid, "trace_id": tid}
    if err:
        d["error"] = err
    return json.dumps(d)


class LogSummaryTest(unittest.TestCase):
    def write(self, lines):
        fd, p = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        self.addCleanup(os.remove, p)
        return p

    def test_clusters_and_client_caused_flag(self):
        p = self.write([
            line("2026-11-19T10:00:00Z", "/v1/chat", 200, 50),
            line("2026-11-19T10:00:01Z", "/v1/chat", 500, 90, "MaxTokensExceeded: max_tokens=128 (prompt_tokens=170)", "a", "ta"),
            line("2026-11-19T10:00:02Z", "/v1/chat", 500, 95, "MaxTokensExceeded: max_tokens=256 (prompt_tokens=900)", "b", "tb"),
            line("2026-11-19T10:00:03Z", "/v1/me", 500, 20, "KeyError: 'user'", "c", "tc"),
            "not json",
        ])
        rows, bad = log_summary.load(p, {"ts": "ts", "path": "path", "status": "status", "latency": "latency_ms",
                                         "request_id": "request_id", "trace_id": "trace_id", "error": "error"})
        self.assertEqual(bad, 1)
        r = log_summary.build(rows, 0, None)["current"]
        self.assertEqual(r["5xx"], 3)
        self.assertEqual(r["defects"], 2)  # two root causes, not three requests
        top = r["clusters"][0]
        self.assertEqual(top["count"], 2)
        self.assertTrue(top["client_caused_suspect"])
        self.assertFalse(r["clusters"][1]["client_caused_suspect"])

    def test_window_and_previous_window(self):
        p = self.write([
            line("2026-11-19T08:30:00Z", "/x", 500, err="boom"),
            line("2026-11-19T09:30:00Z", "/x", 500, err="boom"),
            line("2026-11-19T09:40:00Z", "/x", 500, err="boom"),
        ])
        out = io.StringIO()
        with redirect_stdout(out):
            code = log_summary.main([p, "--window-hours", "1"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("this window: 1 defects, 2 requests hit", text)
        self.assertIn("previous window: 1 defects, 1 requests hit", text)

    def test_percentile_nearest_rank(self):
        self.assertEqual(log_summary.percentile(list(range(1, 101)), 95), 95)
        self.assertIsNone(log_summary.percentile([], 95))

    def test_missing_file_exits_2(self):
        self.assertEqual(log_summary.main(["/no/such/file.jsonl"]), 2)


class RiskCheckTest(unittest.TestCase):
    HIGH_CASES = [
        "auth/session.py", "app/auth/session.py", "APP/Auth/x.py", "infra/prod/main.tf", "db/migrations/001.sql",
        "billing/invoice.py", ".claude/settings.json", ".claude/rules/00-guardrails.md", "CLAUDE.md", "CODEOWNERS",
        ".github/workflows/ci.yml", ".coderabbit.yaml", "modules/vpc.tf", "prod.tfvars", ".env.production",
        "certs/server.pem", "secrets/token.txt",
    ]
    LOW_CASES = ["app/main.py", "tests/test_chat.py", "docs/OBSERVABILITY.md", "README.md", "app/authors.py"]

    def test_high_paths(self):
        for p in self.HIGH_CASES:
            self.assertEqual(risk_check.assess([p])[0], "HIGH", p)

    def test_low_paths(self):
        for p in self.LOW_CASES:
            self.assertEqual(risk_check.assess([p])[0], "LOW", p)

    def test_rename_out_of_auth_is_high(self):
        paths = risk_check.parse_paths(["R100\tapp/auth/session.py\tapp/session.py"])
        self.assertEqual(paths, ["app/auth/session.py", "app/session.py"])
        self.assertEqual(risk_check.assess(paths)[0], "HIGH")

    def test_fail_closed_and_limits(self):
        self.assertEqual(risk_check.assess([])[0], "HIGH")
        self.assertEqual(risk_check.assess(["app/main.py"], changed_lines=51)[0], "HIGH")
        self.assertEqual(risk_check.assess(["app/main.py"], changed_lines=50)[0], "LOW")
        self.assertEqual(risk_check.assess(["other/x.py"], service_dir="services/chat")[0], "HIGH")
        self.assertEqual(risk_check.assess(["services/chat/app.py"], service_dir="./services/chat/")[0], "LOW")
        # Found in the 2026-11-20 smoke run: --service-dir . wrongly returned HIGH.
        self.assertEqual(risk_check.assess(["app/main.py", "./tests/t.py"], service_dir=".")[0], "LOW")

    def test_pattern_matches_workflow(self):
        # Walk up from the script folder: kit repo root, or a user repo root above .claude/skills/ops-agent/scripts.
        wf, d = None, HERE
        for _ in range(6):
            cand = os.path.join(d, ".github", "workflows", "auto-merge-low-risk.yml")
            if os.path.isfile(cand):
                wf = cand
                break
            d = os.path.dirname(d)
        if wf is None:
            self.skipTest("auto-merge-low-risk.yml not found above this folder")
        m = re.search(r"HIGH='([^']+)'", open(wf, encoding="utf-8").read())
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), risk_check.HIGH, "risk_check.HIGH drifted from the workflow")


if __name__ == "__main__":
    unittest.main()
