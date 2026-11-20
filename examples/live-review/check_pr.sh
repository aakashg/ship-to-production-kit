#!/usr/bin/env bash
# Record what the live review did on the sandbox PRs, in one command.
# Needs: gh logged in. Run after CodeRabbit is installed on the sandbox repo and has reviewed.
#   bash examples/live-review/check_pr.sh                 # both PRs in aakashg/ship-kit-demo
#   bash examples/live-review/check_pr.sh owner/repo 1 2  # any repo and PR numbers
# Writes examples/live-review/results-<date>.md next to this script and prints it.
set -euo pipefail

REPO="${1:-aakashg/ship-kit-demo}"
shift || true
PRS=("$@")
[ ${#PRS[@]} -eq 0 ] && PRS=(1 2)
OUT="$(cd "$(dirname "$0")" && pwd)/results-$(date -u +%Y-%m-%d).md"

{
  echo "# Live review results for $REPO ($(date -u +%Y-%m-%dT%H:%MZ))"
  for n in "${PRS[@]}"; do
    echo
    echo "## PR #$n"
    gh pr view "$n" -R "$REPO" --json title,url,state,mergeStateStatus,reviewDecision,mergedAt,labels,autoMergeRequest \
      --jq '"- \(.title)\n- \(.url)\n- state: \(.state), merge state: \(.mergeStateStatus), review decision: \(.reviewDecision // "none"), merged at: \(.mergedAt // "not merged")\n- labels: \([.labels[].name] | join(", ") | if . == "" then "none" else . end)\n- auto-merge: \(if .autoMergeRequest then "on (\(.autoMergeRequest.mergeMethod), enabled by \(.autoMergeRequest.enabledBy.login))" else "off" end)"'
    echo
    echo "### Checks"
    gh pr checks "$n" -R "$REPO" 2>/dev/null | awk -F'\t' '{print "- " $1 ": " $2}' || echo "- none reported"
    echo
    echo "### Reviews (state, author)"
    gh api "repos/$REPO/pulls/$n/reviews" --paginate \
      --jq '.[] | "- \(.state) by \(.user.login) at \(.submitted_at)"' | { grep . || echo "- none yet"; }
    echo
    echo "### CodeRabbit comments"
    {
      gh api "repos/$REPO/issues/$n/comments" --paginate \
        --jq '.[] | select(.user.login | test("coderabbit"; "i")) | "- [summary] \(.body | split("\n") | map(select(length > 0)) | .[0:3] | join(" / ") | .[0:300])"'
      gh api "repos/$REPO/pulls/$n/comments" --paginate \
        --jq '.[] | select(.user.login | test("coderabbit"; "i")) | "- [inline] \(.path):\(.line // .original_line) \(.body | split("\n") | map(select(length > 0)) | .[0] | .[0:200])"'
      gh api "repos/$REPO/pulls/$n/reviews" --paginate \
        --jq '.[] | select(.user.login | test("coderabbit"; "i")) | select(.body != "") | "- [review \(.state)] \(.body | split("\n") | map(select(length > 0)) | .[0:2] | join(" / ") | .[0:300])"'
    } | { grep . || echo "- none yet (is the CodeRabbit app installed on $REPO?)"; }
  done
} | tee "$OUT"
echo
echo "Saved: $OUT"
