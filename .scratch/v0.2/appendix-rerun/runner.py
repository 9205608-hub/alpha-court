"""Commander-side β_t appendix-only re-run (rework-02 accepted at `a51f66e4`).

The hero main sweep (2026-07-18/19, 880 arms) stays untouched and ACCEPTED; only
the appendix arms were quarantined (t3.0 silent fallback-β; matched-β bracket
clamped at the 0.05 grid floor). This driver replicates exactly the appendix
invocation in ``run.py`` (the ``cfg.run_beta_t_appendix`` block) against the
delivered fail-closed path, with the re-frozen calibration (existing 14 β* keys
verified bit-identical; single new key 3.0) at R = cfg.r0.

Usage: python -m .scratch... (run via path) <out_dir> <calibration.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from examples.power_calibration.beta_t import run_beta_t_power
from examples.power_calibration.calibrate import load_calibration
from examples.power_calibration.config import FROZEN_STRENGTH_GRID, PowerConfig
from examples.power_calibration.run import _make_evaluator


def main() -> int:
    out_dir = Path(sys.argv[1])
    cal_path = sys.argv[2]
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = PowerConfig(
        provider_uri=None,
        out_dir=str(out_dir),
        skip_download=True,
        strength_grid=FROZEN_STRENGTH_GRID,
    )
    calibration = load_calibration(cal_path)
    (out_dir / "rerun_config.json").write_text(
        json.dumps(
            {
                "purpose": "beta_t appendix-only re-run (rework-02, quarantine lift)",
                "r": cfg.r0,
                "targets": list(cfg.beta_t_icir_targets),
                "calibration": str(cal_path),
                "match_beta_grid": "relative [b/2, 4b] (rework-02 FIX-B default)",
            },
            indent=2,
        )
        + "\n"
    )
    evaluator = _make_evaluator(cfg)
    payload = run_beta_t_power(
        cfg,
        evaluator=evaluator,
        calibration=calibration,
        out_dir=out_dir / "beta_t",
        n_seeds=cfg.r0,
        targets=cfg.beta_t_icir_targets,
    )
    (out_dir / "beta_t_appendix.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    print("[appendix-rerun] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
