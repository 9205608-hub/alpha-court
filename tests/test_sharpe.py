"""Literature-vector tests for court/sharpe.py (dsr.md §4.1–§4.2, §5.6; spec §7).

Written first under TDD; implementation follows.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.stats import norm

from court.sharpe import (
    annualized_sr,
    psr,
    series_moments,
    sharpe_ratio,
    sr_standard_error,
    sr_var_factor,
)

# ---------------------------------------------------------------------------
# dsr.md §4.1 — PSR Normal returns
# ---------------------------------------------------------------------------


def test_psr_normal_returns() -> None:
    """dsr.md §4.1: n=24, SR=0.5, SR*=0, γ3=0, γ4=3 → var_factor, z, psr anchors."""
    sr_hat = 0.5
    n_obs = 24
    skew_hat = 0.0
    kurt_hat = 3.0
    sr_benchmark = 0.0

    vf = sr_var_factor(sr_hat, skew_hat, kurt_hat)
    # Spec §7 / dsr.md §4.1 pin exact equality for the rational anchor
    assert vf == 1.125

    se = sr_standard_error(sr_hat, n_obs, skew_hat, kurt_hat)
    z = (sr_hat - sr_benchmark) / se
    assert z == pytest.approx(2.26077666104, abs=1e-9)

    result = psr(sr_hat, sr_benchmark, n_obs, skew_hat, kurt_hat)
    assert result == pytest.approx(0.98811345473, abs=1e-9)
    assert result == pytest.approx(float(norm.cdf(z)), abs=1e-12)


# ---------------------------------------------------------------------------
# dsr.md §4.2 — PSR non-Normal returns (clean z = 2)
# ---------------------------------------------------------------------------


def test_psr_non_normal_returns() -> None:
    """dsr.md §4.2: n=24, SR=0.5, γ3=-0.5, γ4=4 → var_factor=1.4375, z=2, psr."""
    sr_hat = 0.5
    n_obs = 24
    skew_hat = -0.5
    kurt_hat = 4.0
    sr_benchmark = 0.0

    vf = sr_var_factor(sr_hat, skew_hat, kurt_hat)
    # Spec §7 / dsr.md §4.2 pin exact equality for the rational anchor
    assert vf == 1.4375

    se = sr_standard_error(sr_hat, n_obs, skew_hat, kurt_hat)
    z = (sr_hat - sr_benchmark) / se
    assert z == pytest.approx(2.0, abs=1e-9)

    result = psr(sr_hat, sr_benchmark, n_obs, skew_hat, kurt_hat)
    assert result == pytest.approx(0.97724986805, abs=1e-9)


# ---------------------------------------------------------------------------
# dsr.md §5.6 — Normal-case variance-factor identity
# ---------------------------------------------------------------------------


def test_sr_var_factor_normal_identity() -> None:
    """Normal (γ3=0, γ4=3) recovers Lo's 1 + SR²/2 (dsr.md §2.a / §5.6)."""
    for sr in (0.0, 0.5, 1.0):
        expected = 1.0 + 0.5 * sr * sr
        # Spec §7 pins exact equality for the Normal identity
        assert sr_var_factor(sr, 0.0, 3.0) == expected


# ---------------------------------------------------------------------------
# Series moments / sharpe_ratio smoke (Bessel σ, raw kurtosis)
# ---------------------------------------------------------------------------


def test_series_moments_and_sharpe_ratio() -> None:
    """μ̂, σ̂ (Bessel), SR̂, population skew/kurt (raw) on a hand series."""
    values = np.array([0.01, 0.02, -0.005, 0.015, 0.0], dtype=np.float64)
    m = series_moments(values)

    assert m.n_obs == 5
    assert m.mu_hat == pytest.approx(float(np.mean(values)), abs=1e-12)
    assert m.sigma_hat == pytest.approx(float(np.std(values, ddof=1)), abs=1e-12)
    assert m.sr_hat == pytest.approx(m.mu_hat / m.sigma_hat, abs=1e-12)
    assert sharpe_ratio(values) == pytest.approx(m.sr_hat, abs=1e-12)
    # Population (biased) skew / raw kurtosis — scipy defaults used by ruling C1
    from scipy.stats import kurtosis, skew

    assert m.skew_hat == pytest.approx(float(skew(values, bias=True)), abs=1e-12)
    assert m.kurt_hat == pytest.approx(
        float(kurtosis(values, fisher=False, bias=True)), abs=1e-12
    )


def test_sharpe_ratio_source_does_not_call_series_moments() -> None:
    """v0.2-14: lean path — sharpe_ratio body must not call series_moments."""
    import inspect
    import textwrap

    src = textwrap.dedent(inspect.getsource(sharpe_ratio))
    # Drop docstring so comments about full-moments helpers do not false-positive.
    body = src.split('"""', 2)[-1] if '"""' in src else src
    assert "series_moments" not in body
    assert "np.mean" in body
    assert "np.std" in body


def test_annualized_sr_display_only() -> None:
    """BLdP 2012 Eq. (5): SR_ann = √q · SR̂ (display only)."""
    assert annualized_sr(0.5, 252.0) == pytest.approx(0.5 * math.sqrt(252.0), abs=1e-12)


# ---------------------------------------------------------------------------
# Guards (fail-closed)
# ---------------------------------------------------------------------------


def test_guard_n_obs_lt_2() -> None:
    with pytest.raises(ValueError):
        series_moments([1.0])
    with pytest.raises(ValueError):
        sharpe_ratio(np.array([1.0]))
    with pytest.raises(ValueError):
        sr_standard_error(0.5, 1, 0.0, 3.0)
    with pytest.raises(ValueError):
        psr(0.5, 0.0, 1, 0.0, 3.0)


def test_guard_non_finite_values() -> None:
    with pytest.raises(ValueError):
        series_moments([1.0, float("nan")])
    with pytest.raises(ValueError):
        series_moments([1.0, float("inf")])
    with pytest.raises(ValueError):
        sharpe_ratio([0.0, float("-inf")])


def test_guard_sigma_zero() -> None:
    with pytest.raises(ValueError):
        series_moments([1.0, 1.0, 1.0])
    with pytest.raises(ValueError):
        sharpe_ratio(np.array([2.0, 2.0]))


def test_guard_var_factor_non_positive() -> None:
    # Choose extreme skew so var_factor = 1 - γ3·SR + (γ4-1)/4·SR² ≤ 0
    # e.g. sr=1, skew=10, kurt=3 → 1 - 10 + 0.5 = -8.5
    with pytest.raises(ValueError):
        sr_standard_error(1.0, 24, 10.0, 3.0)
    with pytest.raises(ValueError):
        psr(1.0, 0.0, 24, 10.0, 3.0)


def test_guard_periods_per_year_non_positive() -> None:
    with pytest.raises(ValueError):
        annualized_sr(0.5, 0.0)
    with pytest.raises(ValueError):
        annualized_sr(0.5, -12.0)


@pytest.mark.parametrize(
    "fn,kwargs",
    [
        (sr_var_factor, {"sr_hat": float("nan"), "skew_hat": 0.0, "kurt_hat": 3.0}),
        (sr_var_factor, {"sr_hat": 0.5, "skew_hat": float("inf"), "kurt_hat": 3.0}),
        (sr_var_factor, {"sr_hat": 0.5, "skew_hat": 0.0, "kurt_hat": float("-inf")}),
        (
            sr_standard_error,
            {"sr_hat": 0.5, "n_obs": 24, "skew_hat": float("nan"), "kurt_hat": 3.0},
        ),
        (
            psr,
            {
                "sr_hat": 0.5,
                "sr_benchmark": 0.0,
                "n_obs": 24,
                "skew_hat": float("nan"),
                "kurt_hat": 3.0,
            },
        ),
        (
            psr,
            {
                "sr_hat": 0.5,
                "sr_benchmark": float("nan"),
                "n_obs": 24,
                "skew_hat": 0.0,
                "kurt_hat": 3.0,
            },
        ),
        (annualized_sr, {"sr_hat": float("nan"), "periods_per_year": 252.0}),
        (annualized_sr, {"sr_hat": 0.5, "periods_per_year": float("inf")}),
    ],
)
def test_guard_non_finite_scalars_sharpe(fn, kwargs) -> None:
    """Every public scalar float param must be finite (spec §6)."""
    with pytest.raises(ValueError, match="non-finite"):
        fn(**kwargs)
