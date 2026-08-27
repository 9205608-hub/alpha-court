"""Probability of Backtest Overfitting (PBO) via Combinatorially Symmetric
Cross-Validation (CSCV).

Implements Bailey, Borwein, López de Prado & Zhu (2017) Algorithm 2.3 with the
documented step-(c) train/test label correction and the operational φ rule
(strict λ < 0). See docs/research/pbo-cscv.md §3 and docs/design/court-kernel-spec.md
§5.3.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable
from typing import NamedTuple

import numpy as np
from scipy.stats import rankdata


class PboResult(NamedTuple):
    """CSCV estimate of PBO and per-combination logits.

    Attributes
    ----------
    phi :
        Fraction of combinations with λ_c < 0 (strict). Bailey et al. (2017) §3.1;
        pbo-cscv.md §3.5.
    logits :
        One λ_c per combination, in ``itertools.combinations(range(S), S//2)`` order
        (spec ruling D6).
    n_combinations :
        C(S, S/2).
    n_lambda_negative :
        Count of combinations with strict λ_c < 0.
    """

    phi: float
    logits: tuple[float, ...]
    n_combinations: int
    n_lambda_negative: int


def pbo_cscv(
    values: np.ndarray,
    n_splits: int,
    metric: Callable[[np.ndarray], float],
) -> PboResult:
    """Estimate PBO by CSCV on a T×N performance matrix.

    Bailey, Borwein, López de Prado & Zhu (2017), Algorithm 2.3 steps 2–5 and
    §3.1 (φ = left-tail mass of f(λ)). Project mapping: pbo-cscv.md §3.2–§3.5,
    §3.7; court-kernel-spec.md §5.3 (rulings D1–D6).

    Parameters
    ----------
    values :
        T×N matrix: rows time-ordered, columns = trials.
    n_splits :
        Even number of contiguous row-blocks S (paper's S).
    metric :
        Required callable mapping a 1-D half-sample column to a finite float.
        Metric-agnostic procedure (pbo-cscv.md §2.3); no default (ruling D1).

    Returns
    -------
    PboResult
        φ, logits in pinned combination order, combination counts.

    Raises
    ------
    ValueError
        Fail-closed on structural preconditions or non-finite metric output
        (pbo-cscv.md §6.3–6.4; rulings D3, D5).
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"values must be 2-D (T x N); got ndim={arr.ndim}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("values must contain only finite entries")

    t_obs, n_trials = arr.shape
    if n_trials < 2:
        raise ValueError(f"N (n_trials) must be >= 2; got N={n_trials} (vacuous for N=1)")
    if n_splits < 2 or n_splits % 2 != 0:
        raise ValueError(f"n_splits must be even and >= 2; got n_splits={n_splits}")
    if t_obs % n_splits != 0:
        raise ValueError(
            f"T must be divisible by n_splits; got T={t_obs}, n_splits={n_splits}"
        )
    # Amended D5 (2026-07-10): each block ≥ 2 rows ⇒ T ≥ 2S. Also excludes T=0
    # and T=S so an empty/degenerate matrix never yields candidate-favorable φ=0.
    if t_obs < 2 * n_splits:
        raise ValueError(
            f"T must be >= 2 * n_splits (block length >= 2); "
            f"got T={t_obs}, n_splits={n_splits}"
        )

    s = n_splits
    half = s // 2
    block_len = t_obs // s

    # Contiguous row-blocks, time order preserved (Alg. 2.3 step 2; note §3.2).
    # Prefer index masks over materializing every J/J̄ (note §4.2).
    block_row_indices = [
        np.arange(i * block_len, (i + 1) * block_len) for i in range(s)
    ]

    logits: list[float] = []
    n_lambda_negative = 0

    # Combination order pinned to itertools.combinations (ruling D6).
    for is_blocks in itertools.combinations(range(s), half):
        is_set = set(is_blocks)
        oos_blocks = tuple(i for i in range(s) if i not in is_set)

        # Concatenate blocks in original time order (Alg. 2.3(a)–(b)).
        is_rows = np.concatenate([block_row_indices[i] for i in sorted(is_blocks)])
        oos_rows = np.concatenate([block_row_indices[i] for i in sorted(oos_blocks)])

        j_is = arr[is_rows, :]
        j_oos = arr[oos_rows, :]

        # Step (c): IS metrics on training J (paper PDF mislabels J as testing;
        # corrected per pbo-cscv.md §3.4). Step (d): OOS on J̄.
        r_is = np.empty(n_trials, dtype=np.float64)
        r_oos = np.empty(n_trials, dtype=np.float64)
        for n in range(n_trials):
            r_is[n] = float(metric(j_is[:, n]))
            r_oos[n] = float(metric(j_oos[:, n]))

        if not np.all(np.isfinite(r_is)) or not np.all(np.isfinite(r_oos)):
            raise ValueError(
                "metric returned a non-finite value on an IS or OOS half "
                "(fail closed for the whole run; ruling D3)"
            )

        # Ranks: higher = better, best = N; midranks on ties (ruling D2).
        # scipy rankdata: method="average" midranks; higher raw value → higher rank
        # when we want larger rank = better, use rankdata(values) directly.
        r_oos_ranks = rankdata(r_oos, method="average")

        # n* = argmax of IS metric, smallest-index tie-break (np.argmax; ruling D2).
        n_star = int(np.argmax(r_is))

        # ω̄_c = r̄_{n*} / (N+1); λ_c = ln(ω̄/(1-ω̄))  (Alg. 2.3(f)–(g)).
        omega_bar = float(r_oos_ranks[n_star]) / (n_trials + 1)
        # Ranks in {1..N} ⇒ ω̄ ∈ (0,1); still guard division for safety.
        if omega_bar <= 0.0 or omega_bar >= 1.0:
            raise ValueError(
                f"relative OOS rank out of open unit interval: omega_bar={omega_bar}"
            )
        lambda_c = math.log(omega_bar / (1.0 - omega_bar))
        logits.append(lambda_c)

        # φ counts strict λ < 0 only (note §3.5; ruling D4).
        # Operational identity: λ < 0 ⟺ r̄_{n*} < (N+1)/2.
        if lambda_c < 0.0:
            n_lambda_negative += 1

    n_combinations = len(logits)
    phi = n_lambda_negative / n_combinations
    return PboResult(
        phi=phi,
        logits=tuple(logits),
        n_combinations=n_combinations,
        n_lambda_negative=n_lambda_negative,
    )
