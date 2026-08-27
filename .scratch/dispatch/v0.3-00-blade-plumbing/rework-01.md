# Rework 01 for v0.3-00 — blade plumbing hardening (batch)

You are the same worker session that delivered v0.3-00 (commit f9297ebf in
this worktree). The referee panel (3 adversarial lenses, probe-verified)
ACCEPTED the delivery's core and orders ONE batched rework. Attribution up
front: **R1's root cause is contract under-specification (commander fault —
the ticket never specified the JSON boundary); no worker-fault findings.**
R2–R7 are hardening items batched per proportionality discipline. You may
dispute any attribution in your receipt's `deviations`/`open_questions`.

Work in THIS worktree, on the current branch, on top of f9297ebf.

## R1 (MAJOR) — JSON-boundary pre-check before ANY append; atomic report batch

Referee evidence (verbatim):

> "np.int64 in report stats -> ValueError : declaration payload is not
> JSON-serializable: Object of type int64 is not JSON serializable | status:
> registered | blade_reports already on chain: 1 (partial: good's report
> appended, npint's lost)."
> "retrying evaluate() then writes DUPLICATE blade_reports permanently onto
> the append-only chain … after fixing bad blade and retrying:
> blade_reports=[good, good, bad] (n=3)."

The trigger is realistic: tickets 1–3 blades compute numpy statistics
(np.int64 counts, np.bool_ comparisons, NaN correlations on degenerate
series). `court/ledger.py` append uses `json.dumps(..., allow_nan=False)`.

Fix (frozen):
1. In `_apply_blades`, after the existing validate/name checks and BEFORE the
   first `append_declaration`, serializability-check EVERY report in the
   batch: `json.dumps(report, allow_nan=False)`; on failure raise
   `CertificationError` naming the offending blade (chain from the
   underlying error). Result: the append loop can no longer fail on payload
   content — the batch is all-or-nothing in practice.
2. Belt-and-braces: wrap the append loop so an unexpected `ValueError` from
   `append_declaration` surfaces as `CertificationError` (error taxonomy:
   blade-protocol failures are certification failures, run.py:61-67).

Tests: np.int64 in statistics → `CertificationError`, ZERO blade_reports on
chain, trial stays `registered`; NaN in statistics → same; after replacing
the bad blade, a retry produces exactly ONE clean report set (no duplicates).

## R2 (minor) — blade protocol violations → CertificationError, not bare AttributeError

> "P8: 'ESCAPED AS AttributeError: NamelessBlade object has no attribute
> name'"

Validate the roster up front (at attach time in `__init__` — earliest): every
blade must expose a non-empty-str `.name` and a callable `.run`; violation →
`CertificationError` (from `create`/`open` call). Test both.

## R3 (minor) — screened trials are terminal on the certified path

> "P2: reports for B after 1st/3rd evaluate: 1 / 3 … P7 (post-judge
> re-evaluate): … reports for B: 2 | verify PASSES with blade_report AFTER
> judgment declaration."

With R1's atomicity, on-chain blade_reports for a trial == a completed blade
pass; a completed pass that left the trial `registered` == screened. Fix:
`evaluate(trial_id)` where status is `registered` AND ≥1 blade_report
declaration exists for that trial_id → `CertificationError` ("trial was
screened; re-evaluation refused"). Test: second evaluate raises, report
count unchanged; include a post-judge attempt.

## R4 (minor) — duplicate blade names refused

Two attached blades sharing a name make reports unattributable and the
screen decision ambiguous. Refuse at attach time (`CertificationError`).
Test.

## R5 (minor) — empty roster == no roster

`blades=[]` currently enters `_apply_blades` and demands calibration though
nothing runs. Normalize: an empty sequence is stored as `None` (no blade
machinery). Test: `create(..., blades=[])` + evaluate records fine without
any calibration on chain.

## R6 (minor) — calibration uniqueness + report linkage

> "append_blade_calibration enforces no uniqueness … blade_report payloads
> carry no reference to the governing calibration declaration id."

Fix: (a) `append_blade_calibration` raises `ValueError` if a
`blade_calibration` declaration already exists on the ledger; (b) each
blade_report declaration payload gains `"calibration_id": <declaration_id of
the governing calibration>` as a sibling of `"trial_id"` (NOT inside
`report`). You will need the calibration record's id — extend the lookup
(keep `find_blade_calibration(ledger) -> dict | None` API; add a helper that
returns the record or id). Tests: payload carries the right id; second
calibration append refused.

## R7 (minor) — close the evidence-supply test gap + document two-phase semantics

The panel RULED your two-phase append (run+validate all → append all →
decide) an improvement within contract ambiguity — KEEP it, but:
(a) document the phase order and its atomicity rationale in
`_apply_blades`'s docstring;
(b) add the missing assertion that an UNFLAGGED executed blade leaves its
report on chain (the e2e test currently only checks trial B's flagged
report; assert trial A's flagged=False report exists too).

## Acceptance criteria (referee re-runs independently)

1. `python3 -m pytest tests/test_blades_harness.py -v` → exit 0.
2. `python3 -m pytest -q` → exit 0. Known environment caveat: 3 wall-clock
   perf tests (test_adapter_kernel_perf.py ×2, test_sharpe_perf.py ×1) can
   fail on a loaded machine and fail identically at base — if they fail,
   re-run just those three and report both results honestly.
3. `ruff check .` → exit 0.
4. Ownership unchanged: only `harness/blades.py`, `harness/run.py`,
   `tests/test_blades_harness.py` differ from f9297ebf.
5. New failing-first coverage for R1 (record a red run in the receipt).

## Delivery protocol

1. This worktree only; write files incrementally; act early, keep responses
   short.
2. Run every AC yourself; record real exit codes.
3. Commit: `git add -A && git commit -m "v0.3-00 rework-01: blade plumbing hardening (R1-R7)"`.
4. Final output = ONLY the JSON receipt validating against this schema:

```json
{"type":"object","required":["ticket_id","status","branch","commit","worktree_path","summary"],"properties":{"ticket_id":{"type":"string"},"status":{"type":"string","enum":["done","partial","failed"]},"branch":{"type":"string"},"commit":{"type":"string"},"worktree_path":{"type":"string"},"summary":{"type":"string"},"files":{"type":"array","items":{"type":"string"}},"commands":{"type":"array","items":{"type":"object","required":["command","exit_code"],"properties":{"command":{"type":"string"},"exit_code":{"type":"integer"},"summary":{"type":"string"}}}},"deviations":{"type":"array","items":{"type":"string"}},"open_questions":{"type":"array","items":{"type":"string"}}}}
```

`ticket_id` = `v0.3-00-rework-01`.
