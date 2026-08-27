#!/usr/bin/env bash
# reflow-gate.sh — the acceptance gate for RP-0 self-binding artifacts.
#
# Verifies every commander-rework entry carries its CONTENT contract (not just
# that a file exists) and cites a FROZEN root_cause_id. This is a SHAPE check:
# it proves the four fields are present and the id is in the vocab. It cannot
# prove the fields are honest — that is the job of the RP-1 external review.
# Two layers: this gate stops empty files; grok stops empty content.
#
# Exit 0 = all entries well-formed; non-zero = at least one violation.
# Wire as a Stop / session-close hook, and run it as the acceptance-gate red-test.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
CR_DIR="$ROOT/.scratch/reflow/commander-rework"
VOCAB="$ROOT/.scratch/reflow/root-cause-vocab.md"
REQ=(root_cause_id attribution occurrences evidence fix anti-recurrence polluted-rework)

fail=0
count=0
for f in "$CR_DIR"/CR-*.md; do
  [ -f "$f" ] || continue
  count=$((count + 1))
  base="$(basename "$f")"
  for field in "${REQ[@]}"; do
    if ! grep -qi -- "$field" "$f"; then
      echo "MISSING field '$field' in $base"; fail=1
    fi
  done
  rcid="$(grep -oiE 'root_cause_id\*\*: *\`?[a-z-]+' "$f" | head -1 | grep -oE '[a-z-]+$' || true)"
  if [ -n "$rcid" ]; then
    if ! grep -q -- "\`$rcid\`" "$VOCAB"; then
      echo "UNFROZEN root_cause_id '$rcid' in $base (not in $VOCAB)"; fail=1
    fi
  fi
done

if [ "$count" -eq 0 ]; then
  echo "reflow-gate: no commander-rework entries found under $CR_DIR"; exit 1
fi
if [ "$fail" -eq 0 ]; then
  echo "reflow-gate: PASS — $count entries, all carry the content contract with frozen ids"
else
  echo "reflow-gate: FAIL"
fi
exit "$fail"
