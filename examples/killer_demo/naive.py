"""Naive selection arm (killer-demo.md §5.1).

Full-window in-sample argmax |t| with court.tstats.t_stat (same function the
judge uses). Sign flips allowed (two-sided garden of forking paths).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from court.tstats import t_stat


@dataclass(frozen=True)
class NaivePick:
    """Result of naive max-|t| selection (§5.1)."""

    trial_id: str
    trial_index: int
    t: float
    abs_t: float
    direction: str  # "long" if t >= 0 else "contrarian" (flipped negative)
    naive_p: float
    annualized_icir: float
    all_abs_t: tuple[float, ...]
    all_t: tuple[float, ...]


def compute_t_values(
    series_list: Sequence[np.ndarray | Sequence[float]],
    *,
    se_kind: str = "iid",
) -> list[float]:
    """Per-factor t via ``court.tstats.t_stat`` (killer-demo.md §5.1)."""
    out: list[float] = []
    for values in series_list:
        tr = t_stat(values, se_kind=se_kind)
        out.append(float(tr.t))
    return out


def naive_select(
    trial_ids: Sequence[str],
    series_list: Sequence[np.ndarray | Sequence[float]],
    *,
    se_kind: str = "iid",
    periods_per_year: float = 252.0,
) -> NaivePick:
    """Pick the accused: argmax |t|; ties → smallest trial index (§5.1)."""
    if len(trial_ids) != len(series_list):
        raise ValueError("trial_ids and series_list length mismatch")
    if not trial_ids:
        raise ValueError("empty trial list")

    t_vals = compute_t_values(series_list, se_kind=se_kind)
    abs_t = [abs(t) for t in t_vals]
    # argmax |t|; ties: smallest index
    best_i = 0
    best_a = abs_t[0]
    for i in range(1, len(abs_t)):
        if abs_t[i] > best_a:
            best_a = abs_t[i]
            best_i = i

    t_star = t_vals[best_i]
    n_obs = len(np.asarray(series_list[best_i], dtype=np.float64))
    naive_p = float(2.0 * (1.0 - norm.cdf(best_a)))
    # annualized ICIR = t/√T × √252 (dual-reported; monotone in t) — §5.1
    icir = float(t_star / np.sqrt(n_obs) * np.sqrt(periods_per_year))

    return NaivePick(
        trial_id=trial_ids[best_i],
        trial_index=best_i,
        t=float(t_star),
        abs_t=float(best_a),
        direction="long" if t_star >= 0 else "contrarian",
        naive_p=naive_p,
        annualized_icir=icir,
        all_abs_t=tuple(abs_t),
        all_t=tuple(t_vals),
    )
