#!/usr/bin/env python3
"""Intra-blade joint null calibration for single_year_luck (LOBO OR HHI-p).

Solves for the largest p_min on a pre-registered grid such that the joint null
flag rate P(LOBO_min ≤ 0 OR HHI-p < p_min) ≤ target-fpr. Family-level (four-blade)
calibration is a later step; this script calibrates this blade's OR-rule only.

Null world: iid standard normal series via ``numpy.random.Generator.standard_normal``.
``court.noise.empirical_null_p`` does not generate series (it consumes an observed
statistic and a supplied null jury), so it is not used here.

Same CLI arguments produce byte-identical JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from gates.single_year_luck import SingleYearLuckBlade  # noqa: E402

P_MIN_GRID = (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05)


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _equal_size_blocks(n_obs: int, n_blocks: int) -> list[int]:
    if n_obs % n_blocks != 0:
        raise ValueError(
            f"n-obs ({n_obs}) must be divisible by n-blocks ({n_blocks}) "
            "for equal-size contiguous blocks"
        )
    width = n_obs // n_blocks
    blocks: list[int] = []
    for lab in range(n_blocks):
        blocks.extend([lab] * width)
    return blocks


def calibrate(
    *,
    seed_root: int,
    n_null: int,
    n_obs: int,
    n_blocks: int,
    target_fpr: float,
    n_perm: int,
) -> dict[str, Any]:
    blocks = _equal_size_blocks(n_obs, n_blocks)
    # Dummy p_min: the script reads statistics, not the blade's flagged bit.
    blade = SingleYearLuckBlade(p_min=0.05, n_perm=n_perm, seed=seed_root, min_blocks=2)
    rng = np.random.default_rng(int(seed_root))
    index = tuple(str(i) for i in range(n_obs))
    lobo_hits = np.empty(n_null, dtype=bool)
    hhi_ps = np.empty(n_null, dtype=np.float64)

    for i in range(n_null):
        values = rng.standard_normal(n_obs)
        series = SimpleNamespace(index=index, values=tuple(float(x) for x in values))
        report = blade.run(f"null-{i}", {}, {"blocks": blocks}, None, series)
        stats = report["statistics"]
        lobo_hits[i] = bool(stats["lobo_min"] <= 0.0)
        hhi_p = stats["hhi_p"]
        hhi_ps[i] = float(hhi_p) if hhi_p is not None else np.nan

    n_lobo = int(np.sum(lobo_hits))
    lobo_null_rate = float(n_lobo) / float(n_null)

    chosen: float | None = None
    joint_null_rate: float | None = None
    for p_min in sorted(P_MIN_GRID, reverse=True):
        hhi_hits = (~np.isnan(hhi_ps)) & (hhi_ps < p_min)
        n_joint = int(np.sum(lobo_hits | hhi_hits))
        rate = float(n_joint) / float(n_null)
        if rate <= target_fpr:
            chosen = float(p_min)
            joint_null_rate = rate
            break

    downgrade = chosen is None
    if downgrade:
        p_small = min(P_MIN_GRID)
        hhi_hits = (~np.isnan(hhi_ps)) & (hhi_ps < p_small)
        n_joint = int(np.sum(lobo_hits | hhi_hits))
        joint_null_rate = float(n_joint) / float(n_null)

    null_recipe = {
        "generator": "numpy.random.Generator.standard_normal",
        "distribution": "iid_standard_normal",
        "court_noise": (
            "not used: court.noise.empirical_null_p compares an observed statistic "
            "to a supplied null jury and does not generate series"
        ),
        "seed_root": int(seed_root),
        "n_null": int(n_null),
        "n_obs": int(n_obs),
        "n_blocks": int(n_blocks),
        "block_scheme": "equal_size_contiguous",
        "block_labels": "opaque integers 0 .. n_blocks-1",
        "n_perm": int(n_perm),
        "p_min_grid": [float(x) for x in P_MIN_GRID],
        "blade_seed": int(seed_root),
    }
    payload: dict[str, Any] = {
        "seed_root": int(seed_root),
        "null_recipe": null_recipe,
        "target_fpr": float(target_fpr),
        "lobo_null_rate": lobo_null_rate,
        "chosen_p_min": chosen,
        "joint_null_rate": joint_null_rate,
        "n_perm": int(n_perm),
        "script": "blade_calibration_syl.py",
        "downgrade": bool(downgrade),
    }
    if downgrade:
        payload["recommendation"] = "ship as on_flag: record"
    return payload


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Intra-blade joint null calibration for single_year_luck"
    )
    p.add_argument("--seed-root", type=int, required=True)
    p.add_argument("--n-null", type=int, required=True)
    p.add_argument("--n-obs", type=int, required=True)
    p.add_argument("--n-blocks", type=int, required=True)
    p.add_argument("--target-fpr", type=float, required=True)
    p.add_argument("--n-perm", type=int, default=2000)
    p.add_argument("--out", type=str, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.n_null < 1:
        print("error: --n-null must be >= 1", file=sys.stderr)
        return 2
    if args.n_blocks < 2:
        print("error: --n-blocks must be >= 2", file=sys.stderr)
        return 2
    if args.n_obs < args.n_blocks:
        print("error: --n-obs must be >= --n-blocks", file=sys.stderr)
        return 2
    if not (0.0 < float(args.target_fpr) < 1.0):
        print("error: --target-fpr must be in (0, 1)", file=sys.stderr)
        return 2
    if int(args.n_perm) < 100:
        print("error: --n-perm must be >= 100", file=sys.stderr)
        return 2
    try:
        payload = calibrate(
            seed_root=int(args.seed_root),
            n_null=int(args.n_null),
            n_obs=int(args.n_obs),
            n_blocks=int(args.n_blocks),
            target_fpr=float(args.target_fpr),
            n_perm=int(args.n_perm),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = _dumps(payload)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
