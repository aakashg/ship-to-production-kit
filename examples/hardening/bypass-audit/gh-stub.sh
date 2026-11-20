#!/bin/bash
# stub: input JSON from $PRJSON, apply the real --jq filter
[ -n "$GHFAIL" ] && exit 1
jqf=""; while [ $# -gt 0 ]; do [ "$1" = "--jq" ] && jqf="$2"; shift; done
jq -r "$jqf" < "$PRJSON"
