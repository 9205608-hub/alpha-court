# Ticket: v0.2-14 — make court.sharpe.sharpe_ratio lean (drop the unused skew/kurtosis)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained. Do not invent scope beyond it.

## Context

`court.sharpe.sharpe_ratio(values)` returns only the native Sharpe `μ̂/σ̂`, but it
computes it as `series_moments(values).sr_hat` — and `series_moments` ALSO computes
`scipy.stats.skew(arr, bias=True)` and `scipy.stats.kurtosis(arr, fisher=False,
bias=True)` on every call. Those two higher moments are **discarded** by
`sharpe_ratio` (only DSR/PSR, which call `series_moments` directly, use them).

`sharpe_ratio` is the PBO-CSCV metric (`court.judge._METRIC_REGISTRY["sharpe"]`,
and via `_abs_sharpe`/`_neg_sharpe`). PBO calls the metric
`C(n_splits, n_splits/2) × N × 2` times — for the power sweep's n_splits=16, N=100
that is **~2.57 million calls**. The wasted skew+kurtosis make one `_apply_pbo` take
**~928 s** on a (480, 100) matrix; the same PBO with a lean `mean/std` metric takes
**~20.5 s** — a **~45×** difference, and the power-calibration sweep runs PBO twice
per (strength, seed), so this single waste is the sweep's dominant cost
(~31 min/seed, ~12 days for the full run).

**The fix is bit-identical:** `sharpe_ratio` must return the SAME `μ̂/σ̂`. The
commander verified on a (480,100) battery that PBO φ with a lean `mean/std` metric
is **bit-identical** to PBO φ with the current `sharpe_ratio` (n_splits=8 and 10:
`φ` and `n_lambda_negative` match exactly), and `sharpe_ratio(x) == mean/std(x,
ddof=1)` bit-for-bit on 5 seeds. The skew/kurtosis simply never enter the Sharpe
value or the PBO ranking.

## The exact code (pasted from `court/sharpe.py`)

```python
def series_moments(values: object) -> SeriesMoments:
    arr = _as_1d_float_array(values)          # raises: n<2, non-1d, non-finite
    n_obs = int(arr.size)
    mu_hat = float(np.mean(arr))
    sigma_hat = float(np.std(arr, ddof=1))
    if sigma_hat == 0.0:
        raise ValueError("sigma_hat == 0: Sharpe ratio undefined")
    sr_hat = mu_hat / sigma_hat
    skew_hat = float(skew(arr, bias=True))                    # <-- unused by sharpe_ratio
    kurt_hat = float(kurtosis(arr, fisher=False, bias=True))  # <-- unused by sharpe_ratio
    return SeriesMoments(n_obs, mu_hat, sigma_hat, sr_hat, skew_hat, kurt_hat)

def sharpe_ratio(values: object) -> float:
    """Native-frequency Sharpe ratio μ̂/σ̂ (Bessel σ̂)."""
    return series_moments(values).sr_hat        # <-- computes full moments, returns only sr_hat
```

## Task

Rewrite `sharpe_ratio` to compute `μ̂/σ̂` **directly** — mean and Bessel std only,
NOT via `series_moments` — so the unused skew/kurtosis are never computed:

```python
def sharpe_ratio(values: object) -> float:
    arr = _as_1d_float_array(values)          # SAME validation/raises as before
    mu_hat = float(np.mean(arr))
    sigma_hat = float(np.std(arr, ddof=1))
    if sigma_hat == 0.0:
        raise ValueError("sigma_hat == 0: Sharpe ratio undefined")
    return mu_hat / sigma_hat
```

This is bit-identical: `series_moments` computes `mu_hat`/`sigma_hat`/`sr_hat` with
exactly these three lines, so the returned value is unchanged; the ONLY difference
is that `skew`/`kurtosis` are not computed. The raise conditions (n<2, non-1d,
non-finite via `_as_1d_float_array`; σ̂==0) MUST be preserved verbatim and fire on
the same inputs with the same messages. Do NOT touch `series_moments` (DSR/PSR need
its full moments), `_abs_sharpe`, `_neg_sharpe`, the registry, or `_apply_pbo` —
they all inherit the speedup through `sharpe_ratio`.

## Hard constraints (project iron laws — violations = rejected delivery)

1. `court/` stays market-agnostic (allowlist: stdlib/__future__/court/numpy/scipy).
   No new import; you REMOVE the skew/kurtosis use from the `sharpe_ratio` path only.
2. **Numeric result frozen (bit-identical):** `sharpe_ratio(x)` must equal the
   current `series_moments(x).sr_hat` to `atol=0` (exact) for every finite input;
   PBO φ / n_lambda_negative / logits via `court.judge` must be unchanged; DSR
   (which uses `series_moments`, unchanged) is unaffected. Existing tests
   `test_sharpe.py`, `test_pbo.py`, `test_dsr.py`, `test_judge.py`,
   `test_judge_direction.py` all pass unchanged.
3. Determinism; English code/docstrings/comments. TDD: a failing test FIRST (record
   the red run in the receipt), then green.
4. File ownership — modify ONLY: `court/sharpe.py`, `tests/test_sharpe.py`, and
   (new) `tests/test_sharpe_perf.py`. Do NOT touch `court/judge.py`, `court/pbo.py`,
   `court/dsr.py`, other court files, `harness/`, `adapters/`, `examples/`, `docs/`,
   `pyproject.toml`, or any other test.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0.
2. **Bit-identity test** (NEW, `tests/test_sharpe_perf.py`): on a battery of random
   finite series (varied length ≥2, scale, sign), `sharpe_ratio(x)` equals a frozen
   reference `float(np.mean(x)) / float(np.std(x, ddof=1))` with `==` (exact), and
   equals the pre-change `series_moments(x).sr_hat` exactly. Include the σ̂==0
   (`[2,2]`), n<2 (`[1.0]`), and non-finite (`[0, inf]`) raise cases — same
   exceptions as before.
3. **PBO φ-invariance test** (NEW): build a (T=240, N=40) matrix; assert
   `court.judge.judge`-driven `pbo_cscv` φ (and `n_lambda_negative`) is bit-identical
   to a frozen reference computed with a local `mean/std` metric (paste the metric
   into the test). This proves the PBO ranking is unchanged.
4. `.venv/bin/python -m pytest tests/test_sharpe.py tests/test_pbo.py tests/test_dsr.py tests/test_judge.py tests/test_judge_direction.py tests/test_sharpe_perf.py -v` → exit 0.
5. `python3 -m pytest` → exit 0 (nothing else regresses; qlib/matplotlib tests may skip under `[dev]` — note it, do not fix it here).
6. `.venv/bin/ruff check .` → exit 0.
7. **Performance test** (`tests/test_sharpe_perf.py`): a `court.judge`-driven PBO on a
   (T=480, N=100) matrix with `n_splits=12` completes in **< 5.0 s** (the pre-change
   cost at n_splits=12 is ~70 s; ≥10× headroom over the expected ~1.5 s so it will
   not flake, but fails hard if skew/kurtosis are still computed). Record the measured
   time in the receipt.
8. TDD: at least one red-phase pytest with non-zero exit before green.
9. Before FIRST commit `BASE=$(git rev-parse HEAD)`; `git diff --stat $BASE..HEAD`
   touches ONLY `court/sharpe.py`, `tests/test_sharpe.py`, `tests/test_sharpe_perf.py`.

## Out of scope

- `series_moments`, DSR/PSR, `_apply_pbo`, the metric registry, `pbo_cscv` internals
  (they inherit the speedup unchanged; do not modify).
- Vectorizing `pbo_cscv` itself (a separate, bigger change — not this ticket).
- `annualized_sr`, `sr_var_factor`, `sr_standard_error`, `psr` (leave untouched).

## Delivery protocol

1. Fresh git worktree; work here only. Write files incrementally. **Act early; keep
   each response short — do not emit a long analysis block before your first edit**
   (a prior dispatch died of max_tokens on an over-long turn-1 reasoning block).
2. Run the AC; record each + real exit code in the receipt. Include the measured PBO
   time. Honest `partial` beats dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-14: lean sharpe_ratio (drop
   unused skew/kurtosis; bit-identical SR, ~45x faster PBO metric)"`.
4. Final output = ONLY the JSON receipt (`branch`, `commit`, `worktree_path`,
   `ticket_id`=`v0.2-14`).
