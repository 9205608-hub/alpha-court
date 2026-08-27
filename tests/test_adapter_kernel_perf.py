"""Numeric equivalence + performance for the vectorized IC kernel fast path (v0.2-13).

No qlib dependency. The reference IC loop is a verbatim paste of the pre-optimization
``_shared_kernel`` IC branch so this test is a before/after oracle independent of
the qlib ``calc_ic`` oracle.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from adapters.qlib_cn import (
    QlibCNFactorEvaluator,
    _pearson,
    _rank_panel,
    _ranks_within_joint,
    _shared_kernel,
)

# ---------------------------------------------------------------------------
# Frozen reference: verbatim pre-optimization IC loop from adapters/qlib_cn.py
# ---------------------------------------------------------------------------


def _reference_kernel_ic(
    scores: np.ndarray,
    labels: np.ndarray,
    pit_mask: np.ndarray,
    *,
    min_cross_section: int,
    offsets: list[int],
) -> np.ndarray:
    """Verbatim copy of the pre-vectorization IC branch (double Python loop)."""
    t_len, _n_inst = scores.shape
    score_finite = np.isfinite(scores)
    label_finite = np.isfinite(labels)
    out = np.empty((len(offsets), t_len), dtype=np.float64)

    score_ranks_full = _rank_panel(scores)
    label_ranks_full = _rank_panel(labels)
    score_order = np.argsort(scores, axis=1, kind="mergesort")
    label_order = np.argsort(labels, axis=1, kind="mergesort")
    base_ok = pit_mask & label_finite

    for oi, delta in enumerate(offsets):
        src = (np.arange(t_len) - delta) % t_len
        for t in range(t_len):
            s = int(src[t])
            joint = base_ok[t] & score_finite[s]
            n_cs = int(joint.sum())
            if n_cs < min_cross_section:
                raise ValueError(
                    f"min_cross_section violated on evaluation date index {t}: "
                    f"usable cross-section {n_cs} < {min_cross_section}"
                )
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
                raise ValueError(
                    f"non-finite ic on evaluation date index {t} "
                    f"(zero variance or degenerate cross-section)"
                )
            out[oi, t] = val
    return out


def _make_evaluator(
    labels: np.ndarray,
    *,
    pit_mask: np.ndarray | None = None,
    min_cross_section: int = 10,
    dates: pd.DatetimeIndex | None = None,
) -> QlibCNFactorEvaluator:
    t_len, n_inst = labels.shape
    if dates is None:
        dates = pd.bdate_range("2020-01-01", periods=t_len)
    instruments = [f"S{i:04d}" for i in range(n_inst)]
    label_df = pd.DataFrame(labels, index=dates, columns=instruments)
    return QlibCNFactorEvaluator.from_panels(
        label_panel=label_df,
        config={
            "window": {
                "start": str(label_df.index[0].date()),
                "end": str(label_df.index[-1].date()),
            },
            "declared_data_tag": "synthetic-kernel-perf",
            "quantile": 0.2,
            "min_cross_section": min_cross_section,
            "universe": "synthetic",
            "provider_uri": "synthetic",
        },
        pit_mask=pit_mask,
    )


def _dense_panels(t_len: int, n_inst: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    scores = rng.normal(size=(t_len, n_inst)) + np.arange(n_inst) * 1e-9
    labels = rng.normal(size=(t_len, n_inst)) + np.arange(n_inst) * 1e-10
    return scores.astype(np.float64), labels.astype(np.float64)


def _score_df(scores: np.ndarray, dates: pd.DatetimeIndex) -> pd.DataFrame:
    instruments = [f"S{i:04d}" for i in range(scores.shape[1])]
    return pd.DataFrame(scores, index=dates, columns=instruments)


# ---------------------------------------------------------------------------
# AC-2: numeric equivalence vs frozen reference loop
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "dense",
        "pit_churn",
        "nan_punched",
        "tie_heavy",
        "min_cs_boundary",
    ],
)
def test_shared_kernel_ic_matches_reference(case: str):
    """New IC path equals frozen double-loop reference at rtol=1e-12, atol=0."""
    t_len, n_inst = 24, 40
    min_cs = 10
    scores, labels = _dense_panels(t_len, n_inst, seed=42)
    pit = np.ones((t_len, n_inst), dtype=bool)

    if case == "pit_churn":
        for t in range(t_len):
            start = (t * 3) % n_inst
            for k in range(8):
                pit[t, (start + k) % n_inst] = False
    elif case == "nan_punched":
        for t in range(t_len):
            scores[t, t % n_inst : (t % n_inst) + 5] = np.nan
            labels[t, (t + 3) % n_inst : ((t + 3) % n_inst) + 4] = np.nan
    elif case == "tie_heavy":
        for t in range(t_len):
            scores[t, : n_inst // 2] = float(t % 5)
            labels[t, n_inst // 3 : 2 * n_inst // 3] = float((t + 1) % 4)
    elif case == "min_cs_boundary":
        # Exactly min_cs joint members most days; dense otherwise
        pit[:] = False
        for t in range(t_len):
            pit[t, :min_cs] = True

    offsets = [0, 1, 3, 7, -2]
    got = _shared_kernel(
        scores,
        labels,
        pit,
        metric="ic",
        quantile=0.2,
        min_cross_section=min_cs,
        offsets=offsets,
    )
    ref = _reference_kernel_ic(
        scores,
        labels,
        pit,
        min_cross_section=min_cs,
        offsets=offsets,
    )
    np.testing.assert_allclose(got, ref, rtol=1e-12, atol=0.0)


def test_evaluate_and_evaluate_shifted_match_reference():
    """Public evaluate / evaluate_shifted match reference via shared kernel."""
    t_len, n_inst = 16, 30
    scores, labels = _dense_panels(t_len, n_inst, seed=99)
    # Mix: denser + some NaNs so both fast and slow paths fire
    scores[3, 2:6] = np.nan
    labels[5, 10:14] = np.nan
    pit = np.ones((t_len, n_inst), dtype=bool)
    for t in range(0, t_len, 4):
        pit[t, 0:3] = False

    dates = pd.bdate_range("2020-01-01", periods=t_len)
    ev = _make_evaluator(labels, pit_mask=pit, min_cross_section=8, dates=dates)
    score_df = _score_df(scores, dates)
    offsets = [0, 2, 5]

    ref = _reference_kernel_ic(
        scores, labels, pit, min_cross_section=8, offsets=offsets
    )
    grid = ev.evaluate_shifted(score_df, "ic", offsets)
    np.testing.assert_allclose(grid.values, ref, rtol=1e-12, atol=0.0)

    single = ev.evaluate(score_df, "ic")
    np.testing.assert_allclose(single.values, ref[0], rtol=1e-12, atol=0.0)
    # Equivalence invariant: evaluate_shifted(..., [0]) == evaluate (bit-identical)
    zero_grid = ev.evaluate_shifted(score_df, "ic", [0])
    np.testing.assert_array_equal(zero_grid.values[0], single.values)


# ---------------------------------------------------------------------------
# AC-6: performance — vectorized fast path on dense csi300-sized panel
# ---------------------------------------------------------------------------


def _csi300_like_pit(t_len: int, n_inst: int, *, drop_frac: float = 0.12) -> np.ndarray:
    """Per-date PIT mask excluding ~drop_frac of the instrument union (csi300-like)."""
    pit = np.ones((t_len, n_inst), dtype=bool)
    n_drop = max(1, int(round(n_inst * drop_frac)))
    for t in range(t_len):
        start = (t * 7) % n_inst
        for k in range(n_drop):
            pit[t, (start + k) % n_inst] = False
    return pit


def test_shared_kernel_ic_matches_reference_large_pit_churn():
    """csi300-sized PIT-churn panel: unified path vs frozen reference (slow-path dates)."""
    t_len, n_inst = 48, 80
    min_cs = 10
    scores, labels = _dense_panels(t_len, n_inst, seed=7)
    # Also punch a few NaNs so joint is not just PIT
    scores[::5, :3] = np.nan
    labels[::7, 5:9] = np.nan
    pit = _csi300_like_pit(t_len, n_inst, drop_frac=0.12)
    offsets = [0, 1, 5, 17, -3]
    got = _shared_kernel(
        scores,
        labels,
        pit,
        metric="ic",
        quantile=0.2,
        min_cross_section=min_cs,
        offsets=offsets,
    )
    ref = _reference_kernel_ic(
        scores, labels, pit, min_cross_section=min_cs, offsets=offsets
    )
    np.testing.assert_allclose(got, ref, rtol=1e-12, atol=0.0)
    # Prove we are exercising re-rank (PIT excludes finite cells)
    n_pit = int(pit.sum() / t_len)
    assert n_pit < n_inst


def test_evaluate_shifted_ic_dense_panel_under_3s():
    """Dense (T=480, N=336) × 199 offsets must finish in < 3.0 s (vectorized path)."""
    t_len, n_inst = 480, 336
    scores, labels = _dense_panels(t_len, n_inst, seed=0)
    pit = np.ones((t_len, n_inst), dtype=bool)
    dates = pd.bdate_range("2018-01-01", periods=t_len)
    ev = _make_evaluator(labels, pit_mask=pit, min_cross_section=10, dates=dates)
    score_df = _score_df(scores, dates)
    offsets = list(range(199))

    t0 = time.perf_counter()
    grid = ev.evaluate_shifted(score_df, "ic", offsets)
    elapsed = time.perf_counter() - t0

    assert grid.values.shape == (199, t_len)
    assert np.all(np.isfinite(grid.values))
    assert elapsed < 3.0, f"evaluate_shifted(199) took {elapsed:.3f}s (budget 3.0s)"
    # Surface measured time for the receipt / human logs
    print(f"PERF dense evaluate_shifted(199) elapsed={elapsed:.4f}s")


def test_evaluate_shifted_ic_churn_panel_under_5s():
    """PIT-churn (T=480, N=336, ~12% drop/date) × 199 offsets must finish in < 5.0 s.

    Mirrors real csi300: every date excludes finite cells → re-rank-within-joint path.
    """
    t_len, n_inst = 480, 336
    scores, labels = _dense_panels(t_len, n_inst, seed=1)
    pit = _csi300_like_pit(t_len, n_inst, drop_frac=0.12)
    dates = pd.bdate_range("2018-01-01", periods=t_len)
    ev = _make_evaluator(labels, pit_mask=pit, min_cross_section=10, dates=dates)
    score_df = _score_df(scores, dates)
    offsets = list(range(199))

    t0 = time.perf_counter()
    grid = ev.evaluate_shifted(score_df, "ic", offsets)
    elapsed = time.perf_counter() - t0

    assert grid.values.shape == (199, t_len)
    assert np.all(np.isfinite(grid.values))
    assert elapsed < 5.0, f"churn evaluate_shifted(199) took {elapsed:.3f}s (budget 5.0s)"
    print(f"PERF churn evaluate_shifted(199) elapsed={elapsed:.4f}s")
