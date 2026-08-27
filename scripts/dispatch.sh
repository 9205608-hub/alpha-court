#!/usr/bin/env bash
# alpha-court M0 commander→worker bridge.
# Dispatch a self-contained worker ticket to a headless worker CLI, inside a
# commander-created isolated git worktree, with the delivery receipt validated
# commander-side against scripts/receipt.schema.json.
#
# Minimal worker contract — a worker is any headless CLI that:
#   (a) takes a self-contained prompt (file or argv),
#   (b) works in a commander-created isolated worktree (pinned by a cwd flag
#       where the CLI has one, otherwise by the subshell cwd),
#   (c) returns a receipt conforming to scripts/receipt.schema.json,
#   (d) runs fully non-interactively.
# Three workers wired, each a worker_invoke / worker_extract_receipt branch
# over the same isolation / tripwire / validation spine (registry still
# deferred, YAGNI):
#   ds      DeepSeek Harness headless profile — DEFAULT since 2026-08-15
#   cursor  cursor-agent (added 2026-08-13; RETIRED 2026-08-15, see below)
#   grok    grok CLI (RETIRED 2026-08-13, kept for the record)
#
# Owner ruling 2026-08-15: "改用 ds，全线." Cursor's subscription lapsed to
# Free — every named model now returns `ActionRequiredError: Named models
# unavailable Free plans can only use Auto`, so the cursor seam can no longer
# honour the cross-vendor builder rule (auto is an unpinnable moving target).
# All worker traffic moves to DeepSeek. Builder=DeepSeek, reviewer/judge=
# Claude/other keeps the cross-vendor iron rule intact.
#
# Usage:
#   scripts/dispatch.sh <ticket.md> [-k ds|cursor|grok] [-n BEST_OF_N] [-m MODEL] [-t MAX_TURNS] [-w WORKTREE_NAME]
#
# Isolation is enforced on the commander side: we `git worktree add` a fresh
# worktree on a dedicated branch and pin the worker into it with `--cwd`.
# (grok's own --worktree flag is NOT used: in headless mode it proved
# unreliable — the worker ended up running in the dispatching checkout.)
#
# Outputs (next to the ticket file):
#   raw-<stamp>.json      full grok JSON envelope (text/structuredOutput/sessionId/...)
#   receipt-<stamp>.json  schema-conformant worker receipt (from structuredOutput)
#
# The receipt is the worker's factual self-report. It is NOT an evaluation:
# the commander-side referee must review the diff and re-run the acceptance
# commands independently before merging. After merging:
#   git worktree remove <worktree-path> && git branch -d <dispatch-branch>

set -euo pipefail
# Ignore SIGPIPE: the receipt is persisted to files below, and a downstream
# `dispatch.sh ... | head` closing the pipe must not kill this script before
# that persistence runs (v0.1 incident: `| head` SIGPIPE dropped a receipt).
trap '' PIPE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="$SCRIPT_DIR/receipt.schema.json"

TICKET="${1:?usage: dispatch.sh <ticket.md> [-k ds|cursor|grok] [-n N] [-m MODEL] [-t MAX_TURNS] [-w NAME]}"
shift

BEST_OF_N=""
MODEL=""
MAX_TURNS="60"
WORKTREE_NAME=""
# grok-4.5's model menu tops out at "high" (its default too); pin it explicitly
# so a CLI default change can never silently lower worker reasoning effort.
EFFORT="high"
# Worker kind: ds | cursor | grok. Owner rulings retired grok (2026-08-13,
# wrong-account 402) and then cursor (2026-08-15, subscription lapsed to Free
# → named models rejected). ds is the default; both retired seams stay in the
# file for the record and revival via -k. Knobs that a given CLI cannot honour
# are rejected loudly below rather than silently ignored — a silently dropped
# -t/-n/-e would weaken the worker contract without anyone noticing.
WORKER="ds"
CURSOR_BIN="${CURSOR_AGENT_BIN:-cursor-agent}"   # never bare `agent`: grok ships a same-named binary earlier on PATH

# --- ds (DeepSeek Harness) knobs --------------------------------------------
# Version is PINNED: dsh is a 0.1.x developer preview, so `@latest` could change
# the worker under us between dispatches. Override with DSH_PKG (or point
# DSH_BIN at a globally installed `dsh`).
DSH_PKG="${DSH_PKG:-@deepseek-ai/dsh@0.1.0-rc.6}"
if [ -n "${DSH_BIN:-}" ]; then DSH_CMD=("$DSH_BIN"); else DSH_CMD=(npx --yes "$DSH_PKG"); fi
# Persistent DSH_HOME so session dirs survive for resume-worker.sh.
DSH_HOME="${DSH_HOME:-$HOME/.alpha-court/dsh-home}"
DS_MODEL=""   # resolved after getopts: headless ships deepseek-v4-flash, -m overrides

while getopts "n:m:t:w:e:k:" opt; do
  case "$opt" in
    n) BEST_OF_N="$OPTARG" ;;
    m) MODEL="$OPTARG" ;;
    t) MAX_TURNS="$OPTARG" ;;
    w) WORKTREE_NAME="$OPTARG" ;;
    e) EFFORT="$OPTARG" ;;
    k) WORKER="$OPTARG" ;;
    *) exit 1 ;;
  esac
done

[ -f "$TICKET" ] || { echo "ticket not found: $TICKET" >&2; exit 1; }
[ -f "$SCHEMA" ] || { echo "receipt schema not found: $SCHEMA" >&2; exit 1; }

case "$WORKER" in
  grok) ;;
  cursor)
    # grok-only knobs must fail loudly, not silently degrade the contract.
    [ -z "$BEST_OF_N" ] || { echo "-n is grok-only (cursor has no best-of-n)" >&2; exit 1; }
    command -v "$CURSOR_BIN" >/dev/null 2>&1 || { echo "cursor worker: $CURSOR_BIN not found on PATH" >&2; exit 1; }
    echo "[dispatch] WARNING: the cursor seam is RETIRED (2026-08-15: subscription" >&2
    echo "           lapsed to Free, named models rejected). Expect ActionRequiredError" >&2
    echo "           unless -m auto. Default worker is now ds." >&2
    ;;
  ds)
    # dsh headless takes only the task text: no best-of-n, no turn cap, no
    # reasoning-effort dial. Reject rather than silently drop.
    [ -z "$BEST_OF_N" ] || { echo "-n is grok-only (dsh headless has no best-of-n)" >&2; exit 1; }
    [ "$MAX_TURNS" = "60" ] || { echo "-t is not honoured by dsh headless (no turn cap flag); rerun without it" >&2; exit 1; }
    [ "$EFFORT" = "high" ] || { echo "-e is not honoured by dsh headless (no reasoning-effort flag); use -m deepseek-v4-pro instead" >&2; exit 1; }
    DS_MODEL="${MODEL:-deepseek-v4-flash}"
    case "$DS_MODEL" in
      deepseek-v4-flash|deepseek-v4-pro) ;;
      *) echo "ds worker: unknown model '$DS_MODEL' (deepseek-v4-flash|deepseek-v4-pro)" >&2; exit 1 ;;
    esac
    [ -n "${DSH_BIN:-}" ] || command -v npx >/dev/null 2>&1 || { echo "ds worker: npx not found on PATH (need node, or set DSH_BIN)" >&2; exit 1; }
    # The #1 ds failure mode: no key in the environment. The key is NOT in the
    # shell profile — it lives in a gitignored file and must be sourced.
    [ -n "${DEEPSEEK_API_KEY:-}" ] || {
      echo "ds worker: DEEPSEEK_API_KEY is empty. Load it first:" >&2
      echo "  set -a; . ~/Desktop/智能投研助手/run_research.local.sh; set +a" >&2
      exit 1; }
    mkdir -p "$DSH_HOME"
    ;;
  *) echo "unknown worker kind: $WORKER (ds|cursor|grok)" >&2; exit 1 ;;
esac

OUT_DIR="$(cd "$(dirname "$TICKET")" && pwd)"
TICKET_ABS="$OUT_DIR/$(basename "$TICKET")"
STAMP="$(date +%Y%m%d-%H%M%S)"
RAW="$OUT_DIR/raw-$STAMP.json"
RECEIPT="$OUT_DIR/receipt-$STAMP.json"

# --- commander-side isolation: fresh worktree on a dispatch branch ---------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "dispatch.sh must run from inside the repo" >&2; exit 1
fi
[ -n "$WORKTREE_NAME" ] || WORKTREE_NAME="$(basename "$OUT_DIR")"
DISPATCH_ROOT="${DISPATCH_WORKTREE_ROOT:-$HOME/.alpha-court/dispatch-worktrees}"
mkdir -p "$DISPATCH_ROOT"
WT_PATH="$DISPATCH_ROOT/$WORKTREE_NAME-$STAMP"
WT_BRANCH="dispatch/$WORKTREE_NAME-$STAMP"

# Contract freeze (RP-0), now a HARD gate, not a warning. The worker worktree
# is built from HEAD, so any TRACKED file modified or staged in the dispatching
# checkout is invisible to the worker — a named contract among them judges the
# worker against a stale base. That was v0.1's "post-hoc legislation" trust-
# burner. Untracked files (scratch, ticket drafts) are fine; they cannot shadow
# a committed contract. There is no silent override: commit or stash first.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[dispatch] CONTRACT FROZEN: tracked files are modified/staged; the" >&2
  echo "           worker worktree is built from HEAD and will NOT see them." >&2
  echo "           Commit (or stash) before dispatching. Modified/staged:" >&2
  git diff --name-only | sed 's/^/             M /' >&2
  git diff --cached --name-only | sed 's/^/             + /' >&2
  exit 1
fi

# The tripwire must ignore dispatch artifacts. Excluding only THIS run's
# ticket dir is not enough: concurrent dispatches write raw/receipt files
# into sibling dirs and would false-trip each other (incident, 2026-07-10).
# Exclude the whole .scratch/dispatch convention dir, plus OUT_DIR if the
# ticket lives elsewhere.
REPO_ROOT="$(git rev-parse --show-toplevel)"
STATUS_PATHSPEC=(-- . ":(exclude).scratch/dispatch")
case "$OUT_DIR" in
  "$REPO_ROOT"/*) STATUS_PATHSPEC+=(":(exclude)${OUT_DIR#"$REPO_ROOT"/}") ;;
esac

BASE_HEAD="$(git rev-parse HEAD)"
BASE_STATUS="$(git status --porcelain "${STATUS_PATHSPEC[@]}")"

git worktree add -b "$WT_BRANCH" "$WT_PATH" HEAD >/dev/null
echo "[dispatch] worktree: $WT_PATH (branch $WT_BRANCH, base ${BASE_HEAD:0:8})"

# --- worker seams -----------------------------------------------------------
# Per-worker invocation seams over the shared isolation / tripwire /
# validation spine.
worker_invoke_grok() {
  local CMD
  CMD=(grok --prompt-file "$TICKET_ABS"
       --cwd "$WT_PATH"
       --output-format json
       --json-schema "$(cat "$SCHEMA")"
       --permission-mode auto
       --reasoning-effort "$EFFORT"
       --max-turns "$MAX_TURNS")
  [ -n "$BEST_OF_N" ] && CMD+=(--best-of-n "$BEST_OF_N")
  [ -n "$MODEL" ] && CMD+=(--model "$MODEL")
  "${CMD[@]}" > "$RAW"
}

# cursor-agent has no --cwd flag; the worktree is pinned by both the subshell
# cwd and --workspace (probe-verified 2026-08-13: headless shell runs execute
# in the workspace dir). No --json-schema flag either, so the receipt schema
# MUST ride the prompt (CR-16: the first cursor dispatch came back status=done
# but bounced at validation exit 3 because the worker never saw the schema).
# Shared receipt-schema preamble for the seams whose CLI has no --json-schema
# flag (cursor, ds). The "instance, not a copy" paragraph is load-bearing:
# without it the worker templates its receipt straight off the schema text and
# carries `$schema`/`title` into the instance, which the strict validator
# rejects (`unexpected key '$schema'`) — observed on the first ds dispatch,
# 2026-08-15, same family as CR-16. The validator is NOT loosened and the
# extractor does NOT strip keys: the receipt is the worker's factual
# self-report, so the commander must never rewrite it.
receipt_prompt_suffix() {
  cat <<EOF

## RECEIPT SCHEMA (enforced commander-side; your final JSON receipt MUST validate against it)

$(cat "$SCHEMA")

## RECEIPT RULES (read before writing the receipt)

1. Your final message MUST end with the receipt as a single JSON object.
2. The receipt is an INSTANCE of the schema above, NOT a copy of the schema.
   Emit ONLY the keys listed under "properties". Do NOT include \`\$schema\`,
   \`title\`, \`type\`, \`required\`, or any other schema metadata key —
   validation is strict and any extra top-level key fails the dispatch.
3. Do not print any JSON object after the receipt.
EOF
}

worker_invoke_cursor() {
  local PROMPT
  PROMPT="$(cat "$TICKET_ABS")
$(receipt_prompt_suffix)"
  ( cd "$WT_PATH" && "$CURSOR_BIN" -p \
      --output-format json \
      --force \
      --workspace "$WT_PATH" \
      --model "${MODEL:-cursor-grok-4.6-high}" \
      "$PROMPT" ) > "$RAW"
}

# dsh headless is the narrowest seam of the three: the task is argv, there is
# no --cwd, no --json-schema, no --model, no --max-turns (probe-verified
# 2026-08-15 against 0.1.0-rc.6 `--profile headless --help`). So:
#   cwd     → subshell cd (dsh runs its tools in the process cwd; verified by
#             a scratch-repo run that edited files and ran pytest in place)
#   schema  → rides the prompt, exactly as the cursor seam does (CR-16)
#   model   → generated --patch overlay on the agent-default-model entry
#   output  → dsh prints the final assistant message as PLAIN TEXT, not JSON,
#             so we wrap it into the cursor-shaped envelope
#             {"result":..., "session_id":...} and reuse that normalizer.
# session_id is recovered from the session dir dsh writes under
# $DSH_HOME/sessions/<escaped-cwd>/, so resume-worker.sh keeps working.
worker_invoke_ds() {
  local PROMPT TXT PATCH RC MARK
  PROMPT="$(cat "$TICKET_ABS")
$(receipt_prompt_suffix)"
  TXT="$OUT_DIR/raw-$STAMP.text"
  MARK="$OUT_DIR/.dsh-mark-$STAMP"
  : > "$MARK"

  local CMD=("${DSH_CMD[@]}" --profile headless)
  if [ "$DS_MODEL" != "deepseek-v4-flash" ]; then
    PATCH="$OUT_DIR/dsh-model-$STAMP.patch.yml"
    printf -- '- id: agent-default-model\n  config:\n    provider: deepseek-official\n    model: %s\n' "$DS_MODEL" > "$PATCH"
    CMD+=(--patch "$PATCH")
  fi

  ( cd "$WT_PATH" && DSH_HOME="$DSH_HOME" "${CMD[@]}" "$PROMPT" ) > "$TXT" 2>"$OUT_DIR/raw-$STAMP.stderr"
  RC=$?

  DSH_HOME="$DSH_HOME" python3 - "$TXT" "$RAW" "$MARK" "$DSH_HOME" <<'PY'
import json, os, sys
txt_path, out_path, mark_path, dsh_home = sys.argv[1:5]
with open(txt_path, encoding="utf-8", errors="replace") as f:
    text = f.read()
# newest session dir created after the mark file = this run's session
since, sid = os.path.getmtime(mark_path), None
sessions = os.path.join(dsh_home, "sessions")
best = -1.0
for root, dirs, _ in os.walk(sessions):
    for d in dirs:
        if not d.startswith("session-"):
            continue
        p = os.path.join(root, d)
        m = os.path.getmtime(p)
        if m >= since - 1 and m > best:
            best, sid = m, d[len("session-"):]
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"result": text, "session_id": sid}, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
  rm -f "$MARK"
  return $RC
}

worker_invoke() {
  case "$WORKER" in
    grok)   worker_invoke_grok ;;
    cursor) worker_invoke_cursor ;;
    ds)     worker_invoke_ds ;;
  esac
}

# Receipt extract + commander-side schema validation.
# Non-zero exit (3 = invalid, 4 = missing) fails the dispatch hard.
# Cursor envelope is {"type":"result","result":"<final text>","session_id":..};
# the ds seam writes that same shape itself. Normalize either to the grok
# shape (structuredOutput/text/sessionId) so the validator stays
# single-sourced. The last JSON object found in the final text is the receipt
# candidate; none found → validator exits 4 (fail-closed).
worker_extract_receipt() {
  local SRC="$RAW"
  if [ "$WORKER" = "cursor" ] || [ "$WORKER" = "ds" ]; then
    SRC="$OUT_DIR/raw-$STAMP.normalized.json"
    python3 - "$RAW" "$SRC" <<'PY'
import json, sys
raw_path, out_path = sys.argv[1], sys.argv[2]
with open(raw_path, encoding="utf-8") as f:
    env = json.load(f)
text = env.get("result") or ""
dec = json.JSONDecoder()
last, i = None, 0
while True:
    j = text.find("{", i)
    if j == -1:
        break
    try:
        obj, end = dec.raw_decode(text, j)
    except json.JSONDecodeError:
        i = j + 1
        continue
    if isinstance(obj, dict):
        last = obj
    i = end
norm = {"structuredOutput": last, "text": text, "sessionId": env.get("session_id")}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(norm, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
  fi
  python3 "$SCRIPT_DIR/dispatch_receipt.py" "$SRC" "$SCHEMA" "$RECEIPT"
}

case "$WORKER" in
  ds)     echo "[dispatch] worker:  ds ($DS_MODEL)" ;;
  cursor) echo "[dispatch] worker:  cursor (${MODEL:-cursor-grok-4.6-high})" ;;
  grok)   echo "[dispatch] worker:  grok (${MODEL:-default}, effort $EFFORT)" ;;
esac
echo "[dispatch] ticket:  $TICKET_ABS"
echo "[dispatch] raw:     $RAW"
echo "[dispatch] receipt: $RECEIPT"

# Load-bearing set +e / set -e: a nonzero grok must survive errexit to reach
# the tripwire and the graceful "grok exited $GROK_EXIT" branch.
set +e
worker_invoke
GROK_EXIT=$?
set -e

# --- post-flight tripwire ---------------------------------------------------
# Working-tree pollution (outside dispatch artifacts) = hard fail: the worker
# wrote files into the dispatching checkout.
if [ "$(git status --porcelain "${STATUS_PATHSPEC[@]}")" != "$BASE_STATUS" ]; then
  echo "[dispatch] ISOLATION BREACH: files changed in the dispatching checkout." >&2
  echo "           Inspect immediately; do not trust the delivery." >&2
  exit 2
fi
# HEAD movement = loud warning, not failure: the commander may legitimately
# commit while workers run, but a worker escaping its worktree also lands
# commits here (incident #1). The referee must eyeball the listed commits.
if [ "$(git rev-parse HEAD)" != "$BASE_HEAD" ]; then
  echo "[dispatch] WARNING: HEAD moved during the run. New commits:" >&2
  git log --format='           %h %s' "$BASE_HEAD..HEAD" >&2
  echo "           If any of these are not yours, treat as an isolation breach." >&2
fi

if [ "$GROK_EXIT" -ne 0 ]; then
  echo "[dispatch] $WORKER exited $GROK_EXIT; envelope (if any) at $RAW" >&2
  exit "$GROK_EXIT"
fi

worker_extract_receipt
# Session id lives on the envelope (grok: sessionId, cursor: session_id);
# the extractor does not print it.
python3 -c 'import json,sys; e=json.load(open(sys.argv[1])); print("[dispatch] session:  " + str(e.get("sessionId") or e.get("session_id") or "?"))' "$RAW"

echo "[dispatch] done. Referee checklist: review diff on $WT_BRANCH,"
echo "           re-run acceptance commands in $WT_PATH independently,"
echo "           then merge or reject. Cleanup after merge:"
echo "           git worktree remove '$WT_PATH' && git branch -d '$WT_BRANCH'"
