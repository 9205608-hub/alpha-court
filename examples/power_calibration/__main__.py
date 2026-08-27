"""CLI entry: ``python -m examples.power_calibration`` (power sweep).

Real-data full sweep is a multi-day referee acceptance job. Workers test on
reduced synthetic configs only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapters.qlib_cn import DEFAULT_PROVIDER
from examples.power_calibration.calibrate import load_calibration
from examples.power_calibration.config import (
    FROZEN_STRENGTH_GRID,
    PowerConfig,
)
from examples.power_calibration.run import run_power_sweep


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m examples.power_calibration",
        description=(
            "Power-calibration sweep (power-calibration.md §5): court ROC on a "
            "known injected signal. Uncertified calculator use."
        ),
    )
    p.add_argument(
        "--out",
        type=str,
        default="examples/power_calibration/out",
        help="output directory",
    )
    p.add_argument(
        "--skip-download",
        action="store_true",
        help="do not download the data pack; fail if missing",
    )
    p.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help=f"qlib provider_uri (default {DEFAULT_PROVIDER})",
    )
    p.add_argument(
        "--calibration",
        type=str,
        default=None,
        help="path to frozen calibration.json (default: re-run calibrate into --out)",
    )
    p.add_argument(
        "--run-config",
        type=str,
        default=None,
        help="optional run_config.json with frozen beta_star (alternative to --calibration)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = str(Path(args.out))
    cfg = PowerConfig(
        provider_uri=args.data_dir,
        out_dir=out,
        skip_download=args.skip_download,
        strength_grid=FROZEN_STRENGTH_GRID,
    )
    calibration = None
    if args.calibration:
        calibration = load_calibration(args.calibration)
    elif args.run_config:
        data = json.loads(Path(args.run_config).read_text())
        if "beta_star" in data:
            cfg.beta_star = {float(k): float(v) for k, v in data["beta_star"].items()}
        if "shell_phi" in data:
            cfg.shell_phi = float(data["shell_phi"])
    result = run_power_sweep(cfg, calibration=calibration)
    print(
        f"POWER SWEEP done in {result.wall_clock_s:.1f}s → {result.out_dir}; "
        f"n_strengths={len(result.summaries)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
