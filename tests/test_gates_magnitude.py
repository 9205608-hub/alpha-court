"""Red-first tests for gates.magnitude_vs_turnover (ticket v0.3-02).

Pure economic-floor blade: net(c) = mean_gross − c·tau. No significance
statistics. Integration fixtures copied from tests/test_blades_harness.py
(do not import that module).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from court.ledger import DeclaredProtocol, SeConvention, Window
from gates.magnitude_vs_turnover import MagnitudeVsTurnoverBlade

# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------

_TEN_BP = (0.001, 0.001, 0.001, 0.001, 0.001)


def _series(values: tuple[float, ...]) -> SimpleNamespace:
    index = tuple(f"d{i}" for i in range(len(values)))
    return SimpleNamespace(index=index, values=values)


def _mean(values: tuple[float, ...]) -> float:
    return float(np.asarray(values, dtype=np.float64).mean())


def _spec(c_ref: float, **extra: Any) -> dict:
    cfg: dict[str, Any] = {"c_ref": c_ref}
    cfg.update(extra)
    return {"blades": {"magnitude_vs_turnover": cfg}}


def _run(
    values: tuple[float, ...] = _TEN_BP,
    *,
    tau: float | None = 1.0,
    c_ref: float | None = 0.002,
    blade: MagnitudeVsTurnoverBlade | None = None,
    params: dict | None = None,
    spec: dict | None = None,
) -> dict:
    if blade is None:
        blade = MagnitudeVsTurnoverBlade()
    if spec is None:
        spec = {} if c_ref is None else _spec(c_ref)
    if params is None:
        params = {} if tau is None else {"turnover": tau}
    return blade.run("trial-1", spec, params, None, _series(values))


# ---------------------------------------------------------------------------
# a. Hand vector: 10 bp gross, tau=1.0
# ---------------------------------------------------------------------------


def test_hand_vector_flagged_when_net_negative() -> None:
    values = _TEN_BP
    mean_gross = _mean(values)
    tau = 1.0
    c_ref = 0.002
    report = _run(values, tau=tau, c_ref=c_ref)
    expected_net = mean_gross - c_ref * tau
    assert report["blade"] == "magnitude_vs_turnover"
    assert report["statistics"]["mean_gross"] == mean_gross
    assert report["statistics"]["n_obs"] == len(values)
    assert report["statistics"]["turnover"] == tau
    assert report["statistics"]["c_ref"] == c_ref
    assert report["statistics"]["net_at_c_ref"] == expected_net
    assert expected_net == -0.001
    assert report["flagged"] is True


def test_hand_vector_not_flagged_when_net_positive() -> None:
    values = _TEN_BP
    mean_gross = _mean(values)
    tau = 1.0
    c_ref = 0.0005
    report = _run(values, tau=tau, c_ref=c_ref)
    expected_net = mean_gross - c_ref * tau
    assert report["statistics"]["net_at_c_ref"] == expected_net
    assert expected_net == 0.0005
    assert report["flagged"] is False


# ---------------------------------------------------------------------------
# b. Grid table
# ---------------------------------------------------------------------------


def test_net_mean_grid_rows_are_c_and_mean_minus_c_tau() -> None:
    grid = (0.0, 0.0005, 0.001, 0.002, 0.005)
    values = _TEN_BP
    mean_gross = _mean(values)
    tau = 1.0
    blade = MagnitudeVsTurnoverBlade(cost_grid=grid)
    report = _run(values, tau=tau, c_ref=0.0005, blade=blade)
    expected = [[float(c), mean_gross - float(c) * tau] for c in grid]
    assert report["statistics"]["net_mean_grid"] == expected


# ---------------------------------------------------------------------------
# c. break_even_c
# ---------------------------------------------------------------------------


def test_break_even_c_positive_case() -> None:
    values = _TEN_BP
    mean_gross = _mean(values)
    tau = 1.0
    report = _run(values, tau=tau, c_ref=0.0005)
    assert report["statistics"]["break_even_c"] == mean_gross / tau


def test_zero_turnover_break_even_none_and_never_flagged() -> None:
    report_pos = _run(_TEN_BP, tau=0.0, c_ref=0.002)
    assert report_pos["statistics"]["break_even_c"] is None
    assert report_pos["flagged"] is False
    ev = json.dumps(report_pos["evidence"]).lower()
    assert "zero-turnover" in ev or "zero turnover" in ev or "tau == 0" in ev

    neg = (-0.001, -0.001, -0.001)
    report_neg = _run(neg, tau=0.0, c_ref=99.0)
    assert report_neg["statistics"]["break_even_c"] is None
    assert report_neg["flagged"] is False


def test_negative_mean_reports_signed_break_even() -> None:
    values = (-0.001, -0.001, -0.001, -0.001, -0.001)
    mean_gross = _mean(values)
    tau = 1.0
    report = _run(values, tau=tau, c_ref=0.0005)
    assert report["statistics"]["break_even_c"] == mean_gross / tau
    assert report["statistics"]["break_even_c"] < 0.0
    assert report["flagged"] is True


# ---------------------------------------------------------------------------
# d. Missing / invalid inputs → evaluable=False, flagged=False
# ---------------------------------------------------------------------------


def test_missing_turnover_not_evaluable() -> None:
    report = _run(tau=None, c_ref=0.001)
    assert report["flagged"] is False
    assert report["statistics"]["evaluable"] is False
    blob = json.dumps(report["evidence"]).lower()
    assert "turnover" in blob
    json.dumps(report, allow_nan=False)


def test_missing_c_ref_not_evaluable() -> None:
    report = _run(tau=1.0, c_ref=None)
    assert report["flagged"] is False
    assert report["statistics"]["evaluable"] is False
    blob = json.dumps(report["evidence"]).lower()
    assert "c_ref" in blob
    json.dumps(report, allow_nan=False)


def test_negative_tau_not_evaluable() -> None:
    report = _run(tau=-0.1, c_ref=0.001)
    assert report["flagged"] is False
    assert report["statistics"]["evaluable"] is False
    blob = json.dumps(report["evidence"]).lower()
    assert "turnover" in blob or "tau" in blob
    json.dumps(report, allow_nan=False)


def test_empty_series_not_evaluable() -> None:
    report = _run((), tau=1.0, c_ref=0.001)
    assert report["flagged"] is False
    assert report["statistics"]["evaluable"] is False
    json.dumps(report, allow_nan=False)


# ---------------------------------------------------------------------------
# e. Constructor validation
# ---------------------------------------------------------------------------


def test_constructor_empty_grid_raises() -> None:
    with pytest.raises(ValueError):
        MagnitudeVsTurnoverBlade(cost_grid=())


def test_constructor_negative_entry_raises() -> None:
    with pytest.raises(ValueError):
        MagnitudeVsTurnoverBlade(cost_grid=(0.0, -0.0001, 0.001))


def test_constructor_non_increasing_raises() -> None:
    with pytest.raises(ValueError):
        MagnitudeVsTurnoverBlade(cost_grid=(0.0, 0.001, 0.001))
    with pytest.raises(ValueError):
        MagnitudeVsTurnoverBlade(cost_grid=(0.002, 0.001))


# ---------------------------------------------------------------------------
# g. Determinism
# ---------------------------------------------------------------------------


def test_identical_report_on_repeat_call() -> None:
    blade = MagnitudeVsTurnoverBlade()
    spec = _spec(0.0005)
    params = {"turnover": 1.0}
    series = _series(_TEN_BP)
    first = blade.run("t", spec, params, None, series)
    second = blade.run("t", spec, params, None, series)
    assert first == second


# ---------------------------------------------------------------------------
# f. Integration smoke — fixtures copied from tests/test_blades_harness.py
# ---------------------------------------------------------------------------

INDEX = ("d1", "d2", "d3", "d4", "d5")
VALUES_A = (0.01, -0.02, 0.03, 0.01, -0.01)


def _window() -> Window:
    return Window(start="2020-01-01", end="2020-12-31")


def _declared(*, direction: str = "two-sided", metric: str = "returns") -> DeclaredProtocol:
    return DeclaredProtocol(
        metric=metric,
        window=_window(),
        periods_per_year=252.0,
        direction=direction,
        se=SeConvention(kind="iid"),
    )


def _run_config() -> dict[str, Any]:
    return {
        "universe": "csi300",
        "label_expr": "Ref($close, -2)/Ref($close, -1) - 1",
        "provider_uri": "/data/qlib/cn_data",
        "quantile": 0.2,
        "min_cross_section": 50,
        "declared_data_tag": "test-tag",
        "adapter_version": "0.0-test",
        "qlib_version": "0.0.0",
        "config": {
            "provider_uri": "/data/qlib/cn_data",
            "universe": "csi300",
            "window": {"start": "2020-01-01", "end": "2020-12-31"},
            "label_expr": "Ref($close, -2)/Ref($close, -1) - 1",
            "quantile": 0.2,
            "min_cross_section": 50,
            "declared_data_tag": "test-tag",
        },
    }


def _meta(*, metric: str = "returns", **overrides: Any) -> dict[str, Any]:
    cfg = {
        "provider_uri": "/data/qlib/cn_data",
        "universe": "csi300",
        "window": {"start": "2020-01-01", "end": "2020-12-31"},
        "label_expr": "Ref($close, -2)/Ref($close, -1) - 1",
        "quantile": 0.2,
        "min_cross_section": 50,
        "declared_data_tag": "test-tag",
    }
    meta: dict[str, Any] = {
        "metric": metric,
        "metric_params": {"quantile": 0.2} if metric == "returns" else {},
        "label_expr": "Ref($close, -2)/Ref($close, -1) - 1",
        "price_field": "$close",
        "universe": "csi300",
        "window": {"start": "2020-01-01", "end": "2020-12-31"},
        "n_evaluation_dates": len(INDEX),
        "cost_declaration": "long-short top/bottom quantile; costs not subtracted",
        "data_version": {
            "declared_tag": "test-tag",
            "calendar_end": "2020-12-31",
            "n_instruments": 10,
        },
        "qlib_version": "0.0.0",
        "adapter_version": "0.0-test",
        "config": cfg,
    }
    meta.update(overrides)
    return meta


@dataclass(frozen=True)
class FakeEvalResult:
    index: list[str]
    values: np.ndarray
    meta: dict


class FakeEvaluator:
    """Deterministic evaluator; series keyed by call order."""

    def __init__(
        self,
        series_queue: list[tuple[tuple[str, ...], tuple[float, ...]]] | None = None,
        meta_overrides: dict | None = None,
    ) -> None:
        self._queue = list(
            series_queue
            or [
                (INDEX, VALUES_A),
            ]
        )
        self._meta_overrides = meta_overrides or {}
        self.calls: list[tuple[Any, str]] = []

    def evaluate(self, scores: Any, metric: str) -> FakeEvalResult:
        self.calls.append((scores, metric))
        if not self._queue:
            raise RuntimeError("FakeEvaluator series queue exhausted")
        index, values = self._queue.pop(0)
        meta = _meta(metric=metric, **self._meta_overrides)
        meta["n_evaluation_dates"] = len(index)
        return FakeEvalResult(
            index=list(index),
            values=np.asarray(values, dtype=np.float64),
            meta=meta,
        )


def _policy():
    from harness.aggregation_policy import AggregationPolicy

    return AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )


def _create(tmp_path: Path, **kwargs):
    from harness.run import CertifiedRun

    path = kwargs.pop("path", tmp_path / "ledger.jsonl")
    return CertifiedRun.create(
        path,
        run_config=kwargs.pop("run_config", _run_config()),
        policy=kwargs.pop("policy", _policy()),
        evaluator=kwargs.pop("evaluator", FakeEvaluator()),
        anchor=kwargs.pop("anchor", None),
        blades=kwargs.pop("blades", None),
    )


def _calibrate(ledger) -> str:
    from harness.blades import append_blade_calibration

    return append_blade_calibration(
        ledger,
        seed_root=7,
        null_recipe={"generator": "gaussian"},
        target_fpr={"per_blade": 0.01, "joint": 0.05},
        thresholds={"magnitude_vs_turnover": 0.0},
        calibration_fingerprint="fp-test-v0.3-02",
    )


def _blade_reports(ledger) -> list[dict]:
    from harness.blades import BLADE_REPORT_KIND

    out: list[dict] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_REPORT_KIND:
            out.append(payload)
    return out


def test_screen_on_flag_leaves_trial_registered_with_flagged_report(tmp_path: Path):
    blade = MagnitudeVsTurnoverBlade()
    evaluator = FakeEvaluator(series_queue=[(INDEX, _TEN_BP)])
    run = _create(tmp_path, blades=[blade], evaluator=evaluator)
    _calibrate(run.ledger)
    spec = {
        "name": "cost-killed",
        "blades": {
            "magnitude_vs_turnover": {"on_flag": "screen", "c_ref": 0.002},
        },
    }
    tid = run.propose("claim-screen", spec, {"turnover": 1.0}, _declared())
    run.evaluate(tid, scores={"i": 0})
    assert run.ledger.status(tid) == "registered"
    reports = _blade_reports(run.ledger)
    assert len(reports) == 1
    assert reports[0]["report"]["blade"] == "magnitude_vs_turnover"
    assert reports[0]["report"]["flagged"] is True


def test_default_on_flag_records_when_spec_silent(tmp_path: Path):
    blade = MagnitudeVsTurnoverBlade()
    evaluator = FakeEvaluator(series_queue=[(INDEX, _TEN_BP)])
    run = _create(tmp_path, blades=[blade], evaluator=evaluator)
    _calibrate(run.ledger)
    spec = {
        "name": "cost-killed-record",
        "blades": {"magnitude_vs_turnover": {"c_ref": 0.002}},
    }
    tid = run.propose("claim-record", spec, {"turnover": 1.0}, _declared())
    run.evaluate(tid, scores={"i": 0})
    assert run.ledger.status(tid) == "evaluated"
    reports = _blade_reports(run.ledger)
    assert len(reports) == 1
    assert reports[0]["report"]["flagged"] is True
    rec = run.ledger.trials([tid])[0]
    assert rec.series is not None
