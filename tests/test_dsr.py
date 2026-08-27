"""Literature-vector tests for court/dsr.py (dsr.md §4.3–§4.5; spec §7).

Written first under TDD; implementation follows.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.stats import norm

from court.dsr import (
    EULER_MASCHERONI,
    avg_pairwise_correlation,
    dsr,
    expected_max_sr,
    implied_independent_trials,
    rho_is_ill_conditioned,
)

# ---------------------------------------------------------------------------
# dsr.md §4.3 — expected maximum SR
# ---------------------------------------------------------------------------


def test_expected_max_sr_hand_vector() -> None:
    """dsr.md §4.3: E=0, std=0.5, N=10 → E[max] ≈ 0.78729915067."""
    n_trials = 10.0
    sr_trials_std = 0.5
    gamma = EULER_MASCHERONI

    # Complementary-tail quantiles (same construction as production code)
    z1 = float(norm.isf(1.0 / n_trials))
    z2 = float(norm.isf(1.0 / (n_trials * math.e)))
    max_z = (1.0 - gamma) * z1 + gamma * z2
    assert max_z == pytest.approx(1.57459830135, abs=1e-9)

    result = expected_max_sr(0.0, sr_trials_std, n_trials)
    assert result == pytest.approx(0.78729915067, abs=1e-9)
    assert result == pytest.approx(0.0 + sr_trials_std * max_z, abs=1e-12)


def test_expected_max_sr_large_n_isf_stable() -> None:
    """dsr.md §5.5: isf avoids low-precision 1-1/N; finite at extreme N."""
    n = 1e9
    z1 = float(norm.isf(1.0 / n))
    z2 = float(norm.isf(1.0 / (n * math.e)))
    assert math.isfinite(z1)
    assert math.isfinite(z2)
    # Production path must match isf to 1e-12 at N=1e9
    gamma = EULER_MASCHERONI
    max_z = (1.0 - gamma) * z1 + gamma * z2
    expected = 0.5 * max_z
    result = expected_max_sr(0.0, 0.5, n)
    assert math.isfinite(result)
    assert result == pytest.approx(expected, abs=1e-12)
    assert abs(result - expected) < 1e-12

    # At N≈1e16, ppf(1-1/N) collapses; isf path must remain finite
    huge = expected_max_sr(0.0, 0.5, 1e16)
    assert math.isfinite(huge)
    assert huge > 0.0


# ---------------------------------------------------------------------------
# dsr.md §4.4 — DSR = PSR at expected-max benchmark
# ---------------------------------------------------------------------------


def test_dsr_hand_vector() -> None:
    """dsr.md §4.4: SR=1, T=24, γ3=-0.2, γ4=3.5, std=0.5, N=10."""
    result = dsr(
        sr_hat=1.0,
        n_obs=24,
        skew_hat=-0.2,
        kurt_hat=3.5,
        sr_trials_std=0.5,
        n_trials=10.0,
    )
    assert result.sr_star == pytest.approx(0.78729915067, abs=1e-9)
    assert result.z == pytest.approx(0.75509519676, abs=1e-9)
    assert result.dsr == pytest.approx(0.77490406751, abs=1e-9)
    assert result.var_factor == pytest.approx(1.825, abs=1e-9)
    # dsr and z share one computation path: Φ(z) == dsr
    assert result.dsr == pytest.approx(float(norm.cdf(result.z)), abs=1e-15)


# ---------------------------------------------------------------------------
# dsr.md §4.5 — paper numerical example cross-check
# ---------------------------------------------------------------------------


def test_dsr_paper_cross_check() -> None:
    """dsr.md §4.5: native-frequency paper example at N=100, 46, and Normal N=88."""
    # Native inputs from the note
    sr_hat = 2.5 / math.sqrt(250.0)  # 0.15811388301
    n_obs = 1250
    skew_hat = -3.0
    kurt_hat = 10.0
    # annualized cross-trial var = 1/2 → native std = sqrt((1/2)/250)
    sr_trials_std = math.sqrt((0.5) / 250.0)  # 0.04472135955

    r100 = dsr(sr_hat, n_obs, skew_hat, kurt_hat, sr_trials_std, 100.0)
    assert r100.dsr == pytest.approx(0.90039683445, abs=1e-9)

    r46 = dsr(sr_hat, n_obs, skew_hat, kurt_hat, sr_trials_std, 46.0)
    assert r46.dsr == pytest.approx(0.95050170688, abs=1e-9)

    # Normal moments; paper-rounded figure → looser tolerance 5e-4
    r_norm = dsr(sr_hat, n_obs, 0.0, 3.0, sr_trials_std, 88.0)
    assert r_norm.dsr == pytest.approx(0.9505, abs=5e-4)


# ---------------------------------------------------------------------------
# implied independent trials limits (2014 Eq. 9)
# ---------------------------------------------------------------------------


def test_implied_independent_trials_limits() -> None:
    """ρ̂=0 → N̂=M; ρ̂=1 → N̂=1 (dsr.md §2.c / 2014 Eq. 9)."""
    m = 20
    assert implied_independent_trials(m, 0.0) == pytest.approx(float(m), abs=1e-12)
    assert implied_independent_trials(m, 1.0) == pytest.approx(1.0, abs=1e-12)
    # Midpoint: ρ=0.5, M=5 → 1 + 4*0.5 = 3
    assert implied_independent_trials(5, 0.5) == pytest.approx(3.0, abs=1e-12)


def test_implied_independent_trials_negative_rho_extrapolation() -> None:
    """Negative ρ̂ is allowed: N̂ > M (harsher hurdle; ruling C7)."""
    n_hat = implied_independent_trials(10, -0.1)
    assert n_hat == pytest.approx(1.0 + 9.0 * 1.1, abs=1e-12)
    assert n_hat > 10.0


# ---------------------------------------------------------------------------
# avg_pairwise_correlation + rho_is_ill_conditioned
# ---------------------------------------------------------------------------


def test_avg_pairwise_correlation_perfect() -> None:
    """Identical columns → ρ̂ = 1."""
    col = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    mat = np.column_stack([col, col, col])
    assert avg_pairwise_correlation(mat) == pytest.approx(1.0, abs=1e-12)


def test_avg_pairwise_correlation_orthogonal() -> None:
    """Two uncorrelated series → ρ̂ ≈ 0 (centered, equal length)."""
    # Use a pair with known zero Pearson correlation
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    b = np.array([2.0, 1.0, 0.0, 1.0, 2.0])  # symmetric about center vs linear a
    expected = float(np.corrcoef(a, b)[0, 1])
    mat = np.column_stack([a, b])
    assert avg_pairwise_correlation(mat) == pytest.approx(expected, abs=1e-12)


def test_rho_is_ill_conditioned() -> None:
    """True iff T < ½ M(M-1) (2014 App. A.3 caveat; disclosure, not error)."""
    # M=5 → ½*5*4 = 10 pairs; T=9 → ill-conditioned; T=10 → ok
    assert rho_is_ill_conditioned(9, 5) is True
    assert rho_is_ill_conditioned(10, 5) is False
    assert rho_is_ill_conditioned(100, 5) is False


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_expected_max_sr_n_equals_one_returns_mean() -> None:
    """N=1: max of one draw = mean (ruling C4); no EVT."""
    assert expected_max_sr(0.3, 0.5, 1.0) == pytest.approx(0.3, abs=1e-15)
    assert expected_max_sr(-0.1, 1.0, 1) == pytest.approx(-0.1, abs=1e-15)


def test_expected_max_sr_std_zero_returns_mean() -> None:
    assert expected_max_sr(0.2, 0.0, 10.0) == pytest.approx(0.2, abs=1e-15)


def test_expected_max_sr_hurdle_never_below_mean_small_n() -> None:
    """The expected-max hurdle must never fall below the single-trial mean.

    E[max of N≥1 draws] ≥ E[single draw] = mean for all N ≥ 1, with equality
    at N=1. The EVT approximation (Eq. (1)) is only valid for N ≫ 1 and dips
    *below* the mean for N in (1, ~1.29); left unclamped it makes the DSR
    deflation anti-conservative — a multiplicity adjustment that *lowers* the
    hurdle, certifying near-zero-skill strategies. dsr.md §5.5 flags N as low
    as 2; N̂ is real-valued so the whole (1, 2) band is reachable
    (e.g. two trials at ρ̂≈0.7 → N̂≈1.3).
    """
    for n in (1.01, 1.05, 1.1, 1.2, 1.28, 1.5, 2.0):
        assert expected_max_sr(0.0, 0.5, n) >= 0.0, f"negative hurdle at N={n}"
    # non-zero mean: hurdle must not drop below that mean either
    assert expected_max_sr(0.3, 0.5, 1.2) >= 0.3


def test_dsr_does_not_certify_zero_skill_at_small_n() -> None:
    """A near-zero-skill candidate at a small implied trial count must not pass.

    Two correlated trials give N̂≈1.2; with the pre-clamp negative hurdle the
    inflated z produced DSR≈0.957 — clearing a 0.95 court on essentially no
    skill (the exact failure the court exists to prevent).
    """
    result = dsr(
        sr_hat=0.05,
        n_obs=250,
        skew_hat=0.0,
        kurt_hat=3.0,
        sr_trials_std=0.5,
        n_trials=1.2,
    )
    assert result.sr_star >= 0.0
    assert result.dsr < 0.95


def test_guard_n_trials_lt_one() -> None:
    with pytest.raises(ValueError):
        expected_max_sr(0.0, 0.5, 0.5)
    with pytest.raises(ValueError):
        expected_max_sr(0.0, 0.5, 0.0)
    with pytest.raises(ValueError):
        dsr(1.0, 24, 0.0, 3.0, 0.5, 0.9)


def test_guard_sr_trials_std_negative() -> None:
    with pytest.raises(ValueError):
        expected_max_sr(0.0, -0.01, 10.0)
    with pytest.raises(ValueError):
        dsr(1.0, 24, 0.0, 3.0, -0.1, 10.0)


def test_guard_implied_trials_raw_lt_one() -> None:
    with pytest.raises(ValueError):
        implied_independent_trials(0, 0.5)


def test_guard_avg_corr_outside_open_closed() -> None:
    """ρ̂ accepted on (−1, 1]; outside raises (ruling C7)."""
    with pytest.raises(ValueError):
        implied_independent_trials(5, -1.0)  # not in (−1, 1]
    with pytest.raises(ValueError):
        implied_independent_trials(5, -1.01)
    with pytest.raises(ValueError):
        implied_independent_trials(5, 1.01)
    # Boundary +1 is allowed
    assert implied_independent_trials(5, 1.0) == 1.0


def test_guard_avg_pairwise_constant_column() -> None:
    mat = np.array(
        [
            [1.0, 2.0],
            [1.0, 3.0],
            [1.0, 4.0],
        ],
        dtype=np.float64,
    )
    with pytest.raises(ValueError):
        avg_pairwise_correlation(mat)


def test_guard_avg_pairwise_shape_and_finite() -> None:
    with pytest.raises(ValueError):
        avg_pairwise_correlation(np.array([1.0, 2.0, 3.0]))  # not 2-D
    with pytest.raises(ValueError):
        avg_pairwise_correlation(np.ones((3, 1)))  # M < 2
    with pytest.raises(ValueError):
        avg_pairwise_correlation(np.ones((1, 2)))  # T < 2
    bad = np.array([[1.0, 2.0], [float("nan"), 3.0]])
    with pytest.raises(ValueError):
        avg_pairwise_correlation(bad)


@pytest.mark.parametrize(
    "fn,args",
    [
        (expected_max_sr, (0.0, float("nan"), 10.0)),
        (expected_max_sr, (float("nan"), 0.5, 10.0)),
        (expected_max_sr, (0.0, 0.5, float("inf"))),
        (implied_independent_trials, (5, float("nan"))),
        (dsr, (1.0, 24, float("nan"), 3.5, 0.5, 10.0)),
        (dsr, (float("nan"), 24, -0.2, 3.5, 0.5, 10.0)),
        (dsr, (1.0, 24, -0.2, 3.5, float("nan"), 10.0)),
        (dsr, (1.0, 24, -0.2, 3.5, 0.5, float("nan"))),
    ],
)
def test_guard_non_finite_scalars_dsr(fn, args) -> None:
    """Every public scalar float param must be finite (spec §6)."""
    with pytest.raises(ValueError, match="non-finite"):
        fn(*args)
