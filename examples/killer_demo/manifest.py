"""run_config.json manifest (killer-demo.md §9.2)."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from examples.killer_demo.config import SWEEP_SEEDS, DemoConfig


def _pkg_version(name: str) -> str:
    try:
        mod = __import__(name)
        return str(getattr(mod, "__version__", "unknown"))
    except Exception:  # noqa: BLE001 — manifest best-effort
        return "unknown"


def build_run_config(
    cfg: DemoConfig,
    *,
    window: dict[str, str],
    t_len: int,
    data_version: dict[str, Any],
    court_version: str,
    adapter_version: str,
    offsets: list[int],
    accused_trial_id: str,
    n_survivors: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the full-chain run manifest (§9.2)."""
    try:
        import qlib

        qlib_version = getattr(qlib, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        qlib_version = "unavailable"

    try:
        import scipy

        scipy_version = scipy.__version__
    except Exception:  # noqa: BLE001
        scipy_version = "unknown"

    manifest: dict[str, Any] = {
        "master_seed": cfg.master_seed,
        "sweep_seeds": list(SWEEP_SEEDS),
        "thresholds": {
            "fdr_q": cfg.fdr_q,
            "dsr_confidence": cfg.dsr_confidence,
            "pbo_phi_threshold": cfg.pbo_phi_threshold,
            "noise_alpha": cfg.noise_alpha,
            "n_splits": cfg.n_splits,
        },
        "n_candidates": cfg.n_candidates,
        "B": cfg.n_offsets,
        "delta_min": cfg.delta_min,
        "window": dict(window),
        "T": t_len,
        "S": cfg.n_splits,
        "universe": cfg.universe,
        "metric": cfg.metric,
        "data_version": dict(data_version),
        "court_version": court_version,
        "adapter_version": adapter_version,
        "qlib_version": qlib_version,
        "numpy_version": np.__version__,
        "scipy_version": scipy_version,
        "pandas_version": pd.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "offsets": list(offsets),
        "accused_trial_id": accused_trial_id,
        "n_survivors": n_survivors,
    }
    if extra:
        manifest.update(extra)
    return manifest


def write_run_config(out_dir: str | Path, manifest: dict[str, Any]) -> Path:
    path = Path(out_dir) / "run_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return path
