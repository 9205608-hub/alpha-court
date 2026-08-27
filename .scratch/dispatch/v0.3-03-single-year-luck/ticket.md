# Ticket: v0.3-03 — gates/single_year_luck blade + intra-blade null joint calibration script

You are a headless worker agent for the alpha-court project. This ticket is
self-contained. Do not invent scope beyond it.

## Context

v0.3 blade library, ticket 3 of 3 parallel blade tickets (harness plumbing
merged at your base). Frozen design excerpt
(`.scratch/v0.3/blades-design-draft-v2.md` §2.4 + §3, committed at your
base):

> **§2.4 single_year_luck（检验学钉死）**: contribution of block b =
> Σ_{i∈b} x_i (sign preserved); concentration via **HHI(|contribution|)**
> (absolute values, guards sign instability). Decision rule is merged into a
> SINGLE calibration object: flag ⇔ LOBO_min ≤ 0 **OR** HHI-p < p_min, and
> the two OR-ed rules are **jointly calibrated in a null world for the
> overall false-positive rate** (no separately hand-picked thresholds). If
> calibration cannot reach the target, this blade ships as
> `on_flag: record` (downgrade clause). blocks = adapter-provided OPAQUE
> integer labels; court must never parse calendars from strings.
>
> **§3**: calibration is pre-registered on synthetic null only (reusing the
> v0.2 noise battery's pure-noise world), frozen before any real run;
> thresholds enter the spec hash. Owner ruling OQ-A: per-blade FPR = 1%.

Definitions frozen for this ticket:
- Blocks partition the observations: `params["blocks"]` = list[int], same
  length as series.values, each int an opaque block label (≥1 distinct).
- Contribution C_b = sum of x_i with block label b. Total T = Σ_b C_b.
- **LOBO_min** = min over blocks of (T − C_b) — "leave one block out" total.
  LOBO_min ≤ 0 means one block carries the entire sign of the result.
- **HHI** = Σ_b (|C_b| / Σ_b'|C_b'|)² (Herfindahl–Hirschman index over
  absolute contributions; ∈ [1/n_blocks, 1]). Degenerate Σ|C_b| = 0 →
  HHI undefined → report None, not-flagged, evidence explains.
- **HHI-p**: right-tail p-value of observed HHI under the intra-series null:
  RANDOM REASSIGNMENT of the observed values to blocks (permutation of the
  block labels vector, preserving block sizes), n_perm from constructor,
  seeded, p = (1 + #{perm HHI ≥ observed}) / (1 + n_perm) (add-one
  estimator, Phipson & Smyth 2010).

## Blade protocol (implemented in harness/blades.py at your base — read it)

- Blade = object with `name: str` and
  `run(trial_id, spec, params, declared, series) -> dict` returning
  `{"blade": <name>, "flagged": bool, "statistics": dict, "evidence": dict,
  "params": dict}`; JSON-serializable, allow_nan=False (cast numpy scalars,
  None instead of NaN). `series` duck-typed (.index/.values tuples). No
  court/harness imports inside gates/ (stdlib+numpy+scipy only; tests may
  import anything). Blades never decide record/screen. Every executed blade
  leaves a report.

## Task

1. `gates/single_year_luck.py` — class `SingleYearLuckBlade`:
   - `__init__(self, p_min: float, n_perm: int = 2000, seed: int = 0,
     min_blocks: int = 2)`; validate p_min ∈ (0,1), n_perm ≥ 100.
   - `name = "single_year_luck"`.
   - `run(...)`: blocks from `params["blocks"]`; validation: missing, length
     mismatch, or fewer than min_blocks distinct labels → evaluable=False
     report (flagged=False, evidence names the culprit; never raise on trial
     inputs). Otherwise compute per-block contributions (report as
     {str(label): value} dict), total, LOBO_min (+argmin label), HHI, HHI-p
     (seeded permutation; rng = numpy default_rng(seed)). Flag ⇔ LOBO_min ≤ 0
     OR HHI-p < p_min. statistics carries every number above +
     n_blocks/n_obs/n_perm; params carries {p_min, n_perm, seed, min_blocks}.
   - Docstrings cite: HHI (Herfindahl 1950 / Hirschman 1945 concentration
     index), permutation p add-one estimator (Phipson & Smyth 2010).
2. `scripts/blade_calibration_syl.py` — intra-blade joint calibration for
   THIS blade's OR-rule (family-level calibration across all four blades is
   a LATER step, not this ticket):
   - CLI: `python3 scripts/blade_calibration_syl.py --seed-root N
     --n-null 1000 --n-obs 252 --n-blocks 4 --target-fpr 0.01
     [--n-perm 2000] [--out PATH]`.
   - Null world: pure iid Gaussian noise series (reuse the noise recipe
     spirit of `court/noise.py` — read it; if its API fits, import and use
     it from the SCRIPT (scripts/ may import court), otherwise
     numpy default_rng(seed_root) standard normal, and SAY which you did in
     the output).
   - For each of n-null draws: equal-size contiguous blocks (opaque labels
     0..n_blocks−1), compute LOBO_min ≤ 0 indicator and HHI-p. Then solve
     the JOINT rule: find the largest p_min on the grid
     {0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05} such that the joint
     null flag rate P(LOBO_min ≤ 0 OR HHI-p < p_min) ≤ target-fpr. Report
     the standalone LOBO null rate too — if LOBO alone already exceeds
     target-fpr, print the **downgrade recommendation** (§2.4: ship as
     on_flag record) and exit 0 with that stated in the JSON.
   - Output: JSON to --out (default stdout):
     {seed_root, null_recipe:{...all params...}, target_fpr,
     lobo_null_rate, chosen_p_min (or null + downgrade:true),
     joint_null_rate, n_perm, script:"blade_calibration_syl.py"} — shaped to
     drop into `append_blade_calibration`'s thresholds/null_recipe args.
   - Determinism: same CLI args → byte-identical JSON.
3. `tests/test_gates_single_year_luck.py` — red-first TDD:
   a. Hand vector: 4 blocks, one block = +10 and the rest sum −1 each →
      LOBO_min = total − big block < 0 → flagged (any p_min). Balanced
      blocks → LOBO_min > 0.
   b. HHI arithmetic on a hand case (assert exact formula value).
   c. HHI-p: planted concentration (one block values scaled ×10 vs
      shuffled labels) gives small p; iid noise gives p not small
      (seeded, assert p > 0.2).
   d. Degenerate Σ|C_b|=0 → HHI None, not flagged, JSON-serializable.
   e. Input validation paths (missing blocks / length mismatch / 1 block) →
      evaluable=False, no raise.
   f. Determinism: same seed → identical report incl. HHI-p.
   g. Calibration script smoke: run via subprocess with --n-null 50
      --n-perm 200 (small, fast), assert exit 0, JSON parses, contains
      chosen_p_min or downgrade:true, and re-running with same args is
      byte-identical.
   h. Integration smoke (crib fixtures from tests/test_blades_harness.py,
      copy don't import): blade attached to CertifiedRun with calibration
      declared; concentrated trial with `on_flag: screen` ends `registered`
      with flagged report; balanced trial records.

## Hard constraints (iron laws — violations = rejected delivery)

1. gates/ module imports ONLY stdlib+numpy+scipy; the SCRIPT may import
   court (it is commander-side tooling). No calendar parsing anywhere —
   blocks stay opaque ints.
2. Statistical definitions exactly as frozen above; citations in docstrings.
   No silent re-tuning: the script REPORTS thresholds, code never hard-codes
   them (p_min is a constructor input).
3. Determinism everywhere (seeded rng only); English; TDD red recorded.
4. File ownership — modify/create ONLY: `gates/single_year_luck.py`,
   `scripts/blade_calibration_syl.py`, `tests/test_gates_single_year_luck.py`.
   Do NOT touch gates/__init__.py, gates/base.py, other gates files (sibling
   tickets in flight NOW own them), harness/, court/, other scripts, any
   other test. Import your class directly from its module.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m pytest tests/test_gates_single_year_luck.py -v` → exit 0.
2. `python3 -m pytest -q` → exit 0. Known environment caveat: 3 wall-clock
   perf tests (test_adapter_kernel_perf.py ×2, test_sharpe_perf.py ×1) can
   fail on a loaded machine and fail identically at base — if they fail,
   re-run just those three and report both results honestly.
3. `ruff check .` → exit 0.
4. `python3 scripts/blade_calibration_syl.py --seed-root 7 --n-null 200
   --n-obs 252 --n-blocks 4 --target-fpr 0.01 --n-perm 500` → exit 0, valid
   JSON; record its lobo_null_rate / chosen_p_min (or downgrade) in the
   receipt.
5. TDD red run recorded. 6. Ownership diff = exactly the three files.

## Out of scope

- Family-level (four-blade) joint calibration and the on-chain
  blade_calibration declaration for real runs — later step, after all blade
  tickets merge.
- Sibling blades, gates/__init__.py registration, any harness change.
- Block-label SEMANTICS (years, regimes…) — adapter's business, opaque here.

## Delivery protocol

1. Fresh git worktree; work here only; write files incrementally; act early,
   keep responses short.
2. Run every AC yourself; record real exit codes. Honest `partial` beats
   dishonest `done`.
3. Commit ALL work:
   `git add -A && git commit -m "v0.3-03: single_year_luck blade + intra-blade null joint calibration script"`.
4. Final output = ONLY the JSON receipt (schema appended below by the
   dispatch bridge). `ticket_id` = `v0.3-03`.
