"""Tests for court.pbo — CSCV estimator of Probability of Backtest Overfitting.

Literature vectors and guards follow docs/research/pbo-cscv.md §5 and §6.3–6.4
and docs/design/court-kernel-spec.md §5.3 / §7 (test_pbo.py rows).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from court.pbo import pbo_cscv

# Hand-worked S=4 / N=3 / T=8 fixture from pbo-cscv.md §5.1.
FIXTURE_M = np.array(
    [
        [3, 0, 4],
        [3, 2, 1],
        [3, 4, 6],
        [3, 1, 5],
        [4, 4, 0],
        [2, 5, 5],
        [3, 5, 5],
        [2, 6, 2],
    ],
    dtype=float,
)

MEAN_METRIC = lambda col: float(np.mean(col))  # noqa: E731 — pluggable mean (§5)

LN_ONE_THIRD = math.log(1.0 / 3.0)  # ≈ -1.0986122886681098
EXPECTED_LOGITS = (0.0, LN_ONE_THIRD, 0.0, 0.0, LN_ONE_THIRD, LN_ONE_THIRD)


def test_s4_fixture_logits_phi() -> None:
    """pbo-cscv.md §5.4: six logits in combinations order; phi = 3/6 = 0.5.

    Spec §7: pinned conventions (φ=0.5, λ=0.0, and bit-exact ln(1/3)) use exact
    equality, not approx.
    """
    result = pbo_cscv(FIXTURE_M, n_splits=4, metric=MEAN_METRIC)

    assert result.n_combinations == 6
    assert result.n_lambda_negative == 3
    assert result.phi == 0.5
    assert len(result.logits) == 6
    assert result.logits == EXPECTED_LOGITS


def test_lambda_zero_does_not_count_toward_phi() -> None:
    """Strict λ < 0 only: three zero logits in the fixture do not inflate φ (D4)."""
    result = pbo_cscv(FIXTURE_M, n_splits=4, metric=MEAN_METRIC)

    zero_count = sum(1 for lam in result.logits if lam == 0.0)
    assert zero_count == 3
    # If zeros counted, phi would be 6/6; operational rule yields 3/6.
    assert result.n_lambda_negative == 3
    assert result.phi == 0.5


def test_guard_not_2d() -> None:
    with pytest.raises(ValueError):
        pbo_cscv(np.array([1.0, 2.0, 3.0]), n_splits=2, metric=MEAN_METRIC)


def test_guard_non_finite_values() -> None:
    bad = FIXTURE_M.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        pbo_cscv(bad, n_splits=4, metric=MEAN_METRIC)

    bad_inf = FIXTURE_M.copy()
    bad_inf[1, 1] = np.inf
    with pytest.raises(ValueError):
        pbo_cscv(bad_inf, n_splits=4, metric=MEAN_METRIC)


def test_guard_n_less_than_2() -> None:
    """N=1 is vacuous (pbo-cscv.md §6.4); raise."""
    single = FIXTURE_M[:, :1]
    with pytest.raises(ValueError):
        pbo_cscv(single, n_splits=4, metric=MEAN_METRIC)


def test_guard_n_splits_odd_or_too_small() -> None:
    with pytest.raises(ValueError):
        pbo_cscv(FIXTURE_M, n_splits=3, metric=MEAN_METRIC)
    with pytest.raises(ValueError):
        pbo_cscv(FIXTURE_M, n_splits=1, metric=MEAN_METRIC)
    with pytest.raises(ValueError):
        pbo_cscv(FIXTURE_M, n_splits=0, metric=MEAN_METRIC)


def test_guard_t_not_divisible_by_n_splits() -> None:
    # T=8, S=6 → 8 % 6 != 0
    with pytest.raises(ValueError):
        pbo_cscv(FIXTURE_M, n_splits=6, metric=MEAN_METRIC)


def test_guard_t_less_than_2s() -> None:
    """Amended D5: T >= 2S (block length >= 2). Covers T=0, T=S, and T just under 2S."""
    # T=0: empty matrix must not silently yield φ=0.0
    with pytest.raises(ValueError):
        pbo_cscv(np.empty((0, 2)), n_splits=2, metric=MEAN_METRIC)

    # T=S: block length 1 (S=2, T=2)
    with pytest.raises(ValueError):
        pbo_cscv(np.ones((2, 2), dtype=float), n_splits=2, metric=MEAN_METRIC)

    # T just under 2S with T % S == 0: S=4, 2S=8, T=4 (=S; blocks of length 1)
    with pytest.raises(ValueError):
        pbo_cscv(np.ones((4, 2), dtype=float), n_splits=4, metric=MEAN_METRIC)


def test_guard_non_finite_metric_raises_whole_run() -> None:
    """Non-finite metric on any half fails the whole run (ruling D3; note §6.3)."""

    def sharpe_like(col: np.ndarray) -> float:
        # Zero-variance half → NaN from mean/std.
        std = float(np.std(col, ddof=1))
        if std == 0.0:
            return float("nan")
        return float(np.mean(col) / std)

    # Column 0 of the fixture is constant 3 on rows 1–4; S=2 halves can hit
    # constant slices. Build a matrix that forces a zero-variance half.
    # T=4, N=2, S=2: first trial constant on first two rows.
    values = np.array(
        [
            [1.0, 0.0],
            [1.0, 1.0],
            [2.0, 3.0],
            [0.0, 1.0],
        ],
        dtype=float,
    )
    with pytest.raises(ValueError):
        pbo_cscv(values, n_splits=2, metric=sharpe_like)
