# Ticket: v0.1-08a — court/ledger.py: append-only trial ledger

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus two repo documents
it names as authoritative (they are in your worktree; read them in full).

## Context

alpha-court is a "statistical court" for quantitative factor research: it
consumes return/IC series and rules on whether an apparent alpha should be
believed. The **trial ledger** is the court's single source of evidence: an
append-only audit log of hypotheses, trials, and verdicts, stored as a
single-file JSONL event log. You are implementing it as `court/ledger.py`,
test-first.

Authoritative documents (read BOTH in full before writing any code):

1. `docs/design/court-kernel-spec.md` — the implementation spec. Your
   contract is §3 (global conventions, fail-closed error semantics), §4
   rulings B1–B10 (ledger decisions), §5.7 (record types, API signatures,
   fail-closed table), §7 (the test_ledger.py rows of the pytest plan).
2. `docs/design/trial-ledger.md` — the underlying design contract (record
   semantics §5, JSONL storage invariants §6, API layers §7). The spec
   implements this contract and never overrides it.

Key contract points, restated (the documents remain authoritative):

- Three record types (`HypothesisRecord`, `TrialRecord`, `VerdictRecord`) as
  frozen dataclasses; a trial is assembled from a registration event plus at
  most one evaluation event. No derived statistics are ever stored on a trial.
- Status is derived, never stored: `registered` → `evaluated` → `judged`
  (appears in ≥1 verdict's decisions). There is NO `abandoned` state.
- Storage: `ledger.jsonl`, one JSON object per line, envelope
  `{"type": ..., "at": ..., ...payload}`, `type` ∈ {hypothesis, trial,
  evaluation, verdict}. The envelope `at` IS the record timestamp. Every
  append: `json.dumps(..., allow_nan=False)` + newline + flush + fsync before
  returning. IDs are zero-padded sequential per type (`h-000001`, `t-000001`,
  `v-000001`) in event order.
- Replay on open: mid-file unparseable line or invariant violation (unknown
  reference, duplicate evaluation) → `LedgerCorruptionError(RuntimeError)`.
  A torn FINAL line is truncated from the file (fsync) and ignored.
- `matrix(trial_ids)` → `(index, float64 T×N ndarray)`, columns in argument
  order; every trial's series index must be identical label-for-label,
  otherwise raise — never outer-join, resample, or reorder.
- Everything fails closed: any violated precondition raises `ValueError`
  (corruption raises `LedgerCorruptionError`); never repair, coerce, or drop.
  The complete raise-condition table is spec §5.7 — implement every row.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality; do NOT build factor generation.
2. `court/` imports only: Python stdlib, numpy, pandas, scipy. No qlib, no
   market-specific anything. `tests/test_smoke.py` enforces this — keep it green.
3. The ledger layer understands NO statistics: no SR, no p-values, no imports
   from other court modules. Bookkeeping only.
4. Files you may create/modify: `court/ledger.py`, `tests/test_ledger.py` —
   NOTHING else. In particular do not touch `court/__init__.py` (reserved for
   ticket v0.1-08f), other `court/*.py`, docs, or config files.
5. Code, docstrings, comments: English. Docstrings cite the contract sections
   they implement (e.g. "trial-ledger.md §6 invariant 3").
6. TDD is contractual: write `tests/test_ledger.py` FIRST from the behavioral
   rows in spec §7 (test_ledger.py rows: contract behavior, storage/replay,
   matrix alignment, every guard row), run it to confirm it fails, then
   implement `court/ledger.py` to green. State in your receipt notes that
   tests were written first.

## Task

1. Write `tests/test_ledger.py` covering, at minimum:
   - register → record → append_verdict happy path; status derivation through
     all three states; series stored by value and returned intact.
   - Physical line order: a trial's `trial` line precedes its `evaluation`
     line in the file.
   - Fail-closed: every row of the spec §5.7 raise table (unknown ids,
     duplicate evaluation, length mismatch, empty series, duplicate index
     labels, non-finite values, bad declared protocol including
     `newey_west` without lags and `lags` with `iid`, non-JSON-serializable
     spec/params, bad decisions values, empty scope, matrix misalignment).
   - Persistence: close + reopen replays to equal records; torn final line is
     discarded and the next append works; mid-file corruption raises
     `LedgerCorruptionError`; duplicate evaluation on replay raises
     `LedgerCorruptionError`.
2. Implement `court/ledger.py` per spec §5.7: `SeConvention`, `Window`,
   `DeclaredProtocol`, `Series`, `HypothesisRecord`, `TrialRecord`,
   `VerdictRecord`, `LedgerCorruptionError`, `Ledger` with the exact method
   signatures given there.
3. Make the full suite pass (`pytest`), including the existing smoke tests,
   and `ruff check .` clean.

## Acceptance criteria

Run from the repo root; record real exit codes:

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_ledger.py -v` → exit 0, ≥ 15 tests passed
3. `.venv/bin/python -m pytest` → exit 0 (smoke tests still green)
4. `.venv/bin/ruff check .` → exit 0
5. `git show --stat HEAD` lists only `court/ledger.py` and
   `tests/test_ledger.py`
6. `git status --porcelain` after your final commit → empty

## Out of scope

- Any statistic (SR, p, DSR, PBO, FDR, noise) — other tickets own those.
- The judge orchestrator and `court/__init__.py` exports (ticket v0.1-08f).
- Concurrent writers, non-JSONL backends, enforcement hooks (v0.2).

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.1-08a: trial ledger"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-08a`

## Operational note (added after a failed first dispatch)

The first attempt at this ticket died with a `max_tokens_truncation` error —
almost certainly from emitting one very large file in a single response.
Write files INCREMENTALLY: create `court/ledger.py` section by section
(several smaller edits rather than one giant write), and keep each individual
response well under the output ceiling. Same for the test file. Functional
requirements are unchanged.
