"""Court-arm battery configuration (killer-demo.md §5.2 / §6 v0.2).

Order: fdr_by → dsr → pbo_cscv → noise pool_max → noise individual × N.

Callers pass the base PBO metric name (``\"sharpe\"``); the judge resolves the
direction-consistent form (``abs_sharpe`` under two-sided, signed under
greater, ``neg_sharpe`` under less) and stamps each verdict's ``role``
(selection-verdict-isomorphism.md Q2/Q3). Under the demo's two-sided |t|
scan, DSR is informational and does not vote in aggregation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from court.judge import Application
from examples.killer_demo.config import (
    NOISE_RECIPE,
    RANKING_STAT,
    DemoConfig,
)
from examples.killer_demo.grid import OffsetGrid


def build_applications(
    cfg: DemoConfig,
    *,
    accused_trial_id: str,
    trial_ids: Sequence[str],
    grid: OffsetGrid,
    data_version: dict[str, Any],
) -> list[Application]:
    """104 applications for the full menu (1+1+1+1+100); N for reduced runs."""
    provenance_base: dict[str, Any] = {
        "recipe": NOISE_RECIPE,
        "delta_min": cfg.delta_min,
        "seed": cfg.master_seed,
        "offsets": list(grid.offsets),
        "ranking_stat": RANKING_STAT,
        "data_version": dict(data_version),
    }

    apps: list[Application] = [
        Application("fdr_by", {"q": cfg.fdr_q}),
        Application(
            "dsr",
            {
                "selected_trial_id": accused_trial_id,
                "confidence": cfg.dsr_confidence,
            },
        ),
        Application(
            "pbo_cscv",
            {
                "selected_trial_id": accused_trial_id,
                "n_splits": cfg.n_splits,
                "phi_threshold": cfg.pbo_phi_threshold,
                "metric": "sharpe",
            },
        ),
        Application(
            "noise_control",
            {
                "mode": "pool_max",
                "alpha": cfg.noise_alpha,
                "null_stats": grid.pool_nulls(),
                **provenance_base,
            },
        ),
    ]

    for i, tid in enumerate(trial_ids):
        apps.append(
            Application(
                "noise_control",
                {
                    "mode": "individual",
                    "alpha": cfg.noise_alpha,
                    "judged_trial_id": tid,
                    "null_stats": grid.individual_nulls(i),
                    **provenance_base,
                },
            )
        )
    return apps
