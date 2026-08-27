"""Seed-sweep appendix orchestration (killer-demo.md §7.4).

Implements the flag path; the full 20-seed run (~15 h) is out of scope for
ticket v0.1-11a — only aggregation logic is unit-tested here.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from examples.killer_demo.aggregate import aggregate_sweep_rows
from examples.killer_demo.config import SWEEP_SEEDS, DemoConfig
from examples.killer_demo.run import run_demo


def run_sweep(
    base_cfg: DemoConfig,
    seeds: tuple[int, ...] = SWEEP_SEEDS,
) -> list[dict[str, Any]]:
    """Run the demo once per seed into ``out/sweep/seed-<seed>/``."""
    rows: list[dict[str, Any]] = []
    base_out = Path(base_cfg.out_dir)
    for seed in seeds:
        seed_out = base_out / "sweep" / f"seed-{seed}"
        cfg = replace(base_cfg, master_seed=seed, out_dir=str(seed_out))
        print(f"[sweep] seed={seed} → {seed_out}", flush=True)
        result = run_demo(cfg)
        sign = "pos" if result.accused_t >= 0 else "neg"
        rows.append(
            {
                "seed": seed,
                "accused_name": result.accused_name,
                "accused_trial_id": result.accused_trial_id,
                "sign": sign,
                "abs_t": result.accused_abs_t,
                "n_survivors": result.n_survivors,
                "accused_gate_verdicts": dict(result.gate_verdicts),
            }
        )
    summary = aggregate_sweep_rows(rows)
    summary_path = base_out / "sweep" / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    summary_path.write_text(
        json.dumps({"rows": rows, "summary": summary}, indent=2) + "\n",
        encoding="utf-8",
    )
    return rows
