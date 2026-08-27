"""Power-calibration sweep (power-calibration.md §5).

Per strength: 1 injected + n_noise pure-noise, all ``direction="greater"``.
Primary A = P(unanimous pass | won); B = P(win) from first R₀ seeds only;
submission power = forced-judged branch. Aggregation via
``harness.aggregation_policy`` only (audit D13).

Uncertified calculator use: direct ``court.judge``, not ``harness.run``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import court
from adapters.qlib_cn import ADAPTER_VERSION, DEFAULT_PROVIDER, QlibCNFactorEvaluator
from court.judge import judge
from court.ledger import DeclaredProtocol, Ledger, SeConvention, Series, Window
from court.tstats import t_stat
from examples.killer_demo.generation import draw_offsets
from examples.power_calibration.battery import build_greater_applications
from examples.power_calibration.calibrate import (
    CalibrationResult,
    apply_calibration_to_config,
    run_calibration,
    write_calibration,
)
from examples.power_calibration.config import (
    AGGREGATION_POLICY_ID,
    CLAIM_SCOPE,
    COST_DECLARATION,
    DIRECTION,
    UNIT_FOOTNOTE,
    PowerConfig,
)
from examples.power_calibration.jury import (
    build_directed_t_grid,
    directed_t_row,
    inject_row,
)
from examples.power_calibration.signal import (
    build_injected_panel,
    build_noise_panels,
    median_demo_shell_phi,
    power_master_seeds,
    spawn_power_seed_tree,
)
from examples.power_calibration.stats_util import (
    annualized_icir,
    gate_key,
    wilson_half_width,
    wilson_interval,
)
from harness.aggregation_policy import (
    AggregationPolicy,
    apply_policy,
    trial_survives,
)


@dataclass
class SeedNoiseCache:
    """Per-seed cached noise-pool evaluations (cross-β reuse only)."""

    master_seed: int
    trial_ids_noise: list[str]  # placeholder ids order for noise
    noise_panels: list[pd.DataFrame]
    noise_series: list[np.ndarray]
    noise_t: list[float]
    offsets: list[int]
    noise_grid: Any  # DirectedTGrid
    data_version: dict[str, Any]
    dates: list[str]
    instruments: list[str]
    labels: np.ndarray
    injected_shell_ss: np.random.SeedSequence


@dataclass
class StrengthSeedOutcome:
    """One (strength, seed) observation."""

    strength: float
    beta: float
    seed_index: int
    master_seed: int
    won: bool
    injected_t: float
    champion_t: float
    champion_is_injected: bool
    unanimous_pass: bool  # injected survives unanimous (A numerator when won)
    submission_unanimous_pass: bool
    realized_icir: float
    gate_pass: dict[str, bool]  # injected trial gates (hero A / per-gate among won)
    submission_gate_pass: dict[str, bool]
    # FIX 1: directed-scan champion (always exists) — size-panel estimand
    champion_unanimous_pass: bool = False
    champion_gate_pass: dict[str, bool] = field(default_factory=dict)


@dataclass
class StrengthSummary:
    strength: float
    beta: float
    n_seeds: int
    n_won: int
    n_won_r0: int
    a_hat: float
    a_lo: float
    a_hi: float
    a_half_width: float
    b_hat: float
    b_lo: float
    b_hi: float
    submission_hat: float
    submission_lo: float
    submission_hi: float
    gate_tpr: dict[str, float]
    underpowered: bool
    mean_realized_icir_won: float
    # FIX 1: unconditional champion rates (size panel; ≈α at β=0)
    n_champion_samples: int = 0
    champion_unanimous_hat: float = float("nan")
    champion_unanimous_lo: float = float("nan")
    champion_unanimous_hi: float = float("nan")
    champion_gate_tpr: dict[str, float] = field(default_factory=dict)
    outcomes: list[StrengthSeedOutcome] = field(default_factory=list)


@dataclass
class PowerSweepResult:
    """In-memory summary of a completed (reduced or full) sweep."""

    out_dir: Path
    calibration: CalibrationResult
    summaries: list[StrengthSummary]
    master_seeds: list[int]
    shell_phi: float
    claim_scope: str
    unit_footnote: str
    report_text: str = ""
    wall_clock_s: float = 0.0
    run_config: dict[str, Any] = field(default_factory=dict)


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


def _declared(cfg: PowerConfig, window: dict[str, str]) -> DeclaredProtocol:
    return DeclaredProtocol(
        metric=cfg.metric,
        window=Window(start=window["start"], end=window["end"]),
        periods_per_year=cfg.periods_per_year,
        direction=DIRECTION,
        se=SeConvention(kind="iid"),
    )


def _extract_gate_pass(
    verdicts: list[Any], trial_id: str
) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for v in verdicts:
        if trial_id not in v.decisions:
            continue
        key = gate_key(v.statistic, v.params)
        # For individual noise, only the matching judged trial
        if v.statistic == "noise_control" and v.params.get("mode") == "individual":
            if v.params.get("judged_trial_id") != trial_id:
                continue
            key = "noise_individual"
        out[key] = v.decisions[trial_id] == "pass"
    return out


def _build_noise_cache(
    cfg: PowerConfig,
    evaluator: QlibCNFactorEvaluator,
    *,
    master_seed: int,
    phi: float,
) -> SeedNoiseCache:
    dates = evaluator.evaluation_dates
    instruments = evaluator.instruments
    labels = evaluator.labels
    t_len = len(dates)

    noise_ss, off_ss, inj_ss = spawn_power_seed_tree(master_seed)
    noise_panels = build_noise_panels(
        n_noise=cfg.n_noise,
        phi=phi,
        candidate_ss=noise_ss,
        dates=dates,
        instruments=instruments,
    )
    offsets = draw_offsets(
        off_ss,
        n_offsets=cfg.n_offsets,
        delta_min=cfg.delta_min,
        t_len=t_len,
    )

    noise_series: list[np.ndarray] = []
    noise_t: list[float] = []
    data_version: dict[str, Any] = {}
    for panel in noise_panels:
        res = evaluator.evaluate(panel, cfg.metric)
        data_version = dict(res.meta.get("data_version", {}))
        arr = np.asarray(res.values, dtype=np.float64)
        noise_series.append(arr)
        noise_t.append(float(t_stat(arr, se_kind="iid").t))

    noise_grid = build_directed_t_grid(
        evaluator,
        noise_panels,
        offsets,
        metric=cfg.metric,
        progress=False,
    )
    return SeedNoiseCache(
        master_seed=master_seed,
        trial_ids_noise=[],  # filled per ledger
        noise_panels=noise_panels,
        noise_series=noise_series,
        noise_t=noise_t,
        offsets=offsets,
        noise_grid=noise_grid,
        data_version=data_version,
        dates=dates,
        instruments=instruments,
        labels=labels,
        injected_shell_ss=inj_ss,
    )


def _register_pool(
    ledger: Ledger,
    cfg: PowerConfig,
    window: dict[str, str],
    *,
    n_noise: int,
) -> tuple[str, list[str]]:
    """Register injected (index 0) + n_noise noise trials; all direction=greater."""
    declared = _declared(cfg, window)
    hid_inj = ledger.register_hypothesis(
        "injected constructed oracle (β-mixed forward-return; calibration only)"
    )
    injected_tid = ledger.register(
        hid_inj,
        spec={
            "kind": "injected_oracle",
            "direction": DIRECTION,
            "disclaimer": "constructed oracle ≠ discoverable alpha",
        },
        params={"role": "injected"},
        declared=declared,
    )
    noise_tids: list[str] = []
    for i in range(n_noise):
        hid = ledger.register_hypothesis(
            f"pure-noise AR(1) shell #{i} (power pool; φ-fixed median)"
        )
        tid = ledger.register(
            hid,
            spec={
                "kind": "ar1_noise",
                "index": i,
                "generator": {"kind": "ar1_noise", "phi_source": "demo_median"},
            },
            params={"role": "noise", "index": i},
            declared=declared,
        )
        noise_tids.append(tid)
    return injected_tid, noise_tids


def _run_one_strength_seed(
    cfg: PowerConfig,
    evaluator: QlibCNFactorEvaluator,
    cache: SeedNoiseCache,
    *,
    strength: float,
    beta: float,
    seed_index: int,
    out_dir: Path,
    force_submission: bool = True,
) -> StrengthSeedOutcome:
    """Evaluate injected at β, judge natural + optional submission branch."""
    window = cfg.window or {
        "start": cache.dates[0],
        "end": cache.dates[-1],
    }
    ledger_path = (
        out_dir
        / "ledgers"
        / f"str{strength:.2f}_seed{seed_index:03d}_m{cache.master_seed}.jsonl"
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if ledger_path.exists():
        ledger_path.unlink()

    ledger = Ledger.open(ledger_path)
    injected_tid, noise_tids = _register_pool(
        ledger, cfg, window, n_noise=cfg.n_noise
    )
    trial_ids = [injected_tid, *noise_tids]

    # Record noise series
    for tid, arr in zip(noise_tids, cache.noise_series, strict=True):
        ser = Series(
            index=tuple(cache.dates),
            values=tuple(float(x) for x in arr),
        )
        ledger.record(tid, ser)

    # Injected panel
    inj_panel = build_injected_panel(
        cache.labels,
        beta=beta,
        phi=float(cfg.shell_phi if cfg.shell_phi is not None else 0.97),
        seed_sequence=cache.injected_shell_ss,
        dates=cache.dates,
        instruments=cache.instruments,
    )
    assert isinstance(inj_panel, pd.DataFrame)
    inj_res = evaluator.evaluate(inj_panel, cfg.metric)
    inj_arr = np.asarray(inj_res.values, dtype=np.float64)
    ledger.record(
        injected_tid,
        Series(index=tuple(cache.dates), values=tuple(float(x) for x in inj_arr)),
    )
    _, _, realized_icir = annualized_icir(
        inj_arr, periods_per_year=cfg.periods_per_year
    )
    injected_t = float(t_stat(inj_arr, se_kind="iid").t)

    # Won test: argmax signed t over full pool (directed; no flip guard).
    # Ties → smallest index (injected wins a tie for first place).
    all_t = [injected_t, *cache.noise_t]
    best_i = 0
    best_t = all_t[0]
    for i in range(1, len(all_t)):
        if all_t[i] > best_t:
            best_t = all_t[i]
            best_i = i
    won = best_i == 0
    champion_tid = trial_ids[best_i]
    champion_t = float(all_t[best_i])

    # Directed jury: inject row 0
    inj_row = directed_t_row(
        evaluator, inj_panel, cache.offsets, metric=cfg.metric
    )
    full_grid = inject_row(cache.noise_grid, inj_row)

    # Natural branch: accuse the directed champion
    apps = build_greater_applications(
        cfg,
        selected_trial_id=champion_tid,
        trial_ids=trial_ids,
        grid=full_grid,
        data_version=cache.data_version,
        master_seed=cache.master_seed,
        check_pool_max_consistency=True,
    )
    judge(ledger, trial_ids, apps)
    verdicts = ledger.verdicts()

    # pool-max consistency (natural branch only): selected ranking must match
    # argmax t when the judge recomputes from series — assert champion.
    pool_v = next(
        v
        for v in verdicts
        if v.statistic == "noise_control" and v.params.get("mode") == "pool_max"
    )
    pool_selected = pool_v.computed.get("selected_trial_id")
    if pool_selected != champion_tid:
        raise RuntimeError(
            f"pool-max consistency failed: selected={pool_selected!r} "
            f"champion={champion_tid!r}"
        )

    policy = AggregationPolicy(
        policy_id=AGGREGATION_POLICY_ID,
        rule="unanimous-discriminating",
        params={},
    )
    # Unanimous for the injected candidate (primary A conditions on won)
    unan = trial_survives(injected_tid, verdicts)
    # Cross-check apply_policy
    applied = apply_policy(policy, trial_ids, verdicts)
    assert isinstance(applied["survivor_ids"], list)

    gate_pass = _extract_gate_pass(verdicts, injected_tid)
    # FIX 1: champion (always exists) gate map for directional-size panel
    champion_unan = trial_survives(champion_tid, verdicts)
    champion_gates = _extract_gate_pass(verdicts, champion_tid)

    # Submission-power branch: force injected as judged candidate (§5 / §9)
    # Fresh ledger path for forced applications on a second ledger file
    sub_pass = False
    sub_gates: dict[str, bool] = {}
    if force_submission:
        sub_path = ledger_path.with_name(ledger_path.stem + "_submission.jsonl")
        if sub_path.exists():
            sub_path.unlink()
        sub_ledger = Ledger.open(sub_path)
        inj2, noise2 = _register_pool(sub_ledger, cfg, window, n_noise=cfg.n_noise)
        tids2 = [inj2, *noise2]
        for tid, arr in zip(noise2, cache.noise_series, strict=True):
            sub_ledger.record(
                tid,
                Series(
                    index=tuple(cache.dates),
                    values=tuple(float(x) for x in arr),
                ),
            )
        sub_ledger.record(
            inj2,
            Series(
                index=tuple(cache.dates),
                values=tuple(float(x) for x in inj_arr),
            ),
        )
        # Force injected as selected; disable pool-max won⇒argmax assertion
        apps_sub = build_greater_applications(
            cfg,
            selected_trial_id=inj2,
            trial_ids=tids2,
            grid=full_grid,
            data_version=cache.data_version,
            master_seed=cache.master_seed,
            check_pool_max_consistency=False,
        )
        judge(sub_ledger, tids2, apps_sub)
        sub_verdicts = sub_ledger.verdicts()
        # FIX 4: exclude pool_max from submission unanimous (stated denominator)
        sub_pass = _trial_survives_submission(inj2, sub_verdicts)
        sub_gates = _extract_gate_pass(sub_verdicts, inj2)
        # Drop pool_max from the reported submission gate map for honesty
        sub_gates = {k: v for k, v in sub_gates.items() if k != "noise_pool_max"}

    return StrengthSeedOutcome(
        strength=float(strength),
        beta=float(beta),
        seed_index=seed_index,
        master_seed=cache.master_seed,
        won=won,
        injected_t=injected_t,
        champion_t=champion_t,
        champion_is_injected=won,
        unanimous_pass=unan,
        submission_unanimous_pass=sub_pass,
        realized_icir=float(realized_icir),
        gate_pass=gate_pass,
        submission_gate_pass=sub_gates,
        champion_unanimous_pass=champion_unan,
        champion_gate_pass=champion_gates,
    )


def _trial_survives_submission(trial_id: str, verdicts: list[Any]) -> bool:
    """Unanimous over discriminating gates **excluding pool_max** (FIX 4).

    pool_max has no force knob: it always judges the argmax champion. A forced
    non-champion never appears in pool_max.decisions, so including pool_max would
    silently shrink the denominator. Exclude it explicitly so the gate set is
    stated: fdr_by, dsr, pbo_cscv, noise_individual.
    """
    filtered = [
        v
        for v in verdicts
        if not (
            getattr(v, "statistic", None) == "noise_control"
            and getattr(v, "params", {}).get("mode") == "pool_max"
        )
    ]
    return trial_survives(trial_id, filtered)


def _summarize_strength(
    strength: float,
    beta: float,
    outcomes: list[StrengthSeedOutcome],
    *,
    r0: int,
    n_won_target: int,
) -> StrengthSummary:
    n = len(outcomes)
    won_mask = [o.won for o in outcomes]
    n_won = sum(won_mask)
    r0_outcomes = outcomes[:r0]
    n_won_r0 = sum(1 for o in r0_outcomes if o.won)

    # A: among won (hero curve — may be NaN/wide when n_won small, e.g. β=0)
    n_a_pass = sum(1 for o in outcomes if o.won and o.unanimous_pass)
    a_hat, a_lo, a_hi = wilson_interval(n_a_pass, n_won)
    a_hw = wilson_half_width(n_a_pass, n_won)

    # B: from first R0 only
    b_hat, b_lo, b_hi = wilson_interval(n_won_r0, len(r0_outcomes))

    # Submission (pool_max excluded from denominator — FIX 4)
    n_sub = sum(1 for o in outcomes if o.submission_unanimous_pass)
    s_hat, s_lo, s_hi = wilson_interval(n_sub, n)

    # Per-gate TPR among won (natural branch; hero per-gate panel)
    gate_names: set[str] = set()
    for o in outcomes:
        if o.won:
            gate_names.update(o.gate_pass.keys())
    gate_tpr: dict[str, float] = {}
    for g in sorted(gate_names):
        if n_won == 0:
            gate_tpr[g] = float("nan")
        else:
            gate_tpr[g] = sum(
                1 for o in outcomes if o.won and o.gate_pass.get(g, False)
            ) / n_won

    # FIX 1: unconditional champion rates over ALL seeds (size-panel estimand)
    n_champ = n  # one champion every seed
    n_champ_unan = sum(1 for o in outcomes if o.champion_unanimous_pass)
    c_hat, c_lo, c_hi = wilson_interval(n_champ_unan, n_champ)
    champ_gate_names: set[str] = set()
    for o in outcomes:
        champ_gate_names.update(o.champion_gate_pass.keys())
    champion_gate_tpr: dict[str, float] = {}
    for g in sorted(champ_gate_names):
        champion_gate_tpr[g] = (
            sum(1 for o in outcomes if o.champion_gate_pass.get(g, False)) / n_champ
            if n_champ > 0
            else float("nan")
        )

    won_icirs = [o.realized_icir for o in outcomes if o.won]
    mean_icir_won = float(np.mean(won_icirs)) if won_icirs else float("nan")
    # FIX 3: use cfg.n_won_target; also flag β=0 when champion sample is tiny
    underpowered = n_won < n_won_target if strength > 0 else n_champ < n_won_target

    return StrengthSummary(
        strength=strength,
        beta=beta,
        n_seeds=n,
        n_won=n_won,
        n_won_r0=n_won_r0,
        a_hat=a_hat,
        a_lo=a_lo,
        a_hi=a_hi,
        a_half_width=a_hw,
        b_hat=b_hat,
        b_lo=b_lo,
        b_hi=b_hi,
        submission_hat=s_hat,
        submission_lo=s_lo,
        submission_hi=s_hi,
        gate_tpr=gate_tpr,
        underpowered=underpowered,
        mean_realized_icir_won=mean_icir_won,
        n_champion_samples=n_champ,
        champion_unanimous_hat=c_hat,
        champion_unanimous_lo=c_lo,
        champion_unanimous_hi=c_hi,
        champion_gate_tpr=champion_gate_tpr,
        outcomes=outcomes,
    )


def run_power_sweep(
    cfg: PowerConfig,
    *,
    calibration: CalibrationResult | None = None,
) -> PowerSweepResult:
    """Full §5 sweep (or reduced). Calibrates first if β* not supplied."""
    t0 = time.perf_counter()
    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if calibration is None:
        if cfg.beta_star:
            # Synthesize from config
            calibration = CalibrationResult(
                shell_phi=float(
                    cfg.shell_phi
                    if cfg.shell_phi is not None
                    else median_demo_shell_phi()
                ),
                calibration_seed_root=cfg.calibration_seed_root,
                calibration_k=cfg.calibration_k,
                beta_grid=list(cfg.calibration_beta_grid),
                mean_ic=[],
                mean_ic_vol=[],
                mean_icir=[],
                se_icir=[],
                beta_star={str(float(k)): float(v) for k, v in cfg.beta_star.items()},
                strength_grid=list(cfg.strength_grid),
            )
        else:
            calibration = run_calibration(cfg)
            write_calibration(out_dir, calibration)
    apply_calibration_to_config(cfg, calibration)

    phi = float(cfg.shell_phi)  # type: ignore[arg-type]
    evaluator = _make_evaluator(cfg)
    if cfg.window is None and cfg.synthetic is not None:
        lp: pd.DataFrame = cfg.synthetic["label_panel"]
        cfg.window = {
            "start": lp.index[0].strftime("%Y-%m-%d"),
            "end": lp.index[-1].strftime("%Y-%m-%d"),
        }

    master_seeds = power_master_seeds(cfg.power_seed_root, cfg.r_max)
    # Pre-register seeds into run_config before results
    run_config: dict[str, Any] = {
        "kind": "power_calibration_run_config",
        "uncertified": True,
        "claim_scope": CLAIM_SCOPE,
        "unit_footnote": UNIT_FOOTNOTE,
        "cost_declaration": COST_DECLARATION,
        "shell_phi": phi,
        "calibration": calibration.to_dict(),
        "power_seed_root": cfg.power_seed_root,
        "master_seeds": master_seeds,
        "r0": cfg.r0,
        "r_max": cfg.r_max,
        "n_won_target": cfg.n_won_target,
        "strength_grid": list(cfg.strength_grid),
        "beta_star": {str(float(k)): float(v) for k, v in cfg.beta_star.items()},
        "n_noise": cfg.n_noise,
        "n_offsets": cfg.n_offsets,
        "n_splits": cfg.n_splits,
        "target_t": cfg.target_t,
        "direction": DIRECTION,
        "aggregation_policy_id": AGGREGATION_POLICY_ID,
        "court_version": court.__version__,
        "adapter_version": ADAPTER_VERSION,
        "frozen_before_sweep": True,
    }
    (out_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, sort_keys=True) + "\n"
    )

    summaries: list[StrengthSummary] = []
    # Cache noise per seed_index (cross-β within seed); rebuild across seeds
    noise_caches: dict[int, SeedNoiseCache] = {}

    for strength in cfg.strength_grid:
        beta = float(cfg.beta_star.get(float(strength), 0.0))
        if float(strength) == 0.0:
            beta = 0.0
        outcomes: list[StrengthSeedOutcome] = []
        # Baseline R0 seeds
        n_target = cfg.r0
        seed_i = 0
        while seed_i < n_target:
            if seed_i not in noise_caches:
                noise_caches[seed_i] = _build_noise_cache(
                    cfg,
                    evaluator,
                    master_seed=master_seeds[seed_i],
                    phi=phi,
                )
            cache = noise_caches[seed_i]
            oc = _run_one_strength_seed(
                cfg,
                evaluator,
                cache,
                strength=float(strength),
                beta=beta,
                seed_index=seed_i,
                out_dir=out_dir,
            )
            outcomes.append(oc)
            seed_i += 1

        # Adaptive re-seed in transition band until n_won ≥ target or R_max
        if cfg.in_adaptive_band(float(strength)):
            n_won = sum(1 for o in outcomes if o.won)
            while n_won < cfg.n_won_target and seed_i < cfg.r_max:
                if seed_i not in noise_caches:
                    noise_caches[seed_i] = _build_noise_cache(
                        cfg,
                        evaluator,
                        master_seed=master_seeds[seed_i],
                        phi=phi,
                    )
                cache = noise_caches[seed_i]
                oc = _run_one_strength_seed(
                    cfg,
                    evaluator,
                    cache,
                    strength=float(strength),
                    beta=beta,
                    seed_index=seed_i,
                    out_dir=out_dir,
                )
                outcomes.append(oc)
                if oc.won:
                    n_won += 1
                seed_i += 1

        summary = _summarize_strength(
            float(strength),
            beta,
            outcomes,
            r0=cfg.r0,
            n_won_target=cfg.n_won_target,
        )
        summaries.append(summary)
        print(
            f"[sweep] strength={strength} β={beta:.4f} "
            f"n={summary.n_seeds} n_won={summary.n_won} "
            f"A={summary.a_hat:.3f} B={summary.b_hat:.3f} "
            f"sub={summary.submission_hat:.3f}",
            flush=True,
        )

    # β_t appendix (matched-ICIR primary + greater-battery TPR drops; §7 / FIX 2)
    beta_t_payload: dict[str, Any] = {}
    if cfg.run_beta_t_appendix:
        from examples.power_calibration.beta_t import run_beta_t_power

        match_grid = (
            [0.05, 0.15, 0.30, 0.50] if cfg.synthetic is not None else None
        )
        # Reduced: few seeds; real job uses cfg.r0 (or more)
        beta_t_r = min(cfg.r0, 2) if cfg.synthetic is not None else cfg.r0
        beta_t_payload = run_beta_t_power(
            cfg,
            evaluator=evaluator,
            calibration=calibration,
            out_dir=out_dir / "beta_t",
            n_seeds=beta_t_r,
            match_beta_grid=match_grid,
            targets=cfg.beta_t_icir_targets,
        )
        # Mirror summary at out root for discoverability
        (out_dir / "beta_t_appendix.json").write_text(
            json.dumps(beta_t_payload, indent=2, sort_keys=True) + "\n"
        )

    # Reporting
    from examples.power_calibration.report import render_report

    report_text = render_report(
        out_dir=out_dir,
        summaries=summaries,
        calibration=calibration,
        cfg=cfg,
        run_config=run_config,
        beta_t_payload=beta_t_payload,
    )

    # Figures (matplotlib optional)
    try:
        from examples.power_calibration.figure import render_figures

        render_figures(out_dir=out_dir, summaries=summaries, calibration=calibration)
    except ImportError:
        print("[sweep] matplotlib not available; skipping figures", flush=True)

    wall = time.perf_counter() - t0
    # Append results (never write realized ICIR back onto strength axis)
    results_payload = {
        "summaries": [
            {
                "strength": s.strength,
                "beta": s.beta,
                "n_seeds": s.n_seeds,
                "n_won": s.n_won,
                "n_won_r0": s.n_won_r0,
                "A": {
                    "hat": s.a_hat,
                    "lo": s.a_lo,
                    "hi": s.a_hi,
                    "half_width": s.a_half_width,
                },
                "B": {"hat": s.b_hat, "lo": s.b_lo, "hi": s.b_hi},
                "submission": {
                    "hat": s.submission_hat,
                    "lo": s.submission_lo,
                    "hi": s.submission_hi,
                },
                "gate_tpr": s.gate_tpr,
                "underpowered": s.underpowered,
                "mean_realized_icir_won": s.mean_realized_icir_won,
                "n_champion_samples": s.n_champion_samples,
                "champion_unanimous": {
                    "hat": s.champion_unanimous_hat,
                    "lo": s.champion_unanimous_lo,
                    "hi": s.champion_unanimous_hi,
                },
                "champion_gate_tpr": s.champion_gate_tpr,
            }
            for s in summaries
        ],
        "wall_clock_s": wall,
    }
    (out_dir / "results.json").write_text(
        json.dumps(results_payload, indent=2, sort_keys=True) + "\n"
    )

    return PowerSweepResult(
        out_dir=out_dir,
        calibration=calibration,
        summaries=summaries,
        master_seeds=master_seeds,
        shell_phi=phi,
        claim_scope=CLAIM_SCOPE,
        unit_footnote=UNIT_FOOTNOTE,
        report_text=report_text,
        wall_clock_s=wall,
        run_config=run_config,
    )
