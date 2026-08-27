"""Greater-battery applications (power-calibration.md §5; ticket reference wiring).

Built FRESH — does not call ``killer_demo.battery`` (hardwired two-sided
provenance). All trials declare ``direction="greater"``; DSR is discriminating;
PBO uses signed ``sharpe`` (judge resolves form from direction).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from court.judge import Application
from examples.power_calibration.config import (
    NOISE_RECIPE,
    RANKING_STAT,
    PowerConfig,
)
from examples.power_calibration.jury import DirectedTGrid


def build_greater_applications(
    cfg: PowerConfig,
    *,
    selected_trial_id: str,
    trial_ids: Sequence[str],
    grid: DirectedTGrid,
    data_version: dict[str, Any],
    master_seed: int,
    check_pool_max_consistency: bool = True,
) -> list[Application]:
    """Build fdr_by → dsr → pbo_cscv → pool_max → individual × N applications.

    Parameters
    ----------
    selected_trial_id:
        Accused for DSR/PBO (natural winner, or forced injected for submission
        power).
    check_pool_max_consistency:
        Bookkeeping flag for callers; pool-max assertion is enforced outside
        the judge (disabled on the forced-submission branch, §9).
    """
    _ = check_pool_max_consistency  # documented for callers; assertion is external
    provenance_base: dict[str, Any] = {
        "recipe": NOISE_RECIPE,
        "delta_min": cfg.delta_min,
        "seed": master_seed,
        "offsets": list(grid.offsets),
        "ranking_stat": RANKING_STAT,
        "data_version": dict(data_version),
    }

    apps: list[Application] = [
        Application("fdr_by", {"q": cfg.fdr_q}),
        Application(
            "dsr",
            {
                "selected_trial_id": selected_trial_id,
                "confidence": cfg.dsr_confidence,
            },
        ),
        Application(
            "pbo_cscv",
            {
                "selected_trial_id": selected_trial_id,
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
