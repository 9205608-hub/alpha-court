"""Offset grid feed for noise control (killer-demo.md §5.3; noise-control.md §5).

Common offsets across candidates preserve cross-candidate dependence
(White 2000 Reality Check). Reduction uses court.tstats.t_stat on the demo side.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from court.tstats import t_stat


@dataclass(frozen=True)
class OffsetGrid:
    """G[i, b] = |t| of candidate i at offset δ_b; pool-max nulls = row maxes."""

    offsets: list[int]
    # shape (n_candidates, n_offsets)
    abs_t_grid: np.ndarray
    # length n_offsets: max over candidates at each offset
    pool_max_nulls: np.ndarray

    def individual_nulls(self, candidate_index: int) -> list[float]:
        return [float(x) for x in self.abs_t_grid[candidate_index]]

    def pool_nulls(self) -> list[float]:
        return [float(x) for x in self.pool_max_nulls]


def reduce_abs_t_iid(series: np.ndarray) -> float:
    """Ranking statistic |t_iid| matching declared two-sided protocol (§5.1/§5.3)."""
    tr = t_stat(series, se_kind="iid")
    return float(abs(tr.t))


def build_offset_grid(
    evaluator: Any,
    score_panels: Sequence[pd.DataFrame],
    offsets: list[int],
    *,
    metric: str = "ic",
    progress: bool = False,
) -> OffsetGrid:
    """Evaluate every candidate at every offset; reduce to |t| grid (§5.3).

    Uses ``evaluator.evaluate_shifted(scores, metric, offsets)`` per candidate.
    """
    n = len(score_panels)
    b = len(offsets)
    grid = np.empty((n, b), dtype=np.float64)

    for i, panel in enumerate(score_panels):
        if progress:
            print(f"[grid] candidate {i + 1}/{n} evaluate_shifted…", flush=True)
        result = evaluator.evaluate_shifted(panel, metric, offsets)
        # result.values shape: (n_offsets, T)
        for bi in range(b):
            grid[i, bi] = reduce_abs_t_iid(result.values[bi])

    pool_max = grid.max(axis=0)
    return OffsetGrid(
        offsets=list(offsets),
        abs_t_grid=grid,
        pool_max_nulls=pool_max,
    )
