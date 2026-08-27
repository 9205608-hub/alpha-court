# Ticket: v0.2-05 — Power-calibration harness (the court's ROC on a known signal)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

The killer demo proves the court has **size** (rejects pure noise 0/100). It
has never been shown to have **power** — to *pass* a genuine signal. "An
always-reject stub scores the identical 0/100." This ticket builds the
experiment that measures the court's true-positive rate (TPR) as a function of
a known-strength injected signal — the other half of v0.2's charter.

The authoritative, FROZEN pre-registration book is
`docs/design/power-calibration.md` (v3, committed in your worktree) — **read
all of it**; §2 (mirror), §4 (signal + calibration + grid), §5 (experiment),
§6 (reporting), §7 (appendices), §8 (no-victory-theater), §12–13 (rulings) are
binding. The owning issue is `.scratch/v0.2/issues/05-power-calibration-harness.md`
(with its audit-amendment section). Where this ticket pins something more
precisely, this ticket wins.

**Landed context you build on (all merged):**
- The killer demo `examples/killer_demo/` — its noise shells, adapter pipeline,
  seed tree, window. **REUSE `examples.killer_demo.generation` ONLY** (the AR(1)
  shells `ar1_panel`, `draw_offsets`, `spawn_seed_tree`, `build_factor_specs`);
  import, do not modify. **Do NOT reuse `killer_demo.grid` (`build_offset_grid`
  / `OffsetGrid`) nor `killer_demo.battery` (`build_applications`)** — both are
  hardwired **two-sided**: `OffsetGrid` stores only `abs_t_grid` and battery
  provenance pins `ranking_stat="abs_t_iid"`. The §5 jury needs **directed t
  (greater → signed t, NOT |t|)** and per-offset **signed** max-of-99; build the
  directed-t jury grid and the greater battery FRESH from
  `evaluator.evaluate_shifted` + `court.tstats.t_stat` (see Reference wiring).
- `harness.aggregation_policy` (ticket 09): the discriminating-only aggregation
  helpers (`trial_survives`, `survivor_ids`, `apply_policy`, …). Power reuses
  THIS — **no second aggregation code path** (audit D13).
- Direction-aware judge (ticket 08): verdicts carry `role`; the judge branches
  gate forms on `declared.direction`; a scope must be direction-homogeneous.
  Under `direction="greater"`: DSR becomes a **discriminating** (load-bearing,
  voting) gate, and PBO resolves to signed `sharpe` (not `abs_sharpe`).

**The binding experiment, pasted from the frozen book:**

Signal construction (§4.1) — one injected candidate, each signal day t,
instrument i:
```
oracle_i,t = Φ⁻¹(rank_xs(forward_return_i,t))   # van der Waerden score of the day-t forward return
noise_i,t  = Φ⁻¹(rank_xs(AR1_i,t(φ)))           # same transform of the killer-demo AR(1) shell
factor_i,t = β·oracle_i,t + √(1−β²)·noise_i,t
```
`forward_return` is the SAME label the adapter evaluates against
(`Ref($close,-2)/Ref($close,-1)-1`) — a deliberate, disclosed look-ahead.
**The oracle's `forward_return` panel is `evaluator.labels`** — the read-only
(T,N) defensive copy exposed by `QlibCNFactorEvaluator.labels` (added in the
enabling commit that precedes this ticket; rows aligned to
`evaluator.evaluation_dates`, cols to `evaluator.instruments`, NaN where no
label). **Use `evaluator.labels`; do NOT read the private `_labels`, and do NOT
re-derive labels from qlib.** `AR1(φ)` is the killer-demo shell with φ fixed to
the **median of the 100 killer-demo shell φ values** (record the numeric value
in run_config). Both terms are cross-sectionally rank-then-normal-quantile
transformed (unit variance), so β is a well-defined mixing weight and
RankIC(factor) is monotone increasing in β. The mix preserves the null's
serially-uncorrelated daily IC.

β→ICIR calibration (§4.2) — run once, freeze β* into run_config BEFORE any
sweep:
1. Same window/universe/label/φ as the power run (T=480, csi300, RankIC, gross).
2. Calibration seeds `SeedSequence(320260711).spawn(64)` (K=64, written to
   run_config; must NOT reuse the power run's noise realizations — different
   seed root). Candidate β grid `0.02, 0.04, …, 0.30` (15 points). φ = median
   of the 100 demo shell φ (recorded).
3. Per candidate β: build the injected factor, `evaluate` → daily RankIC series;
   record mean(IC), std(IC, ddof=1), annualized ICIR = mean/std·√252.
4. Freeze the **mean over 64 seeds** (report the sample SE in an appendix line).
5. Solve β* for each frozen ICIR target by **monotone PCHIP interpolation** of
   the 64-seed-mean ICIR(β) curve (root-find on the interpolant).
6. Frozen: the β* table goes into run_config. The main experiment's realized
   ICIR is **NEVER written back** onto the axis.

Frozen strength grid (§4.3, annualized ICIR targets): transition (dense)
`2.0, 2.3, 2.6, 2.9, 3.2, 3.6, 4.0, 4.5, 5.0`; low `0, 0.5, 1.0, 1.5`; upper
anchor `6.0` (optional `8.0`). β=0 is the size anchor.

Experiment (§5):
- Pool = 1 injected genuine + 99 pure-noise = N=100. **All 100 trials declare
  `direction="greater"`** (direction-homogeneous).
- "Won" = the injected candidate is the `argmax t` (directed scan; no flip
  guard — a negative-t champion cannot win a directed scan).
- Primary estimate **A** = `P(unanimous pass | won)` over R seeds per strength,
  Wilson CI; the injected sits inside the 99-noise pool so pool gates run at
  N=100.
- **B** = `P(argmax t = injected | strength)`, estimated from the **first R₀=40
  fixed seeds only** (freezing B's denominator removes the stop-on-win bias).
- Submission power (secondary table) = `P(unanimous pass | injected forced as
  the judged candidate)`; DSR conservative off-champion; **never** overlaid on A.
- Replication: baseline R₀=40 per strength; in the transition band (2.0–3.6)
  adaptively re-seed (a pre-registered algorithmic seed sequence) until
  n_won ≥ 20, capped R=120. Wilson half-widths reported honestly. Adding
  samples = adding SEEDS only, never resampling the noise pool.
- Compute reuse: per seed, evaluate the 99 noise ONCE and cache their IC series,
  t, the 199-column jury **directed t** (greater → t, NOT |t|), and the
  per-offset signed max-of-99; each β then only evaluates the injected factor +
  a cheap battery re-run. Cross-β reuse within a seed only; cross-seed reuse
  forbidden.

Reporting (§6): hero = power curve `P(unanimous pass | won)` vs realized
annualized ICIR, with the β=0 "directional size" anchor, **B plotted beside
it**, and the **five per-gate TPR curves as a default panel**. Size same-axis
separate panel ("directional size" — a re-run of THIS greater-battery at β=0;
NOT the killer demo's two-sided size; assert `P(pass) ≈ nominal α` for size-type
gates FDR/pool-max/individual, PBO excluded). First-screen honesty: the §1
claim-scope + the §4.3 unit footnote (axis is project-annualized ICIR =
daily·√252 ≈ ×16). Under-powered strengths → wide CIs, flagged, never smoothed.

Appendix (§7) β_t regime-switch (PBO-optimism corrector): main = half-window
(forward-off / backward-off), **primary contrast = matched realized ICIR** (the
half-window arm's β solved so the full-sample ICIR equals the constant-β
reference, targets ≈4.0 and ≈3.0); secondary = same-nominal-β arm (labeled as
confounding strength with episodicity); sensitivity = random-block (honestly
scoped). Answers one number: points unanimous/PBO-TPR drops constant→matched
episodic. Calibration decomposition: small plots of E[IC](β), ICvol(β).

## The compute boundary (read carefully — this is the #1 thing to get right)

The real calibration needs qlib + the csi300 data pack; the real full sweep is
**1.5–4 days of compute** — you do NOT run either. Mirror how the killer demo
was delivered (worker built + tested on a reduced synthetic config; the referee
ran the real-data E2E at acceptance):

- **You build** the harness with TWO one-command entry points:
  `python -m examples.power_calibration.calibrate` (produces the β* table into
  run_config; minutes on real data) and `python -m examples.power_calibration`
  (the sweep; days on real data).
- **You TEST** on a **reduced synthetic config** (small T, few instruments, a
  handful of candidates, 2–3 seeds, 2–3 strengths) that runs in **seconds
  without qlib** — exactly as `tests/test_killer_demo.py` uses a reduced config.
  Guard any real-qlib path with `importorskip("qlib")` so the suite is green
  without the data pack.
- **The referee runs** the real calibration (freezes β*) and the real full
  sweep (days) at acceptance, and reviews the artifacts. Your deliverable is
  **code + reduced-config tests**, NOT real-data artifacts. Do NOT attempt the
  multi-day run; do NOT commit real-data output.

## Hard constraints (project iron laws — violations = rejected delivery)

1. No backtesting engine; no idea generation. Statistical steps cite the book
   section + any paper in the docstring.
2. `court/` must not be modified and must not import market code. `examples/`
   and the power package may import `court`, `harness`, `adapters`,
   `examples.killer_demo`.
3. **Uncertified calculator use** (audit D13): the power harness calls `court`
   directly (NOT the certified `harness.run` path). Every power artifact's first
   screen discloses "constructed oracle ≠ discoverable alpha" (§1) and that this
   is an uncertified calibration experiment.
4. **No second aggregation code path** (audit D13): reuse
   `harness.aggregation_policy` for the discriminating-only unanimous rule.
5. **禁赢学 / no victory theater** (§8): the frozen grid/seeds/decision lines are
   fixed before any run; results reported however they land (an unflattering
   power curve is reported as-is); **size is reported beside power, always**; no
   re-rolling seeds, no post-hoc threshold moves, no writing realized ICIR back
   onto the axis.
6. Determinism on a fixed machine + locked deps, as the killer demo.
7. Code, docstrings, comments: English. TDD contractual: failing tests FIRST
   (red run in the receipt `self_test`), then green.
8. File ownership — you may modify ONLY: a new `examples/power_calibration/`
   package (its `.py` modules + `__init__.py` + `__main__.py` +
   `calibrate.py` entry), (new) `tests/test_power_calibration.py`, **and the ONE
   line in `pyproject.toml` `[tool.setuptools].packages` that registers
   `examples.power_calibration`** (ratified 2026-07-17 — mirrors the
   `examples.killer_demo` packaging precedent; the lenient editable install
   resolves the subpackage without it, but listing it is packaging-correct for a
   wheel build, so it is permitted). Do NOT modify `court/`, `harness/`,
   `adapters/`, `examples/killer_demo/`, other `docs/`, or any other test or
   pyproject line. (Reuse killer_demo/harness/court by IMPORT.)

## Task (deliverables)

1. **Signal construction** module: the injected factor per §4.1 (van der Waerden
   oracle + AR(1)-shell noise mix; φ = median of the demo shells). Reuse
   `examples.killer_demo.generation` for the AR(1) shells and seed tree.
2. **Calibration** (`calibrate.py`): the §4.2 procedure end-to-end → a frozen β*
   table keyed by ICIR target, written into a `run_config`-style artifact; plus
   the E[IC](β)/ICvol(β) decomposition data. Deterministic; reduced-config
   testable.
3. **Sweep** (`run.py` + `__main__.py`): per strength, the §5 experiment —
   noise-pool-once caching, per-β injected evaluate, the greater-battery via
   `court.judge` (all trials `greater`), the `argmax t` won-test, A / B /
   submission-power, R₀=40 adaptive re-seed to n_won≥20 (cap 120, transition
   band only, B frozen at first 40). Reuse `harness.aggregation_policy` for
   unanimous-over-discriminating.
4. **Reporting**: the hero power curve + B + per-gate TPR panel + directional-
   size panel + submission-power table + β_t appendix (matched-ICIR primary) +
   calibration decomposition, mirroring `examples/killer_demo/report.py` +
   `figure.py`. First-screen honesty text (§1 + §4.3 unit footnote). Matplotlib
   is a `[demo]` extra — guard imports so non-figure tests don't need it.
5. **Determinism + honesty tests**: reduced-config determinism (two runs
   byte-identical stats), the frozen-grid/seed pre-registration is loaded from a
   pinned source (not recomputed after results), size-beside-power is always
   emitted, and the "won ⇒ argmax t" + direction-homogeneous-scope invariants
   hold.

## Reference wiring (API names verified against real APIs at this HEAD)

The verdict vertical slice below was proven end-to-end on the real post-08/09
APIs with **zero** `court/`/`harness/` modification. These are the exact public
names — mirror `examples/killer_demo/run.py` for the ledger dance. You still
write this test-first (TDD); this is the API map, not code to paste.

1. Evaluator: `QlibCNFactorEvaluator.from_panels(label_panel, config)` (synthetic,
   no qlib) → `evaluator.labels` (T,N), `evaluator.evaluation_dates`,
   `evaluator.instruments`.
2. Oracle (§4.1): `scipy.stats.rankdata` + `scipy.stats.norm.ppf` on
   `evaluator.labels`, cross-sectionally per row; noise via
   `examples.killer_demo.generation.ar1_panel(...)`; `factor = β·oracle +
   √(1−β²)·noise`.
3. Seeds: `np.random.SeedSequence(320260711).spawn(K)` (calibration root, K=64;
   the sweep uses the DISTINCT root `POWER_SEED_ROOT = 420260711`, ratified in
   book §4.2 on 2026-07-17 — the v3 book had pinned only the calibration root).
4. Ledger (import `from court.ledger import Ledger, DeclaredProtocol, Series,
   Window, SeConvention`; `from court.judge import judge, Application`):
   `Ledger.open(path)` → `register_hypothesis(statement)` →
   `register(hid, spec, params, declared=DeclaredProtocol(metric="ic",
   window=Window(start,end), periods_per_year=…, direction="greater",
   se=SeConvention(kind="iid")))` → `evaluator.evaluate(panel,"ic")` →
   `record(tid, Series(index=tuple(res.index), values=tuple(res.values)))`.
   ALL 100 trials `direction="greater"` (direction-homogeneous scope).
5. Won-test: per-trial `court.tstats.t_stat(series_values, se_kind="iid").t`
   (`TStatResult(t, mean, se, n_obs)`); `argmax t` over the pool = "won" (directed;
   a negative-t champion cannot win).
6. Directed-t jury (FRESH, not killer_demo.grid): per candidate
   `evaluator.evaluate_shifted(panel,"ic",offsets)` → `t_stat(col).t` (signed) →
   per-offset **signed** max-of-99 → the `null_stats` for the individual gate.
7. Battery: `judge(ledger, trial_ids, [Application(statistic, params), …])`.
   Under `direction="greater"` the judge sets `role` and metric internally:
   `Application("fdr_by", {"q":0.05})`; `Application("dsr",
   {"selected_trial_id":accused,"confidence":0.95})` (discriminating under
   greater); `Application("pbo_cscv",
   {"selected_trial_id":accused,"n_splits":S,"phi_threshold":0.2,
   "metric":"sharpe"})` (signed sharpe under greater);
   `Application("noise_control", {"mode":"pool_max",…})`; N×
   `Application("noise_control", {"mode":"individual","judged_trial_id":tid,
   "null_stats":directed_jury[i],…})`. Read outcomes via `ledger.verdicts()` and
   `verdict.decisions[injected_tid]` per gate (the per-gate TPR feed).
8. Aggregation (NO second code path): `harness.aggregation_policy.apply_policy(
   AggregationPolicy(policy_id, rule="unanimous-discriminating", params={}),
   trial_ids, ledger.verdicts())` and `survivor_ids(...)` / `trial_survives(...)`.
9. Submission power (forced non-champion): pass the injected as
   `selected_trial_id` (DSR/PBO) / `judged_trial_id` (individual); the pool-max
   won⇒argmax consistency assertion is disabled in the forced branch (§9).

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,demo]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_power_calibration.py -v` → exit 0;
   ≥ 12 tests, including reduced-config end-to-end (calibrate → sweep → report
   on a synthetic reduced config, no qlib), the determinism test, and the
   won/direction invariants. Tests must be green WITHOUT qlib installed
   (`importorskip` guards any real-data path).
3. `python3 -m pytest` → exit 0 (qlib-dependent tests may skip; nothing else
   regresses; ~30 min — run once at the end)
4. `.venv/bin/ruff check .` → exit 0
5. Before your FIRST commit, `BASE=$(git rev-parse HEAD)`; then
   `git diff --stat $BASE..HEAD` touches ONLY files under
   `examples/power_calibration/`, `tests/test_power_calibration.py`, and the
   single `examples.power_calibration` line in `pyproject.toml` (per iron-law #8)
6. TDD evidence: at least one recorded pytest command with a non-zero exit code
   from the red phase, before the green run
7. `notes_for_referee`: the exact two commands the referee runs on real data
   (`… .calibrate` then `… power_calibration`), their expected runtime, and the
   qlib/data-pack prerequisites — so the referee can launch the multi-day job.

## Out of scope

- Running the real calibration or the multi-day sweep (referee acceptance job).
- Committing any real-data artifacts.
- Any `court/` / `harness/` / `adapters/` / `killer_demo` modification (reuse by
  import).
- The certified `harness.run` path (power is uncertified, §12).
- The optional 8.0 anchor, multiple-genuine, and 2–3 φ appendices (mark as
  hooks, do not implement unless free).

## Delivery protocol

1. Fresh git worktree; work here only.
2. Run the AC commands; record each + real exit code in the receipt. Honest
   `partial` beats dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-05: power-calibration
   harness (build + reduced-config tests; real sweep is referee acceptance)"`.
4. Final output = ONLY the JSON receipt. Gather: `branch`=`git branch
   --show-current`, `commit`=`git rev-parse HEAD`, `worktree_path`=`pwd`,
   `ticket_id`=`v0.2-05`.

## Operational notes

- Write files INCREMENTALLY (several smaller edits — a v0.1 dispatch died of
  max_tokens on one giant file).
- Keep the reduced test config tiny (seconds) — the inner loop must not need
  qlib. Mirror `tests/test_killer_demo.py`'s reduced-config *shape* but **NOT
  its `n_splits`**: PBO (`pbo_cscv`) cost is `C(n_splits, n_splits/2)` per
  candidate, so the demo's `n_splits=16` (12870 combinations) makes ONE battery
  ~20s at N=100 — and the power sweep runs the battery **once per (strength ×
  seed)**, which would blow past both "seconds" and AC-3's ~30 min. Use a small
  **`n_splits` (e.g. 4 → 6 combinations, ~0.01s)** with reduced `T` divisible by
  it, 2–3 seeds, 2–3 strengths. (Independently timed at HEAD: S=4→0.01s,
  S=8→0.11s, S=16→20.8s for N=100.) Real-data `n_splits` is fixed by the book,
  not by the reduced test.
- The venv in AC-1 is the only environment change; never `pip install` outside
  it; do NOT install qlib (the referee does that for the real run).
