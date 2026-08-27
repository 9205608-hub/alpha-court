# Ticket: v0.3-02 — gates/magnitude_vs_turnover blade (pure economic floor)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained. Do not invent scope beyond it.

## Context

v0.3 blade library, ticket 2 of 3 parallel blade tickets (harness plumbing
merged at your base). Frozen design excerpt
(`.scratch/v0.3/blades-design-draft-v2.md` §2.3, committed at your base):

> **§2.3 magnitude_vs_turnover（语义收缩）**: PURE economic-floor blade, NO
> significance semantics: net(c) = r_gross − c·tau; report break-even c* and
> a cost-grid table of net means. Flag condition: **E[net] ≤ 0 @ the
> spec-declared c_ref** (the old t_min concept is deleted; significance
> belongs entirely to the battery's FDR/noise gates).

This blade is deliberately dumb-simple economics: does the candidate's gross
mean survive its own turnover at a declared reference cost? It never judges
statistical significance.

## Blade protocol (implemented in harness/blades.py at your base — read it)

- A blade is any object with `name: str` and
  `run(trial_id, spec, params, declared, series) -> dict` returning
  `{"blade": <name>, "flagged": bool, "statistics": dict, "evidence": dict,
  "params": dict}`.
- Report MUST be JSON-serializable with `allow_nan=False`: cast numpy scalars
  via `float()`, never emit NaN (use `None` + explain in evidence).
- `series` duck-typed: `.index` tuple[str, ...], `.values` tuple[float, ...]
  (per-period gross returns of the candidate).
- No court/harness imports inside `gates/` modules (stdlib + numpy only;
  scipy allowed but this blade shouldn't need it). Blades never decide
  record/screen.
- Every executed blade leaves a report, flagged or not.

## Inputs contract (frozen)

- **turnover tau**: transparent scalar from `params["turnover"]` (the trial's
  registration params; per-period one-sided turnover fraction, tau ≥ 0).
- **c_ref**: from the trial spec,
  `spec.get("blades", {}).get("magnitude_vs_turnover", {}).get("c_ref")`
  (cost per unit turnover, same period units as returns).
- **cost_grid**: blade constructor input, tuple of floats ≥ 0 (the reporting
  grid; c_ref need not be in it).
- Missing/invalid `turnover` or `c_ref` (absent, non-numeric, negative tau):
  the blade CANNOT evaluate its economics — emit flagged=False with
  `statistics = {"evaluable": False, ...}` and evidence naming exactly what
  was missing/invalid. Never raise for missing inputs; raise ValueError only
  for constructor misuse (empty grid, negative grid entries).

## Task

1. `gates/magnitude_vs_turnover.py` — class `MagnitudeVsTurnoverBlade`:
   - `__init__(self, cost_grid: tuple[float, ...] = (0.0, 0.0005, 0.001,
     0.002, 0.005))`; validate entries finite, ≥ 0, strictly increasing.
   - `name = "magnitude_vs_turnover"`.
   - `run(...)`: r = series.values; statistics (all Python floats):
     `mean_gross`, `n_obs`, `turnover`, `c_ref`,
     `net_mean_grid` = [[c, mean_gross − c·tau], …] for the grid,
     `break_even_c` = mean_gross / tau (None when tau == 0 — evidence
     explains: zero-turnover candidate is never cost-killed; also None when
     mean_gross ≤ 0 with tau > 0? NO — a negative break-even is meaningful,
     report the signed value), `net_at_c_ref` = mean_gross − c_ref·tau.
     Flag ⇔ `net_at_c_ref ≤ 0`. Empty series (n_obs == 0) → evaluable=False
     path.
   - Docstring: state the net formula and that significance is out of scope
     by design (§2.3).
2. `tests/test_gates_magnitude.py` — red-first TDD:
   a. Hand vector: mean_gross = 10 bp, tau = 1.0, c_ref = 0.002 → net
      −10 bp → flagged; c_ref = 0.0005 → net +5 bp → not flagged. Exact
      arithmetic asserted (== on floats built from the same expressions).
   b. Grid table correctness (each row = c, mean − c·tau).
   c. break_even_c: positive case; tau=0 → None + not flagged regardless of
      c_ref; negative mean → negative break-even reported.
   d. Missing turnover / missing c_ref / negative tau → evaluable=False,
      flagged=False, evidence names the culprit; report passes
      `json.dumps(report, allow_nan=False)`.
   e. Constructor validation: empty grid, negative entry, non-increasing →
      ValueError.
   f. Integration smoke (tests may import harness/court): CertifiedRun +
      calibration declared + blade attached; a trial with params
      `{"turnover": 1.0}` and spec c_ref making net negative and
      `on_flag: "screen"` → ends `registered` with flagged report; same
      candidate with `on_flag` absent (default record, owner ruling OQ-B) →
      records. Crib fixtures from `tests/test_blades_harness.py` (copy, don't
      import).
   g. Determinism: identical report on repeat call.

## Hard constraints (iron laws — violations = rejected delivery)

1. `gates/` modules import ONLY stdlib + numpy (+scipy if truly needed). No
   court/harness imports in gates/ (tests may).
2. NO significance statistics in this blade (no t-stats, no p-values) — that
   is the design's explicit semantic contraction (§2.3 / adversarial-review
   MAJOR 7).
3. Determinism; English; TDD red run recorded.
4. File ownership — modify/create ONLY: `gates/magnitude_vs_turnover.py`,
   `tests/test_gates_magnitude.py`. Do NOT touch `gates/__init__.py`,
   `gates/base.py`, other gates files (sibling tickets v0.3-01/-03 own them
   and are in flight NOW), harness/, court/, scripts/, any other test.
   Import your class directly (`from gates.magnitude_vs_turnover import …`)
   — registration in `gates/__init__.py` happens in a later consolidation,
   not here.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m pytest tests/test_gates_magnitude.py -v` → exit 0.
2. `python3 -m pytest -q` → exit 0. Known environment caveat: 3 wall-clock
   perf tests (test_adapter_kernel_perf.py ×2, test_sharpe_perf.py ×1) can
   fail on a loaded machine and fail identically at base — if they fail,
   re-run just those three and report both results honestly.
3. `ruff check .` → exit 0.
4. TDD: at least one red-phase pytest (non-zero exit) recorded in receipt.
5. Ownership: record `BASE=$(git rev-parse HEAD)` before first commit;
   `git diff --stat $BASE..HEAD` touches ONLY the two files in constraint 4.

## Out of scope

- Turnover ESTIMATION (tau arrives as a declared transparent scalar; deriving
  it from positions/trades is adapter-side, not court/gates-side).
- Multi-cost optimization, capacity modeling, significance of net means.
- Sibling blades and gates/__init__.py registration.

## Delivery protocol

1. Fresh git worktree; work here only; write files incrementally; act early,
   keep responses short.
2. Run every AC yourself; record real exit codes. Honest `partial` beats
   dishonest `done`.
3. Commit ALL work:
   `git add -A && git commit -m "v0.3-02: magnitude_vs_turnover economic-floor blade"`.
4. Final output = ONLY the JSON receipt (schema appended below by the
   dispatch bridge). `ticket_id` = `v0.3-02`.
