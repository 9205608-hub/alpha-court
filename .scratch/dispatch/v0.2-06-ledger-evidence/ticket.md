# Ticket: v0.2-06 — Ledger evidence layer: source_ref, attestation, hash chain, declaration/seal events

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court v0.1 shipped `court/` — a pure statistical-court kernel with an
append-only JSONL trial ledger (`court/ledger.py`, you wrote most of it in
ticket v0.1-08a). v0.2 adds a **pre-registration gate**: a `harness/` certified
path (ticket 07, NOT this ticket) that makes it impossible for a factor-mining
agent to fool itself on the certified path. That gate needs an **evidence
layer inside the ledger** — this ticket. You are the sole owner of every
`court/` change in v0.2; ticket 07 builds on what you deliver and cannot touch
`court/`.

The authoritative design contract is `docs/design/prereg-gate.md` (v3,
committed in your worktree) — read §3 (architecture), §4 (hash chain & seal),
§5 (fail-closed semantics), §7 (your ticket's bullet). The ledger contract is
`docs/design/trial-ledger.md`; the kernel spec (exact current API, record
types, fail-closed table) is `docs/design/court-kernel-spec.md` §5.7. The
issue file is `.scratch/v0.2/issues/06-ledger-provenance.md` (including its
2026-07-12 audit-amendment section, which this ticket supersedes-and-details).
All are committed in your base — cited sections are binding; where this ticket
pins something more precisely, this ticket wins.

Current code facts (verified): `Ledger._append_event` (court/ledger.py:404)
serializes with `json.dumps(event, allow_nan=False, separators=(",", ":"))`
(insertion order, default `ensure_ascii=True`) + newline + flush + fsync.
`register()` hard-codes `"source_ref": None` and has no parameter for it.
`record(trial_id, series)` takes no attestation. Event vocabulary is
{`hypothesis`, `trial`, `evaluation`, `verdict`}; envelope is
`{"type": ..., "at": ..., ...payload}`; IDs are zero-padded sequential per
type (`h-`/`t-`/`v-`). Torn final line is truncated (+fsync) on open; mid-file
corruption raises `LedgerCorruptionError`.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality.
2. Do NOT build idea/factor generation logic.
3. `court/` must not import any market-specific code or library (no qlib, no
   exchange calendars, no universe definitions; the existing decoupling smoke
   test must stay green). stdlib + numpy/pandas/scipy only — this ticket needs
   only stdlib (`hashlib`, `struct`, `json`).
4. Fail-closed everywhere: violated preconditions raise (`ValueError` for
   caller errors, `LedgerCorruptionError` for corrupt evidence). Never repair,
   coerce, or silently drop.
5. Code, docstrings, comments: English.
6. TDD is contractual: write the failing tests FIRST, run them RED, then
   implement to green. The referee reads your test-first evidence in the
   receipt (`self_test` entries with real exit codes showing the red run).
7. File ownership boundary: you may modify ONLY `court/ledger.py`,
   `tests/test_ledger.py`, and (new) `tests/test_ledger_chain.py`. Do NOT
   touch `court/judge.py` (ticket 08 owns it), `harness/` (ticket 07),
   `adapters/`, `examples/`, `docs/`, or any other test file.
8. Storage-line serialization of existing behavior is FROZEN: existing fields
   keep `json.dumps(..., allow_nan=False, separators=(",", ":"))` insertion
   order and default `ensure_ascii`; torn-write recovery semantics unchanged.
   The canonical serialization below exists ONLY on the hash path (ticket 12's
   torn-write semantics depend on this — prereg-gate.md §7).

## Task

### 1. `source_ref` reachability

`register(self, hypothesis_id, spec, params, declared, source_ref: str | None
= None)` — stored on the trial event, replayed into `TrialRecord.source_ref`,
round-trips across reopen. It stays a *pointer* (opaque string), never a meta
dump.

### 2. Attestation on `record`

`record(self, trial_id, series, attestation: dict | None = None)`.
When `attestation` is provided (fail-closed `ValueError` on violation):

- it must be JSON-serializable under `allow_nan=False`;
- keys `metric` and `window` are REQUIRED; `attestation["metric"] ==
  declared.metric`; `attestation["window"]` must be a mapping containing
  EXACTLY the keys `{"start", "end"}` and equal the trial's `declared.window`
  start/end strings;
- if key `n_evaluation_dates` is present, it must be a non-bool `int` equal
  to `len(series.values)`;
- all other keys are stored opaquely — the court never interprets them
  (universe/version checks belong to the harness, ticket 07, against the
  run_config declaration — NOT your job).

The attestation is stored on the `evaluation` event under key `attestation`
and replayed (expose it on the read surface: `TrialRecord` gains
`attestation: dict | None = None`). Replay applies the SAME attestation-vs-
declared checks; a hand-crafted evaluation event whose attestation violates
them raises `LedgerCorruptionError` (mirroring the duplicate-evaluation
precedent: caller error at write time, corrupt evidence at replay time). `attestation=None` stays legal
(uncertified calculator use).

### 3. Hash chain (prereg-gate.md §4.1, pinned here)

Every event line in a **chained** ledger carries two new fields, appended
last in insertion order: `prev_hash`, `event_hash`. Definition (binding):

```
content       = the stored event dict minus {"at", "prev_hash", "event_hash"}
                # "type" and the full payload ARE in content
content_hash  = sha256( canonical_json(content).encode("utf-8") ).hexdigest()
event_hash    = sha256( (prev_hash + content_hash).encode("ascii") ).hexdigest()
genesis       prev_hash = "0" * 64
```

`canonical_json(obj)`: FIRST recursively pre-transform the tree — every float
`x` is replaced by the string `struct.pack('<d', x).hex()` (note:
`json.dumps` never calls `default=` for floats, hence the pre-transform;
`bool` is not `float`, ints stay ints; NaN/Inf must be impossible here because
ledger finiteness/allow_nan guards run first) — THEN
`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False)`.

Write order per append: compute hashes → write the single complete line →
flush + fsync (ruling B4 unchanged). Never write a hashless line and patch a
hash in later.

Expose `Ledger.chain_head -> str | None`: the last event's `event_hash`;
for an EMPTY chained ledger it is the genesis `"0" * 64`; it is `None` ONLY
for legacy files (see 4) — the two signals never overlap.

**Chain verification on replay (open):** for a chained file, recompute the
chain from genesis; any mismatch — edited content, flipped `type`, inserted /
deleted / reordered MID-file line, wrong `prev_hash` linkage — raises
`LedgerCorruptionError`. Torn FINAL line (invalid JSON tail) keeps the v0.1
behavior: truncate + fsync, chain head = last intact event, subsequent
appends link to it.

**Honest boundary (do NOT "fix"; prereg-gate.md §6):** deleting a whole
suffix of intact lines is undetectable pre-seal by design. Write the test
that ASSERTS this passes replay (with a comment pointing at
`docs/design/prereg-gate.md` §6) so the boundary stays on the record.

### 4. Legacy compatibility (pinned ruling — homogeneous per file)

- The legacy/chained determination happens AFTER torn-final-line truncation;
  a file that is empty after truncation is **chained**.
- A ledger opened on a **new/empty file** is chained: every event carries
  hashes.
- An existing file whose FIRST event has no `event_hash` field is **legacy**:
  replay it without chain verification, `chain_head` is `None`, and — to keep
  files homogeneous — subsequent appends to it also carry NO hash fields.
  (The committed killer-demo ledger keeps replaying; ticket 08 regenerates it
  chained later.)
- A MIXED file (hashed and hashless events in either order) raises
  `LedgerCorruptionError`.

### 5. Two court-opaque event types: `declaration` and `seal`

- `append_declaration(self, payload: dict) -> str` — id `d-000001`, …;
  `append_seal(self, payload: dict) -> str` — id `s-000001` (at most one).
  Payload must be JSON-serializable under `allow_nan=False`; the court stores
  and replays it WITHOUT interpretation (no schema, no market semantics —
  the harness, ticket 07, interprets).
- Read surface: `declarations(self) -> list[DeclarationRecord]` and
  `seal(self) -> SealRecord | None` — frozen dataclasses with
  (`declaration_id`/`seal_id`, `payload: dict`, `created_at: str`). Event
  lines: `{"type": "declaration", "at": …, "declaration_id": …,
  "payload": {…}, …hash fields}` (seal analogous with `seal_id`).
- **Seal × torn line (pinned):** a torn trailing line is NOT an event; a torn
  tail after a seal is truncated exactly per v0.1 (trial-ledger invariant:
  the write never happened) — it is NOT a corruption error.
- **Seal semantics:** after a seal exists, EVERY mutating append
  (`register_hypothesis`, `register`, `record`, `append_verdict`,
  `append_declaration`, `append_seal`) raises `ValueError`. On replay: any
  event after a `seal` event, or a second `seal`, raises
  `LedgerCorruptionError` (the seal must be the final event —
  prereg-gate.md §5).
- Event types are orthogonal to chaining (they work on legacy files too;
  the harness will require chained — not your concern).
- Existing semantics (`status`, `trials`, `matrix`, `verdicts`, ID replay
  scanning) must be untouched for the existing event types; extend the ID
  scanner for `d-`/`s-`.

### 6. Tests (red first). `tests/test_ledger_chain.py` is MANDATORY (all
chain/seal/legacy/attestation tests live there; you may additionally extend
`tests/test_ledger.py` — AC-2 runs both files)

Cover at least: source_ref round-trip + default None; attestation
stored/replayed, each violation of §2 raises (metric mismatch, window
mismatch, n_evaluation_dates mismatch, missing metric/window key,
non-serializable), `attestation=None` legal; fresh ledger events carry
hashes and reopen verifies with a stable `chain_head`; determinism (same
content twice → same content hash); tamper mid-file content → raises; flip a
`type` → raises; reorder two mid-file lines → raises; delete a MID-file line
→ raises; suffix truncation PASSES replay (honesty test, comment required);
torn final line still truncates and the next append links correctly; legacy:
a copy of `examples/killer_demo/out/ledger.jsonl` replays fine,
`chain_head is None` (copy it to a tmp dir first — NEVER open the committed
file in place); appending to a legacy file stays hashless; mixed file raises;
declaration/seal round-trip; second seal raises; every mutating append after
seal raises; a hand-crafted file with an event after the seal raises on open.
All existing ledger tests must pass unmodified (behavioral contract is
frozen) — if one genuinely must change, report it under `deviations` with the
reason, do not silently edit assertions.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,demo]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_ledger.py tests/test_ledger_chain.py -v` → exit 0; ≥ 18 NEW tests beyond the v0.1 baseline, including the honesty-boundary test and the killer-demo legacy-replay test
3. `.venv/bin/python -m pytest` → exit 0 (qlib-dependent tests may skip; nothing else may fail — zero regressions)
4. `.venv/bin/ruff check .` → exit 0
5. Before your FIRST commit, record `BASE=$(git rev-parse HEAD)`. Then
   `git diff --stat $BASE..HEAD` touches ONLY `court/ledger.py`,
   `tests/test_ledger.py`, `tests/test_ledger_chain.py` (the referee re-runs
   this from your branch's fork point)
6. TDD evidence in the receipt: at least one recorded pytest command with a non-zero exit code from the red phase, before the green run

## Out of scope

- `harness/` Run/seal logic, run_config content, anchor backends, any
  verification CLI (ticket 07).
- `court/judge.py`, `VerdictRecord.role` (ticket 08).
- Interpreting declaration/seal payloads; universe/version conformance
  (ticket 07 against run_config).
- Regenerating `examples/killer_demo/out/` (ticket 08).
- Any refactor of storage serialization, ID scheme, or read surface beyond
  what is listed.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-06: ledger evidence layer (source_ref, attestation, hash chain, declaration/seal)"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.2-06`

## Operational notes

- Write files INCREMENTALLY (several smaller edits, never one giant emission
  — a v0.1 dispatch died of max_tokens_truncation on exactly this file).
- No command here should run longer than ~2 minutes except the full pytest
  (~2–4 min); if you must run anything longer, detach and poll.
- The venv in AC-1 is the only environment change allowed; never `pip install`
  outside it.
