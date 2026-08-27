"""β→ICIR calibration (power-calibration.md §4.2).

Run once, freeze β* into run_config BEFORE any power sweep. Real data takes
minutes; reduced synthetic config takes seconds. No battery, no offset grid.

Entry: ``python -m examples.power_calibration.calibrate``
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from adapters.qlib_cn import DEFAULT_PROVIDER, QlibCNFactorEvaluator
from examples.power_calibration.config import (
    CALIBRATION_BETA_GRID,
    CALIBRATION_K,
    CALIBRATION_SEED_ROOT,
    CLAIM_SCOPE,
    FROZEN_STRENGTH_GRID,
    PERIODS_PER_YEAR,
    UNIT_FOOTNOTE,
    PowerConfig,
)
from examples.power_calibration.signal import (
    build_injected_panel,
    median_demo_shell_phi,
)
from examples.power_calibration.stats_util import annualized_icir, pchip_beta_for_icir


@dataclass
class CalibrationResult:
    """Frozen calibration artifact (§4.2)."""

    shell_phi: float
    calibration_seed_root: int
    calibration_k: int
    beta_grid: list[float]
    mean_ic: list[float]
    mean_ic_vol: list[float]
    mean_icir: list[float]
    se_icir: list[float]
    beta_star: dict[str, float]  # target_icir str key → β*
    strength_grid: list[float]
    claim_scope: str = CLAIM_SCOPE
    unit_footnote: str = UNIT_FOOTNOTE
    extra: dict[str, Any] = field(default_factory=dict)

    def beta_star_float_keys(self) -> dict[float, float]:
        return {float(k): float(v) for k, v in self.beta_star.items()}

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def _make_evaluator(cfg: PowerConfig) -> QlibCNFactorEvaluator:
    if cfg.synthetic is not None:
        label_panel: pd.DataFrame = cfg.synthetic["label_panel"]
        pit_mask = cfg.synthetic.get("pit_mask")
        window = cfg.window or {
            "start": label_panel.index[0].strftime("%Y-%m-%d"),
            "end": label_panel.index[-1].strftime("%Y-%m-%d"),
        }
        config = {
            "window": dict(window),
            "declared_data_tag": cfg.declared_data_tag,
            "universe": cfg.universe,
            "label_expr": cfg.label_expr,
            "min_cross_section": cfg.min_cross_section,
            "provider_uri": cfg.provider_uri or DEFAULT_PROVIDER,
        }
        return QlibCNFactorEvaluator.from_panels(
            label_panel, config, pit_mask=pit_mask
        )

    # Real path (referee); guarded by qlib availability at CLI
    from examples.killer_demo.data import ensure_data_pack
    from examples.killer_demo.window import choose_window_for_t, load_day_calendar

    provider = cfg.provider_uri or DEFAULT_PROVIDER
    ensure_data_pack(provider, skip_download=cfg.skip_download)
    if cfg.window is not None:
        window = dict(cfg.window)
    else:
        calendar = load_day_calendar(provider)
        window, _ = choose_window_for_t(calendar, target_t=cfg.target_t)
    config = {
        "provider_uri": provider,
        "universe": cfg.universe,
        "window": window,
        "label_expr": cfg.label_expr,
        "min_cross_section": cfg.min_cross_section,
        "declared_data_tag": cfg.declared_data_tag,
    }
    return QlibCNFactorEvaluator(config)


def run_calibration(cfg: PowerConfig) -> CalibrationResult:
    """End-to-end §4.2 procedure → frozen β* table + E[IC]/ICvol decomposition.

    Deterministic given cfg (seed root, K, β grid, labels, φ).
    """
    t0 = time.perf_counter()
    phi = cfg.shell_phi if cfg.shell_phi is not None else median_demo_shell_phi()
    evaluator = _make_evaluator(cfg)
    labels = evaluator.labels  # public defensive copy
    dates = evaluator.evaluation_dates
    instruments = evaluator.instruments
    t_len, n_inst = labels.shape
    if t_len < 2:
        raise RuntimeError(f"need T≥2 evaluation dates, got {t_len}")

    beta_grid = list(cfg.calibration_beta_grid)
    k = int(cfg.calibration_k)
    seed_children = np.random.SeedSequence(cfg.calibration_seed_root).spawn(k)

    # shape (K, n_beta): per-seed annualized ICIR
    icir_mat = np.empty((k, len(beta_grid)), dtype=np.float64)
    ic_mat = np.empty((k, len(beta_grid)), dtype=np.float64)
    vol_mat = np.empty((k, len(beta_grid)), dtype=np.float64)

    for si, ss in enumerate(seed_children):
        for bi, beta in enumerate(beta_grid):
            panel = build_injected_panel(
                labels,
                beta=float(beta),
                phi=phi,
                seed_sequence=ss,
                dates=dates,
                instruments=instruments,
            )
            assert isinstance(panel, pd.DataFrame)
            res = evaluator.evaluate(panel, cfg.metric)
            mean_ic, std_ic, icir = annualized_icir(
                res.values, periods_per_year=cfg.periods_per_year
            )
            ic_mat[si, bi] = mean_ic
            vol_mat[si, bi] = std_ic
            icir_mat[si, bi] = icir

    mean_ic = list(np.mean(ic_mat, axis=0))
    mean_vol = list(np.mean(vol_mat, axis=0))
    mean_icir = list(np.mean(icir_mat, axis=0))
    # Sample SE of the K-seed mean ICIR
    if k > 1:
        se_icir = list(np.std(icir_mat, axis=0, ddof=1) / math_sqrt(k))
    else:
        se_icir = [float("nan")] * len(beta_grid)

    # Main strength grid + appendix β_t targets (rework-02 FIX-A): every
    # configured beta_t_icir_targets entry must freeze a β* entry so the
    # appendix cannot silently fall back to target/20.
    strength_grid = list(cfg.strength_grid)
    appendix_targets = list(getattr(cfg, "beta_t_icir_targets", ()) or ())
    solve_targets: list[float] = []
    seen: set[float] = set()
    for t in [*strength_grid, *appendix_targets]:
        ft = float(t)
        if ft in seen:
            continue
        seen.add(ft)
        solve_targets.append(ft)

    beta_star: dict[str, float] = {}
    for target in solve_targets:
        if float(target) == 0.0:
            beta_star["0.0"] = 0.0
            continue
        b_star = pchip_beta_for_icir(beta_grid, mean_icir, float(target))
        beta_star[str(float(target))] = float(b_star)

    wall = time.perf_counter() - t0
    print(
        f"[calibrate] φ={phi:.6f} K={k} n_beta={len(beta_grid)} "
        f"T={t_len} N={n_inst} wall={wall:.2f}s",
        flush=True,
    )
    return CalibrationResult(
        shell_phi=float(phi),
        calibration_seed_root=int(cfg.calibration_seed_root),
        calibration_k=k,
        beta_grid=[float(b) for b in beta_grid],
        mean_ic=[float(x) for x in mean_ic],
        mean_ic_vol=[float(x) for x in mean_vol],
        mean_icir=[float(x) for x in mean_icir],
        se_icir=[float(x) for x in se_icir],
        beta_star=beta_star,
        strength_grid=[float(s) for s in strength_grid],
        extra={
            "t_len": t_len,
            "n_instruments": n_inst,
            "periods_per_year": cfg.periods_per_year,
            "wall_clock_s": wall,
            "metric": cfg.metric,
        },
    )


def math_sqrt(x: float) -> float:
    return float(np.sqrt(x))


def write_calibration(out_dir: str | Path, result: CalibrationResult) -> Path:
    """Write calibration.json + merge-ready beta_star into run_config skeleton."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "calibration.json"
    path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")
    # Also write a run_config fragment the sweep loads
    run_cfg_path = out / "run_config.json"
    fragment = {
        "kind": "power_calibration_run_config",
        "uncertified": True,
        "claim_scope": CLAIM_SCOPE,
        "unit_footnote": UNIT_FOOTNOTE,
        "shell_phi": result.shell_phi,
        "calibration_seed_root": result.calibration_seed_root,
        "calibration_k": result.calibration_k,
        "calibration_beta_grid": result.beta_grid,
        "mean_ic_of_beta": result.mean_ic,
        "mean_ic_vol_of_beta": result.mean_ic_vol,
        "mean_icir_of_beta": result.mean_icir,
        "se_icir_of_beta": result.se_icir,
        "beta_star": result.beta_star,
        "strength_grid": result.strength_grid,
        "frozen_before_sweep": True,
    }
    run_cfg_path.write_text(json.dumps(fragment, indent=2, sort_keys=True) + "\n")
    print(f"[calibrate] wrote {path} and {run_cfg_path}", flush=True)
    return path


def load_calibration(path: str | Path) -> CalibrationResult:
    """Load a previously frozen calibration artifact."""
    data = json.loads(Path(path).read_text())
    return CalibrationResult(
        shell_phi=float(data["shell_phi"]),
        calibration_seed_root=int(data["calibration_seed_root"]),
        calibration_k=int(data["calibration_k"]),
        beta_grid=list(data["beta_grid"]),
        mean_ic=list(data["mean_ic"]),
        mean_ic_vol=list(data["mean_ic_vol"]),
        mean_icir=list(data["mean_icir"]),
        se_icir=list(data["se_icir"]),
        beta_star=dict(data["beta_star"]),
        strength_grid=list(data["strength_grid"]),
        claim_scope=data.get("claim_scope", CLAIM_SCOPE),
        unit_footnote=data.get("unit_footnote", UNIT_FOOTNOTE),
        extra=dict(data.get("extra", {})),
    )


def apply_calibration_to_config(
    cfg: PowerConfig, result: CalibrationResult
) -> PowerConfig:
    """Copy frozen φ and β* into a PowerConfig (no write-back of realized ICIR)."""
    cfg.shell_phi = result.shell_phi
    cfg.beta_star = result.beta_star_float_keys()
    return cfg


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m examples.power_calibration.calibrate",
        description=(
            "β→ICIR calibration (power-calibration.md §4.2). "
            "Freeze β* before the power sweep."
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
        "--k",
        type=int,
        default=CALIBRATION_K,
        help=f"calibration seed count K (default {CALIBRATION_K})",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = PowerConfig(
        calibration_k=args.k,
        calibration_seed_root=CALIBRATION_SEED_ROOT,
        calibration_beta_grid=CALIBRATION_BETA_GRID,
        strength_grid=FROZEN_STRENGTH_GRID,
        periods_per_year=PERIODS_PER_YEAR,
        provider_uri=args.data_dir,
        out_dir=str(args.out),
        skip_download=args.skip_download,
    )
    result = run_calibration(cfg)
    write_calibration(args.out, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
