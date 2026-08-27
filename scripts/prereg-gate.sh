#!/usr/bin/env bash
# prereg-gate.sh <prereg-doc> <results-path> — the 禁赢学 tooth.
#
# Enforces rule 1 of /honest-validation: thresholds/seeds/aggregation must be
# frozen (committed) BEFORE any results exist. A results artifact committed
# before its pre-registration inverts the discipline — that is how post-hoc
# threshold-tuning and seed-fishing hide. This gate makes the ordering checkable
# from git history (tamper-evident, per RP-0), not a promise.
#
# Exit 0 = pre-registration precedes results (or results not yet committed).
# Exit 1 = pre-registration missing or committed after results.
set -uo pipefail

prereg="${1:?usage: prereg-gate.sh <prereg-doc> <results-path>}"
results="${2:?usage: prereg-gate.sh <prereg-doc> <results-path>}"

# Earliest commit that ADDED the file (unix time). Empty = never committed.
first_add_ct() { git log --diff-filter=A --follow --format=%ct -- "$1" 2>/dev/null | tail -1; }

pc="$(first_add_ct "$prereg")"
if [ -z "$pc" ]; then
  echo "prereg-gate: FAIL — pre-registration '$prereg' is not committed. Freeze it first." >&2
  exit 1
fi

rc="$(first_add_ct "$results")"
if [ -z "$rc" ]; then
  echo "prereg-gate: PASS — pre-registration '$prereg' committed; results not yet in history (nothing to invert)."
  exit 0
fi

if [ "$rc" -lt "$pc" ]; then
  echo "prereg-gate: FAIL — results '$results' were committed BEFORE the pre-registration '$prereg'." >&2
  echo "  That inverts 禁赢学: thresholds/seeds/aggregation must be frozen before results exist." >&2
  exit 1
fi

echo "prereg-gate: PASS — pre-registration '$prereg' precedes results '$results'."
