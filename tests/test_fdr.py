"""Tests for court/fdr.py — BH/BY step-up FDR (spec §5.5, bhy.md §2–§3, §6).

Hand-worked N=10 fixture from docs/research/bhy.md §6.
"""

from __future__ import annotations

import numpy as np
import pytest

from court.fdr import fdr_bh, fdr_by, harmonic_number

# Raw p-values in input order H1..H10 (bhy.md §6.3)
P_FIXTURE = [
    0.0400,  # H1
    0.0008,  # H2
    0.0280,  # H3
    0.0900,  # H4
    0.0050,  # H5
    0.0260,  # H6
    0.0100,  # H7
    0.0450,  # H8
    0.0030,  # H9
    0.0280,  # H10
]
Q = 0.05


def test_harmonic_number_10_exact() -> None:
    """Ascending float64 sum must match bhy.md §6.1 pinned value (ruling E8)."""
    assert harmonic_number(10) == 2.9289682539682538


def test_fdr_bh_n10_fixture() -> None:
    """BH at q=0.05: k*=9; reject all except H4 (input index 3).

    Rejection set by label (bhy.md §6.5):
      {H2, H9, H5, H7, H6, H3, H10, H1, H8}
    Input positions (0-based): H2=1, H9=8, H5=4, H7=6, H6=5, H3=2, H10=9, H1=0, H8=7.
    """
    result = fdr_bh(P_FIXTURE, Q)
    assert result.k_star == 9
    assert result.c_factor == 1.0
    assert len(result.reject) == 10
    assert len(result.adjusted_p) == 10

    rejected_positions = [i for i, r in enumerate(result.reject) if r]
    # Everything except H4 (position 3)
    assert rejected_positions == [0, 1, 2, 4, 5, 6, 7, 8, 9]
    assert result.reject[3] is False  # H4 p=0.0900


def test_fdr_bh_step_up_includes_rank_5() -> None:
    """H6 (p=0.026) fails its own τ_5=0.025 but is rejected because k*=9 (step-up).

    bhy.md §6.5 / §7.1 canary: never reject only individual p_i ≤ τ_i lines.
    """
    result = fdr_bh(P_FIXTURE, Q)
    # H6 is input position 5
    assert result.reject[5] is True


def test_fdr_bh_boundary_equality() -> None:
    """H1 (p=0.0400=τ_8) and H8 (p=0.0450=τ_9) ARE rejected under ≤ (bhy.md §6.5)."""
    result = fdr_bh(P_FIXTURE, Q)
    assert result.reject[0] is True  # H1
    assert result.reject[7] is True  # H8


def test_fdr_by_n10_fixture() -> None:
    """BY at q=0.05: k*=3; reject {H2, H9, H5} = positions {1, 8, 4}.

    c_factor == harmonic_number(10) (bhy.md §6.5–6.6).
    """
    result = fdr_by(P_FIXTURE, Q)
    assert result.k_star == 3
    assert result.c_factor == harmonic_number(10)
    assert result.c_factor == 2.9289682539682538

    rejected_positions = [i for i, r in enumerate(result.reject) if r]
    assert rejected_positions == [1, 4, 8]
    # Explicit set check in any order
    assert set(rejected_positions) == {1, 4, 8}


def test_adjusted_p_properties_bh() -> None:
    """Adjusted p: monotone in sorted order; ≤1; adjusted_p[i]≤q ⟺ reject[i]."""
    result = fdr_bh(P_FIXTURE, Q)
    _assert_adjusted_p_properties(P_FIXTURE, result, Q)


def test_adjusted_p_properties_by() -> None:
    """Same adjusted-p properties for BY (bhy.md §3.2 / §7.2)."""
    result = fdr_by(P_FIXTURE, Q)
    _assert_adjusted_p_properties(P_FIXTURE, result, Q)


def _assert_adjusted_p_properties(p_values, result, q: float) -> None:
    adj = np.asarray(result.adjusted_p, dtype=np.float64)
    assert np.all(adj <= 1.0)
    assert np.all(adj >= 0.0)

    # Monotone non-decreasing in sorted order (stable argsort); exact in IEEE-754
    order = np.argsort(np.asarray(p_values, dtype=np.float64), kind="stable")
    adj_sorted = adj[order]
    assert np.all(adj_sorted[1:] >= adj_sorted[:-1])

    for i, (r, a) in enumerate(zip(result.reject, result.adjusted_p, strict=True)):
        assert (a <= q) is r, f"position {i}: adjusted_p={a}, reject={r}, q={q}"


def test_empty_input() -> None:
    """Empty p-vector → k*=0, empty tuples (ruling E5; bhy.md §7.4)."""
    for fn in (fdr_bh, fdr_by):
        result = fn([], Q)
        assert result.k_star == 0
        assert result.reject == ()
        assert result.adjusted_p == ()


def test_fdr_raises_p_out_of_range() -> None:
    with pytest.raises(ValueError):
        fdr_bh([0.1, 1.5], Q)
    with pytest.raises(ValueError):
        fdr_by([0.1, -0.01], Q)


def test_fdr_raises_p_nan() -> None:
    with pytest.raises(ValueError):
        fdr_bh([0.1, float("nan")], Q)
    with pytest.raises(ValueError):
        fdr_by([float("inf"), 0.1], Q)


def test_fdr_raises_bad_q() -> None:
    with pytest.raises(ValueError):
        fdr_bh(P_FIXTURE, 0.0)
    with pytest.raises(ValueError):
        fdr_bh(P_FIXTURE, 1.0)
    with pytest.raises(ValueError):
        fdr_by(P_FIXTURE, -0.1)
    with pytest.raises(ValueError):
        fdr_by(P_FIXTURE, 1.5)


def test_fdr_raises_scalar_p() -> None:
    """0-d scalar must raise (no silent reshape to N=1; spec §3.5 fail-closed)."""
    with pytest.raises(ValueError):
        fdr_bh(0.03, Q)
    with pytest.raises(ValueError):
        fdr_by(0.03, Q)
    with pytest.raises(ValueError):
        fdr_bh(np.float64(0.03), Q)
