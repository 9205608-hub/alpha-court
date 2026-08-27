"""Hand-worked vectors and guards for court.noise.empirical_null_p.

Sources:
- docs/design/noise-control.md §8 (vectors 1–4)
- docs/design/court-kernel-spec.md §5.6, §7 (test_noise.py rows)
- Formula: Phipson & Smyth (2010) Eq. (2): p̂ = (1 + #{null_j ≥ observed}) / (K + 1)
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from court.noise import NoiseResult, empirical_null_p

# ---------------------------------------------------------------------------
# §8 hand-worked vectors (α = 0.05 default)
# ---------------------------------------------------------------------------


def test_vector1_basic_reject() -> None:
    """noise-control.md §8.1: observed=2.0, nulls=(1.0, 2.5, 0.5, 3.0), K=4.

    #{null ≥ 2.0} = 2 (2.5, 3.0) → p̂ = (1+2)/(4+1) = 3/5 = 0.6 → reject.
    """
    r = empirical_null_p(2.0, (1.0, 2.5, 0.5, 3.0))
    assert isinstance(r, NoiseResult)
    assert r.n_nulls == 4
    assert r.n_at_least == 2
    assert r.p_hat == 0.6
    assert r.p_hat == 3 / 5
    assert r.decision == "reject"


def test_vector2_tie_counts_against() -> None:
    """noise-control.md §8.2: tie at observed counts against the candidate.

    observed=2.0, nulls=(1.9, 2.0, 0.5), K=3.
    #{null ≥ 2.0} = 1 (the exact tie) → p̂ = (1+1)/(3+1) = 2/4 = 0.5 → reject.
    """
    r = empirical_null_p(2.0, (1.9, 2.0, 0.5))
    assert r.n_nulls == 3
    assert r.n_at_least == 1
    assert r.p_hat == 0.5
    assert r.p_hat == 2 / 4
    assert r.decision == "reject"


def test_vector3_all_nulls_below_pass() -> None:
    """noise-control.md §8.3: K=199 all nulls < observed → p̂ = 1/200 = 0.005 → pass.

    At α=0.05, 0.005 ≤ 0.05 ⇒ decision "pass".
    """
    nulls = np.full(199, 3.0, dtype=np.float64)
    r = empirical_null_p(4.0, nulls)
    assert r.n_nulls == 199
    assert r.n_at_least == 0
    assert r.p_hat == 0.005
    assert r.p_hat == 1 / 200
    assert r.decision == "pass"


def test_vector4_resolution_floor_never_zero() -> None:
    """noise-control.md §8.4: with K=199, min attainable p̂ is 1/200 = 0.005; never 0.0.

    Sweep observed values; add-one form always has p̂ ≥ 1/(K+1).
    """
    k = 199
    nulls = np.linspace(-5.0, 5.0, k, dtype=np.float64)
    floor = 1.0 / (k + 1)
    for observed in (-10.0, -1.0, 0.0, 1.0, 5.0, 10.0, 100.0):
        r = empirical_null_p(observed, nulls)
        assert r.p_hat >= floor
        assert r.p_hat != 0.0
        assert r.p_hat > 0.0
        assert r.n_nulls == k
    # Extreme above all nulls: n_at_least == 0 → exact floor
    r_top = empirical_null_p(float(nulls.max()) + 1.0, nulls)
    assert r_top.n_at_least == 0
    assert r_top.p_hat == floor
    assert r_top.p_hat == 0.005


# ---------------------------------------------------------------------------
# Guards (spec §5.6 / fail-closed)
# ---------------------------------------------------------------------------


def test_guard_empty_nulls() -> None:
    with pytest.raises(ValueError, match="empty"):
        empirical_null_p(1.0, [])


def test_guard_nulls_not_1d() -> None:
    with pytest.raises(ValueError, match="1-D|1D|one-dimensional|ndim"):
        empirical_null_p(1.0, np.array([[1.0, 2.0], [3.0, 4.0]]))


def test_guard_nulls_non_finite() -> None:
    with pytest.raises(ValueError, match="finite|non-finite|nan|inf"):
        empirical_null_p(1.0, [1.0, float("nan"), 2.0])
    with pytest.raises(ValueError, match="finite|non-finite|nan|inf"):
        empirical_null_p(1.0, [1.0, float("inf")])


def test_guard_observed_non_finite() -> None:
    with pytest.raises(ValueError, match="finite|non-finite|nan|inf"):
        empirical_null_p(float("nan"), [1.0, 2.0])
    with pytest.raises(ValueError, match="finite|non-finite|nan|inf"):
        empirical_null_p(float("inf"), [1.0, 2.0])
    with pytest.raises(ValueError, match="finite|non-finite|nan|inf"):
        empirical_null_p(float("-inf"), [1.0, 2.0])


def test_guard_alpha_outside_open_unit_interval() -> None:
    with pytest.raises(ValueError, match="alpha"):
        empirical_null_p(1.0, [0.5], alpha=0.0)
    with pytest.raises(ValueError, match="alpha"):
        empirical_null_p(1.0, [0.5], alpha=1.0)
    with pytest.raises(ValueError, match="alpha"):
        empirical_null_p(1.0, [0.5], alpha=-0.1)
    with pytest.raises(ValueError, match="alpha"):
        empirical_null_p(1.0, [0.5], alpha=1.5)
    with pytest.raises(ValueError, match="alpha"):
        empirical_null_p(1.0, [0.5], alpha=float("nan"))


def test_decision_at_alpha_boundary() -> None:
    """decision is \"pass\" iff p̂ ≤ α (spec ruling F1)."""
    # p̂ = 0.5 for observed=2.0, nulls with one tie of three
    r_eq = empirical_null_p(2.0, (1.9, 2.0, 0.5), alpha=0.5)
    assert r_eq.p_hat == 0.5
    assert r_eq.decision == "pass"
    r_strict = empirical_null_p(2.0, (1.9, 2.0, 0.5), alpha=0.49)
    assert r_strict.decision == "reject"


def test_accepts_list_and_ndarray() -> None:
    """nulls may be any 1-D sequence; result is deterministic."""
    a = empirical_null_p(2.0, [1.0, 2.5, 0.5, 3.0])
    b = empirical_null_p(2.0, np.array([1.0, 2.5, 0.5, 3.0]))
    assert a == b
    assert math.isfinite(a.p_hat)
