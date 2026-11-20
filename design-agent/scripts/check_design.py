#!/usr/bin/env python3
"""Check a design-agent feature folder against the skill's hard gates.

Two gates:
  --gate design (default)  Run by the agent before it stops. Are the four docs
                           complete enough for a human to review?
  --gate build             Run before writing any application code. Exit 0
                           only if a human approved IMPL-PLAN.md and no
                           `needs you` row in DECISIONS.md is still open.

Checks (design gate):
  docs       PRD.md, ENG-PLAN.md, IMPL-PLAN.md, DECISIONS.md all exist
  status     IMPL-PLAN.md line 1 is the DRAFT line, or a well-formed APPROVED line
  decisions  10 to 15 numbered rows, each decided by `agent` or `needs you`,
             every `needs you` row above every `agent` row, and the count line
             "N need you, M decided by the agent" matches the table
  metric     PRD.md has a success metric section containing a number
  examples   PRD.md has 10+ acceptance examples (table rows or list items)
  cpo        PRD.md ends with a "CPO check" section covering strategic
             alignment, clarity, edge cases and scope
  eval       if ENG-PLAN.md mentions an LLM or model call, it names an eval (warning)
  code       with --repo, git shows no changed or new files under app/, infra/, tests/

Exit codes: 0 all gates pass, 1 a gate failed, 2 usage error.

Examples:
  python3 check_design.py docs/features/spend-alerts --repo .
  python3 check_design.py docs/features/spend-alerts --gate build
"""
import argparse
import os
import re
import subprocess
import sys

DOCS = ["PRD.md", "ENG-PLAN.md", "IMPL-PLAN.md", "DECISIONS.md"]
DRAFT = "Status: DRAFT - awaiting human approval"
APPROVED_RE = re.compile(r"^Status: APPROVED by \S.*\S$")
COUNT_RE = re.compile(r"(\d+)\s+needs?\s+you\b.*?(\d+)\s+decided by the agent", re.IGNORECASE)
CODE_DIRS = ("app/", "infra/", "tests/")


def read(folder, name):
    p = os.path.join(folder, name)
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def section(text, heading_pattern):
    """Body of the first markdown section whose heading matches, up to the next heading of the same or higher level."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m and re.search(heading_pattern, m.group(2), re.IGNORECASE):
            level = len(m.group(1))
            body = []
            for nxt in lines[i + 1:]:
                m2 = re.match(r"^(#{1,6})\s", nxt)
                if m2 and len(m2.group(1)) <= level:
                    break
                body.append(nxt)
            return "\n".join(body)
    return None


def decision_rows(text):
    """Numbered table rows: | 3 | ... | Decided by |. Returns (number, decided_by_cell)."""
    rows = []
    for ln in text.splitlines():
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"\d+", cells[0]):
            rows.append((int(cells[0]), cells[-1]))
    return rows


def kind(cell):
    c = cell.lower().strip("`* ")
    if c.startswith("needs you"):
        return "needs_you"
    if c.startswith("answered") or c.startswith("human"):
        return "answered"
    if c.startswith("agent"):
        return "agent"
    return "unknown"


def count_items(body):
    if body is None:
        return 0
    n = 0
    for ln in body.splitlines():
        s = ln.strip()
        if s.startswith("|") and not re.fullmatch(r"\|[\s:|-]+\|?", s):
            n += 1
        elif re.match(r"^(\d+[.)]|[-*])\s+\S", s):
            n += 1
    # Subtract one header row per table.
    tables = len(re.findall(r"^\s*\|[\s:-]+\|[\s:|-]*$", body, flags=re.MULTILINE))
    return max(0, n - tables)


def git_code_changes(repo):
    r = subprocess.run(["git", "-C", repo, "status", "--porcelain", "--untracked-files=all"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    hits = []
    for ln in r.stdout.splitlines():
        path = ln[3:].split(" -> ")[-1].strip('"')
        if path.startswith(CODE_DIRS):
            hits.append(path)
    return hits


def run(folder, gate, repo):
    results = []  # (level, check, message) level in PASS/FAIL/WARN

    def add(level, check, msg):
        results.append((level, check, msg))

    texts = {d: read(folder, d) for d in DOCS}
    missing = [d for d, t in texts.items() if t is None]
    add("FAIL" if missing else "PASS", "docs", f"missing: {', '.join(missing)}" if missing else "all four docs present")

    impl = texts["IMPL-PLAN.md"]
    first = impl.splitlines()[0].strip() if impl else ""
    approved = bool(APPROVED_RE.match(first))
    if impl is None:
        pass
    elif first == DRAFT:
        add("PASS" if gate == "design" else "FAIL", "status",
            "DRAFT, waiting for a human" if gate == "design" else "IMPL-PLAN.md is still DRAFT: no code until a human approves")
    elif approved:
        add("PASS", "status", f"approved: '{first}'")
    else:
        add("FAIL", "status", f"line 1 must be '{DRAFT}' or 'Status: APPROVED by <name> <date>', found '{first[:80]}'")

    dec = texts["DECISIONS.md"]
    if dec is not None:
        rows = decision_rows(dec)
        kinds = [kind(c) for _, c in rows]
        n_you, n_agent = kinds.count("needs_you"), kinds.count("agent")
        n_ans = kinds.count("answered")
        if gate == "design":
            if not 10 <= len(rows) <= 15:
                add("FAIL", "decisions", f"{len(rows)} decisions; the skill asks for 10 to 15")
            else:
                add("PASS", "decisions", f"{len(rows)} decisions")
            unknown = [n for (n, _), k in zip(rows, kinds) if k == "unknown"]
            if unknown:
                add("FAIL", "decisions", f"rows {unknown} have a 'Decided by' cell that is neither 'agent' nor 'needs you'")
            seen_agent, order_ok = False, True
            for k in kinds:
                if k == "agent":
                    seen_agent = True
                elif k in ("needs_you", "answered") and seen_agent:
                    order_ok = False
            add("PASS" if order_ok else "FAIL", "decisions",
                "needs-you rows come first" if order_ok else "a `needs you` row sits below an `agent` row; put them at the top")
            m = COUNT_RE.search(dec)
            if not m:
                add("FAIL", "decisions", "count line missing: 'N need you, M decided by the agent'")
            elif (int(m.group(1)), int(m.group(2))) != (n_you + n_ans, n_agent):
                add("FAIL", "decisions", f"count line says {m.group(1)} / {m.group(2)}, table has {n_you + n_ans} / {n_agent}")
            else:
                add("PASS", "decisions", f"count line matches: {n_you + n_ans} need you, {n_agent} agent")
        else:
            open_rows = [n for (n, _), k in zip(rows, kinds) if k == "needs_you"]
            add("FAIL" if open_rows else "PASS", "decisions",
                f"unanswered `needs you` rows: {open_rows}" if open_rows else f"no open `needs you` rows ({n_ans} answered)")

    prd = texts["PRD.md"]
    if prd is not None and gate == "design":
        metric = section(prd, r"success|metric")
        if metric is None:
            add("FAIL", "metric", "no 'Success metric' section in PRD.md")
        elif not re.search(r"\d", metric):
            add("FAIL", "metric", "success metric section has no number")
        else:
            add("PASS", "metric", "success metric has a number")
        n_ex = count_items(section(prd, r"acceptance"))
        add("PASS" if n_ex >= 10 else "FAIL", "examples", f"{n_ex} acceptance examples (need 10+)")
        cpo = section(prd, r"cpo check")
        if cpo is None:
            add("FAIL", "cpo", "no '## CPO check' section in PRD.md")
        else:
            lacking = [k for k, pat in [("strategic alignment", r"strateg"), ("clarity", r"clarity|clear"),
                                        ("edge cases", r"edge"), ("scope", r"scope|non-goal")]
                       if not re.search(pat, cpo, re.IGNORECASE)]
            add("FAIL" if lacking else "PASS", "cpo", f"CPO check lacks: {', '.join(lacking)}" if lacking else "all four checks present")

    eng = texts["ENG-PLAN.md"]
    if eng is not None and gate == "design":
        if re.search(r"\bLLM\b|model call|\bprompt\b|completion", eng) and not re.search(r"\beval", eng, re.IGNORECASE):
            add("WARN", "eval", "ENG-PLAN mentions an LLM but names no eval")

    if repo and gate == "design" and not approved:
        hits = git_code_changes(repo)
        if hits is None:
            add("WARN", "code", f"could not run git status in {repo}")
        elif hits:
            add("FAIL", "code", f"files under app/, infra/ or tests/ changed before approval: {hits[:5]}")
        else:
            add("PASS", "code", "no changes under app/, infra/, tests/")
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="feature folder, e.g. docs/features/<slug>")
    ap.add_argument("--gate", choices=["design", "build"], default="design")
    ap.add_argument("--repo", help="repo root; adds the no-code-before-approval git check")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.folder):
        print(f"error: not a folder: {a.folder}", file=sys.stderr)
        return 2
    results = run(a.folder, a.gate, a.repo)
    for level, check, msg in results:
        print(f"{level:4}  {check:9}  {msg}")
    fails = sum(1 for r in results if r[0] == "FAIL")
    print(f"\n{a.gate} gate: {'PASS' if not fails else 'FAIL'} ({fails} failed, "
          f"{sum(1 for r in results if r[0] == 'WARN')} warnings)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
