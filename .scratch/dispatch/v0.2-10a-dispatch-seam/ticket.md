# Ticket: v0.2-10a — Dispatch bridge: isolate the two grok seams + commander-side receipt validation

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

`scripts/dispatch.sh` is the M0 commander→worker bridge: it isolates a worker
in a fresh git worktree, invokes the worker CLI, and extracts a
schema-constrained JSON receipt. The v0.2 design ruling
`docs/agents/dispatch-and-governance.md` Part A (committed in your worktree —
read it, especially the 2026-07-12 "Audit revisions" block) decided (paraphrased):

- Refactor the two grok-hardcoded seams into `worker_invoke` /
  `worker_extract_receipt` behind a minimal worker contract (a/b/c + (d)
  fully non-interactive); only grok is wired; a registry is YAGNI-deferred.
- Add **commander-side receipt validation** against
  `scripts/receipt.schema.json` — validation failure = delivery rejected,
  independent of any worker's native schema support. (The ruling's word was
  "jsonschema validation"; the *intent* is "validate the receipt against the
  schema, commander-side" — a stdlib structural checker satisfies it.)

This ticket implements exactly that — a **behavior-preserving** refactor of
the grok path plus the new validation gate. Do not change the isolation, the
tripwire, the SIGPIPE trap, or the worktree/branch mechanics — those are
battle-tested and stay byte-for-byte in behavior.

Current code facts (verified at this base):
- `scripts/dispatch.sh` — the grok-specific seams are: (1) the
  `CMD=(grok --prompt-file … --cwd … --output-format json --json-schema …
  --permission-mode auto --reasoning-effort … --max-turns …)` array +
  `--best-of-n`/`--model` appends + the invocation, wrapped in a
  **load-bearing** `set +e` / `set -e` guard:
  `set +e; "${CMD[@]}" > "$RAW"; GROK_EXIT=$?; set -e` — under the top-level
  `set -euo pipefail` this guard lets a NON-ZERO grok exit survive errexit and
  reach the tripwire + the graceful `grok exited $GROK_EXIT` branch. A naive
  `worker_invoke; GROK_EXIT=$?` would errexit-die on a nonzero grok. (2) the
  inline `python3 - "$RAW" "$RECEIPT" <<'PYEOF' … PYEOF`
  heredoc that reads `envelope["structuredOutput"]` (with a `text`
  concat-decode fallback) and writes the receipt. Everything else
  (STATUS_PATHSPEC, worktree add, post-flight tripwire `exit 2`, HEAD-moved
  warning, `trap '' PIPE`) is worker-agnostic and must stay.
- `scripts/receipt.schema.json` — draft-07 schema; top-level `required` =
  ticket_id, status, summary, branch, commit, worktree_path, files_changed,
  self_test, deviations, open_questions; `status` enum = done/partial/
  blocked/failed; `files_changed[]` require path/action(enum added/modified/
  deleted)/purpose with `additionalProperties:false`; `self_test[]` require
  cmd/exit_code(integer) + optional output_tail; top-level
  `additionalProperties:false` (only `notes_for_referee` is the extra
  allowed optional).
- Validation must be **dependency-free** (stdlib only): dispatch.sh must stay
  runnable with zero pip installs on a bare `python3`, so it must not *depend*
  on `jsonschema` even where a given machine happens to have it — a fresh
  clone, a CI runner, or a different worker environment may not. Do NOT add a
  `jsonschema` import or any pip dependency; hand-roll a stdlib structural
  checker.

## Hard constraints (project iron laws — violations = rejected delivery)

1. No backtesting; no idea generation; no `court/` or market changes.
2. Behavior-preserving for the grok path: a real grok dispatch must produce
   the same worktree/branch/tripwire/receipt behavior as today. The two
   seams move into functions; their logic is unchanged except the added
   validation step.
3. Fail-closed: an invalid or missing receipt = non-zero exit + a clear
   stderr message; never write a malformed receipt and report success.
4. **Dependency-free** validation (stdlib `json` only; no jsonschema, no pip).
5. Code, docstrings, comments: English.
6. TDD contractual: failing tests FIRST (red run recorded in the receipt
   `self_test`), then green.
7. File ownership — you may modify ONLY: `scripts/dispatch.sh`;
   (new) `scripts/dispatch_receipt.py`; `docs/agents/worker-bridge.md`;
   (new) `tests/test_dispatch_receipt.py`. Nothing else.

## Task

### 1. Extract receipt handling into a testable, dependency-free script

Create `scripts/dispatch_receipt.py` (stdlib only) with a CLI:
`python3 scripts/dispatch_receipt.py <raw_envelope.json> <schema.json>
<receipt_out.json>`. It must:
- **extract** the receipt: `envelope["structuredOutput"]` if it is a dict;
  else the `text` concat-decode fallback (the existing loop that
  `raw_decode`s successive JSON objects and keeps the last dict) — preserve
  this fallback exactly;
- if no dict receipt is found → **exit 4** with a stderr message naming the
  raw path (matches today's `no structured receipt found`);
- **validate** the extracted receipt against `<schema.json>` with a
  dependency-free structural checker covering: every top-level `required`
  key present; `status` ∈ the enum; `type` checks for each property
  (string/array/object/integer as the schema says); `files_changed[]` and
  `self_test[]` item required-keys + enums + no unexpected keys
  (`additionalProperties:false`); top-level no-unexpected-keys except
  `notes_for_referee`. On ANY violation → **exit 3** with a stderr message
  naming the first failing path (e.g. `receipt invalid: status
  'finished' not in [done, partial, blocked, failed]`). Read the schema at
  runtime. The full construct set this schema uses, ALL of which the checker
  must enforce (not just the top-level required list): top-level `required` +
  `enum` (status) + `properties[].type` + top-level `additionalProperties:false`
  (only `notes_for_referee` extra); **array `items.type`** for `deviations` /
  `open_questions` (each element a string) and **`items` is an object** for
  `files_changed` / `self_test`; and for those object-item arrays, the item
  `required` keys + `action` enum + item `additionalProperties:false`. Do not
  hard-code the required list in a way that drifts from `receipt.schema.json`
  (parse it at runtime). Raise on any schema construct you did NOT implement
  rather than passing silently).
- on success (exit 0): write the pretty receipt to `<receipt_out.json>`
  (`json.dump(..., indent=2, ensure_ascii=False)`) and print the same
  `[dispatch] status/branch/commit/worktree` summary lines dispatch.sh
  prints today (keep `session` printing in dispatch.sh, which has the
  envelope's sessionId).

### 2. Refactor dispatch.sh's two seams into functions

- `worker_invoke` — wraps building the `CMD` array (grok + all its flags,
  incl. the `--best-of-n`/`--model` appends) and running it to `"$RAW"`,
  returning grok's exit code **WITHOUT letting a nonzero exit errexit-kill the
  script** (keep the `set +e` / `set -e` semantics — inside the function, or
  call it as `worker_invoke || GROK_EXIT=$?`). A nonzero grok must still reach
  the tripwire and the existing `if [ "$GROK_EXIT" -ne 0 ]` graceful branch. A
  one-line comment marks it the grok-specific seam (a second worker later = a
  second `worker_invoke` branch, not a rewrite).
- `worker_extract_receipt` — calls `python3 scripts/dispatch_receipt.py
  "$RAW" "$SCHEMA" "$RECEIPT"`; **its non-zero exit fails the dispatch**
  (propagate exit 3/4 as a hard failure with the tool's message; do not
  swallow it). dispatch.sh then prints the `session` line (it has
  `sessionId` from the envelope — read it from `"$RAW"` with a one-line stdlib
  `python3 -c` (the envelope is read twice — harmless); the extractor does NOT
  print the session line).
- Everything else (STATUS_PATHSPEC, `git worktree add`, the `set +e`/`set -e`
  guard around the invocation, the `if [ "$GROK_EXIT" -ne 0 ]` block, the post-flight
  tripwire `exit 2`, the HEAD-moved warning, `trap '' PIPE`, the final
  referee-checklist echo) stays byte-for-byte.
- The minimal worker contract goes in a header comment: a worker (a) takes a
  self-contained prompt file, (b) works in a commander-created isolated
  worktree pinned by a cwd flag, (c) returns a receipt conforming to
  `receipt.schema.json`, (d) runs fully non-interactively.

### 3. `docs/agents/worker-bridge.md` — "Worker generalization" section

Add a section documenting the two-seam design, the four-point worker
contract (a–d), the commander-side dependency-free validation (and why:
independent of worker native schema support), and that grok is the only
wired worker (registry deferred, YAGNI). Reconcile the existing 3-point
contract summary already in `worker-bridge.md` (the v0.2-ruling paragraph,
which lacks (d) non-interactive) so the doc carries ONE consistent a–d
contract, not two.

### 4. Tests (red first; new `tests/test_dispatch_receipt.py` only)

Drive `scripts/dispatch_receipt.py` as a subprocess (or import its functions)
against fixtures written to `tmp_path` — do NOT call grok, do NOT run
`dispatch.sh` end-to-end (no live worker). Cover:
- a **valid** envelope → exit 0, receipt written, summary printed. Use a
  committed real envelope as the fixture:
  `.scratch/dispatch/v0.2-09-aggregation-policy/raw-20260713-160854.json`
  (its `structuredOutput` is a conforming receipt — copy it to tmp, or read
  it directly read-only);
- `structuredOutput` absent but a valid receipt in the `text`
  concat-decode fallback → exit 0 (build this envelope in the test);
- no receipt anywhere → exit 4;
- receipts that each violate ONE rule → exit 3, message names the rule:
  missing a required key; `status` not in enum; `self_test` item missing
  `exit_code`; `files_changed` item with a bad `action` enum; a top-level
  unexpected key (not `notes_for_referee`); `exit_code` a string not int.
- a valid receipt WITH `notes_for_referee` → exit 0 (the one allowed extra).

## Acceptance criteria (the referee re-runs these independently)

1. `bash -n scripts/dispatch.sh` → exit 0 (syntax) — and
   `bash -n` on any new shell you add
2. `python3 -m pytest tests/test_dispatch_receipt.py -v` → exit 0; ≥ 8 tests
   including the valid-envelope, the text-fallback, the no-receipt (exit 4),
   and at least four distinct exit-3 violation tests
3. `python3 scripts/dispatch_receipt.py
   .scratch/dispatch/v0.2-09-aggregation-policy/raw-20260713-160854.json
   scripts/receipt.schema.json /tmp/r.json` → exit 0 and `/tmp/r.json`
   is a valid receipt (this proves the real path works on a real envelope)
4. `python3 -m pytest` → exit 0 (nothing else regresses; note the full suite
   is ~30 min — run once at the end)
5. `python3 -m ruff check scripts/dispatch_receipt.py tests/test_dispatch_receipt.py`
   → exit 0 (ruff is reachable via base `python3 -m ruff` on this machine; run
   it). The two new .py files must be ruff-clean; do not touch `.scratch/`. Only
   if `python3 -m ruff` genuinely errors as unavailable, record that and skip —
   do not add a dep or use it as an excuse to skip a reachable ruff.
6. Before your FIRST commit, `BASE=$(git rev-parse HEAD)`; then
   `git diff --stat $BASE..HEAD` touches ONLY the four files of constraint 7
7. TDD evidence in the receipt: at least one recorded pytest command with a
   non-zero exit code from the red phase, before the green run

## Out of scope

- A second worker / a worker registry (YAGNI — deferred by the ruling).
- Any change to isolation, tripwire, SIGPIPE trap, worktree mechanics, or the
  grok flag set (beyond moving it into `worker_invoke`).
- Adding `jsonschema` or any pip dependency.
- Live end-to-end dispatch tests (no grok call in tests).

## Delivery protocol

1. Fresh git worktree; work here only.
2. Run the AC commands; record each command + real exit code in the receipt.
   Honest `partial` beats dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-10a: dispatch two-seam
   refactor + dependency-free commander-side receipt validation"`.
4. Final output = ONLY the JSON receipt. Gather: `branch`=`git branch
   --show-current`, `commit`=`git rev-parse HEAD`, `worktree_path`=`pwd`,
   `ticket_id`=`v0.2-10a`. In `notes_for_referee`, **state which blocks moved
   byte-for-byte** (the `CMD` grok flag set, the tripwire `exit 2` block,
   `trap '' PIPE`, the worktree/branch mechanics, the `set +e`/`set -e` guard)
   and which lines you changed — the behavior-preserving claim is otherwise
   only checkable by the referee reading the diff.

## Operational notes

- Write files incrementally. No command here is long except the full pytest.
- `dispatch.sh` must remain runnable on a bare system `python3` — verify your
  `dispatch_receipt.py` uses only the standard library.
