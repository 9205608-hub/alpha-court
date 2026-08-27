#!/usr/bin/env bash
# resume-worker.sh — the CR-13 tooth: preflighted, tripwired worker resume.
#
# Raw `grok --resume` is no longer a permitted dispatch verb (CR-13,
# `bridge-isolation-failure` recurrence #2): when the worker's dispatch worktree
# had been deleted, a naked resume let the worker adopt the commander's checkout
# and commit directly onto the production branch. This wrapper enforces, BEFORE
# the resume, that the worker's recorded worktree still exists, is a real git
# worktree of THIS repo, and lives under the dispatch-worktree allowlist root —
# and, AFTER the resume, that the commander checkout was not touched (tripwire:
# detection-not-prevention, stated in tests/test_resume_preflight.py).
#
# usage: scripts/resume-worker.sh <original-receipt.json> <rework-note.md>
#   env: DISPATCH_WORKTREE_ROOT  allowlist root (default ~/.alpha-court/dispatch-worktrees)
#        RESUME_SESSION_ID       override session id (else sibling raw-<stamp>.json)
#
# Outputs (next to the receipt): raw-<note-name>.json + <note-name>.stderr.
# Exit: 2 on any preflight/tripwire failure; otherwise the worker CLI's exit.

# No `set -e`: every failure path is explicit. SIGPIPE ignored so a downstream
# `| head` cannot kill the script before output persistence (CR-04 class).
set -u
trap '' PIPE

die() { echo "resume-worker: $*" >&2; exit 2; }

RECEIPT="${1:?usage: resume-worker.sh <receipt.json> <rework-note.md>}"
NOTE="${2:?usage: resume-worker.sh <receipt.json> <rework-note.md>}"
DROOT="${DISPATCH_WORKTREE_ROOT:-$HOME/.alpha-court/dispatch-worktrees}"

[ -f "$RECEIPT" ] || die "receipt not found: $RECEIPT"
case "$NOTE" in
  /*) ;;
  *) die "rework note must be an ABSOLUTE path (relative paths resolve against the worker cwd and will not exist there): $NOTE" ;;
esac
[ -s "$NOTE" ] || die "rework note missing or empty: $NOTE"

# --- V01 (+RP-1 type discipline): worktree_path from the receipt, fail-closed
WT_RAW=$(python3 - "$RECEIPT" <<'PY'
import json, sys
try:
    r = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
v = r.get("worktree_path")
if v is None or v == "":
    pass
elif not isinstance(v, str):
    print(f"TYPE_ERROR:{type(v).__name__}")
else:
    print(v)
PY
)
case "$WT_RAW" in
  TYPE_ERROR:*) die "receipt worktree_path is not a string (${WT_RAW#TYPE_ERROR:}) — refusing type-confused input" ;;
esac
[ -n "$WT_RAW" ] || die "receipt has no worktree_path — cannot verify isolation; re-dispatch fresh via scripts/dispatch.sh with the rework note as the ticket"

# --- V13: session id (env override, else sibling raw-<stamp>.json) ---------
SID="${RESUME_SESSION_ID:-}"
if [ -z "$SID" ]; then
  RAW_SIBLING="$(dirname "$RECEIPT")/$(basename "$RECEIPT" | sed 's/^receipt-/raw-/')"
  if [ -f "$RAW_SIBLING" ]; then
    SID=$(python3 - "$RAW_SIBLING" <<'PY'
import json, sys
try:
    v = json.load(open(sys.argv[1])).get("sessionId")
except Exception:
    v = None
print(v if isinstance(v, str) else "")
PY
)
  fi
fi
[ -n "$SID" ] || die "no session id (no RESUME_SESSION_ID and no string sessionId in sibling raw json) — re-dispatch fresh via scripts/dispatch.sh"

# --- worker-kind guard: this script resumes GROK only -----------------------
# The invocation below is `grok --resume`. A ds or cursor delivery carries a
# session id from a different CLI, and grok is RETIRED (2026-08-13) — resuming
# one against grok would either fail obscurely or, with a stale login, adopt a
# foreign session. dsh headless has NO resume flag at all (0.1.0-rc.6:
# `--profile headless --help` lists only -h), so a ds ticket is re-dispatched
# fresh with the rework note appended to the original ticket, NOT resumed.
# Detection: grok envelopes carry `sessionId`; ds/cursor carry `session_id`.
RAW_SIBLING="${RAW_SIBLING:-$(dirname "$RECEIPT")/$(basename "$RECEIPT" | sed 's/^receipt-/raw-/')}"
if [ -f "$RAW_SIBLING" ]; then
  FOREIGN=$(python3 - "$RAW_SIBLING" <<'PY'
import json, sys
try:
    e = json.load(open(sys.argv[1]))
except Exception:
    e = {}
print("1" if (isinstance(e, dict) and "session_id" in e and "sessionId" not in e) else "")
PY
)
  [ -z "$FOREIGN" ] || die "this delivery is NOT a grok run (envelope has session_id, not sessionId) and resume-worker.sh only speaks \`grok --resume\`.
  ds has no headless resume; cursor is retired. Re-dispatch fresh instead:
    append the rework note to the original ticket, then
    scripts/dispatch.sh <ticket.md> -k ds -w <same-worktree-name>"
fi

# --- V04/V14: existence + canonicalization BEFORE any policy check ---------
[ -d "$WT_RAW" ] || die "worker worktree gone: $WT_RAW — re-dispatch fresh via scripts/dispatch.sh (never adopt another checkout)"
WT=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$WT_RAW")
DROOT_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$DROOT")
REPO_REAL=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$(pwd)")

# Containment by INODE identity (samefile over the ancestor chain), not byte
# prefixes: on a case-insensitive FS, realpath does not case-normalize, so a
# case-twin path defeats byte comparison in BOTH directions (escape into the
# checkout / false-reject of a legit root) — grok RP-1 major, 2026-07-20.
_contains() {  # exit 0 iff $2 is $1 or lives inside it (inode identity)
  python3 - "$1" "$2" <<'PY'
import os, sys
root, p = sys.argv[1], os.path.realpath(sys.argv[2])
while True:
    try:
        if os.path.samefile(root, p):
            sys.exit(0)
    except OSError:
        pass
    parent = os.path.dirname(p)
    if parent == p:
        sys.exit(1)
    p = parent
PY
}

# --- V02/V03: never the commander checkout or anything inside it -----------
# (kept BEFORE the allowlist so a dispatch root misconfigured into the repo —
# symlinked or case-twinned — still dies here; defended config-fault)
if _contains "$REPO_REAL" "$WT"; then
  die "worktree_path resolves into the commander checkout ($WT) — that is the CR-13 incident; re-dispatch fresh via scripts/dispatch.sh"
fi
# --- allowlist: must live under the dispatch root --------------------------
if ! _contains "$DROOT_REAL" "$WT"; then
  die "worktree_path $WT is outside the dispatch allowlist root $DROOT_REAL — re-dispatch fresh via scripts/dispatch.sh"
fi

# --- V05: must be a real git worktree --------------------------------------
git -C "$WT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "$WT is not a git worktree — re-dispatch fresh via scripts/dispatch.sh"

# --- V06: must belong to THIS repo -----------------------------------------
WT_COMMON=$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
MY_COMMON=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
WT_COMMON=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$WT_COMMON")
MY_COMMON=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$MY_COMMON")
[ "$WT_COMMON" = "$MY_COMMON" ] || die "$WT belongs to a different repository ($WT_COMMON) — refusing to resume against a foreign base"

# --- V09: contract freeze (mirror dispatch.sh: tracked modifications only) --
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  die "contract freeze: commander checkout has modified/staged tracked files — commit or stash first (the worker judges against its worktree base, a dirty commander tree cannot be what you think you froze)"
fi

# --- V12: refuse to overwrite a previous delivery --------------------------
NOTE_NAME=$(basename "$NOTE" .md)
OUT_DIR=$(dirname "$RECEIPT")
OUT_RAW="$OUT_DIR/raw-$NOTE_NAME.json"
OUT_ERR="$OUT_DIR/$NOTE_NAME.stderr"
[ -e "$OUT_RAW" ] && die "output already exists: $OUT_RAW — will not overwrite a prior delivery; pick a new rework note name"

# --- snapshot for the post-flight tripwire ---------------------------------
# Exclude ONLY the script's own two outputs, by exact repo-relative path via
# git pathspec — a basename grep would exempt a worker writing a same-named
# file anywhere in the checkout (caught by commander self-probe, test v11b).
STATUS_PATHSPEC=(".")
for out in "$OUT_RAW" "$OUT_ERR"; do
  rel=$(python3 -c 'import os,sys; print(os.path.relpath(os.path.realpath(sys.argv[1]), sys.argv[2]))' "$out" "$REPO_REAL")
  case "$rel" in
    ..*) ;;  # output lives outside the checkout — nothing to exclude
    *) STATUS_PATHSPEC+=(":(exclude)$rel") ;;
  esac
done
_status() { git status --porcelain -- "${STATUS_PATHSPEC[@]}"; }
PRE_HEAD=$(git rev-parse HEAD)
PRE_STATUS=$(_status)

echo "resume-worker: preflight OK — session=$SID worktree=$WT"
echo "resume-worker: resuming worker (outputs: $OUT_RAW)"

grok --resume "$SID" --prompt-file "$NOTE" --output-format json > "$OUT_RAW" 2> "$OUT_ERR"
GEXIT=$?

# --- post-flight tripwire (V11 + TOCTOU rump of V04) -----------------------
[ -d "$WT" ] || die "TRIPWIRE: worker worktree disappeared during the run — audit the delivery location before judging anything"
POST_HEAD=$(git rev-parse HEAD)
POST_STATUS=$(_status)
if [ "$POST_HEAD" != "$PRE_HEAD" ] || [ "$POST_STATUS" != "$PRE_STATUS" ]; then
  die "TRIPWIRE: commander checkout changed during resume (HEAD $PRE_HEAD -> $POST_HEAD) — the worker escaped isolation; quarantine and audit before judging (CR-13)"
fi

echo "resume-worker: done, worker exit=$GEXIT — receipt/raw at $OUT_RAW"
exit "$GEXIT"
