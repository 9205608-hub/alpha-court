"""CLI entry: ``python -m examples.killer_demo`` (killer-demo.md §9.1)."""

from __future__ import annotations

import argparse
from pathlib import Path

from adapters.qlib_cn import DEFAULT_PROVIDER
from examples.killer_demo.config import DEFAULT_MASTER_SEED, DemoConfig
from examples.killer_demo.run import run_demo
from examples.killer_demo.sweep import run_sweep


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m examples.killer_demo",
        description=(
            "Killer demo: 100 pure-noise factors → naive selection → court battery "
            "(docs/design/killer-demo.md)."
        ),
    )
    p.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_MASTER_SEED,
        help=f"master seed (default {DEFAULT_MASTER_SEED})",
    )
    p.add_argument(
        "--sweep",
        action="store_true",
        help="run §7.4 seed sweep (seeds 20260711–20260730) after the master run",
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
        "--out",
        type=str,
        default="examples/killer_demo/out",
        help="output directory (default examples/killer_demo/out)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = str(Path(args.out))
    cfg = DemoConfig(
        master_seed=args.seed,
        provider_uri=args.data_dir,
        out_dir=out,
        skip_download=args.skip_download,
    )
    result = run_demo(cfg)
    print(
        f"HEADLINE: survivors={result.n_survivors}/{cfg.n_candidates} "
        f"accused={result.accused_name} |t|={result.accused_abs_t:.4f} "
        f"gates={result.gate_verdicts}",
        flush=True,
    )
    if args.sweep:
        run_sweep(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
