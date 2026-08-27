"""Directed-t offset jury for the greater-battery (power-calibration.md §5).

FRESH construction — does **not** reuse ``killer_demo.grid`` (hardwired
``abs_t_grid`` / ``abs_t_iid``). Under ``direction="greater"`` the ranking
statistic is signed ``t`` (court.tstats.t_stat), and pool nulls are the
per-offset **signed** max-of-noise.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from court.tstats import t_stat


@dataclass(frozen=True)
class DirectedTGrid:
    """G[i, b] = signed t of candidate i at offset δ_b; pool-max = max over i.

    Parameters
    ----------
    offsets:
        Shared offset list (White 2000 common offsets).
    t_grid:
        Shape (n_candidates, n_offsets) signed t values.
    pool_max_nulls:
        Length n_offsets: signed max over the noise pool at each offset.
        For the power experiment this is max-of-n_noise (injected excluded
        from the null max when built via ``from_noise_and_injected``).
    """

    offsets: list[int]
    t_grid: np.ndarray
    pool_max_nulls: np.ndarray

    def individual_nulls(self, candidate_index: int) -> list[float]:
        return [float(x) for x in self.t_grid[candidate_index]]

    def pool_nulls(self) -> list[float]:
        return [float(x) for x in self.pool_max_nulls]


def reduce_t_iid(series: np.ndarray) -> float:
    """Ranking statistic t_iid matching declared greater protocol (§5 / F2)."""
    tr = t_stat(series, se_kind="iid")
    return float(tr.t)


def build_directed_t_grid(
    evaluator: Any,
    score_panels: Sequence[pd.DataFrame],
    offsets: list[int],
    *,
    metric: str = "ic",
    progress: bool = False,
) -> DirectedTGrid:
    """Evaluate every candidate at every offset; reduce to signed-t grid (§5).

    Uses ``evaluator.evaluate_shifted(scores, metric, offsets)`` per candidate.
    Pool-max nulls = max over all provided panels (caller passes noise-only
    when max-of-99 is required).
    """
    n = len(score_panels)
    b = len(offsets)
    grid = np.empty((n, b), dtype=np.float64)

    for i, panel in enumerate(score_panels):
        if progress:
            print(f"[jury] candidate {i + 1}/{n} evaluate_shifted…", flush=True)
        result = evaluator.evaluate_shifted(panel, metric, offsets)
        # result.values shape: (n_offsets, T)
        for bi in range(b):
            grid[i, bi] = reduce_t_iid(result.values[bi])

    pool_max = grid.max(axis=0) if n > 0 else np.array([], dtype=np.float64)
    return DirectedTGrid(
        offsets=list(offsets),
        t_grid=grid,
        pool_max_nulls=pool_max,
    )


def inject_row(
    noise_grid: DirectedTGrid,
    injected_t_row: np.ndarray,
) -> DirectedTGrid:
    """Stack injected candidate as row 0; keep pool_max as noise-only max-of-99.

    The power experiment caches noise jury once; each β only evaluates the
    injected factor's shift row. Pool-max nulls stay the signed max-of-noise
    (power-calibration.md §5 compute reuse).
    """
    row = np.asarray(injected_t_row, dtype=np.float64).reshape(1, -1)
    if row.shape[1] != noise_grid.t_grid.shape[1]:
        raise ValueError(
            f"injected row width {row.shape[1]} != noise n_offsets "
            f"{noise_grid.t_grid.shape[1]}"
        )
    full = np.vstack([row, noise_grid.t_grid])
    return DirectedTGrid(
        offsets=list(noise_grid.offsets),
        t_grid=full,
        pool_max_nulls=np.asarray(noise_grid.pool_max_nulls, dtype=np.float64),
    )


def directed_t_row(
    evaluator: Any,
    panel: pd.DataFrame,
    offsets: list[int],
    *,
    metric: str = "ic",
) -> np.ndarray:
    """Signed-t vector length n_offsets for one panel."""
    result = evaluator.evaluate_shifted(panel, metric, offsets)
    b = len(offsets)
    row = np.empty(b, dtype=np.float64)
    for bi in range(b):
        row[bi] = reduce_t_iid(result.values[bi])
    return row
