"""Tests for examples/killer_demo (killer-demo.md §11 obligations).

TDD: these tests were written against the design before / alongside the
implementation; they assert mechanism invariants, not the production headline.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from examples.killer_demo.aggregate import (
    aggregate_sweep_rows,
    survivor_count,
    trial_survives,
)
from examples.killer_demo.config import TARGET_T, DemoConfig
from examples.killer_demo.figure import build_caption
from examples.killer_demo.generation import (
    build_factor_specs,
    draw_offsets,
    generate_score_panels,
    spawn_seed_tree,
)
from examples.killer_demo.report import caption_is_complete, report_has_four_sections
from examples.killer_demo.run import run_demo
from examples.killer_demo.window import (
    assert_window_constraints,
    choose_window_for_t,
    evaluation_dates_for_window,
    load_day_calendar,
)

# ---------------------------------------------------------------------------
# Helpers: reduced synthetic config (10 candidates × 20 offsets)
# ---------------------------------------------------------------------------


def _synthetic_label_panel(t: int = 32, n_inst: int = 60, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # Business days index (labels only; no market calendar needed for from_panels)
    dates = pd.bdate_range("2024-01-02", periods=t)
    instruments = [f"I{j:03d}" for j in range(n_inst)]
    data = rng.standard_normal((t, n_inst))
    return pd.DataFrame(data, index=dates, columns=instruments)


def _reduced_cfg(tmp_path: Path, seed: int = 20260710) -> DemoConfig:
    t = 32  # divisible by n_splits=16
    label = _synthetic_label_panel(t=t, n_inst=60, seed=1)
    return DemoConfig(
        master_seed=seed,
        n_candidates=10,
        n_offsets=20,
        delta_min=4,
        target_t=t,
        n_splits=16,
        min_cross_section=10,
        out_dir=str(tmp_path / f"out_{seed}"),
        skip_download=True,
        synthetic={"label_panel": label},
        window={
            "start": label.index[0].strftime("%Y-%m-%d"),
            "end": label.index[-1].strftime("%Y-%m-%d"),
        },
    )


# ---------------------------------------------------------------------------
# 1. Aggregation unit tests (hand-built verdict sets; both polarities) — §6
# ---------------------------------------------------------------------------


def _v(statistic: str, decisions: dict[str, str], **params):
    return SimpleNamespace(statistic=statistic, decisions=decisions, params=params)


def test_aggregation_unanimous_all_pass_survives():
    verdicts = [
        _v("fdr_by", {"t0001": "pass", "t0002": "pass"}),
        _v("noise_control", {"t0001": "pass"}, mode="individual"),
        _v("noise_control", {"t0002": "pass"}, mode="individual"),
    ]
    assert trial_survives("t0001", verdicts) is True
    assert trial_survives("t0002", verdicts) is True
    assert survivor_count(["t0001", "t0002"], verdicts) == 2


def test_aggregation_one_reject_kills():
    verdicts = [
        _v("fdr_by", {"t0001": "pass", "t0002": "reject"}),
        _v("dsr", {"t0001": "pass"}),
        _v("pbo_cscv", {"t0001": "pass"}),
        _v("noise_control", {"t0001": "pass"}, mode="pool_max"),
        _v("noise_control", {"t0001": "pass"}, mode="individual"),
        _v("noise_control", {"t0002": "pass"}, mode="individual"),
    ]
    assert trial_survives("t0001", verdicts) is True
    assert trial_survives("t0002", verdicts) is False  # FDR reject kills
    assert survivor_count(["t0001", "t0002"], verdicts) == 1


def test_aggregation_accused_needs_all_five():
    base = [
        _v("fdr_by", {"t0001": "pass"}),
        _v("dsr", {"t0001": "pass"}),
        _v("pbo_cscv", {"t0001": "pass"}),
        _v("noise_control", {"t0001": "pass"}, mode="pool_max"),
        _v("noise_control", {"t0001": "pass"}, mode="individual"),
    ]
    assert trial_survives("t0001", base) is True
    killed = base[:-1] + [_v("noise_control", {"t0001": "reject"}, mode="individual")]
    assert trial_survives("t0001", killed) is False


def test_aggregation_no_verdicts_does_not_survive():
    assert trial_survives("t0001", []) is False


def test_aggregation_informational_dsr_cannot_kill():
    """Idle-gate ruling: informational DSR reject does not flip survival."""
    base = [
        _v("fdr_by", {"t0001": "pass"}),
        SimpleNamespace(
            statistic="dsr",
            decisions={"t0001": "reject"},
            params={},
            role="informational",
        ),
        _v("pbo_cscv", {"t0001": "pass"}),
        _v("noise_control", {"t0001": "pass"}, mode="pool_max"),
        _v("noise_control", {"t0001": "pass"}, mode="individual"),
    ]
    assert trial_survives("t0001", base) is True


def test_aggregation_role_none_legacy_still_counts():
    """Legacy role=None verdicts remain discriminating."""
    verdicts = [
        SimpleNamespace(
            statistic="fdr_by",
            decisions={"t0001": "pass"},
            params={},
            role=None,
        ),
        SimpleNamespace(
            statistic="dsr",
            decisions={"t0001": "reject"},
            params={},
            role=None,
        ),
    ]
    assert trial_survives("t0001", verdicts) is False


def test_sweep_aggregation_logic():
    rows = [
        {
            "seed": 1,
            "n_survivors": 0,
            "accused_gate_verdicts": {
                "fdr_by": "reject",
                "dsr": "reject",
                "pbo_cscv": "reject",
                "noise_pool_max": "reject",
                "noise_individual": "pass",
            },
        },
        {
            "seed": 2,
            "n_survivors": 1,
            "accused_gate_verdicts": {
                "fdr_by": "pass",
                "dsr": "reject",
                "pbo_cscv": "reject",
                "noise_pool_max": "pass",
                "noise_individual": "pass",
            },
        },
    ]
    summary = aggregate_sweep_rows(rows)
    assert summary["n_seeds"] == 2
    assert summary["mean_survivors"] == 0.5
    assert summary["gate_pass_counts"]["fdr_by"] == 1
    assert summary["gate_pass_rates"]["noise_individual"] == 1.0
    assert summary["survivor_counts"] == [0, 1]


# ---------------------------------------------------------------------------
# 2. Window arithmetic — exactly 480, divisible by 16 (§5.2 / §11)
# ---------------------------------------------------------------------------


def test_window_arithmetic_exactly_480_divisible_by_16():
    provider = Path.home() / ".qlib" / "qlib_data" / "cn_data"
    if not (provider / "calendars" / "day.txt").is_file():
        pytest.skip("qlib cn_data pack not present")
    calendar = load_day_calendar(provider)
    window, eval_iso = choose_window_for_t(calendar, target_t=TARGET_T)
    assert len(eval_iso) == TARGET_T
    assert TARGET_T % 16 == 0
    assert_window_constraints(len(eval_iso), 16)
    # Round-trip: adapter rule on the declared window yields the same set
    check = evaluation_dates_for_window(calendar, window["start"], window["end"])
    assert len(check) == TARGET_T
    assert [d.strftime("%Y-%m-%d") for d in check] == eval_iso


def test_assert_window_constraints_rejects_bad_t():
    with pytest.raises(ValueError, match="not divisible"):
        assert_window_constraints(481, 16)


# ---------------------------------------------------------------------------
# 3. Seed determinism (two reduced runs) — §11
# ---------------------------------------------------------------------------


def test_seed_determinism_two_runs(tmp_path: Path):
    cfg_a = _reduced_cfg(tmp_path / "a", seed=20260710)
    cfg_b = _reduced_cfg(tmp_path / "b", seed=20260710)
    res_a = run_demo(cfg_a)
    res_b = run_demo(cfg_b)

    assert res_a.series_values == res_b.series_values
    assert res_a.offsets == res_b.offsets
    assert res_a.accused_trial_id == res_b.accused_trial_id
    assert res_a.accused_abs_t == res_b.accused_abs_t
    assert res_a.n_survivors == res_b.n_survivors
    # Figure numbers (scalar annotations) identical
    for key in ("accused_abs_t", "pool_p_hat", "n_at_least", "null_mean", "null_max"):
        assert res_a.figure_numbers[key] == res_b.figure_numbers[key]


def test_seed_changes_series(tmp_path: Path):
    res_a = run_demo(_reduced_cfg(tmp_path / "a", seed=20260710))
    res_b = run_demo(_reduced_cfg(tmp_path / "b", seed=20260711))
    assert res_a.series_values != res_b.series_values


# ---------------------------------------------------------------------------
# 4. §5.3 consistency assertion (pool-max argmax == naive) — exercised in run
# ---------------------------------------------------------------------------


def test_pool_max_matches_naive_accused(tmp_path: Path):
    res = run_demo(_reduced_cfg(tmp_path, seed=20260710))
    # run_demo raises on mismatch; also re-check from ledger via open()/replay
    from court.ledger import Ledger

    ledger = Ledger.open(res.ledger_path)
    pool = next(
        v
        for v in ledger.verdicts()
        if v.statistic == "noise_control" and v.params.get("mode") == "pool_max"
    )
    assert pool.computed["selected_trial_id"] == res.accused_trial_id


def test_verdict_count_matches_battery(tmp_path: Path):
    cfg = _reduced_cfg(tmp_path, seed=20260710)
    res = run_demo(cfg)
    from court.ledger import Ledger

    ledger = Ledger.open(res.ledger_path)
    # 4 shared + n_candidates individual
    assert len(ledger.verdicts()) == 4 + cfg.n_candidates


# ---------------------------------------------------------------------------
# 5. Report smoke — four sections + complete caption (§8 / §10 / §11)
# ---------------------------------------------------------------------------


def test_report_smoke_four_sections_and_caption(tmp_path: Path):
    res = run_demo(_reduced_cfg(tmp_path, seed=20260710))
    assert report_has_four_sections(res.report_text)
    assert caption_is_complete(res.caption)
    caption2 = build_caption(
        master_seed=20260710,
        t_len=32,
        data_tag="2026-07-05",
        engine_version="0.1.0.dev0",
        cost_declaration="gross paper series — no transaction costs, no market impact",
    )
    assert caption_is_complete(caption2)
    assert (Path(tmp_path) / "out_20260710" / "report.md").is_file()
    assert (Path(tmp_path) / "out_20260710" / "figure.png").is_file()
    assert (Path(tmp_path) / "out_20260710" / "figure.svg").is_file()
    assert (Path(tmp_path) / "out_20260710" / "run_config.json").is_file()
    assert (Path(tmp_path) / "out_20260710" / "ledger.jsonl").is_file()


# ---------------------------------------------------------------------------
# Generation / seed tree unit checks
# ---------------------------------------------------------------------------


def test_factor_menu_full_is_100():
    specs = build_factor_specs(DemoConfig())
    assert len(specs) == 100
    families = {s.family for s in specs}
    assert families == {
        "momentum",
        "reversal",
        "volatility",
        "liquidity",
        "value_quality",
    }


def test_offsets_without_replacement_in_range():
    _, off_ss = spawn_seed_tree(20260710)
    offs = draw_offsets(off_ss, n_offsets=199, delta_min=60, t_len=480)
    assert len(offs) == 199
    assert len(set(offs)) == 199
    assert min(offs) >= 60
    assert max(offs) <= 420


def test_panel_reproducible_from_seed_path():
    cfg = DemoConfig(n_candidates=3)
    specs = build_factor_specs(cfg)
    dates = [f"2024-01-{d:02d}" for d in range(2, 12)]
    instruments = ["A", "B", "C"]
    c0, _ = spawn_seed_tree(cfg.master_seed)
    p1 = generate_score_panels(specs, c0, dates=dates, instruments=instruments)
    c0b, _ = spawn_seed_tree(cfg.master_seed)
    p2 = generate_score_panels(specs, c0b, dates=dates, instruments=instruments)
    for a, b in zip(p1, p2, strict=True):
        np.testing.assert_array_equal(a.to_numpy(), b.to_numpy())
