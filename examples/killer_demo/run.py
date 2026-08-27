"""End-to-end killer demo orchestration (killer-demo.md §4–§10)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import court
from adapters.qlib_cn import (
    ADAPTER_VERSION,
    COST_DECLARATION,
    DEFAULT_PROVIDER,
    QlibCNFactorEvaluator,
)
from court.judge import judge
from court.ledger import (
    DeclaredProtocol,
    Ledger,
    SeConvention,
    Series,
    Window,
)
from examples.killer_demo.aggregate import survivor_count, survivor_ids
from examples.killer_demo.battery import build_applications
from examples.killer_demo.config import DemoConfig
from examples.killer_demo.data import ensure_data_pack
from examples.killer_demo.figure import build_caption, render_figure
from examples.killer_demo.generation import (
    build_factor_specs,
    draw_offsets,
    generate_score_panels,
    spawn_seed_tree,
)
from examples.killer_demo.grid import build_offset_grid
from examples.killer_demo.manifest import build_run_config, write_run_config
from examples.killer_demo.naive import naive_select
from examples.killer_demo.report import render_report
from examples.killer_demo.window import (
    assert_window_constraints,
    choose_window_for_t,
    load_day_calendar,
)


@dataclass
class DemoResult:
    """In-memory summary of one completed run (tests + sweep)."""

    ledger_path: Path
    trial_ids: list[str]
    accused_trial_id: str
    accused_abs_t: float
    accused_t: float
    n_survivors: int
    survivor_trial_ids: list[str]
    figure_numbers: dict[str, Any]
    gate_verdicts: dict[str, str]
    series_values: list[tuple[float, ...]]
    offsets: list[int]
    window: dict[str, str]
    t_len: int
    wall_clock_s: float
    data_version: dict[str, Any] = field(default_factory=dict)
    accused_name: str = ""
    report_text: str = ""
    caption: str = ""


def _make_evaluator(cfg: DemoConfig, window: dict[str, str]) -> QlibCNFactorEvaluator:
    if cfg.synthetic is not None:
        label_panel: pd.DataFrame = cfg.synthetic["label_panel"]
        pit_mask = cfg.synthetic.get("pit_mask")
        config = {
            "window": dict(window),
            "declared_data_tag": cfg.declared_data_tag,
            "universe": cfg.universe,
            "label_expr": cfg.label_expr,
            "min_cross_section": cfg.min_cross_section,
            "provider_uri": cfg.provider_uri or DEFAULT_PROVIDER,
        }
        return QlibCNFactorEvaluator.from_panels(label_panel, config, pit_mask=pit_mask)

    provider = cfg.provider_uri or DEFAULT_PROVIDER
    ensure_data_pack(provider, skip_download=cfg.skip_download)
    config = {
        "provider_uri": provider,
        "universe": cfg.universe,
        "window": dict(window),
        "label_expr": cfg.label_expr,
        "min_cross_section": cfg.min_cross_section,
        "declared_data_tag": cfg.declared_data_tag,
    }
    return QlibCNFactorEvaluator(config)


def _resolve_window(cfg: DemoConfig) -> tuple[dict[str, str], list[str] | None]:
    """Return declared window and optional precomputed eval ISO list."""
    if cfg.synthetic is not None:
        label_panel: pd.DataFrame = cfg.synthetic["label_panel"]
        dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in label_panel.index]
        if cfg.window is not None:
            window = dict(cfg.window)
        else:
            window = {"start": dates[0], "end": dates[-1]}
        if len(dates) != cfg.target_t:
            # Allow synthetic panels to define T; keep cfg.target_t aligned by caller.
            pass
        return window, dates

    if cfg.window is not None:
        return dict(cfg.window), None

    provider = cfg.provider_uri or DEFAULT_PROVIDER
    ensure_data_pack(provider, skip_download=cfg.skip_download)
    calendar = load_day_calendar(provider)
    window, eval_iso = choose_window_for_t(calendar, target_t=cfg.target_t)
    return window, eval_iso


def run_demo(cfg: DemoConfig) -> DemoResult:
    """Full chain: generate → register → evaluate → naive → grid → judge → artifacts."""
    t0 = time.perf_counter()
    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()

    window, _pre_eval = _resolve_window(cfg)
    evaluator = _make_evaluator(cfg, window)
    eval_dates = evaluator.evaluation_dates
    t_len = len(eval_dates)
    if cfg.synthetic is None:
        if t_len != cfg.target_t:
            raise RuntimeError(
                f"expected T={cfg.target_t} evaluation dates, adapter returned {t_len}"
            )
    assert_window_constraints(t_len, cfg.n_splits)

    instruments = evaluator.instruments
    print(
        f"[demo] window={window} T={t_len} instruments={len(instruments)} "
        f"n_candidates={cfg.n_candidates} B={cfg.n_offsets}",
        flush=True,
    )

    # --- §4 generation ---
    specs = build_factor_specs(cfg)
    if len(specs) != cfg.n_candidates:
        raise RuntimeError(f"expected {cfg.n_candidates} specs, got {len(specs)}")
    cand_ss, off_ss = spawn_seed_tree(cfg.master_seed)
    panels = generate_score_panels(
        specs, cand_ss, dates=eval_dates, instruments=instruments
    )
    offsets = draw_offsets(
        off_ss,
        n_offsets=cfg.n_offsets,
        delta_min=cfg.delta_min,
        t_len=t_len,
    )
    print(f"[demo] generated {len(panels)} panels; {len(offsets)} offsets", flush=True)

    # --- §4.3 register ALL first (pre-registration theater) ---
    ledger = Ledger.open(ledger_path)
    declared = DeclaredProtocol(
        metric=cfg.metric,
        window=Window(start=window["start"], end=window["end"]),
        periods_per_year=cfg.periods_per_year,
        direction="two-sided",
        se=SeConvention(kind="iid"),
    )
    trial_ids: list[str] = []
    for spec in specs:
        hid = ledger.register_hypothesis(spec.statement)
        tid = ledger.register(
            hid,
            spec=spec.to_ledger_spec(),
            params={"phi": spec.phi, "family": spec.family, "name": spec.name},
            declared=declared,
        )
        trial_ids.append(tid)

    # --- evaluate + record ---
    series_values: list[tuple[float, ...]] = []
    series_arrays: list[np.ndarray] = []
    data_version: dict[str, Any] = {}
    for i, (tid, panel) in enumerate(zip(trial_ids, panels, strict=True)):
        if (i + 1) % 10 == 0 or i == 0:
            print(f"[demo] evaluate {i + 1}/{len(trial_ids)}", flush=True)
        result = evaluator.evaluate(panel, cfg.metric)
        data_version = dict(result.meta.get("data_version", {}))
        ser = Series(index=tuple(result.index), values=tuple(float(x) for x in result.values))
        ledger.record(tid, ser)
        series_values.append(ser.values)
        series_arrays.append(np.asarray(result.values, dtype=np.float64))

    # --- §5.1 naive arm ---
    naive = naive_select(
        trial_ids,
        series_arrays,
        se_kind="iid",
        periods_per_year=cfg.periods_per_year,
    )
    accused_spec = specs[naive.trial_index]
    print(
        f"[demo] naive accused={accused_spec.name} |t|={naive.abs_t:.4f} "
        f"t={naive.t:.4f} dir={naive.direction}",
        flush=True,
    )

    # --- §5.3 offset grid ---
    grid = build_offset_grid(
        evaluator,
        panels,
        offsets,
        metric=cfg.metric,
        progress=True,
    )

    # --- §5.2 court battery ---
    apps = build_applications(
        cfg,
        accused_trial_id=naive.trial_id,
        trial_ids=trial_ids,
        grid=grid,
        data_version=data_version,
    )
    expected_verdicts = 4 + cfg.n_candidates
    if len(apps) != expected_verdicts:
        raise RuntimeError(f"expected {expected_verdicts} applications, got {len(apps)}")

    print(f"[demo] judge: {len(apps)} applications…", flush=True)
    judgment = judge(ledger, trial_ids, apps)
    if len(judgment.verdict_ids) != expected_verdicts:
        raise RuntimeError(
            f"expected {expected_verdicts} verdicts, got {len(judgment.verdict_ids)}"
        )

    # --- §5.3 consistency: pool-max selected == naive accused ---
    pool_verdict = next(
        v
        for v in ledger.verdicts()
        if v.statistic == "noise_control" and v.params.get("mode") == "pool_max"
    )
    pool_selected = pool_verdict.computed.get("selected_trial_id")
    if pool_selected != naive.trial_id:
        raise RuntimeError(
            f"§5.3 consistency failed: pool-max selected {pool_selected!r} "
            f"!= naive accused {naive.trial_id!r}"
        )

    verdicts = ledger.verdicts()
    n_surv = survivor_count(trial_ids, verdicts)
    surv_ids = survivor_ids(trial_ids, verdicts)
    print(f"[demo] survivors={n_surv}/{cfg.n_candidates}", flush=True)

    # Gate outcomes for the accused (headline notes)
    gate_verdicts: dict[str, str] = {}
    for v in verdicts:
        if naive.trial_id not in v.decisions:
            continue
        if v.statistic == "noise_control":
            mode = v.params.get("mode")
            key = f"noise_{mode}" if mode else "noise_control"
        else:
            key = v.statistic
        gate_verdicts[key] = v.decisions[naive.trial_id]

    engine_version = court.__version__
    caption = build_caption(
        master_seed=cfg.master_seed,
        t_len=t_len,
        data_tag=cfg.declared_data_tag,
        engine_version=engine_version,
        universe=cfg.universe,
        metric_label="RankIC",
        cost_declaration=COST_DECLARATION,
    )
    pool_p = float(pool_verdict.computed["p_hat"])
    figure_numbers = render_figure(
        grid.pool_max_nulls,
        accused_abs_t=naive.abs_t,
        accused_name=accused_spec.name,
        accused_naive_p=naive.naive_p,
        pool_p_hat=pool_p,
        n_survivors=n_surv,
        n_candidates=cfg.n_candidates,
        caption=caption,
        out_dir=out_dir,
    )

    report_text = render_report(
        out_dir=out_dir,
        n_survivors=n_surv,
        n_candidates=cfg.n_candidates,
        accused=naive,
        accused_spec=accused_spec,
        trial_ids=trial_ids,
        specs=specs,
        abs_t_list=naive.all_abs_t,
        t_list=naive.all_t,
        verdicts=verdicts,
        ledger=ledger,
        figure_caption=caption,
        engine_version=engine_version,
        master_seed=cfg.master_seed,
        data_version=data_version,
        sweep_table=None,
    )

    manifest = build_run_config(
        cfg,
        window=window,
        t_len=t_len,
        data_version=data_version,
        court_version=engine_version,
        adapter_version=ADAPTER_VERSION,
        offsets=offsets,
        accused_trial_id=naive.trial_id,
        n_survivors=n_surv,
        extra={
            "accused_name": accused_spec.name,
            "accused_abs_t": naive.abs_t,
            "accused_t": naive.t,
            "gate_verdicts": gate_verdicts,
            "cost_declaration": COST_DECLARATION,
        },
    )
    write_run_config(out_dir, manifest)

    wall = time.perf_counter() - t0
    print(f"[demo] done in {wall:.1f}s → {out_dir}", flush=True)

    return DemoResult(
        ledger_path=ledger_path,
        trial_ids=trial_ids,
        accused_trial_id=naive.trial_id,
        accused_abs_t=naive.abs_t,
        accused_t=naive.t,
        n_survivors=n_surv,
        survivor_trial_ids=surv_ids,
        figure_numbers=figure_numbers,
        gate_verdicts=gate_verdicts,
        series_values=series_values,
        offsets=offsets,
        window=window,
        t_len=t_len,
        wall_clock_s=wall,
        data_version=data_version,
        accused_name=accused_spec.name,
        report_text=report_text,
        caption=caption,
    )
