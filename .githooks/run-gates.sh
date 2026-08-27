#!/usr/bin/env bash
# Shared gate runner for the pre-commit / pre-merge-commit hooks (candidate B).
#
# Runs TWO gates over the STAGED index (never the working tree):
#   1. harness.anti_pattern_gate --staged  — hand-rolled-statistics lint on staged .py blobs.
#   2. scripts/skill-review-gate.sh over merge-base(main,HEAD)..write-tree(index) — a changed
#      skill must be named in an archived review, checked at the moment before it FF-lands.
#
# HONEST CEILING (do not over-claim): a LOCAL hook is an auto-fire tripwire, NOT unbypassable
# enforcement. `git commit --no-verify`, `git -c core.hooksPath=/dev/null commit`, a fresh
# clone that never ran install-hooks.sh, cherry-pick/revert/rebase/commit-tree, and GUI clients
# that skip hooks ALL bypass this by construction. Real enforcement = server-side CI /
# branch protection (DESIGNED for when the public mirror has Actions). What this DOES buy: the
# gates fire automatically on a normal `git commit`, closing the "forgot to run it" failure mode
# that let the v0.1 double-standard through.
#
# FAIL-CLOSED: any gate finding, or any error running a gate (missing python, crash, write-tree
# failure), blocks the commit. A non-executable hook is silently ignored by git — install-hooks.sh
# sets the exec bit; this script never relies on being the last word.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "gate-hook: cannot resolve repo root — failing closed" >&2; exit 1; }
cd "$ROOT" || { echo "gate-hook: cannot cd to repo root — failing closed" >&2; exit 1; }

# pick an interpreter, fail closed if none
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "gate-hook: no python interpreter found — failing closed" >&2; exit 1
fi
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

rc=0

# 1) anti-pattern lint over STAGED blobs
if ! "$PY" -m harness.anti_pattern_gate --staged; then
  rc=1
fi

# 1b) court import-boundary over STAGED court/ blobs (iron law #2)
if ! "$PY" -m harness.court_import_gate --staged; then
  rc=1
fi

# 2) skill-review over merge-base(TRUNK,HEAD)..write-tree(index), via a throwaway commit so the
#    gate's reversed-range guard (which needs commit objects) still works.
#    TRUNK defaults to main, overridable with `git config alphacourt.trunk`. If the trunk cannot
#    be resolved but a SKILL is staged, fail CLOSED — otherwise renaming main silently skips the
#    whole skill-review (grok RP-1). No skill staged + no trunk → skip (nothing to guard).
trunk="$(git config --get alphacourt.trunk || echo main)"
skill_staged="$(git diff --cached --name-only --diff-filter=ACMR -z \
  | tr '\0' '\n' | grep -E '^\.claude/skills/[^/]+/SKILL\.md$' || true)"
if git rev-parse --verify -q "$trunk" >/dev/null 2>&1; then
  base="$(git merge-base "$trunk" HEAD 2>/dev/null || true)"
  if [ -n "$base" ]; then
    tree="$(git write-tree)" || { echo "gate-hook: write-tree failed — failing closed" >&2; exit 1; }
    tmp="$(git commit-tree "$tree" -p HEAD -m _precommit_gate 2>/dev/null)" || {
      echo "gate-hook: commit-tree failed (committer identity set?) — failing closed" >&2; exit 1; }
    if ! bash "$ROOT/scripts/skill-review-gate.sh" "$base" "$tmp"; then
      rc=1
    fi
  elif [ -n "$skill_staged" ]; then
    echo "gate-hook: no merge-base between '$trunk' and HEAD but a skill is staged — failing closed" >&2
    rc=1
  else
    echo "gate-hook: no merge-base with '$trunk', no skill staged — skill-review skipped" >&2
  fi
elif [ -n "$skill_staged" ]; then
  echo "gate-hook: trunk '$trunk' not found but a skill is staged — failing closed (set alphacourt.trunk?)" >&2
  rc=1
else
  echo "gate-hook: trunk '$trunk' not found, no skill staged — skill-review skipped" >&2
fi

exit "$rc"
