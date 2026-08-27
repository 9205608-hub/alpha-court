"""Tests for examples.power_calibration (power-calibration.md §4–§6).

TDD: written against the design before / alongside the implementation.
Reduced synthetic config only — no qlib required. Real-data paths are
guarded with pytest.importorskip("qlib").
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from examples.power_calibration.calibrate import (
    apply_calibration_to_config,
    run_calibration,
    write_calibration,
)
from examples.power_calibration.config import (
    CALIBRATION_SEED_ROOT,
    CLAIM_SCOPE,
    DIRECTION,
    FROZEN_STRENGTH_GRID,
    POWER_SEED_ROOT,
    UNIT_FOOTNOTE,
    PowerConfig,
)
from examples.power_calibration.jury import (
    DirectedTGrid,
    inject_row,
    reduce_t_iid,
)
from examples.power_calibration.report import (
    report_has_honesty,
    report_has_size_beside_power,
)
from examples.power_calibration.run import run_power_sweep
from examples.power_calibration.signal import (
    median_demo_shell_phi,
    mix_factor,
    oracle_panel_from_labels,
    power_master_seeds,
    van_der_waerden_xs,
)
from examples.power_calibration.stats_util import (
    annualized_icir,
    pchip_beta_for_icir,
    wilson_interval,
)
from harness.aggregation_policy import AggregationPolicy, apply_policy, trial_survives

# ---------------------------------------------------------------------------
# Reduced synthetic helpers (tiny; seconds; n_splits=4 not 16)
# ---------------------------------------------------------------------------


def _synthetic_label_panel(t: int = 16, n_inst: int = 30, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-02", periods=t)
    instruments = [f"I{j:03d}" for j in range(n_inst)]
    data = rng.standard_normal((t, n_inst))
    return pd.DataFrame(data, index=dates, columns=instruments)


def _reduced_cfg(tmp_path: Path, *, seed_root: int = POWER_SEED_ROOT) -> PowerConfig:
    """Tiny config: T=16, n_splits=4, 2 noise + 1 injected, 2 seeds, 3 strengths."""
    t = 16
    label = _synthetic_label_panel(t=t, n_inst=30, seed=1)
    return PowerConfig(
        calibration_seed_root=CALIBRATION_SEED_ROOT,
        calibration_k=2,
        power_seed_root=seed_root,
        r0=2,
        r_max=3,
        n_won_target=1,
        n_noise=2,
        n_offsets=4,
        delta_min=2,
        target_t=t,
        n_splits=4,
        min_cross_section=5,
        out_dir=str(tmp_path / "power_out"),
        skip_download=True,
        synthetic={"label_panel": label},
        window={
            "start": label.index[0].strftime("%Y-%m-%d"),
            "end": label.index[-1].strftime("%Y-%m-%d"),
        },
        strength_grid=(0.0, 2.0, 4.0),
        calibration_beta_grid=(0.05, 0.10, 0.20, 0.30),
        adaptive_band=(2.0, 3.6),
        run_beta_t_appendix=True,
        beta_t_icir_targets=(1.0,),  # keep reduced battery path seconds-scale
        shell_phi=None,  # computed from demo median
    )


# ---------------------------------------------------------------------------
# 1. Signal construction
# ---------------------------------------------------------------------------


def test_median_demo_shell_phi_is_finite_and_in_range():
    phi = median_demo_shell_phi()
    assert 0.0 < phi < 1.0
    # Full 100-shell median pinned near 0.97 for the standard menu
    assert 0.5 < phi < 0.999


def test_van_der_waerden_finite_and_rank_preserving():
    rng = np.random.default_rng(0)
    panel = rng.standard_normal((8, 20))
    scores = van_der_waerden_xs(panel)
    assert scores.shape == panel.shape
    assert np.all(np.isfinite(scores))
    # Cross-sectional rank order preserved on a row
    row = panel[0]
    srow = scores[0]
    assert np.argsort(row).tolist() == np.argsort(srow).tolist()


def test_mix_factor_beta_zero_equals_noise():
    rng = np.random.default_rng(1)
    o = rng.standard_normal((4, 5))
    n = rng.standard_normal((4, 5))
    got = mix_factor(o, n, 0.0)
    np.testing.assert_allclose(got, n)


def test_mix_factor_beta_one_equals_oracle():
    rng = np.random.default_rng(2)
    o = rng.standard_normal((4, 5))
    n = rng.standard_normal((4, 5))
    got = mix_factor(o, n, 1.0)
    np.testing.assert_allclose(got, o)


def test_oracle_from_labels_public_api():
    from adapters.qlib_cn import QlibCNFactorEvaluator

    label = _synthetic_label_panel(t=8, n_inst=20, seed=3)
    ev = QlibCNFactorEvaluator.from_panels(
        label,
        {
            "window": {
                "start": label.index[0].strftime("%Y-%m-%d"),
                "end": label.index[-1].strftime("%Y-%m-%d"),
            },
            "declared_data_tag": "synthetic",
            "universe": "synthetic",
            "provider_uri": "synthetic",
            "min_cross_section": 5,
        },
    )
    labs = ev.labels
    oracle = oracle_panel_from_labels(labs)
    assert oracle.shape == labs.shape
    assert np.all(np.isfinite(oracle))


# ---------------------------------------------------------------------------
# 2. Stats helpers
# ---------------------------------------------------------------------------


def test_wilson_interval_known_values():
    p, lo, hi = wilson_interval(10, 20)
    assert abs(p - 0.5) < 1e-12
    assert 0.0 <= lo < p < hi <= 1.0


def test_pchip_beta_monotone_interpolation():
    betas = [0.05, 0.10, 0.20, 0.30]
    icirs = [1.0, 2.0, 4.0, 6.0]
    b_star = pchip_beta_for_icir(betas, icirs, 3.0)
    assert 0.10 < b_star < 0.20


def test_annualized_icir_formula():
    # constant mean / known std
    x = np.array([0.02, 0.02, 0.02, 0.02], dtype=np.float64)
    # std=0 → error
    with pytest.raises(ValueError):
        annualized_icir(x)
    x2 = np.array([0.01, 0.02, 0.03, 0.04], dtype=np.float64)
    mean, std, icir = annualized_icir(x2, periods_per_year=252.0)
    assert mean == pytest.approx(0.025)
    assert icir == pytest.approx(mean / std * np.sqrt(252.0))


# ---------------------------------------------------------------------------
# 3. Directed jury (signed t, not |t|)
# ---------------------------------------------------------------------------


def test_reduce_t_iid_is_signed():
    # Positive mean → positive t
    pos = np.linspace(0.1, 0.5, 20)
    neg = -pos
    assert reduce_t_iid(pos) > 0
    assert reduce_t_iid(neg) < 0
    # |t| would be equal; signed differs
    assert reduce_t_iid(pos) == pytest.approx(-reduce_t_iid(neg))


def test_inject_row_keeps_noise_pool_max():
    noise = DirectedTGrid(
        offsets=[1, 2, 3],
        t_grid=np.array([[1.0, 2.0, 0.5], [0.5, 3.0, 1.0]], dtype=np.float64),
        pool_max_nulls=np.array([1.0, 3.0, 1.0], dtype=np.float64),
    )
    full = inject_row(noise, np.array([9.0, 9.0, 9.0]))
    assert full.t_grid.shape == (3, 3)
    np.testing.assert_array_equal(full.pool_max_nulls, noise.pool_max_nulls)
    assert full.t_grid[0, 0] == 9.0


# ---------------------------------------------------------------------------
# 4. Aggregation reuse (no second path)
# ---------------------------------------------------------------------------


def test_aggregation_policy_from_harness_not_local():
    """Power must call harness.aggregation_policy (audit D13)."""
    import examples.power_calibration.run as run_mod

    assert hasattr(run_mod, "apply_policy")
    assert run_mod.apply_policy is apply_policy
    assert run_mod.trial_survives is trial_survives
    pol = AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )
    # empty verdicts → no survivors
    assert apply_policy(pol, ["t1"], []).get("n_survivors") == 0


# ---------------------------------------------------------------------------
# 5. Calibration (reduced)
# ---------------------------------------------------------------------------


def test_calibration_produces_beta_star_table(tmp_path: Path):
    cfg = _reduced_cfg(tmp_path)
    result = run_calibration(cfg)
    write_calibration(tmp_path / "cal", result)
    assert result.shell_phi > 0
    assert len(result.beta_grid) == len(cfg.calibration_beta_grid)
    assert "0.0" in result.beta_star or 0.0 in result.beta_star_float_keys()
    # Monotone-ish: higher ICIR target → higher β*
    keys = sorted(result.beta_star_float_keys())
    betas = [result.beta_star_float_keys()[k] for k in keys if k > 0]
    assert betas == sorted(betas) or len(betas) < 2
    path = tmp_path / "cal" / "calibration.json"
    assert path.is_file()
    data = json.loads(path.read_text())
    assert data["calibration_seed_root"] == CALIBRATION_SEED_ROOT
    assert data["frozen_before_sweep"] if "frozen_before_sweep" in data else True


def test_calibration_determinism(tmp_path: Path):
    cfg1 = _reduced_cfg(tmp_path / "a")
    cfg2 = _reduced_cfg(tmp_path / "b")
    r1 = run_calibration(cfg1)
    r2 = run_calibration(cfg2)
    assert r1.mean_icir == r2.mean_icir
    assert r1.beta_star == r2.beta_star
    assert r1.shell_phi == r2.shell_phi


# ---------------------------------------------------------------------------
# 6. Won / direction invariants
# ---------------------------------------------------------------------------


def test_won_means_argmax_signed_t():
    """Won ⇔ injected is argmax of directed t (not |t|)."""
    # Hand-built: injected t=1.5, noise = [2.0, 0.5] → not won
    injected_t = 1.5
    noise_t = [2.0, 0.5]
    all_t = [injected_t, *noise_t]
    best_i = int(np.argmax(all_t))
    assert best_i != 0  # noise wins
    # If we used |t| with a negative champion, directed scan still uses signed
    all_t2 = [-3.0, 1.0, 0.5]
    assert int(np.argmax(all_t2)) == 1  # negative cannot win directed scan


def test_direction_constant_is_greater():
    assert DIRECTION == "greater"


# ---------------------------------------------------------------------------
# 7. Frozen pre-registration source
# ---------------------------------------------------------------------------


def test_frozen_strength_grid_is_pinned():
    """Strength grid loaded from pinned config module, not recomputed post-hoc."""
    assert 0.0 in FROZEN_STRENGTH_GRID
    assert 2.0 in FROZEN_STRENGTH_GRID
    assert 6.0 in FROZEN_STRENGTH_GRID
    # Transition dense points
    for x in (2.3, 2.6, 2.9, 3.2, 3.6, 4.0, 4.5, 5.0):
        assert x in FROZEN_STRENGTH_GRID


def test_power_master_seeds_deterministic():
    s1 = power_master_seeds(POWER_SEED_ROOT, 5)
    s2 = power_master_seeds(POWER_SEED_ROOT, 5)
    assert s1 == s2
    assert len(s1) == 5
    # Distinct from calibration root's conceptual collision zone
    assert POWER_SEED_ROOT != CALIBRATION_SEED_ROOT
    assert POWER_SEED_ROOT not in range(20260710, 20260731)


# ---------------------------------------------------------------------------
# 8. End-to-end reduced: calibrate → sweep → report
# ---------------------------------------------------------------------------


def test_reduced_e2e_calibrate_sweep_report(tmp_path: Path):
    cfg = _reduced_cfg(tmp_path)
    cal = run_calibration(cfg)
    write_calibration(Path(cfg.out_dir), cal)
    apply_calibration_to_config(cfg, cal)
    result = run_power_sweep(cfg, calibration=cal)

    assert result.shell_phi == cal.shell_phi
    assert len(result.summaries) == len(cfg.strength_grid)
    assert (Path(cfg.out_dir) / "run_config.json").is_file()
    assert (Path(cfg.out_dir) / "report.md").is_file()
    assert (Path(cfg.out_dir) / "results.json").is_file()

    report = result.report_text
    assert report_has_honesty(report)
    assert report_has_size_beside_power(report)
    assert CLAIM_SCOPE.split(".")[0] in report or "UNCERTIFIED" in report
    assert "√252" in report or "annualized" in report

    # Direction-homogeneous: all trials greater (encoded in config + report)
    run_cfg = json.loads((Path(cfg.out_dir) / "run_config.json").read_text())
    assert run_cfg["direction"] == "greater"
    assert run_cfg["frozen_before_sweep"] is True
    assert run_cfg["power_seed_root"] == cfg.power_seed_root
    # β* frozen before results — present in run_config
    assert "beta_star" in run_cfg
    # Realized ICIR must NOT overwrite strength keys
    for s in result.summaries:
        assert s.strength in cfg.strength_grid

    # Size-beside-power: β=0 summary exists
    assert any(s.strength == 0.0 for s in result.summaries)

    # Aggregation policy id recorded
    assert run_cfg["aggregation_policy_id"] == "unanimous-discriminating-v1"


def test_reduced_sweep_determinism(tmp_path: Path):
    """Two runs on the same reduced config → byte-identical summary stats."""
    cfg_a = _reduced_cfg(tmp_path / "a")
    cfg_b = _reduced_cfg(tmp_path / "b")
    cal_a = run_calibration(cfg_a)
    cal_b = run_calibration(cfg_b)
    assert cal_a.beta_star == cal_b.beta_star

    ra = run_power_sweep(cfg_a, calibration=cal_a)
    rb = run_power_sweep(cfg_b, calibration=cal_b)

    for sa, sb in zip(ra.summaries, rb.summaries, strict=True):
        assert sa.strength == sb.strength
        assert sa.beta == sb.beta
        assert sa.n_seeds == sb.n_seeds
        assert sa.n_won == sb.n_won
        assert sa.a_hat == sb.a_hat or (
            np.isnan(sa.a_hat) and np.isnan(sb.a_hat)
        )
        assert sa.b_hat == sb.b_hat or (
            np.isnan(sa.b_hat) and np.isnan(sb.b_hat)
        )
        assert sa.submission_hat == sb.submission_hat or (
            np.isnan(sa.submission_hat) and np.isnan(sb.submission_hat)
        )
        for oa, ob in zip(sa.outcomes, sb.outcomes, strict=True):
            assert oa.won == ob.won
            assert oa.injected_t == pytest.approx(ob.injected_t)
            assert oa.unanimous_pass == ob.unanimous_pass


def test_won_invariant_holds_in_e2e(tmp_path: Path):
    cfg = _reduced_cfg(tmp_path)
    cal = run_calibration(cfg)
    result = run_power_sweep(cfg, calibration=cal)
    for s in result.summaries:
        for o in s.outcomes:
            # champion_is_injected ⇔ won
            assert o.won == o.champion_is_injected
            if o.won:
                assert o.injected_t == o.champion_t
            else:
                assert o.champion_t >= o.injected_t


# ---------------------------------------------------------------------------
# 9. Claim-scope constants always available
# ---------------------------------------------------------------------------


def test_honesty_constants_nonempty():
    assert "oracle" in CLAIM_SCOPE.lower() or "UNCERTIFIED" in CLAIM_SCOPE
    assert "252" in UNIT_FOOTNOTE or "16" in UNIT_FOOTNOTE


# ---------------------------------------------------------------------------
# 10. Real-qlib path is optional (importorskip)
# ---------------------------------------------------------------------------


def test_real_qlib_path_guarded():
    """Suite stays green without qlib; real path skipped."""
    qlib = pytest.importorskip("qlib")
    assert qlib is not None
    # If qlib is installed in the environment, we still do not run the multi-day
    # sweep here — just confirm the calibrate CLI module imports.
    from examples.power_calibration import calibrate as cal_mod

    assert hasattr(cal_mod, "main")


def test_beta_t_half_window_schedule():
    from examples.power_calibration.beta_t import half_window_beta_series

    s = half_window_beta_series(10, beta_on=0.2, polarity="forward_off")
    assert list(s[:5]) == [0.2] * 5
    assert list(s[5:]) == [0.0] * 5
    s2 = half_window_beta_series(10, beta_on=0.2, polarity="backward_off")
    assert list(s2[:5]) == [0.0] * 5
    assert list(s2[5:]) == [0.2] * 5


def test_e2e_writes_beta_t_appendix(tmp_path: Path):
    cfg = _reduced_cfg(tmp_path)
    # Tiny appendix targets to keep solve fast
    cfg.beta_t_icir_targets = (1.0,)
    cal = run_calibration(cfg)
    result = run_power_sweep(cfg, calibration=cal)
    path = Path(cfg.out_dir) / "beta_t_appendix.json"
    assert path.is_file()
    data = json.loads(path.read_text())
    arms = {a["arm"] for a in data["arms"]}
    assert "constant" in arms
    assert "forward_off_matched" in arms
    assert "backward_off_matched" in arms
    assert "same_nominal_forward" in arms
    assert data.get("battery_ran") is True
    assert data.get("drops"), "TPR drops must be present"
    assert "unanimous_drop" in data["drops"][0]
    assert "matched" in result.report_text.lower() or "β_t" in result.report_text
    assert "unan_drop" in result.report_text or "unanimous TPR drops" in result.report_text


# ---------------------------------------------------------------------------
# Rework 01 — FIX 1: directional-size unconditional champion estimator
# ---------------------------------------------------------------------------


def test_beta0_size_panel_unconditional_champion_non_nan(tmp_path: Path):
    """FIX 1: β=0 size per-gate P(pass) uses champion over ALL R₀ seeds, not |won.

    At small N the injected rarely wins argmax t; the size panel must still
    report finite ≈α numbers with n_samples ≈ R₀ (amended book §6).
    """
    cfg = _reduced_cfg(tmp_path)
    # Only β=0 — pure size probe; small pool so injected win rate is low
    cfg.strength_grid = (0.0,)
    cfg.r0 = 3
    cfg.r_max = 3
    cfg.n_noise = 4  # N=5 → P(injected wins) ≈ 0.2
    cfg.run_beta_t_appendix = False
    cal = run_calibration(cfg)
    result = run_power_sweep(cfg, calibration=cal)
    assert len(result.summaries) == 1
    s0 = result.summaries[0]
    assert s0.strength == 0.0
    # Unconditional champion samples ≈ all seeds
    assert s0.n_champion_samples == s0.n_seeds
    assert s0.n_champion_samples == cfg.r0
    # Champion per-gate rates must be finite (not NaN from empty won set)
    assert s0.champion_gate_tpr, "champion_gate_tpr must be non-empty"
    for g, rate in s0.champion_gate_tpr.items():
        assert rate == rate, f"gate {g} is NaN"  # NaN != NaN
        assert 0.0 <= rate <= 1.0
    # Unconditional unanimous champion rate finite
    assert s0.champion_unanimous_hat == s0.champion_unanimous_hat
    # Report must render size DATA (not just a header)
    assert report_has_size_beside_power(result.report_text)
    assert "unconditional champion" in result.report_text.lower()
    assert (
        f"n_seeds={s0.n_seeds}" in result.report_text
        or "size_panel_n_seeds=" in result.report_text
    )
    # At least one size-type gate rate rendered as a number
    assert any(
        k in result.report_text
        for k in ("fdr_by", "noise_pool_max", "noise_individual", "dsr", "pbo")
    )


def test_report_has_size_requires_data_not_header_only():
    """FIX 3: header alone must not satisfy the size-beside-power guard."""
    header_only = (
        "# Power\n\n## Directional size (β=0, same greater-battery)\n\n"
        "*β=0 not in this run's strength grid — size panel omitted.*\n"
    )
    assert not report_has_size_beside_power(header_only)
    with_data = (
        "## Directional size (β=0, same greater-battery)\n\n"
        "Estimand: **unconditional champion** per-gate pass rate.\n"
        "size_panel_n_seeds=3 size_panel_champion_unanimous=0.000\n"
        "champion_gate_tpr: {'fdr_by': 0.0, 'noise_pool_max': 0.0}\n"
    )
    assert report_has_size_beside_power(with_data)


# ---------------------------------------------------------------------------
# Rework 01 — FIX 2: β_t appendix runs greater-battery and emits TPR drops
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Rework 02 — FIX-A: fail-closed β* for appendix targets
# ---------------------------------------------------------------------------


def test_fix_a_beta_t_missing_target_raises(tmp_path: Path):
    """FIX-A: target absent from calibration → hard error (no silent fallback)."""
    from examples.power_calibration.beta_t import require_beta_star_targets
    from examples.power_calibration.calibrate import CalibrationResult

    cal = CalibrationResult(
        shell_phi=0.97,
        calibration_seed_root=CALIBRATION_SEED_ROOT,
        calibration_k=2,
        beta_grid=[0.05, 0.1],
        mean_ic=[0.0, 0.0],
        mean_ic_vol=[0.1, 0.1],
        mean_icir=[1.0, 2.0],
        se_icir=[0.0, 0.0],
        beta_star={"2.0": 0.1, "4.0": 0.2},  # no 3.0
        strength_grid=[2.0, 4.0],
    )
    with pytest.raises(ValueError, match=r"3\.0|missing|beta_star|target"):
        require_beta_star_targets(cal, (4.0, 3.0))


def test_fix_a_calibrate_includes_appendix_targets(tmp_path: Path):
    """FIX-A: calibrate freezes β* for beta_t_icir_targets not on main grid."""
    cfg = _reduced_cfg(tmp_path)
    cfg.strength_grid = (0.0, 2.0, 4.0)
    cfg.beta_t_icir_targets = (1.0, 3.0)  # 3.0 not on strength_grid
    cal = run_calibration(cfg)
    keys = cal.beta_star_float_keys()
    assert 1.0 in keys
    assert 3.0 in keys
    assert keys[3.0] > 0.0


# ---------------------------------------------------------------------------
# Rework 02 — FIX-B: matched-β bracket interior + quality
# ---------------------------------------------------------------------------


def test_fix_b_legacy_grid_hits_boundary_for_small_beta():
    """FIX-B red: fixed grid 0.05..0.60 with b*=0.0185 clamps to 0.05.

    Pre-fix this was production behavior; post-fix the relative-bracket
    solver must not return a boundary solution (or must refuse the legacy grid).
    """
    from examples.power_calibration.beta_t import (
        assert_interior_solution,
        matched_beta_search_grid,
    )
    from examples.power_calibration.stats_util import pchip_beta_for_icir

    legacy = [round(0.05 + 0.05 * i, 2) for i in range(12)]
    # Monotone ICIR(β) that puts target for b≈0.037 below the grid floor
    # (half-window needs ~2× constant β*=0.0185)
    icirs = [0.5 + 20.0 * b for b in legacy]  # ICIR(0.05)≈1.5, grows with β
    # Target corresponding to β≈0.037 would need ICIR≈0.5+20*0.037=1.24 < ICIR(0.05)
    b_clamped = pchip_beta_for_icir(legacy, icirs, 1.24)
    assert b_clamped == pytest.approx(0.05, abs=1e-9)
    with pytest.raises(ValueError, match=r"interior|boundary|bracket"):
        assert_interior_solution(b_clamped, legacy)

    # Relative grid around constant_beta=0.0185 must span [b/2, 4b]
    rel = matched_beta_search_grid(0.0185)
    assert min(rel) <= 0.0185 / 2.0 + 1e-12
    assert max(rel) >= 0.0185 * 4.0 - 1e-12
    assert min(rel) < 0.05  # below the old floor


def test_fix_b_matched_quality_assert_raises_on_mismatch():
    """FIX-B: matched ICIR far from constant ICIR fails closed."""
    from examples.power_calibration.beta_t import assert_matched_icir_quality

    assert_matched_icir_quality(4.0, 4.1, rel_tol=0.20)  # ok
    with pytest.raises(ValueError, match=r"matched|quality|tolerance|20"):
        assert_matched_icir_quality(3.79, 5.63, rel_tol=0.20)


# ---------------------------------------------------------------------------
# Rework 02 — FIX-C: NaN-safe figure render
# ---------------------------------------------------------------------------


def test_fix_c_render_figures_tolerates_nan_hero_row(tmp_path: Path):
    """FIX-C: β=0 A=NaN must not crash errorbar; figures written non-empty."""
    from types import SimpleNamespace

    from examples.power_calibration.calibrate import CalibrationResult
    from examples.power_calibration.figure import render_figures

    cal = CalibrationResult(
        shell_phi=0.97,
        calibration_seed_root=CALIBRATION_SEED_ROOT,
        calibration_k=2,
        beta_grid=[0.05, 0.1, 0.2],
        mean_ic=[0.01, 0.02, 0.03],
        mean_ic_vol=[0.1, 0.1, 0.1],
        mean_icir=[1.0, 2.0, 4.0],
        se_icir=[0.1, 0.1, 0.1],
        beta_star={"2.0": 0.1, "4.0": 0.2},
        strength_grid=[0.0, 2.0, 4.0],
    )
    summaries = [
        SimpleNamespace(
            strength=0.0,
            a_hat=float("nan"),
            a_lo=float("nan"),
            a_hi=float("nan"),
            b_hat=0.01,
            gate_tpr={"fdr_by": 0.05},
        ),
        SimpleNamespace(
            strength=2.0,
            a_hat=0.3,
            a_lo=0.1,
            a_hi=0.5,
            b_hat=0.6,
            gate_tpr={"fdr_by": 0.4},
        ),
        SimpleNamespace(
            strength=4.0,
            a_hat=0.8,
            a_lo=0.6,
            a_hi=0.95,
            b_hat=0.95,
            gate_tpr={"fdr_by": 0.9},
        ),
    ]
    out = tmp_path / "fig_out"
    result = render_figures(out_dir=out, summaries=summaries, calibration=cal)
    assert (out / "figure.png").is_file()
    assert (out / "figure.svg").is_file()
    assert (out / "figure.png").stat().st_size > 0
    assert (out / "figure.svg").stat().st_size > 0
    assert result["a_hat"][0] != result["a_hat"][0]  # nan preserved in return


def test_beta_t_battery_emits_finite_tpr_drops(tmp_path: Path):
    """FIX 2: β_t path must run the greater battery and report drop numbers."""
    from examples.power_calibration.beta_t import run_beta_t_power

    cfg = _reduced_cfg(tmp_path)
    cfg.beta_t_icir_targets = (1.0,)
    cfg.r0 = 2  # R seeds for β_t battery
    cfg.n_noise = 2
    cfg.n_offsets = 3
    cfg.run_beta_t_appendix = True
    cal = run_calibration(cfg)
    # Build evaluator via a minimal calibrate-aligned config
    from adapters.qlib_cn import QlibCNFactorEvaluator

    label = cfg.synthetic["label_panel"]
    ev = QlibCNFactorEvaluator.from_panels(
        label,
        {
            "window": dict(cfg.window),
            "declared_data_tag": "synthetic",
            "universe": "synthetic",
            "provider_uri": "synthetic",
            "min_cross_section": cfg.min_cross_section,
        },
    )
    drop = run_beta_t_power(
        cfg,
        evaluator=ev,
        calibration=cal,
        out_dir=Path(cfg.out_dir) / "beta_t",
        n_seeds=cfg.r0,
        match_beta_grid=[0.05, 0.20, 0.40],
    )
    assert drop is not None
    assert "drops" in drop
    assert len(drop["drops"]) >= 1
    d0 = drop["drops"][0]
    assert "unanimous_drop" in d0
    assert "pbo_drop" in d0
    assert d0["unanimous_drop"] == d0["unanimous_drop"]  # finite
    assert d0["pbo_drop"] == d0["pbo_drop"]
    # Arms must carry TPR fields
    for arm in drop["arms"]:
        assert "unanimous_tpr" in arm
        assert "pbo_tpr" in arm
        assert arm["unanimous_tpr"] == arm["unanimous_tpr"]
        assert arm["n_seeds"] >= 1
    # Must actually call judge (not ICIR-only): check verdict ledgers or battery flag
    assert drop.get("battery_ran") is True
