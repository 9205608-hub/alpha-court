#!/usr/bin/env bash
# rework-lint.sh <rework-note.md> — the POST-dispatch half of CR-05.
#
# The dirty-tree freeze gate in dispatch.sh blocks a stale contract BEFORE a
# worker starts. But v0.1's actual `contract-stale-override` sin was in rework
# notes written AFTER dispatch: "the spec in YOUR worktree is stale, my erratum
# overrides" (08b/c/d/10a). That is post-hoc legislation and no pre-dispatch
# gate can catch it. This linter does: run it on every NEW rework note.
#
# It scans ONE named file (never the repo), so it cannot false-fail on the
# historical rework notes that ARE the documented evidence of the sin.
set -uo pipefail
f="${1:?usage: rework-lint.sh <rework-note.md>}"
[ -f "$f" ] || { echo "not found: $f" >&2; exit 2; }

# Match staleness-claim-plus-override, and the Chinese override idioms directly.
if grep -niE '(worktree|spec|contract|bhy|doc)[^\n]{0,60}(stale|out of date)|(stale|out of date)[^\n]{0,60}(override|overrides|以我勘误|以下勘误)|以我勘误为准|以下勘误为准|erratum overrides|my erratum overrides' "$f"; then
  echo "rework-lint: FAIL — $f carries stale-override phrasing (post-hoc legislation)." >&2
  echo "  A worker is judged only against the contract in its worktree. Instead:" >&2
  echo "  re-dispatch against the amended, committed base, or issue the change as a" >&2
  echo "  new ruling attributed contract-fault (not worker-fault)." >&2
  exit 1
fi
echo "rework-lint: PASS — $f"
