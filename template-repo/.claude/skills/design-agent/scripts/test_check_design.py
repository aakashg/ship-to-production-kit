"""Tests for check_design.py. Standard library only.

Run: python3 -m unittest discover -s design-agent/scripts -p 'test_*.py'
"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_design  # noqa: E402

PRD = """# PRD: Demo
## Success metric
30% of active keys set a budget within 60 days.
## Acceptance examples
| # | Input | Expected | PM label |
|---|---|---|---|
""" + "".join(f"| {i} | spend {i}0% | alert at {i}0% | pass |\n" for i in range(1, 11)) + """
## CPO check
- Strategic alignment: pass
- Clarity: pass
- Edge cases: added empty budget case
- Scope: pass
"""


def decisions(you, agent, count_line=True):
    rows = [f"| {i} | d{i} | a, b | a | high | needs you |" for i in range(1, you + 1)]
    rows += [f"| {i} | d{i} | a, b | a | low | agent |" for i in range(you + 1, you + agent + 1)]
    head = "| # | Decision | Options | Recommendation and why | Risk | Decided by |\n|---|---|---|---|---|---|\n"
    tail = f"\n{you} need you, {agent} decided by the agent.\n" if count_line else ""
    return "# DECISIONS\n" + head + "\n".join(rows) + tail


class CheckDesignTest(unittest.TestCase):
    def make(self, status="Status: DRAFT - awaiting human approval", dec=None, prd=PRD):
        d = tempfile.mkdtemp()
        files = {"PRD.md": prd, "ENG-PLAN.md": "# ENG\nNo model calls.\n",
                 "IMPL-PLAN.md": status + "\n# IMPL\n", "DECISIONS.md": dec or decisions(4, 8)}
        for k, v in files.items():
            with open(os.path.join(d, k), "w") as fh:
                fh.write(v)
        return d

    def gate(self, folder, *extra):
        with redirect_stdout(io.StringIO()) as out:
            code = check_design.main([folder, *extra])
        return code, out.getvalue()

    def test_good_design_passes(self):
        code, out = self.gate(self.make())
        self.assertEqual(code, 0, out)

    def test_too_few_decisions_fails(self):
        code, out = self.gate(self.make(dec=decisions(3, 4)))
        self.assertEqual(code, 1)
        self.assertIn("7 decisions", out)

    def test_needs_you_below_agent_fails(self):
        dec = decisions(4, 8).replace("| 12 | d12 | a, b | a | low | agent |", "| 12 | d12 | a, b | a | high | needs you |")
        code, out = self.gate(self.make(dec=dec))
        self.assertEqual(code, 1)
        self.assertIn("sits below", out)

    def test_wrong_count_line_fails(self):
        dec = decisions(4, 8).replace("4 need you, 8", "5 need you, 7")
        code, out = self.gate(self.make(dec=dec))
        self.assertEqual(code, 1)

    def test_agent_edited_status_fails(self):
        code, out = self.gate(self.make(status="Status: approved"))
        self.assertEqual(code, 1)

    def test_build_gate_needs_approval_and_answers(self):
        code, _ = self.gate(self.make(), "--gate", "build")
        self.assertEqual(code, 1)
        answered = decisions(4, 8).replace("| needs you |", "| answered by Sam: a |")
        folder = self.make(status="Status: APPROVED by Sam 2026-11-20", dec=answered)
        code, out = self.gate(folder, "--gate", "build")
        self.assertEqual(code, 0, out)

    def test_missing_acceptance_examples_and_cpo_fail(self):
        code, out = self.gate(self.make(prd="# PRD\n## Success metric\n10 alerts a day\n"))
        self.assertEqual(code, 1)
        self.assertIn("0 acceptance examples", out)
        self.assertIn("CPO check", out)


if __name__ == "__main__":
    unittest.main()
