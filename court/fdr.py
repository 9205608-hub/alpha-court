"""False-discovery-rate step-up procedures: Benjamini-Hochberg and Benjamini-Yekutieli.

Formulas:
  BH: k* = max{i : p_{(i)} ≤ (i/N)·q}; reject ranks 1..k*
      (Benjamini & Hochberg 1995 §3.1 expression (1); bhy.md §2.2)
  BY: k* = max{i : p_{(i)} ≤ i·q/(N·c(N))} with c(N) = Σ_{i=1..N} 1/i
      (Benjamini & Yekutieli 2001 Theorem 1.3; HLZ 2016 §3.4.3; bhy.md §3.2)
  Adjusted p: backward min recurrence on the sorted list, clip to [0,1],
      map back via stable sort permutation (bhy.md §2.4 / §3.2 / §7.2; ruling E6)

Naming: functions are ``fdr_bh`` and ``fdr_by`` only. HLZ's finance label for the
harmonic procedure is the BY procedure (bhy.md §7.5 name collision).

Citations: Benjamini & Hochberg (1995); Benjamini & Yekutieli (2001);
Harvey, Liu & Zhu (2016) §3.4.3; docs/research/bhy.md; court-kernel-spec.md §5.5.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np


class FdrResult(NamedTuple):
    k_star: int
    reject: tuple[bool, ...]  # input order; True = H0 rejected (discovery)
    adjusted_p: tuple[float, ...]  # input order; monotone in sorted order, clipped
    c_factor: float  # 1.0 for BH; harmonic_number(N) for BY (N=0 BY sentinel: 1.0)


def harmonic_number(n: int) -> float:
    """n-th harmonic number H_n = Σ_{i=1..n} 1/i (ascending float64 sum).

    Benjamini & Yekutieli (2001) Theorem 1.3 uses c(m) = H_m as the
    arbitrary-dependence multiplier. Summation convention is ascending
    float64 addition so that ``harmonic_number(10) == 2.9289682539682538``
    exactly (bhy.md §6.1; ruling E8).

    Parameters
    ----------
    n :
        Positive integer (family size when used as c(N)).

    Returns
    -------
    float
        H_n in float64.
    """
    if not isinstance(n, (int, np.integer)) or isinstance(n, bool):
        raise ValueError(f"n must be a positive int (got {n!r})")
    n = int(n)
    if n < 1:
        raise ValueError(f"n must be >= 1 (got n={n})")
    s = 0.0
    for i in range(1, n + 1):
        s += 1.0 / i
    return s


def fdr_bh(p_values, q: float) -> FdrResult:
    """Benjamini-Hochberg linear step-up FDR procedure.

    Parameters
    ----------
    p_values :
        Sequence of raw p-values in input (ledger) order.
    q :
        Target FDR level in (0, 1). Required — no default (ruling E4).

    Returns
    -------
    FdrResult
        k_star, reject flags and adjusted p-values in input order, c_factor=1.0.

    Raises
    ------
    ValueError
        Any p outside [0, 1] or non-finite; q not in (0, 1).

    Notes
    -----
    Step-up (Benjamini & Hochberg 1995 §3.1 expression (1); bhy.md §2.2, §7.1)::

        k* = max{i : p_{(i)} ≤ (i/N)·q}
        reject the whole initial segment ranks 1..k* (including ranks that
        fail their own line). Boundary p_{(i)} == τ_i counts (≤).

    Empty input returns k_star=0 and empty tuples (ruling E5; bhy.md §7.4).
    """
    return _fdr_step_up(p_values, q, c_factor=1.0)


def fdr_by(p_values, q: float) -> FdrResult:
    """Benjamini-Yekutieli step-up FDR procedure (harmonic correction).

    Valid under arbitrary dependence among p-values
    (Benjamini & Yekutieli 2001 Theorem 1.3; HLZ 2016 §3.4.3; bhy.md §3.2).

    Parameters
    ----------
    p_values :
        Sequence of raw p-values in input (ledger) order.
    q :
        Target FDR level in (0, 1). Required — no default (ruling E4).

    Returns
    -------
    FdrResult
        k_star, reject flags and adjusted p-values in input order,
        c_factor = harmonic_number(N). Empty input (N=0): k_star=0, empty
        tuples, and c_factor=1.0 as an N=0 sentinel (harmonic_number is
        undefined at 0; do not read this as a BH result — check k_star and
        empty reject/adjusted_p).

    Raises
    ------
    ValueError
        Any p outside [0, 1] or non-finite; q not in (0, 1); 0-d scalar input.

    Notes
    -----
    Critical values::

        τ_i = i·q / (N·c(N)),  c(N) = Σ_{i=1..N} 1/i

    Same step-up semantics as ``fdr_bh`` (bhy.md §7.1). Empty input → k*=0
    with c_factor=1.0 (N=0 sentinel; see Returns).
    """
    p = _as_p_vector(p_values)
    n = p.size
    if n == 0:
        _validate_q(q)
        # N=0 sentinel: c(0) undefined; c_factor=1.0 (not a BH claim — see docstring)
        return FdrResult(k_star=0, reject=(), adjusted_p=(), c_factor=1.0)
    c = harmonic_number(n)
    return _fdr_step_up(p, q, c_factor=c)


def _fdr_step_up(p_values, q: float, c_factor: float) -> FdrResult:
    """Shared BH/BY step-up with critical values τ_i = i·q / (N·c_factor)."""
    p = _as_p_vector(p_values)
    _validate_q(q)
    n = int(p.size)

    if n == 0:
        return FdrResult(k_star=0, reject=(), adjusted_p=(), c_factor=c_factor)

    # Stable sort (ruling E7; bhy.md §6.4)
    order = np.argsort(p, kind="stable")
    p_sorted = p[order]

    # Critical values τ_i for ranks i=1..N (1-based)
    # BH: (i/N)*q = i*q/(N*1); BY: i*q/(N*c(N))
    ranks = np.arange(1, n + 1, dtype=np.float64)
    tau = ranks * q / (n * c_factor)

    # k* = max{i : p_{(i)} ≤ τ_i}, or 0 if none (step-up, ≤)
    passes = p_sorted <= tau
    if np.any(passes):
        # Largest 1-based rank that passes
        k_star = int(np.max(np.nonzero(passes)[0]) + 1)
    else:
        k_star = 0

    # Rejection: whole initial segment 1..k* (bhy.md §7.1)
    reject_sorted = np.zeros(n, dtype=bool)
    if k_star > 0:
        reject_sorted[:k_star] = True

    # Adjusted p-values: backward min recurrence, then clip to [0,1].
    # BY base case = min(1, c(N)·P_(N)) per the referee erratum in bhy.md §3.2
    # and amended spec ruling E6 (2026-07-10): the HLZ-printed init P_(N)
    # violates the identity adjusted_p ≤ q ⟺ reject (counterexample
    # p=(0.04,0.04), q=0.05, c(2)=1.5: k*=0 but doc-literal adjusted values
    # claim two rejections); this convention = R p.adjust("BY") /
    # statsmodels fdr_by. BH (c_factor=1) is the c=1 special case.
    # Recurrence: p̃_(i) = min(p̃_(i+1), (N·c/i)·P_(i)), i = N-1..1.
    adj_sorted = np.empty(n, dtype=np.float64)
    scale = n * c_factor
    adj_sorted[n - 1] = min(1.0, (scale / n) * p_sorted[n - 1])
    for i in range(n - 2, -1, -1):
        # 1-based rank = i+1
        candidate = (scale / (i + 1)) * p_sorted[i]
        adj_sorted[i] = min(adj_sorted[i + 1], candidate)
    adj_sorted = np.clip(adj_sorted, 0.0, 1.0)

    # Map back to input order via the stable sort permutation
    reject = np.empty(n, dtype=bool)
    adjusted_p = np.empty(n, dtype=np.float64)
    reject[order] = reject_sorted
    adjusted_p[order] = adj_sorted

    return FdrResult(
        k_star=k_star,
        reject=tuple(bool(x) for x in reject),
        adjusted_p=tuple(float(x) for x in adjusted_p),
        c_factor=float(c_factor),
    )


def _as_p_vector(p_values) -> np.ndarray:
    p = np.asarray(p_values, dtype=np.float64)
    if p.ndim == 0:
        # Fail-closed: no silent scalar→length-1 coercion (spec §3.5)
        raise ValueError("p_values must be a 1-D array or sequence, not a scalar")
    if p.ndim != 1:
        raise ValueError("p_values must be a 1-D array or sequence")
    if p.size == 0:
        return p
    if not np.all(np.isfinite(p)):
        raise ValueError("p_values contain non-finite entries")
    if np.any(p < 0.0) or np.any(p > 1.0):
        raise ValueError("p_values must all lie in [0, 1]")
    return p


def _validate_q(q: float) -> None:
    if not np.isfinite(q) or not (0.0 < q < 1.0):
        raise ValueError(f"q must be in (0, 1) (got q={q})")
