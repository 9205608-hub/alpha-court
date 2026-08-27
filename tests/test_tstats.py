"""Tests for court/tstats.py — t statistic and p-from-t (spec §5.4, bhy.md §4).

Hand-worked vectors from court-kernel-spec.md §5.4. Tolerance: abs=1e-9.
"""

from __future__ import annotations

import math

import pytest

from court.tstats import p_from_t, t_stat


def test_t_stat_iid() -> None:
    """values = [1, 2, 3]: x̄=2, Bessel σ̂=1 ⇒ se=1/√3, t from float64 pipeline.

    Derivation (spec §5.4; referee re-pin 2026-07-10):
      mean = 2.0
      sample variance (ddof=1) = ((1-2)²+(2-2)²+(3-2)²)/(3-1) = 1 ⇒ σ̂ = 1
      se_iid = σ̂/√T = 1/√3 == 0.5773502691896258 (float64)
      t_iid = mean/se = 2.0/0.5773502691896258 == 3.464101615137754
      (the simultaneous pin t == 2√3 ≈ 3.4641016151377544 is 1 ulp off the
      pipeline value and is not used; assert exact == on the pipeline t)
    """
    result = t_stat([1.0, 2.0, 3.0])
    assert result.mean == pytest.approx(2.0, abs=1e-9)
    assert result.n_obs == 3
    assert result.se == pytest.approx(0.5773502691896258, abs=1e-9)
    assert result.t == 3.464101615137754
    assert result.t == 2.0 / 0.5773502691896258


def test_t_stat_newey_west_lags_1() -> None:
    """Same series, newey_west lags=1: γ̂₀=2/3, γ̂₁=0, LRV=2/3, t=3√2.

    Derivation (spec §5.4; Newey & West 1987; bhy.md §4.3):
      values = [1, 2, 3], mean = 2, deviations = (-1, 0, 1), T = 3
      γ̂₀ = (1/T) Σ d_t² = (1+0+1)/3 = 2/3
      γ̂₁ = (1/T) Σ_{t=1}^{T-1} d_t d_{t+1} = ((-1)·0 + 0·1)/3 = 0
      Bartlett weight for ℓ=1, L=1: 1 − 1/(1+1) = 1/2
      LRV = γ̂₀ + 2·(1/2)·γ̂₁ = 2/3 + 0 = 2/3
      se = √(LRV/T) = √(2/9) ≈ 0.4714045207910317
      t = mean/se = 2 / √(2/9) = 2·√(9/2)/1 = 3√2 ≈ 4.242640687119285
    """
    result = t_stat([1.0, 2.0, 3.0], se_kind="newey_west", lags=1)
    assert result.mean == pytest.approx(2.0, abs=1e-9)
    assert result.n_obs == 3
    assert result.se == pytest.approx(0.4714045207910317, abs=1e-9)
    assert result.t == pytest.approx(4.242640687119285, abs=1e-9)
    assert result.t == pytest.approx(3.0 * math.sqrt(2.0), abs=1e-9)


def test_p_from_t_two_sided() -> None:
    """z at Φ=0.975 → two-sided p ≈ 0.05 (HLZ §3.5 fn 26; bhy.md §4.2)."""
    p = p_from_t(1.959963984540054, "two-sided")
    assert p == pytest.approx(0.05, abs=1e-9)


def test_p_from_t_greater() -> None:
    """z at Φ=0.95 → greater-tailed p ≈ 0.05."""
    p = p_from_t(1.6448536269514722, "greater")
    assert p == pytest.approx(0.05, abs=1e-9)


def test_p_from_t_less() -> None:
    """z at Φ=0.05 → less-tailed p ≈ 0.05."""
    p = p_from_t(-1.6448536269514722, "less")
    assert p == pytest.approx(0.05, abs=1e-9)


def test_p_from_t_extreme_tail_no_underflow() -> None:
    """Extreme |t| must not underflow to exactly 0 (a finite t has p > 0).

    ``1 − Φ(|t|)`` cancels catastrophically for |t| ≳ 8.3 and returns 0.0,
    while the survival function stays accurate into the deep tail. A p-value
    fed to BHY adjusted-p must never be a spurious exact zero.
    """
    for t in (8.3, 10.0, 12.0, 15.0):
        assert p_from_t(t, "two-sided") > 0.0, f"two-sided underflow at t={t}"
        assert p_from_t(t, "greater") > 0.0, f"greater underflow at t={t}"
    # accurate deep-tail value (independent reference: 2·Φ(−10) = 1.524e-23)
    assert p_from_t(10.0, "two-sided") == pytest.approx(1.524e-23, rel=1e-3)


# --- Guards (spec §5.4; rulings E2/E3) ---


def test_t_stat_raises_n_obs_lt_2() -> None:
    with pytest.raises(ValueError):
        t_stat([1.0])


def test_t_stat_raises_non_finite() -> None:
    with pytest.raises(ValueError):
        t_stat([1.0, float("nan"), 3.0])
    with pytest.raises(ValueError):
        t_stat([1.0, float("inf"), 3.0])


def test_t_stat_raises_se_zero_iid() -> None:
    """Constant series ⇒ σ̂=0 ⇒ se=0 → raise."""
    with pytest.raises(ValueError):
        t_stat([2.0, 2.0, 2.0])


def test_t_stat_raises_unknown_se_kind() -> None:
    with pytest.raises(ValueError):
        t_stat([1.0, 2.0, 3.0], se_kind="hac")


def test_t_stat_raises_newey_west_without_lags() -> None:
    with pytest.raises(ValueError):
        t_stat([1.0, 2.0, 3.0], se_kind="newey_west")
    with pytest.raises(ValueError):
        t_stat([1.0, 2.0, 3.0], se_kind="newey_west", lags=None)


def test_t_stat_raises_newey_west_bad_lags() -> None:
    with pytest.raises(ValueError):
        t_stat([1.0, 2.0, 3.0], se_kind="newey_west", lags=-1)
    with pytest.raises(ValueError):
        t_stat([1.0, 2.0, 3.0], se_kind="newey_west", lags=3)  # lags >= T
    with pytest.raises(ValueError):
        t_stat([1.0, 2.0, 3.0], se_kind="newey_west", lags=1.5)  # type: ignore[arg-type]


def test_t_stat_raises_lags_with_iid() -> None:
    with pytest.raises(ValueError):
        t_stat([1.0, 2.0, 3.0], se_kind="iid", lags=1)


def test_p_from_t_raises_bad_direction() -> None:
    with pytest.raises(ValueError):
        p_from_t(1.0, "both")


def test_p_from_t_raises_non_finite_t() -> None:
    with pytest.raises(ValueError):
        p_from_t(float("nan"), "two-sided")
    with pytest.raises(ValueError):
        p_from_t(float("inf"), "two-sided")
