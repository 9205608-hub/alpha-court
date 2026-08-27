#!/usr/bin/env bash
# skill-review-gate.sh [base] [head] — mechanizes CR-07.
#
# No skill change reaches main without an archived external review that NAMES it. The
# double-standard the v0.1 meta-review graded B for recurred: a skill merged to main with NO
# review, and only a human forced the after-the-fact grok pass. This gate closes that gap.
#
# For each ADDED/MODIFIED `.claude/skills/<name>/SKILL.md` in the range, a review under
# `.scratch/reflow/meta-reviews/` must name `<name>` in its **added** lines. Design choices,
# each fixing a bypass found by enumeration:
#   - per-skill, ALL must be covered (an unrelated review no longer satisfies a co-changed
#     skill — the range-level co-presence false-PASS logged in lessons-inbox);
#   - **added** lines, not head content (dragging a stale review into range with a no-op touch
#     no longer vouches);
#   - word-bounded name match (hyphen is a word char), so 'foo' is not matched inside 'foobar'
#     and 'research' not inside 'research-session-protocol';
#   - deletions are excluded (--diff-filter=d): removing a skill needs no review.
#
# HONEST LIMITS (CR-08): this checks that a review REFERENCES the skill, not that it is
# *about* it — substance is RP-1's / a human's job. Still passes: a common-word skill name
# (e.g. 'research') that any review mentions in prose; an omnibus review that incidentally
# lists the name; and actively pasting the name into a fake review. It raises the bar from
# 'passively omit a review' to 'the archived review at least names this skill' — not to
# 'a substantive review exists' (a review-*prompt* naming the skill counts too, not only the
# raw verdict). A reversed base/head hard-fails (exit 2); Unicode skill names are out of scope.
#
# Exit 0 = ok. Exit 1 = a changed skill is un-named in any review. Exit 2 = cannot diff.
set -uo pipefail

base="${1:-main}"
head="${2:-HEAD}"
GIT=(git -c core.quotepath=false)

# Reject a reversed range (head older than base): a skill ADD would read as a deletion, and
# the gate would silently PASS "no skill change".
if "${GIT[@]}" merge-base --is-ancestor "$head" "$base" 2>/dev/null \
   && ! "${GIT[@]}" merge-base --is-ancestor "$base" "$head" 2>/dev/null; then
  echo "skill-review-gate: refusing a reversed range ($head is older than $base)" >&2
  exit 2
fi

changed="$("${GIT[@]}" diff --name-only --diff-filter=d "$base" "$head" 2>/dev/null)" || {
  echo "skill-review-gate: cannot diff $base..$head" >&2; exit 2; }

# single-level skill dir only (a nested path is not a skill layout)
skill_changed="$(printf '%s\n' "$changed" | grep -E '^\.claude/skills/[^/]+/SKILL\.md$' || true)"
if [ -z "$skill_changed" ]; then
  echo "skill-review-gate: PASS — no skill change in $base..$head"
  exit 0
fi

# The ADDED lines of any archived review in the range (added-only so a no-op touch of a stale
# review cannot vouch for a fresh skill change).
# added CONTENT lines only: '^\+[^+]' excludes the '+++ b/<path>' file-header line, so a
# review's PATH tokens (b / scratch / reflow / json / md) cannot vouch for a same-named skill.
review_added="$("${GIT[@]}" diff "$base" "$head" -- '.scratch/reflow/meta-reviews/' 2>/dev/null \
  | grep -E '^\+[^+]' || true)"

uncovered=""
while IFS= read -r sk; do
  [ -z "$sk" ] && continue
  name="$(printf '%s' "$sk" | sed -E 's#^\.claude/skills/([^/]+)/SKILL\.md$#\1#')"
  # escape ERE metacharacters so a skill name like 'foo.bar' or 'a|b' matches literally
  name_esc="$(printf '%s' "$name" | sed 's/[^A-Za-z0-9_-]/\\&/g')"
  if ! printf '%s\n' "$review_added" \
      | grep -qE "(^|[^A-Za-z0-9_-])${name_esc}([^A-Za-z0-9_-]|\$)"; then
    uncovered="${uncovered}    uncovered: ${sk} (needs a review naming '${name}')"$'\n'
  fi
done <<< "$skill_changed"

if [ -n "$uncovered" ]; then
  echo "skill-review-gate: FAIL — a changed skill is named in NO archived review ($base..$head):" >&2
  printf '%s' "$uncovered" >&2
  echo "  Each changed skill needs a .scratch/reflow/meta-reviews/* review naming it (CR-07)." >&2
  exit 1
fi

echo "skill-review-gate: PASS — every changed skill is named in an archived review's added lines:"
printf '%s\n' "$skill_changed" | sed 's/^/    skill: /'
exit 0
