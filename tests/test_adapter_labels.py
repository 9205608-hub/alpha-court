"""Qlib-free test for ``QlibCNFactorEvaluator.labels``.

Lives outside ``test_adapter_qlib_cn.py`` because that file is gated on the
``[qlib]`` extra, while ``.labels`` must work WITHOUT qlib: it feeds the
power-calibration oracle (``docs/design/power-calibration.md`` §4.1) through
the synthetic ``from_panels`` path in reduced-config tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from adapters.qlib_cn import QlibCNFactorEvaluator


def _panels(n_dates: int = 8, n_inst: int = 30, seed: int = 0):
    """Dense score/label panels (mirrors test_adapter_qlib_cn helpers)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_dates)
    instruments = [f"S{i:04d}" for i in range(n_inst)]
    scores = rng.normal(size=(n_dates, n_inst))
    labels = rng.normal(size=(n_dates, n_inst))
    return (
        pd.DataFrame(scores, index=dates, columns=instruments),
        pd.DataFrame(labels, index=dates, columns=instruments),
    )


def _evaluator(label_df: pd.DataFrame) -> QlibCNFactorEvaluator:
    return QlibCNFactorEvaluator.from_panels(
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
    )


def test_labels_property_aligned_defensive_copy():
    """`labels` exposes the (T, N) label panel aligned to evaluation_dates ×
    instruments, as a defensive copy (mutating it never touches kernel state)."""
    score_df, label_df = _panels()
    ev = _evaluator(label_df)
    lab = ev.labels
    assert lab.shape == (len(ev.evaluation_dates), len(ev.instruments))
    assert lab.dtype == np.float64
    np.testing.assert_array_equal(lab, label_df.to_numpy(dtype=np.float64))
    # Defensive copy: caller mutation must not leak into later reads/evaluations
    before = ev.evaluate(score_df, "ic").values
    lab[0, 0] = 1e9
    np.testing.assert_array_equal(ev.labels, label_df.to_numpy(dtype=np.float64))
    after = ev.evaluate(score_df, "ic").values
    np.testing.assert_array_equal(before, after)


def test_from_panels_partial_pit_mask_counts_measured_instruments():
    """`_n_instruments_measured` must mean the same thing on both constructor
    paths: instruments with ANY PIT membership (the `__init__` semantics).
    from_panels hand-copied attributes and silently diverged to "all columns"
    (v0.2-12 slice E — the exact drift a shared finalizer prevents)."""
    score_df, label_df = _panels(n_inst=30)
    mask = np.ones(label_df.shape, dtype=bool)
    mask[:, -5:] = False  # 5 instruments never enter the universe
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
        pit_mask=mask,
    )
    assert ev._n_instruments_measured == 25
    assert ev._meta("returns")["data_version"]["n_instruments"] == 25
