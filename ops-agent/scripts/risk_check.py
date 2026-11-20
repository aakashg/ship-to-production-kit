#!/usr/bin/env python3
"""Rate a change LOW or HIGH risk from the files it touches. Fails closed.

The ops agent runs this twice: on the files it plans to edit (before any edit)
and on the real diff (before it commits). Any HIGH means: write the ticket and
the proposed fix, change no code, tag the owner in CODEOWNERS.

HIGH when any of these is true:
  * a path (old or new side of a rename) matches the high-risk pattern below,
    which is the same pattern as .github/workflows/auto-merge-low-risk.yml
  * more than --max-lines changed lines (default 50, the ops-agent LOW limit);
    with --git, Markdown files (ticket, PR description, docs) are path-checked
    but not counted toward the line limit
  * a path falls outside --service-dir, when given
  * the file list is empty or cannot be read (fail closed)

Exit codes: 0 LOW, 2 HIGH, 1 usage error.

Examples:
  python3 risk_check.py app/main.py tests/test_chat.py
  python3 risk_check.py --git main            # uses git diff --name-status -M and --numstat against main
  git diff --name-status -M main | python3 risk_check.py --stdin
"""
import argparse
import re
import subprocess
import sys

# Keep in sync with HIGH= in .github/workflows/auto-merge-low-risk.yml (test_risk_check.py checks it).
HIGH = (r"(^|/)(infra|terraform|migrations|migration|auth|authn|authz|billing|payments|secrets|\.github|\.claude)/"
        r"|^(\.coderabbit\.yaml|claude\.md|codeowners|docs/codeowners)$"
        r"|(^|/)(\.env[^/]*|[^/]*\.tf|[^/]*\.tfvars|[^/]*\.pem|[^/]*\.key)$")
HIGH_RE = re.compile(HIGH, re.IGNORECASE)
STATUS_RE = re.compile(r"^[ACDMRTUX]\d*$")


def parse_paths(lines):
    """Accept plain paths or `git diff --name-status -M` lines (both rename sides kept)."""
    paths = []
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and STATUS_RE.match(parts[0].strip()):
            paths.extend(p.strip() for p in parts[1:] if p.strip())
        else:
            paths.append(line.strip())
    return paths


def assess(paths, changed_lines=None, max_lines=50, service_dir=None):
    reasons = []
    if not paths:
        return "HIGH", ["no files listed: fail closed"]
    paths = [p[2:] if p.startswith("./") else p for p in paths]
    if service_dir is not None:
        service_dir = service_dir.strip().rstrip("/")
        if service_dir.startswith("./"):
            service_dir = service_dir[2:]
        if service_dir in ("", "."):
            service_dir = None  # the repo root is the service: nothing can be outside it
    for p in paths:
        if HIGH_RE.search(p):
            reasons.append(f"high-risk path: {p}")
        if service_dir and not (p == service_dir.rstrip("/") or p.startswith(service_dir.rstrip("/") + "/")):
            reasons.append(f"outside service dir {service_dir}: {p}")
    if changed_lines is not None and changed_lines > max_lines:
        reasons.append(f"{changed_lines} changed lines > {max_lines}")
    return ("HIGH" if reasons else "LOW"), reasons


def from_git(base):
    ns = subprocess.run(["git", "diff", "--name-status", "-M", base], capture_output=True, text=True)
    num = subprocess.run(["git", "diff", "--numstat", base], capture_output=True, text=True)
    if ns.returncode != 0 or num.returncode != 0:
        return None, None
    total = 0
    for line in num.stdout.splitlines():
        a, b, path = (line.split("\t") + ["0", "0", ""])[:3]
        if path.strip().lower().endswith(".md"):
            continue  # tickets, PR descriptions and docs do not count toward the code-size limit
        total += (int(a) if a.isdigit() else 0) + (int(b) if b.isdigit() else 0)
    return parse_paths(ns.stdout.splitlines()), total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="changed or planned file paths")
    ap.add_argument("--stdin", action="store_true", help="read paths (or --name-status lines) from stdin")
    ap.add_argument("--git", metavar="BASE", help="diff the working tree against BASE with git")
    ap.add_argument("--lines", type=int, help="changed line count, if known")
    ap.add_argument("--max-lines", type=int, default=50, help="LOW limit on changed lines (default 50)")
    ap.add_argument("--service-dir", help="every path must sit under this folder to stay LOW")
    a = ap.parse_args(argv)

    lines = a.lines
    if a.git:
        paths, git_lines = from_git(a.git)
        if paths is None:
            print("HIGH\n- git diff failed: fail closed")
            return 2
        lines = git_lines if lines is None else lines
    elif a.stdin:
        paths = parse_paths(sys.stdin.readlines())
    else:
        paths = parse_paths(a.paths)

    verdict, reasons = assess(paths, lines, a.max_lines, a.service_dir)
    print(verdict)
    for r in reasons:
        print(f"- {r}")
    if verdict == "LOW":
        print(f"- {len(paths)} file(s), no high-risk path" + (f", {lines} changed lines" if lines is not None else ""))
        print("- LOW here is necessary, not sufficient: the rules in .claude/rules/ and the 'cannot test it' rule still apply")
    return 0 if verdict == "LOW" else 2


if __name__ == "__main__":
    sys.exit(main())
