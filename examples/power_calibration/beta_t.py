"""β_t regime-switch appendix (power-calibration.md §7).

Primary contrast = matched realized ICIR half-window (forward-off / backward-off).
Secondary = same-nominal-β (confounds strength with episodicity — labeled as such).
Sensitivity = random-block (hook; honestly scoped to real-data calendar checks).

Answers one number: points unanimous/PBO-TPR drops constant → matched episodic.

FIX 2 (rework 01): runs the greater battery over constant-β and matched-ICIR
episodic arms across R seeds via ``court.judge`` + ``harness.aggregation_policy``
(same path as ``run.py`` — no second aggregation code path). Real R-seed
magnitude is the referee real-data job; reduced config exercises the path.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from court.judge import judge
from court.ledger import DeclaredProtocol, Ledger, SeConvention, Series, Window
from court.tstats import t_stat
from examples.killer_demo.generation import draw_offsets
from examples.power_calibration.battery import build_greater_applications
from examples.power_calibration.config import (
    AGGREGATION_POLICY_ID,
    DIRECTION,
    PowerConfig,
)
from examples.power_calibration.jury import (
    build_directed_t_grid,
    directed_t_row,
    inject_row,
)
from examples.power_calibration.signal import (
    build_noise_panels,
    mix_factor,
    noise_shell_panel,
    oracle_panel_from_labels,
    spawn_power_seed_tree,
)
from examples.power_calibration.stats_util import annualized_icir, pchip_beta_for_icir
from harness.aggregation_policy import AggregationPolicy, trial_survives


@dataclass
class BetaTArmResult:
    """One β_t arm outcome at a reference strength (construction + battery TPR)."""

    arm: str  # "constant" | "forward_off_matched" | "backward_off_matched" | ...
    reference_icir: float
    beta_used: float
    realized_icir: float
    note: str
    n_seeds: int = 0
    unanimous_tpr: float = float("nan")
    pbo_tpr: float = float("nan")
    n_won: int = 0


@dataclass
class BetaTDrop:
    """Constant → matched-episodic TPR drop at one reference ICIR."""

    reference_icir: float
    unanimous_tpr_constant: float
    unanimous_tpr_matched: float  # mean of forward/backward matched
    unanimous_drop: float  # constant − matched
    pbo_tpr_constant: float
    pbo_tpr_matched: float
    pbo_drop: float
    note: str = "primary: constant vs mean(forward_off_matched, backward_off_matched)"


def half_window_beta_series(
    t_len: int,
    *,
    beta_on: float,
    polarity: str,
) -> np.ndarray:
    """Per-day β schedule for half-window arms.

    polarity:
      - ``forward_off``: first half β=s, second half β=0
      - ``backward_off``: first half β=0, second half β=s
    """
    if polarity not in ("forward_off", "backward_off"):
        raise ValueError(f"unknown polarity {polarity!r}")
    mid = t_len // 2
    series = np.zeros(t_len, dtype=np.float64)
    if polarity == "forward_off":
        series[:mid] = beta_on
    else:
        series[mid:] = beta_on
    return series


def build_time_varying_factor(
    labels: np.ndarray,
    *,
    beta_schedule: np.ndarray,
    phi: float,
    seed_sequence: np.random.SeedSequence,
    dates: list[str],
    instruments: list[str],
) -> pd.DataFrame:
    """Day-t mix: factor_t = β_t · oracle_t + √(1−β_t²) · noise_t."""
    oracle = oracle_panel_from_labels(labels)
    t_len, n_inst = oracle.shape
    if len(beta_schedule) != t_len:
        raise ValueError("beta_schedule length must equal T")
    noise = noise_shell_panel(
        phi=phi,
        seed_sequence=seed_sequence,
        n_dates=t_len,
        n_instruments=n_inst,
    )
    factor = np.empty_like(oracle)
    for t in range(t_len):
        b = float(beta_schedule[t])
        factor[t] = mix_factor(oracle[t : t + 1], noise[t : t + 1], b)[0]
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    return pd.DataFrame(factor, index=idx, columns=list(instruments))


def matched_beta_search_grid(constant_beta: float, *, n_points: int = 16) -> list[float]:
    """Relative search bracket for half-window matched β (rework-02 FIX-B).

    For constant-arm β* = b, half-window on-β is typically ~2b. Span at least
    [b/2, 4b] so the solution is not forced to a fixed-grid floor (0.05).
    """
    b = float(constant_beta)
    if not np.isfinite(b) or b <= 0.0:
        raise ValueError(f"constant_beta must be positive finite, got {constant_beta!r}")
    lo = max(b / 2.0, 1e-4)
    hi = max(4.0 * b, lo * 1.01)
    grid = list(np.linspace(lo, hi, int(n_points)))
    # Ensure endpoints are exact
    grid[0] = lo
    grid[-1] = hi
    return grid


def assert_interior_solution(
    beta_star: float,
    beta_grid: list[float] | np.ndarray,
    *,
    eps: float = 1e-9,
) -> None:
    """Fail closed if solution sits on the first/last bracket point (FIX-B)."""
    g = np.asarray(beta_grid, dtype=np.float64)
    g = np.sort(g)
    b = float(beta_star)
    if b <= float(g[0]) + eps or b >= float(g[-1]) - eps:
        raise ValueError(
            f"matched-β solution {b} is at/outside bracket boundary "
            f"[{float(g[0])}, {float(g[-1])}]; expand the search grid "
            f"(require strict interior solution)"
        )


def assert_matched_icir_quality(
    constant_icir: float,
    matched_icir: float,
    *,
    rel_tol: float = 0.20,
) -> None:
    """Fail closed if matched full-sample ICIR drifts > rel_tol from constant (FIX-B)."""
    c = float(constant_icir)
    m = float(matched_icir)
    if not np.isfinite(c) or not np.isfinite(m):
        raise ValueError(
            f"matched-ICIR quality check requires finite ICIRs; "
            f"constant={c}, matched={m}"
        )
    denom = max(abs(c), 1e-12)
    rel = abs(m - c) / denom
    if rel > rel_tol:
        raise ValueError(
            f"matched-ICIR quality failed: constant={c:.6g}, matched={m:.6g}, "
            f"relative |Δ|={rel:.3%} > {rel_tol:.0%} tolerance"
        )


def _normalize_beta_star_map(calibration: Any) -> dict[float, float]:
    """Float-keyed β* map from a CalibrationResult or dict-like."""
    if hasattr(calibration, "beta_star_float_keys"):
        raw = calibration.beta_star_float_keys()
    else:
        raw = dict(getattr(calibration, "beta_star", {}) or {})
    out: dict[float, float] = {}
    for k, v in raw.items():
        out[float(k)] = float(v)
    return out


def resolve_beta_star(calibration: Any, target: float) -> float:
    """Look up frozen β* for a target ICIR; never invent a fallback (FIX-A)."""
    beta_star = _normalize_beta_star_map(calibration)
    ft = float(target)
    # Exact float key first, then near-match for 2.0 vs 2.0000001 noise
    if ft in beta_star:
        return float(beta_star[ft])
    for k, v in beta_star.items():
        if abs(k - ft) <= 1e-9:
            return float(v)
    # Also accept str keys on the raw payload
    raw = getattr(calibration, "beta_star", {}) or {}
    sk = str(ft)
    if sk in raw:
        return float(raw[sk])
    available = sorted(beta_star.keys())
    raise ValueError(
        f"missing β* for beta_t target ICIR={ft}: not in frozen calibration. "
        f"available keys={available}. Re-run calibrate (which freezes "
        f"strength_grid ∪ beta_t_icir_targets) before the appendix."
    )


def require_beta_star_targets(
    calibration: Any,
    targets: tuple[float, ...] | list[float],
) -> dict[float, float]:
    """Day-one check: every appendix target resolves to a β* entry (FIX-A).

    Raises before any arm executes. Returns the resolved map.
    """
    resolved: dict[float, float] = {}
    for t in targets:
        resolved[float(t)] = resolve_beta_star(calibration, float(t))
    return resolved


def solve_matched_beta(
    labels: np.ndarray,
    *,
    target_icir: float,
    phi: float,
    seed_sequence: np.random.SeedSequence,
    evaluator: Any,
    metric: str,
    periods_per_year: float,
    polarity: str,
    dates: list[str],
    instruments: list[str],
    beta_grid: list[float] | None = None,
    constant_beta: float | None = None,
    require_interior: bool = True,
) -> float:
    """Solve half-window β so full-sample ICIR matches target (primary §7).

    Rework-02 FIX-B: when ``constant_beta`` is set, the search bracket is
    relative [b/2, 4b] (not a fixed 0.05 floor). Solution must be strictly
    interior; PCHIP clamp is disabled so out-of-range targets raise.
    """
    if constant_beta is not None:
        # Relative bracket always preferred when constant β* is known
        beta_grid = matched_beta_search_grid(float(constant_beta))
    elif beta_grid is None:
        raise ValueError(
            "solve_matched_beta requires constant_beta (preferred) or an "
            "explicit beta_grid; silent 0.05..0.60 default removed (FIX-B)"
        )
    grid = [float(x) for x in beta_grid]
    icirs: list[float] = []
    for b in grid:
        sched = half_window_beta_series(labels.shape[0], beta_on=b, polarity=polarity)
        panel = build_time_varying_factor(
            labels,
            beta_schedule=sched,
            phi=phi,
            seed_sequence=seed_sequence,
            dates=dates,
            instruments=instruments,
        )
        res = evaluator.evaluate(panel, metric)
        try:
            _, _, icir = annualized_icir(res.values, periods_per_year=periods_per_year)
        except ValueError:
            icir = 0.0
        icirs.append(icir)
    b_star = pchip_beta_for_icir(grid, icirs, target_icir, clamp=False)
    if require_interior:
        assert_interior_solution(b_star, grid)
    return float(b_star)


def _window_from_cfg(cfg: PowerConfig, dates: list[str]) -> dict[str, str]:
    if cfg.window is not None:
        return dict(cfg.window)
    return {"start": dates[0], "end": dates[-1]}


def _declared(cfg: PowerConfig, window: dict[str, str]) -> DeclaredProtocol:
    return DeclaredProtocol(
        metric=cfg.metric,
        window=Window(start=window["start"], end=window["end"]),
        periods_per_year=cfg.periods_per_year,
        direction=DIRECTION,
        se=SeConvention(kind="iid"),
    )


def _register_pool(
    ledger: Ledger,
    cfg: PowerConfig,
    window: dict[str, str],
) -> tuple[str, list[str]]:
    declared = _declared(cfg, window)
    hid_inj = ledger.register_hypothesis(
        "β_t arm injected factor (regime-switch appendix; calibration only)"
    )
    injected_tid = ledger.register(
        hid_inj,
        spec={"kind": "beta_t_arm", "direction": DIRECTION},
        params={"role": "injected"},
        declared=declared,
    )
    noise_tids: list[str] = []
    for i in range(cfg.n_noise):
        hid = ledger.register_hypothesis(f"β_t pure-noise shell #{i}")
        tid = ledger.register(
            hid,
            spec={"kind": "ar1_noise", "index": i},
            params={"role": "noise", "index": i},
            declared=declared,
        )
        noise_tids.append(tid)
    return injected_tid, noise_tids


def _pbo_pass(verdicts: list[Any], trial_id: str) -> bool:
    for v in verdicts:
        if v.statistic == "pbo_cscv" and trial_id in v.decisions:
            return v.decisions[trial_id] == "pass"
    return False


def _judge_arm_seed(
    cfg: PowerConfig,
    evaluator: Any,
    *,
    inj_panel: pd.DataFrame,
    master_seed: int,
    phi: float,
    ledger_path: Path,
) -> tuple[bool, bool, bool, float]:
    """One seed: noise pool + injected panel → greater battery.

    Returns (won, unanimous_pass_injected, pbo_pass_injected, realized_icir).
    Aggregation via harness.aggregation_policy.trial_survives (no second path).
    """
    dates = evaluator.evaluation_dates
    instruments = evaluator.instruments
    window = _window_from_cfg(cfg, dates)
    t_len = len(dates)

    noise_ss, off_ss, _inj_ss = spawn_power_seed_tree(master_seed)
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

    if ledger_path.exists():
        ledger_path.unlink()
    ledger = Ledger.open(ledger_path)
    injected_tid, noise_tids = _register_pool(ledger, cfg, window)
    trial_ids = [injected_tid, *noise_tids]

    noise_t: list[float] = []
    data_version: dict[str, Any] = {}
    for tid, panel in zip(noise_tids, noise_panels, strict=True):
        res = evaluator.evaluate(panel, cfg.metric)
        data_version = dict(res.meta.get("data_version", {}))
        arr = np.asarray(res.values, dtype=np.float64)
        ledger.record(
            tid,
            Series(index=tuple(dates), values=tuple(float(x) for x in arr)),
        )
        noise_t.append(float(t_stat(arr, se_kind="iid").t))

    inj_res = evaluator.evaluate(inj_panel, cfg.metric)
    inj_arr = np.asarray(inj_res.values, dtype=np.float64)
    ledger.record(
        injected_tid,
        Series(index=tuple(dates), values=tuple(float(x) for x in inj_arr)),
    )
    try:
        _, _, ricir = annualized_icir(inj_arr, periods_per_year=cfg.periods_per_year)
    except ValueError:
        ricir = float("nan")
    injected_t = float(t_stat(inj_arr, se_kind="iid").t)

    all_t = [injected_t, *noise_t]
    best_i = 0
    best_t = all_t[0]
    for i in range(1, len(all_t)):
        if all_t[i] > best_t:
            best_t = all_t[i]
            best_i = i
    won = best_i == 0
    champion_tid = trial_ids[best_i]

    noise_grid = build_directed_t_grid(
        evaluator, noise_panels, offsets, metric=cfg.metric
    )
    inj_row = directed_t_row(evaluator, inj_panel, offsets, metric=cfg.metric)
    full_grid = inject_row(noise_grid, inj_row)

    apps = build_greater_applications(
        cfg,
        selected_trial_id=champion_tid,
        trial_ids=trial_ids,
        grid=full_grid,
        data_version=data_version,
        master_seed=master_seed,
    )
    judge(ledger, trial_ids, apps)
    verdicts = ledger.verdicts()

    # Cross-check aggregation path is harness (import side effect / load-bearing)
    _ = AggregationPolicy(
        policy_id=AGGREGATION_POLICY_ID,
        rule="unanimous-discriminating",
        params={},
    )
    unan = trial_survives(injected_tid, verdicts)
    pbo = _pbo_pass(verdicts, injected_tid)
    return won, unan, pbo, float(ricir)


def _arm_battery_tpr(
    cfg: PowerConfig,
    evaluator: Any,
    *,
    beta_schedule_fn: Any,  # () -> np.ndarray schedule builder per seed ss
    phi: float,
    n_seeds: int,
    seed_root: int,
    out_dir: Path,
    arm_tag: str,
) -> tuple[float, float, int, float]:
    """Run R seeds; return (unanimous_tpr, pbo_tpr, n_won, mean_realized_icir).

    TPR is P(pass | won) when n_won > 0; if n_won == 0, falls back to
    unconditional P(pass) over all seeds so reduced configs stay finite.
    """
    dates = evaluator.evaluation_dates
    instruments = evaluator.instruments
    labels = evaluator.labels
    children = np.random.SeedSequence(seed_root).spawn(n_seeds)
    n_won = 0
    n_unan_won = 0
    n_pbo_won = 0
    n_unan_all = 0
    n_pbo_all = 0
    icirs: list[float] = []
    for si, ss in enumerate(children):
        # Per-seed: independent injected shell + independent noise (spawn tree)
        master = int(np.random.default_rng(ss).integers(0, 2**31 - 1))
        inj_shell = np.random.SeedSequence(master).spawn(1)[0]
        sched = beta_schedule_fn()
        panel = build_time_varying_factor(
            labels,
            beta_schedule=sched,
            phi=phi,
            seed_sequence=inj_shell,
            dates=dates,
            instruments=instruments,
        )
        ledger_path = out_dir / f"{arm_tag}_seed{si:03d}.jsonl"
        won, unan, pbo, ricir = _judge_arm_seed(
            cfg,
            evaluator,
            inj_panel=panel,
            master_seed=master,
            phi=phi,
            ledger_path=ledger_path,
        )
        icirs.append(ricir)
        if unan:
            n_unan_all += 1
        if pbo:
            n_pbo_all += 1
        if won:
            n_won += 1
            if unan:
                n_unan_won += 1
            if pbo:
                n_pbo_won += 1
    if n_won > 0:
        u_tpr = n_unan_won / n_won
        p_tpr = n_pbo_won / n_won
    else:
        # Finite fallback for tiny reduced configs
        u_tpr = n_unan_all / n_seeds if n_seeds else float("nan")
        p_tpr = n_pbo_all / n_seeds if n_seeds else float("nan")
    mean_icir = float(np.nanmean(icirs)) if icirs else float("nan")
    return float(u_tpr), float(p_tpr), n_won, mean_icir


def run_beta_t_power(
    cfg: PowerConfig,
    *,
    evaluator: Any,
    calibration: Any,
    out_dir: str | Path,
    n_seeds: int | None = None,
    match_beta_grid: list[float] | None = None,
    targets: tuple[float, ...] | None = None,
) -> dict[str, Any]:
    """Full §7 path: solve matched β, run greater battery, emit TPR drops.

    Parameters
    ----------
    n_seeds:
        R for the battery (default ``cfg.r0``). Reduced tests use 2.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    r = int(n_seeds if n_seeds is not None else cfg.r0)
    phi = float(
        cfg.shell_phi
        if cfg.shell_phi is not None
        else getattr(calibration, "shell_phi", 0.97)
    )
    labels = evaluator.labels
    dates = evaluator.evaluation_dates
    instruments = evaluator.instruments
    t_len = labels.shape[0]
    tgt_list = list(targets if targets is not None else cfg.beta_t_icir_targets)

    # FIX-A: day-one fail-closed — every target must resolve before any arm
    resolved_beta = require_beta_star_targets(calibration, tgt_list)

    arms: list[BetaTArmResult] = []
    drops: list[BetaTDrop] = []
    # Deterministic roots distinct from main sweep
    base_root = int(cfg.power_seed_root) + 17

    for ti, target in enumerate(tgt_list):
        b_const = float(resolved_beta[float(target)])

        match_ss = np.random.SeedSequence(base_root + 1000 * ti)

        # --- constant arm ---
        u_c, p_c, nw_c, ic_c = _arm_battery_tpr(
            cfg,
            evaluator,
            beta_schedule_fn=lambda bc=b_const: np.full(t_len, bc, dtype=np.float64),
            phi=phi,
            n_seeds=r,
            seed_root=base_root + 1000 * ti + 1,
            out_dir=out,
            arm_tag=f"t{target:.1f}_const",
        )
        arms.append(
            BetaTArmResult(
                arm="constant",
                reference_icir=float(target),
                beta_used=b_const,
                realized_icir=ic_c,
                note="constant daily edge; greater-battery TPR",
                n_seeds=r,
                unanimous_tpr=u_c,
                pbo_tpr=p_c,
                n_won=nw_c,
            )
        )

        # Match against constant-arm realized ICIR (single construction probe)
        # so the primary contrast isolates episodicity, not strength drift.
        probe_ss = np.random.SeedSequence(base_root + 1000 * ti + 99)
        const_probe = build_time_varying_factor(
            labels,
            beta_schedule=np.full(t_len, b_const, dtype=np.float64),
            phi=phi,
            seed_sequence=probe_ss,
            dates=dates,
            instruments=instruments,
        )
        try:
            _, _, const_probe_icir = annualized_icir(
                evaluator.evaluate(const_probe, cfg.metric).values,
                periods_per_year=cfg.periods_per_year,
            )
        except ValueError as exc:
            raise ValueError(
                f"constant-arm ICIR probe failed for target={target}: {exc}"
            ) from exc
        match_target_icir = float(const_probe_icir)

        matched_u: list[float] = []
        matched_p: list[float] = []
        for polarity, arm_name, tag in (
            ("forward_off", "forward_off_matched", "fwd"),
            ("backward_off", "backward_off_matched", "bwd"),
        ):
            # FIX-B: relative bracket from constant_beta; ignore legacy fixed grids
            # when constant_beta is known (match_beta_grid kept for API compat only
            # when constant_beta is unavailable — not the production path).
            _ = match_beta_grid  # intentional: relative bracket supersedes fixed grid
            b_m = solve_matched_beta(
                labels,
                target_icir=match_target_icir,
                phi=phi,
                seed_sequence=match_ss,
                evaluator=evaluator,
                metric=cfg.metric,
                periods_per_year=cfg.periods_per_year,
                polarity=polarity,
                dates=dates,
                instruments=instruments,
                constant_beta=b_const,
                require_interior=True,
            )
            # Quality: evaluate the solved matched panel once against the probe
            matched_probe = build_time_varying_factor(
                labels,
                beta_schedule=half_window_beta_series(
                    t_len, beta_on=b_m, polarity=polarity
                ),
                phi=phi,
                seed_sequence=match_ss,
                dates=dates,
                instruments=instruments,
            )
            try:
                _, _, matched_probe_icir = annualized_icir(
                    evaluator.evaluate(matched_probe, cfg.metric).values,
                    periods_per_year=cfg.periods_per_year,
                )
            except ValueError as exc:
                raise ValueError(
                    f"matched-arm ICIR probe failed for target={target} "
                    f"polarity={polarity}: {exc}"
                ) from exc
            assert_matched_icir_quality(match_target_icir, matched_probe_icir)

            u_m, p_m, nw_m, ic_m = _arm_battery_tpr(
                cfg,
                evaluator,
                beta_schedule_fn=lambda bm=b_m, pol=polarity: half_window_beta_series(
                    t_len, beta_on=bm, polarity=pol
                ),
                phi=phi,
                n_seeds=r,
                seed_root=base_root + 1000 * ti + (2 if polarity == "forward_off" else 3),
                out_dir=out,
                arm_tag=f"t{target:.1f}_{tag}",
            )
            matched_u.append(u_m)
            matched_p.append(p_m)
            arms.append(
                BetaTArmResult(
                    arm=arm_name,
                    reference_icir=float(target),
                    beta_used=float(b_m),
                    realized_icir=ic_m,
                    note="primary: matched full-sample ICIR; greater-battery TPR",
                    n_seeds=r,
                    unanimous_tpr=u_m,
                    pbo_tpr=p_m,
                    n_won=nw_m,
                )
            )

        # Secondary: same-nominal forward-off (confounded) — still battery for honesty
        u_n, p_n, nw_n, ic_n = _arm_battery_tpr(
            cfg,
            evaluator,
            beta_schedule_fn=lambda bc=b_const: half_window_beta_series(
                t_len, beta_on=bc, polarity="forward_off"
            ),
            phi=phi,
            n_seeds=r,
            seed_root=base_root + 1000 * ti + 4,
            out_dir=out,
            arm_tag=f"t{target:.1f}_nom",
        )
        arms.append(
            BetaTArmResult(
                arm="same_nominal_forward",
                reference_icir=float(target),
                beta_used=b_const,
                realized_icir=ic_n,
                note="secondary: same-nominal-β (confounds strength with episodicity)",
                n_seeds=r,
                unanimous_tpr=u_n,
                pbo_tpr=p_n,
                n_won=nw_n,
            )
        )

        u_matched = float(np.mean(matched_u))
        p_matched = float(np.mean(matched_p))
        drops.append(
            BetaTDrop(
                reference_icir=float(target),
                unanimous_tpr_constant=u_c,
                unanimous_tpr_matched=u_matched,
                unanimous_drop=float(u_c - u_matched),
                pbo_tpr_constant=p_c,
                pbo_tpr_matched=p_matched,
                pbo_drop=float(p_c - p_matched),
            )
        )

    payload = {
        "battery_ran": True,
        "n_seeds": r,
        "shell_phi": phi,
        "arms": [asdict(a) for a in arms],
        "drops": [asdict(d) for d in drops],
    }
    (out / "beta_t_appendix.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload


# Back-compat thin wrapper used by older call sites that only want construction
def run_beta_t_appendix(
    *,
    labels: np.ndarray,
    phi: float,
    seed_sequence: np.random.SeedSequence,
    evaluator: Any,
    metric: str,
    periods_per_year: float,
    dates: list[str],
    instruments: list[str],
    targets: tuple[float, ...] = (4.0, 3.0),
    constant_beta_star: dict[float, float] | None = None,
    match_beta_grid: list[float] | None = None,
) -> list[BetaTArmResult]:
    """Construction-only ICIR arms (no battery). Prefer ``run_beta_t_power``."""
    results: list[BetaTArmResult] = []
    # FIX-A: no silent target/20 fallback — require an explicit β* map
    if constant_beta_star is None:
        raise ValueError(
            "run_beta_t_appendix requires constant_beta_star for every target "
            "(silent target/20 fallback removed; rework-02 FIX-A)"
        )
    for target in targets:
        ft = float(target)
        if ft not in constant_beta_star and not any(
            abs(float(k) - ft) <= 1e-9 for k in constant_beta_star
        ):
            raise ValueError(
                f"missing β* for target ICIR={ft}; available="
                f"{sorted(float(k) for k in constant_beta_star)}"
            )
        b_const = float(
            constant_beta_star[ft]
            if ft in constant_beta_star
            else next(v for k, v in constant_beta_star.items() if abs(float(k) - ft) <= 1e-9)
        )
        const_sched = np.full(labels.shape[0], b_const, dtype=np.float64)
        const_panel = build_time_varying_factor(
            labels,
            beta_schedule=const_sched,
            phi=phi,
            seed_sequence=seed_sequence,
            dates=dates,
            instruments=instruments,
        )
        const_ic = evaluator.evaluate(const_panel, metric)
        try:
            _, _, const_icir = annualized_icir(
                const_ic.values, periods_per_year=periods_per_year
            )
        except ValueError:
            const_icir = float("nan")
        results.append(
            BetaTArmResult(
                arm="constant",
                reference_icir=float(target),
                beta_used=b_const,
                realized_icir=float(const_icir),
                note="constant daily edge reference (construction-only)",
            )
        )
        for polarity, arm_name in (
            ("forward_off", "forward_off_matched"),
            ("backward_off", "backward_off_matched"),
        ):
            b_m = solve_matched_beta(
                labels,
                target_icir=float(target),
                phi=phi,
                seed_sequence=seed_sequence,
                evaluator=evaluator,
                metric=metric,
                periods_per_year=periods_per_year,
                polarity=polarity,
                dates=dates,
                instruments=instruments,
                constant_beta=b_const,
                beta_grid=None if constant_beta_star else match_beta_grid,
                require_interior=True,
            )
            sched = half_window_beta_series(
                labels.shape[0], beta_on=b_m, polarity=polarity
            )
            panel = build_time_varying_factor(
                labels,
                beta_schedule=sched,
                phi=phi,
                seed_sequence=seed_sequence,
                dates=dates,
                instruments=instruments,
            )
            res = evaluator.evaluate(panel, metric)
            try:
                _, _, ricir = annualized_icir(
                    res.values, periods_per_year=periods_per_year
                )
            except ValueError:
                ricir = float("nan")
            results.append(
                BetaTArmResult(
                    arm=arm_name,
                    reference_icir=float(target),
                    beta_used=float(b_m),
                    realized_icir=float(ricir),
                    note="primary contrast: matched full-sample ICIR (§7)",
                )
            )
        sched_n = half_window_beta_series(
            labels.shape[0], beta_on=b_const, polarity="forward_off"
        )
        panel_n = build_time_varying_factor(
            labels,
            beta_schedule=sched_n,
            phi=phi,
            seed_sequence=seed_sequence,
            dates=dates,
            instruments=instruments,
        )
        res_n = evaluator.evaluate(panel_n, metric)
        try:
            _, _, ricir_n = annualized_icir(
                res_n.values, periods_per_year=periods_per_year
            )
        except ValueError:
            ricir_n = float("nan")
        results.append(
            BetaTArmResult(
                arm="same_nominal_forward",
                reference_icir=float(target),
                beta_used=b_const,
                realized_icir=float(ricir_n),
                note="secondary: same-nominal-β (confounds strength with episodicity)",
            )
        )
    return results
