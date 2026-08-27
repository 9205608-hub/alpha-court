# Ticket: v0.2-13 — vectorize the adapter IC kernel's full-support fast path

You are a headless worker agent for the alpha-court project. This ticket is
self-contained. Do not invent scope beyond it.

## Context

`adapters/qlib_cn.py` `_shared_kernel` is the audited market-gate kernel that both
`evaluate` and `evaluate_shifted` route through (contract §7.3). Its IC path is a
**double Python loop** — `for offset in offsets: for t in range(T)` — computing a
per-date Spearman rank-IC via `_pearson`. Profiled on the real csi300 panel
(T=480, N=336): a single `evaluate` takes **~325 ms** and `evaluate_shifted` with
199 offsets takes **~32 s** (161 ms/offset). The power-calibration sweep builds a
199-offset jury for 99 noise candidates per seed → ~53 min/seed → the full R₀=40
run is ~1.8–4 days, dominated entirely by this loop. The loop iterates
199 × 480 ≈ 95k times, each calling `_pearson` on ~336 elements.

**The win:** in the common case the per-date joint mask (PIT ∧ score-finite ∧
label-finite) equals the full finite support of both series — the existing
"fast-path" branch (`score_ranks_full[s, joint]` / `label_ranks_full[t, joint]`).
That branch is a plain row-wise Pearson of two precomputed rank panels and is
**fully vectorizable** across dates (and offsets) with numpy — no Python loop.
Only dates where a finite cell is *excluded* from the joint (the `_ranks_within_joint`
re-rank branch) need the loop. On a dense panel like csi300 the vast majority of
dates are fast-path, so vectorizing that branch is the ~50–100× win.

**This is the frozen v0.1 audited kernel. The numeric result must not move.** The
oracle-equivalence test asserts the IC kernel matches qlib `calc_ic(...).ric` at
`rtol=1e-12, atol=0.0`. Your vectorized kernel must STILL pass that, and must match
the current kernel's output to the same tolerance on every vector.

## The exact code you are optimizing (pasted from `adapters/qlib_cn.py`)

Helpers (DO NOT change their numeric semantics; you MAY call them):
```python
def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = x - x.mean()
    y = y - y.mean()
    denom = np.sqrt(np.dot(x, x) * np.dot(y, y))
    if denom == 0.0:
        return float("nan")
    return float(np.dot(x, y) / denom)

def _rank_panel(panel):  # per-row average ranks on each row's finite support; NaN stays NaN
    ...  # returns (T, N) float64, NaN where not finite
def _ranks_within_joint(values, order, joint):  # avg ranks restricted to joint via precomputed argsort
    ...
```

The IC branch of `_shared_kernel` (the target):
```python
    score_finite = np.isfinite(scores)
    label_finite = np.isfinite(labels)
    out = np.empty((len(offsets), t_len), dtype=np.float64)

    if metric == "ic":
        score_ranks_full = _rank_panel(scores)
        label_ranks_full = _rank_panel(labels)
        score_order = np.argsort(scores, axis=1, kind="mergesort")
        label_order = np.argsort(labels, axis=1, kind="mergesort")
        base_ok = pit_mask & label_finite                      # offset-independent

        for oi, delta in enumerate(offsets):
            src = (np.arange(t_len) - delta) % t_len
            for t in range(t_len):
                s = int(src[t])
                joint = base_ok[t] & score_finite[s]
                n_cs = int(joint.sum())
                if n_cs < min_cross_section:
                    raise ValueError(... "min_cross_section violated on evaluation date index {t}: "
                                          "usable cross-section {n_cs} < {min_cross_section}")
                if np.any(score_finite[s] & ~joint):
                    rx = _ranks_within_joint(scores[s], score_order[s], joint)
                else:
                    rx = score_ranks_full[s, joint]
                if np.any(label_finite[t] & ~joint):
                    ry = _ranks_within_joint(labels[t], label_order[t], joint)
                else:
                    ry = label_ranks_full[t, joint]
                val = _pearson(rx, ry)
                if not np.isfinite(val):
                    raise ValueError(... "non-finite ic on evaluation date index {t} ...")
                out[oi, t] = val
        return out
```

## Task

Rewrite the IC branch so that **fast-path (date, offset) cells** — those where
`joint == (score_finite[s] & label_finite[t] & pit_mask[t])`, i.e. NO finite cell
is excluded from the joint — are computed by a **vectorized masked row-wise
Pearson** of `score_ranks_full` (offset-aligned) against `label_ranks_full`,
instead of the per-date Python loop. Dates/offsets with an excluded finite cell
(the `_ranks_within_joint` branch) keep the loop + re-rank. All raises
(`min_cross_section`, non-finite IC) must fire on exactly the same (date, offset)
cells with the same messages.

**Numeric equivalence is the hard constraint — the vectorized fast path must match
`_pearson(score_ranks_full[s, joint], label_ranks_full[t, joint])` to `rtol=1e-12,
atol=0` (the oracle test's bar).** The safe construction: for each fast-path date,
center each rank vector on its JOINT mean, set the non-joint cells to `0.0` AFTER
centering, then use `np.dot`/`np.sum`. NOTE it will NOT be bit-identical: numpy's
pairwise summation over the full width (with zeros) reorders vs the compacted
`_pearson` dot, giving a ~1e-15 relative difference — **well within rtol=1e-12**
(verified by the commander pre-dispatch: max rel diff 2.0e-15 on a 336-instrument
battery). So target the `rtol=1e-12` bar, NOT bit-identity — do not contort the
code chasing exact equality. Do NOT use `np.corrcoef`/`scipy.stats.pearsonr`
(different formula/summation → can exceed 1e-12). Preserve the `denom == 0.0 → NaN`
rule and the subsequent non-finite→raise.

Also vectorize `returns` if (and only if) you can do it at the same equivalence
bar cheaply; otherwise leave the returns branch untouched (IC is the sweep's
bottleneck). Keep `evaluate` and `evaluate_shifted` routing through the shared
kernel unchanged (the equivalence invariant `evaluate_shifted(S,m,[0]) == evaluate`
must still hold bit-for-bit).

## Hard constraints (project iron laws — violations = rejected delivery)

1. `court/` unchanged and never imported with market code. This ticket touches only
   the adapter (which is where all qlib lives).
2. **Numeric result frozen:** the oracle test (`test_oracle_ic_matches_calc_ic_ric`
   and the NaN/PIT-churn variants) must still pass at `rtol=1e-12, atol=0.0`; the
   equivalence invariant test and determinism test must still pass byte-identically.
3. No new dependency. numpy only (scipy already imported is fine but not needed here).
4. Determinism on fixed input; English code/docstrings/comments. TDD: a failing
   test FIRST (record the red run in the receipt `self_test`), then green.
5. File ownership — modify ONLY: `adapters/qlib_cn.py` and
   `tests/test_adapter_qlib_cn.py`, plus (new) `tests/test_adapter_kernel_perf.py`.
   Do NOT touch `court/`, `harness/`, `examples/`, `docs/`, `pyproject.toml`, or any
   other test.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
   (qlib NOT required for most tests; the oracle test is guarded by
   `importorskip("qlib")` — the referee runs it with qlib installed).
2. Numeric-equivalence test (NEW, no qlib): on a battery of random panels — dense
   full-support, PIT-churn (excluded cells), NaN-punched, tie-heavy, and the
   min_cross_section boundary — the new `_shared_kernel` output equals a **frozen
   reference** (the pre-optimization loop, pasted into the test as
   `_reference_kernel_ic`) at `atol=0, rtol=1e-12` for BOTH `evaluate` and
   `evaluate_shifted` over multiple offsets. (Slow-path dates — excluded cells —
   will match bit-for-bit since that code is unchanged; fast-path dates match to
   ~1e-15.) This is the load-bearing test — it proves the optimization changed
   nothing numerically beyond float-summation-order noise under the oracle bar.
3. `.venv/bin/python -m pytest tests/test_adapter_qlib_cn.py tests/test_adapter_labels.py tests/test_adapter_kernel_perf.py -v` → exit 0 WITHOUT qlib (qlib-gated tests skip); the whole file green WITH qlib is the referee's job.
4. `python3 -m pytest` → exit 0 (nothing else regresses; qlib tests may skip).
5. `.venv/bin/ruff check .` → exit 0.
6. **Performance:** a perf test builds a (T=480, N=336) dense full-support synthetic
   panel and asserts `evaluate_shifted(panel, "ic", list(range(199)))` completes in
   **< 3.0 s** (the current loop takes ~32 s; the threshold has ~10× headroom over
   the expected ~0.3–0.8 s so it will not flake, but fails hard if the loop was not
   vectorized). Also record the measured time in the receipt.
7. TDD evidence: at least one red-phase pytest with a non-zero exit before green.
8. Before your FIRST commit `BASE=$(git rev-parse HEAD)`; `git diff --stat $BASE..HEAD`
   touches ONLY `adapters/qlib_cn.py`, `tests/test_adapter_qlib_cn.py`, and
   `tests/test_adapter_kernel_perf.py`.

## Out of scope

- Any change to `_pearson` / `_rank_panel` / `_ranks_within_joint` numeric semantics
  (you may add a vectorized helper beside them; do not alter these).
- The `returns` branch unless it is a free equivalence-preserving win.
- Parallelism / multiprocessing (a single-thread vectorization is the ask).
- Any court/harness/examples change.

## Delivery protocol

1. Fresh git worktree; work here only. Write files incrementally (a v0.1 dispatch
   died of max_tokens on one giant file).
2. Run the AC commands; record each + real exit code in the receipt. Honest
   `partial` beats dishonest `done`. Include the measured `evaluate_shifted(199)`
   time and the equivalence-test result.
3. Commit ALL work: `git add -A && git commit -m "v0.2-13: vectorize adapter IC
   kernel fast path (numeric result frozen)"`.
4. Final output = ONLY the JSON receipt (`branch`=`git branch --show-current`,
   `commit`=`git rev-parse HEAD`, `worktree_path`=`pwd`, `ticket_id`=`v0.2-13`).

## Operational notes

- **Act early; keep every response short.** Do NOT emit a long analysis/plan block
  before your first tool call — make your first file edit within the first response
  and write the kernel incrementally across several SMALL edits. (A prior dispatch
  of this ticket died of `max_tokens` on an over-long turn-1 reasoning block; the
  vectorization is not hard once you start — center-on-joint-mean + zero-masked +
  full-width `np.dot`, looping only over the ~199 offsets, vectorized over the 480
  dates. Just build it step by step.)
- The equivalence test's `_reference_kernel_ic` must be a verbatim copy of the
  CURRENT loop (paste it) so the test is a true before/after oracle independent of
  the qlib oracle. Keep it in the test file, not the adapter.
- The venv in AC-1 is the only environment change; never `pip install` outside it.
