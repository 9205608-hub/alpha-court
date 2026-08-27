# Ticket: v0.3-01 — gates/: base helpers + identity_degeneracy + pool_redundancy blades

You are a headless worker agent for the alpha-court project. This ticket is
self-contained. Do not invent scope beyond it.

## Context

v0.3 blade library, ticket 1 of 3 parallel blade tickets (the harness
plumbing shipped in v0.3-00, merged at your base). Frozen design (committed at
your base: `.scratch/v0.3/blades-design-draft-v2.md`) — the load-bearing
excerpts:

> **§2 common**: pure functions; report shape
> `BladeReport{blade, flagged, statistics, evidence, params}`; numpy/scipy
> only; each blade eats the trial's ONE declared series. Owner rulings:
> K=5 default (identity lag radius), thresholds come from pre-registered
> calibration (per-blade FPR 1%) — thresholds are INPUTS to blades, never
> hard-coded.
>
> **§2.1 identity_degeneracy**: transform family T = {lag k: |k| ≤ K}
> (identity = k=0; negate/rank are redundant under |spearman|). Statistic:
> max and second-max |spearman(x, lag_k(r))| over reference series r and
> lags k; flag ⇔ max ≥ rho_max. Effective hypothesis count =
> |refs| × (2K+1) — report it.
>
> **§2.2 pool_redundancy**: candidate vs pool members — max and top-5
> |pearson| AND |spearman| BOTH reported; flag ⇔ max (either measure) ≥
> rho_pool. Separate blade from 2.1 for attribution layering.

## Blade protocol (implemented in harness/blades.py at your base — read it)

- A blade is any object with `name: str` and
  `run(trial_id, spec, params, declared, series) -> dict` returning
  `{"blade": <name>, "flagged": bool, "statistics": dict, "evidence": dict,
  "params": dict}`.
- The report MUST be JSON-serializable with `allow_nan=False`: cast numpy
  scalars via `float()`/`int()`, never emit NaN (use `None` and say why in
  evidence). A non-serializable report is a harness `CertificationError`.
- `series` is duck-typed: `.index` = tuple[str, ...], `.values` =
  tuple[float, ...]. Do NOT import court or harness inside `gates/` modules
  (stdlib + numpy + scipy only). Blades never decide record/screen — the
  harness resolves effects from the trial spec.
- EVERY executed blade leaves a report, flagged or not: statistics carries
  the numbers, evidence carries human-auditable pointers (which ref, which
  lag, overlap size…).

## Task

1. `gates/base.py` — shared helpers for this and sibling blade tickets are
   NOT the goal; keep base minimal and strictly what these two blades need:
   - `align(series_a_index, series_a_values, series_b_index, series_b_values)
     -> (np.ndarray, np.ndarray)`: inner-join on index labels (order by
     series_a's index order), returns aligned value arrays.
   - `make_report(blade, flagged, statistics, evidence, params) -> dict` —
     assembles the protocol dict, casting all numpy scalars to Python types
     (deep cast; raise ValueError on NaN rather than emitting it).
2. `gates/identity_degeneracy.py` — class `IdentityDegeneracyBlade`:
   - `__init__(self, refs: dict[str, tuple[tuple[str, ...], tuple[float, ...]]],
     rho_max: float, k: int = 5, min_overlap: int = 30)` — refs maps ref name
     → (index, values). Validate: rho_max in (0,1); k ≥ 1; refs non-empty.
   - `name = "identity_degeneracy"`.
   - `run(...)`: for every ref r and every lag |k'| ≤ k, lag-shift r (shift
     VALUES against the aligned index positions; drop the non-overlapping
     ends), require ≥ min_overlap aligned points, compute
     |spearman| (scipy.stats.spearmanr). Track max and second-max with their
     (ref, lag). Pairs below min_overlap are skipped and COUNTED in evidence
     (`n_skipped_insufficient_overlap`). A degenerate pair (constant series →
     spearman NaN) is skipped and counted (`n_skipped_degenerate`), never
     emitted as NaN. If ALL pairs were skipped: flagged=False, statistics
     `max_abs_spearman=None`, evidence explains. Otherwise flag ⇔ max ≥
     rho_max. statistics: max_abs_spearman, second_max_abs_spearman,
     argmax_ref, argmax_lag, n_pairs_evaluated, n_effective_hypotheses
     (=len(refs)×(2k+1)). params: {rho_max, k, min_overlap, n_refs}.
3. `gates/pool_redundancy.py` — class `PoolRedundancyBlade`:
   - `__init__(self, pool: dict[str, tuple[tuple[str, ...], tuple[float, ...]]],
     rho_pool: float, min_overlap: int = 30)`; `name = "pool_redundancy"`.
   - `run(...)`: candidate vs每 pool member at lag 0 only: |pearson|
     (scipy.stats.pearsonr) AND |spearman| both. statistics: max_abs_pearson,
     max_abs_spearman, top5 lists [(member, value), …] for BOTH measures,
     n_members_evaluated. Same skip/count rules as 2.1. Flag ⇔
     max(max_abs_pearson, max_abs_spearman) ≥ rho_pool.
4. Update `gates/__init__.py` docstring + export the two blade classes.
5. `tests/test_gates_identity_pool.py` — red-first TDD:
   a. Hand-built vectors: candidate == lagged copy of a ref (lag 2) →
      identity blade max ≈ 1 at (that ref, 2), flagged with rho_max=0.9;
      independent noise (seeded) → not flagged.
   b. Second-max correctness on a case with two related refs.
   c. min_overlap: overlap 29 → skipped+counted; all-skipped → flagged=False
      with None statistic.
   d. Constant ref (spearman undefined) → skipped, not NaN, report still
      JSON-serializable (`json.dumps(report, allow_nan=False)` passes).
   e. pool blade: pearson-vs-spearman divergence case (monotone nonlinear
      relation: spearman high, pearson lower) → both reported, flag on
      EITHER crossing rho_pool.
   f. Integration smoke (tests may import harness/court): CertifiedRun with
      calibration declared + IdentityDegeneracyBlade attached; a planted
      lag-copy trial with spec `{"blades": {"identity_degeneracy":
      {"on_flag": "screen"}}}` ends `registered` with flagged report on
      chain; an innocent trial records. Crib fixtures from
      `tests/test_blades_harness.py` (copy, don't import).
   g. Determinism: same inputs → identical report dict twice.

## Hard constraints (iron laws — violations = rejected delivery)

1. `gates/` modules import ONLY stdlib + numpy + scipy. No court/harness
   imports in gates/ (tests may import them).
2. Statistical routines via scipy public API with the reference named in the
   docstring (Spearman rank correlation — scipy.stats.spearmanr; Pearson —
   scipy.stats.pearsonr). No hand-rolled correlation implementations.
3. Thresholds (rho_max/rho_pool) are constructor inputs — never defaulted,
   never hard-coded (calibration owns the values; per-blade FPR 1% is
   calibration policy, not code).
4. Determinism; English code/docstrings/comments; TDD red run recorded.
5. File ownership — modify/create ONLY: `gates/__init__.py`, `gates/base.py`,
   `gates/identity_degeneracy.py`, `gates/pool_redundancy.py`,
   `tests/test_gates_identity_pool.py`. Do NOT touch harness/, court/,
   adapters/, scripts/, other gates files (sibling tickets own
   magnitude_vs_turnover / single_year_luck), or any other test.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m pytest tests/test_gates_identity_pool.py -v` → exit 0.
2. `python3 -m pytest -q` → exit 0. Known environment caveat: 3 wall-clock
   perf tests (test_adapter_kernel_perf.py ×2, test_sharpe_perf.py ×1) can
   fail on a loaded machine and fail identically at base — if they fail,
   re-run just those three and report both results honestly.
3. `ruff check .` → exit 0.
4. TDD: at least one red-phase pytest (non-zero exit) recorded in receipt.
5. Ownership: record `BASE=$(git rev-parse HEAD)` before first commit;
   `git diff --stat $BASE..HEAD` touches ONLY the five files in constraint 5.

## Out of scope

- magnitude_vs_turnover / single_year_luck (sibling tickets, in flight now —
  ownership is disjoint by design; do not "helpfully" add shared helpers for
  them into base.py).
- Threshold calibration (ticket 3 owns the script; family-level calibration
  comes later).
- Any harness/court change; any IC+returns dual-trial logic (v0.4).

## Delivery protocol

1. Fresh git worktree; work here only; write files incrementally; act early,
   keep responses short.
2. Run every AC yourself; record real exit codes. Honest `partial` beats
   dishonest `done`.
3. Commit ALL work:
   `git add -A && git commit -m "v0.3-01: identity_degeneracy + pool_redundancy blades + gates base"`.
4. Final output = ONLY the JSON receipt (schema appended below by the
   dispatch bridge). `ticket_id` = `v0.3-01`.
