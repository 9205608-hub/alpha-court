"""Tests for adapters.qlib_cn — contract §7.5 obligations (TDD: written before impl)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("qlib", reason="adapter tests require the [qlib] extra")

from adapters.qlib_cn import (  # noqa: E402
    COST_DECLARATION,
    EvalGrid,
    EvalResult,
    QlibCNFactorEvaluator,
)

# ---------------------------------------------------------------------------
# Synthetic panel helpers (dense, tie-free; always-on CI, no data pack)
# ---------------------------------------------------------------------------

QLIB_DATA = Path.home() / ".qlib" / "qlib_data" / "cn_data"
HAS_QLIB_DATA = QLIB_DATA.is_dir() and (QLIB_DATA / "calendars").is_dir()


def _tie_free_panels(n_dates: int = 12, n_inst: int = 60, seed: int = 0):
    """Build dense score/label panels with unique values per row (no score ties)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_dates)
    instruments = [f"S{i:04d}" for i in range(n_inst)]
    # Unique scores per row via rank of continuous noise + tiny col jitter
    scores = np.empty((n_dates, n_inst), dtype=np.float64)
    labels = np.empty((n_dates, n_inst), dtype=np.float64)
    for t in range(n_dates):
        scores[t] = rng.normal(size=n_inst) + np.arange(n_inst) * 1e-9
        labels[t] = rng.normal(size=n_inst) + np.arange(n_inst) * 1e-10
    score_df = pd.DataFrame(scores, index=dates, columns=instruments)
    label_df = pd.DataFrame(labels, index=dates, columns=instruments)
    return score_df, label_df


def _to_multiindex_series(panel: pd.DataFrame) -> pd.Series:
    """Stack date×instrument panel to MultiIndex Series (datetime, instrument)."""
    s = panel.stack()
    s.index = s.index.set_names(["datetime", "instrument"])
    return s


def _make_synthetic_evaluator(
    label_df: pd.DataFrame,
    *,
    quantile: float = 0.2,
    min_cross_section: int = 10,
) -> QlibCNFactorEvaluator:
    """Build evaluator from in-memory label panel (no qlib data pack)."""
    return QlibCNFactorEvaluator.from_panels(
        label_panel=label_df,
        config={
            "window": {
                "start": str(label_df.index[0].date()),
                "end": str(label_df.index[-1].date()),
            },
            "declared_data_tag": "synthetic-test",
            "quantile": quantile,
            "min_cross_section": min_cross_section,
            "universe": "synthetic",
            "provider_uri": "synthetic",
        },
    )


# ---------------------------------------------------------------------------
# §7.5.1 Oracle: kernel vs qlib.contrib.eva.alpha
# ---------------------------------------------------------------------------


def _oracle_ric(score_df: pd.DataFrame, label_df: pd.DataFrame) -> np.ndarray:
    """qlib calc_ic ric on stacked panels (NaNs pairwise-dropped by pandas)."""
    from qlib.contrib.eva.alpha import calc_ic

    pred = _to_multiindex_series(score_df)
    lab = _to_multiindex_series(label_df)
    _ic, ric = calc_ic(pred, lab, date_col="datetime", dropna=False)
    return ric.sort_index().to_numpy(dtype=np.float64)


def test_oracle_ic_matches_calc_ic_ric():
    """'ic' metric matches calc_ic(...).ric within rtol 1e-12 (contract §7.5.1)."""
    score_df, label_df = _tie_free_panels()
    ev = _make_synthetic_evaluator(label_df, min_cross_section=10)
    result = ev.evaluate(score_df, "ic")
    assert isinstance(result, EvalResult)
    np.testing.assert_allclose(
        result.values, _oracle_ric(score_df, label_df), rtol=1e-12, atol=0.0
    )


def test_oracle_ic_nan_labels_matches_calc_ic_ric():
    """NaN-bearing labels: joint-subset ranks match calc_ic ric (§7.5.1 blocker fix)."""
    score_df, label_df = _tie_free_panels(n_dates=12, n_inst=60, seed=7)
    # Punch NaNs into labels (asymmetric vs scores) so full-support ranks diverge
    label_df = label_df.copy()
    for t in range(len(label_df)):
        label_df.iloc[t, t : t + 8] = np.nan
    ev = _make_synthetic_evaluator(label_df, min_cross_section=10)
    result = ev.evaluate(score_df, "ic")
    np.testing.assert_allclose(
        result.values, _oracle_ric(score_df, label_df), rtol=1e-12, atol=0.0
    )


def test_oracle_ic_pit_churn_matches_calc_ic_ric():
    """PIT membership churn: joint ranks match calc_ic after non-members → NaN."""
    score_df, label_df = _tie_free_panels(n_dates=12, n_inst=60, seed=11)
    t_len, n_inst = score_df.shape
    pit = np.ones((t_len, n_inst), dtype=bool)
    # Rotate membership: drop a moving block of names each day
    for t in range(t_len):
        start = (t * 3) % n_inst
        for k in range(12):
            pit[t, (start + k) % n_inst] = False
    # Mirror PIT into panels for the qlib oracle (pairwise NaN exclusion)
    s_arr = score_df.to_numpy(dtype=np.float64, copy=True)
    y_arr = label_df.to_numpy(dtype=np.float64, copy=True)
    s_arr[~pit] = np.nan
    y_arr[~pit] = np.nan
    score_for_oracle = pd.DataFrame(s_arr, index=score_df.index, columns=score_df.columns)
    label_for_oracle = pd.DataFrame(y_arr, index=label_df.index, columns=label_df.columns)
    ev = QlibCNFactorEvaluator.from_panels(
        label_panel=label_df,
        config={
            "window": {
                "start": str(label_df.index[0].date()),
                "end": str(label_df.index[-1].date()),
            },
            "declared_data_tag": "synthetic-test",
            "quantile": 0.2,
            "min_cross_section": 10,
            "universe": "synthetic",
            "provider_uri": "synthetic",
        },
        pit_mask=pit,
    )
    result = ev.evaluate(score_df, "ic")
    np.testing.assert_allclose(
        result.values,
        _oracle_ric(score_for_oracle, label_for_oracle),
        rtol=1e-12,
        atol=0.0,
    )


def test_oracle_returns_matches_calc_long_short_return():
    """'returns' metric matches calc_long_short_return long_short_r (§7.5.1)."""
    from qlib.contrib.eva.alpha import calc_long_short_return

    score_df, label_df = _tie_free_panels()
    quantile = 0.2
    ev = _make_synthetic_evaluator(label_df, quantile=quantile, min_cross_section=10)
    result = ev.evaluate(score_df, "returns")

    pred = _to_multiindex_series(score_df)
    lab = _to_multiindex_series(label_df)
    long_short_r, _long_avg = calc_long_short_return(
        pred, lab, date_col="datetime", quantile=quantile, dropna=False
    )
    expected = long_short_r.sort_index().to_numpy(dtype=np.float64)
    np.testing.assert_allclose(result.values, expected, rtol=1e-12, atol=0.0)


# ---------------------------------------------------------------------------
# §7.5.2 Equivalence invariant (array_equal, no tolerance)
# ---------------------------------------------------------------------------


def test_equivalence_shifted_vs_circshift_evaluate():
    """evaluate_shifted(S,[δ]) bit-equals evaluate(circshift(S,δ)) for ic & returns."""
    score_df, label_df = _tie_free_panels(n_dates=15, n_inst=60)
    for metric in ("ic", "returns"):
        ev = _make_synthetic_evaluator(label_df, min_cross_section=10)
        for delta in (0, 1, 3, 7):
            grid = ev.evaluate_shifted(score_df, metric, [delta])
            assert isinstance(grid, EvalGrid)
            # circshift: new[t] = old[(t-δ) mod T]  ==  np.roll(..., delta)
            rolled = pd.DataFrame(
                np.roll(score_df.to_numpy(), delta, axis=0),
                index=score_df.index,
                columns=score_df.columns,
            )
            single = ev.evaluate(rolled, metric)
            assert np.array_equal(grid.values[0], single.values), (
                f"metric={metric} delta={delta}"
            )


def test_equivalence_delta_zero_matches_evaluate():
    """evaluate_shifted(S, m, [0]) reproduces evaluate(S, m) exactly (§7.3)."""
    score_df, label_df = _tie_free_panels()
    for metric in ("ic", "returns"):
        ev = _make_synthetic_evaluator(label_df, min_cross_section=10)
        single = ev.evaluate(score_df, metric)
        grid = ev.evaluate_shifted(score_df, metric, [0])
        assert np.array_equal(grid.values[0], single.values)
        assert grid.index == single.index


# ---------------------------------------------------------------------------
# §7.5.3 Determinism (§8 synthetic double-run)
# ---------------------------------------------------------------------------


def test_determinism_same_process_double_run():
    """Two evaluators + identical inputs → array_equal values (contract §8)."""
    score_df, label_df = _tie_free_panels(seed=42)
    ev1 = _make_synthetic_evaluator(label_df, min_cross_section=10)
    ev2 = _make_synthetic_evaluator(label_df, min_cross_section=10)
    r1 = ev1.evaluate(score_df, "ic")
    r2 = ev2.evaluate(score_df, "ic")
    assert np.array_equal(r1.values, r2.values)
    g1 = ev1.evaluate_shifted(score_df, "returns", [0, 2, 5])
    g2 = ev2.evaluate_shifted(score_df, "returns", [0, 2, 5])
    assert np.array_equal(g1.values, g2.values)


def test_meta_schema_fields_present():
    """EvalResult.meta carries §7.4 keys plus meta.config with every constructor field."""
    score_df, label_df = _tie_free_panels()
    cfg = {
        "window": {
            "start": str(label_df.index[0].date()),
            "end": str(label_df.index[-1].date()),
        },
        "declared_data_tag": "synthetic-test",
        "quantile": 0.2,
        "min_cross_section": 10,
        "universe": "synthetic",
        "provider_uri": "synthetic",
        "label_expr": "Ref($close, -2)/Ref($close, -1) - 1",
    }
    ev = QlibCNFactorEvaluator.from_panels(label_panel=label_df, config=cfg)
    result = ev.evaluate(score_df, "ic")
    meta = result.meta
    for key in (
        "metric",
        "metric_params",
        "label_expr",
        "price_field",
        "universe",
        "window",
        "n_evaluation_dates",
        "cost_declaration",
        "data_version",
        "qlib_version",
        "adapter_version",
        "config",
    ):
        assert key in meta, key
    assert meta["price_field"] == "$close"
    assert meta["cost_declaration"] == COST_DECLARATION
    assert meta["data_version"]["declared_tag"] == "synthetic-test"
    assert "calendar_end" in meta["data_version"]
    assert "n_instruments" in meta["data_version"]
    # meta.config round-trips every constructor field, including ic path (§7.1)
    assert meta["config"]["provider_uri"] == "synthetic"
    assert meta["config"]["universe"] == "synthetic"
    assert meta["config"]["window"] == cfg["window"]
    assert meta["config"]["label_expr"] == cfg["label_expr"]
    assert meta["config"]["quantile"] == 0.2
    assert meta["config"]["min_cross_section"] == 10
    assert meta["config"]["declared_data_tag"] == "synthetic-test"
    # quantile present in config even when metric is ic (not only metric_params)
    assert "quantile" not in meta["metric_params"]


def test_fail_closed_missing_score_row():
    """Missing evaluation-date row raises (contract §7.2)."""
    score_df, label_df = _tie_free_panels(n_dates=10)
    ev = _make_synthetic_evaluator(label_df, min_cross_section=10)
    bad = score_df.iloc[1:]  # drop first eval date
    with pytest.raises(ValueError, match="missing"):
        ev.evaluate(bad, "ic")


def test_fail_closed_bad_offset():
    """Offsets outside 0 <= δ < T raise; empty list raises (§7.3 erratum)."""
    score_df, label_df = _tie_free_panels(n_dates=10)
    ev = _make_synthetic_evaluator(label_df, min_cross_section=10)
    with pytest.raises(ValueError, match="offset"):
        ev.evaluate_shifted(score_df, "ic", [0, 10])  # δ == T illegal
    with pytest.raises(ValueError, match="offset"):
        ev.evaluate_shifted(score_df, "ic", [-1])
    with pytest.raises(ValueError, match="non-empty|empty"):
        ev.evaluate_shifted(score_df, "ic", [])


def test_strict_config_types_no_repair():
    """Config type coercion is rejected (contract §7.1 no-repair)."""
    score_df, label_df = _tie_free_panels(n_dates=5, n_inst=20)
    base = {
        "window": {
            "start": str(label_df.index[0].date()),
            "end": str(label_df.index[-1].date()),
        },
        "declared_data_tag": "synthetic-test",
        "provider_uri": "synthetic",
        "universe": "synthetic",
    }
    with pytest.raises(TypeError, match="min_cross_section"):
        QlibCNFactorEvaluator.from_panels(
            label_df, {**base, "min_cross_section": 49.9, "quantile": 0.2}
        )
    with pytest.raises(TypeError, match="quantile"):
        QlibCNFactorEvaluator.from_panels(
            label_df, {**base, "min_cross_section": 10, "quantile": "0.2"}
        )
    with pytest.raises(TypeError, match="universe"):
        QlibCNFactorEvaluator.from_panels(
            label_df, {**base, "universe": 300, "min_cross_section": 10, "quantile": 0.2}
        )


def test_fail_closed_min_cross_section():
    """Cross-section below min_cross_section raises (contract §5.3)."""
    score_df, label_df = _tie_free_panels(n_dates=5, n_inst=20)
    # Punch a hole: only 3 finite pairs on date 0
    score_df.iloc[0, 3:] = np.nan
    ev = _make_synthetic_evaluator(label_df, min_cross_section=10)
    with pytest.raises(ValueError, match="cross.section|min_cross"):
        ev.evaluate(score_df, "ic")


# ---------------------------------------------------------------------------
# §7.5.4 Convention spot-check on real pack (skip if data missing)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_QLIB_DATA, reason="qlib cn_data pack not present")
def test_convention_spot_check_sh600519():
    """SH600519 $close/$factor/$adjclose match qlib-cn-data.md §3.3 (rounded)."""
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(QLIB_DATA), region=REG_CN, kernels=1)
    close = D.features(
        ["SH600519"],
        ["$close", "$factor", "$adjclose"],
        start_time="2026-06-29",
        end_time="2026-07-03",
    )
    # Documented table (2-d.p. / 4-d.p. display values)
    expected_close = {
        "2026-06-29": 290.62,
        "2026-06-30": 288.32,
        "2026-07-01": 290.15,
        "2026-07-02": 292.58,
        "2026-07-03": 290.50,
    }
    expected_adj = {
        "2026-06-29": 10331.67,
        "2026-06-30": 10249.79,
        "2026-07-01": 10314.81,
        "2026-07-02": 10401.18,
        "2026-07-03": 10327.26,
    }
    for ts, row in close.iterrows():
        d = ts[1].strftime("%Y-%m-%d") if isinstance(ts, tuple) else ts.strftime("%Y-%m-%d")
        # MultiIndex (instrument, datetime)
        if isinstance(close.index, pd.MultiIndex):
            d = ts[1].strftime("%Y-%m-%d")
        assert d in expected_close
        assert abs(float(row["$close"]) - expected_close[d]) < 0.01
        assert abs(float(row["$adjclose"]) - expected_adj[d]) < 0.01
        assert abs(float(row["$factor"]) - 0.2432) < 5e-5
        # $close / $factor ≈ cash scale (~1194) per research note
        cash = float(row["$close"]) / float(row["$factor"])
        assert 1000 < cash < 1400

    # Label expr uses $close (not $adjclose): evaluator construction + label finite
    ev = QlibCNFactorEvaluator(
        {
            "provider_uri": str(QLIB_DATA),
            "window": {"start": "2024-07-03", "end": "2026-07-03"},
            "declared_data_tag": "2026-07-05",
            "min_cross_section": 50,
        }
    )
    assert ev.evaluation_dates  # non-empty
    # last two window days are not evaluation dates (§5.2)
    assert "2026-07-03" not in ev.evaluation_dates
    assert "2026-07-02" not in ev.evaluation_dates
    meta = ev.evaluate(
        _random_scores_for_evaluator(ev, seed=1),
        "ic",
    ).meta
    assert meta["label_expr"] == "Ref($close, -2)/Ref($close, -1) - 1"
    assert meta["price_field"] == "$close"
    assert meta["data_version"]["declared_tag"] == "2026-07-05"
    assert meta["cost_declaration"] == COST_DECLARATION


def _random_scores_for_evaluator(ev: QlibCNFactorEvaluator, seed: int = 0) -> pd.DataFrame:
    """Dense random scores on the evaluator's evaluation dates × instruments."""
    rng = np.random.default_rng(seed)
    dates = pd.DatetimeIndex(ev.evaluation_dates)
    cols = list(ev.instruments)
    arr = rng.normal(size=(len(dates), len(cols)))
    # break ties
    arr = arr + np.arange(len(cols)) * 1e-12
    return pd.DataFrame(arr, index=dates, columns=cols)


# ---------------------------------------------------------------------------
# §8 layer-2 golden fingerprint (integration; skip if pack absent)
# ---------------------------------------------------------------------------

# Generated on this machine against declared_data_tag 2026-07-05, window
# 2024-07-03→2026-07-03, seed 20260705, metric=ic. Re-baseline only via §6 bump.
_GOLDEN_FIRST5 = [
    "-0.01999192198772949",
    "0.010070468390122489",
    "0.0582796011951617",
    "0.08352726322768636",
    "-0.1429294772765733",
]
_GOLDEN_LAST5 = [
    "0.04275421217182369",
    "0.026655851731685908",
    "-0.006731633343319298",
    "-0.05795844751984373",
    "-0.0027953752639834316",
]
_GOLDEN_SHA256 = "b0db8bbe1874e548a87a5c614a1d4117b94fc777c78a0d21366e4f5a675ba328"


@pytest.mark.skipif(not HAS_QLIB_DATA, reason="qlib cn_data pack not present")
def test_golden_fingerprint_rankic_demo_window():
    """§8 layer-2: fixed synthetic factor RankIC fingerprint on pinned pack."""
    import hashlib

    ev = QlibCNFactorEvaluator(
        {
            "provider_uri": str(QLIB_DATA),
            "window": {"start": "2024-07-03", "end": "2026-07-03"},
            "declared_data_tag": "2026-07-05",
            "min_cross_section": 50,
            "quantile": 0.2,
        }
    )
    scores = _random_scores_for_evaluator(ev, seed=20260705)
    result = ev.evaluate(scores, "ic")
    vals = result.values
    assert [repr(float(v)) for v in vals[:5]] == _GOLDEN_FIRST5
    assert [repr(float(v)) for v in vals[-5:]] == _GOLDEN_LAST5
    digest = hashlib.sha256(vals.astype("<f8").tobytes()).hexdigest()
    assert digest == _GOLDEN_SHA256
    assert result.meta["data_version"]["declared_tag"] == "2026-07-05"
    assert result.meta["data_version"]["calendar_end"] == "2026-07-03"
