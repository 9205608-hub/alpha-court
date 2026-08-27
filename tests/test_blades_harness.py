"""Blade plumbing: calibration/report declarations + CertifiedRun screen wiring.

Ticket v0.3-00. Fixtures copied from tests/test_certified_run.py (do not import
that module). Dummy blades here are deterministic stand-ins; real statistics
are later tickets.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from court.judge import Application
from court.ledger import DeclaredProtocol, SeConvention, Window

INDEX = ("d1", "d2", "d3", "d4", "d5")
VALUES_A = (0.01, -0.02, 0.03, 0.01, -0.01)
VALUES_B = (0.02, 0.01, -0.01, 0.02, 0.00)


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
                (INDEX, VALUES_B),
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


def _ok_report(name: str, *, flagged: bool = False) -> dict:
    return {
        "blade": name,
        "flagged": flagged,
        "statistics": {},
        "evidence": {},
        "params": {},
    }


class DummyBlade:
    """Deterministic blade: flags a configured set of trial ids."""

    def __init__(
        self,
        name: str = "dummy",
        flag_ids: set[str] | None = None,
        report: dict | None = None,
    ) -> None:
        self.name = name
        self.flag_ids = flag_ids or set()
        self.report = report
        self.calls: list[str] = []

    def run(self, trial_id: str, spec: dict, params: dict, declared: Any, series: Any) -> dict:
        self.calls.append(trial_id)
        if self.report is not None:
            return dict(self.report)
        return _ok_report(self.name, flagged=trial_id in self.flag_ids)


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
        thresholds={"dummy": 1.96},
        calibration_fingerprint="fp-test-v0.3-00",
    )


def _blade_reports(ledger) -> list[dict]:
    from harness.blades import BLADE_REPORT_KIND

    out: list[dict] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_REPORT_KIND:
            out.append(payload)
    return out


# ---------------------------------------------------------------------------
# 3a. End-to-end screen path
# ---------------------------------------------------------------------------


def test_screen_path_leaves_flagged_trial_registered_and_verify_passes(tmp_path: Path):
    from harness.verify import verify

    blade = DummyBlade(name="dummy")
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)

    tid_a = run.propose("claim-A", {"name": "A"}, {}, _declared())
    tid_b = run.propose(
        "claim-B",
        {"name": "B", "blades": {"dummy": {"on_flag": "screen"}}},
        {},
        _declared(),
    )
    blade.flag_ids = {tid_b}

    run.evaluate(tid_a, scores={"i": 0})
    run.evaluate(tid_b, scores={"i": 1})

    assert run.ledger.status(tid_a) == "evaluated"
    assert run.ledger.status(tid_b) == "registered"
    b_rec = run.ledger.trials([tid_b])[0]
    assert b_rec.series is None

    reports = _blade_reports(run.ledger)
    a_reports = [p for p in reports if p.get("trial_id") == tid_a]
    assert len(a_reports) == 1
    assert a_reports[0]["report"]["flagged"] is False
    assert a_reports[0]["report"]["blade"] == "dummy"
    b_reports = [p for p in reports if p.get("trial_id") == tid_b]
    assert len(b_reports) == 1
    assert b_reports[0]["report"]["flagged"] is True
    assert b_reports[0]["report"]["blade"] == "dummy"

    judgment = run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()
    report = verify(tmp_path / "ledger.jsonl")
    assert len(judgment.verdict_ids) == 1
    assert len(run.ledger.verdicts()) == 1
    assert report.n_verdicts == 1


# ---------------------------------------------------------------------------
# 3b. Default-record ruling (OQ-B)
# ---------------------------------------------------------------------------


def test_default_on_flag_is_record_when_spec_silent(tmp_path: Path):
    blade = DummyBlade(name="dummy")
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)

    tid = run.propose("claim", {"name": "silent"}, {}, _declared())
    blade.flag_ids = {tid}
    run.evaluate(tid, scores=1)

    assert run.ledger.status(tid) == "evaluated"
    reports = _blade_reports(run.ledger)
    assert len(reports) == 1
    assert reports[0]["trial_id"] == tid
    assert reports[0]["report"]["flagged"] is True


# ---------------------------------------------------------------------------
# 3c. Calibration ordering
# ---------------------------------------------------------------------------


def test_evaluate_without_calibration_raises_before_any_blade_or_record(tmp_path: Path):
    from harness.run import CertificationError

    blade = DummyBlade()
    run = _create(tmp_path, blades=[blade])
    tid = run.propose("claim", {}, {}, _declared())

    with pytest.raises(CertificationError, match="blade_calibration|calibration"):
        run.evaluate(tid, scores=1)

    assert blade.calls == []
    assert _blade_reports(run.ledger) == []
    assert run.ledger.status(tid) == "registered"
    assert run.ledger.trials([tid])[0].series is None


# ---------------------------------------------------------------------------
# 3d. Invalid on_flag
# ---------------------------------------------------------------------------


def test_invalid_on_flag_raises_before_any_blade_runs(tmp_path: Path):
    from harness.run import CertificationError

    blade = DummyBlade(name="dummy")
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)
    tid = run.propose(
        "claim",
        {"blades": {"dummy": {"on_flag": "block"}}},
        {},
        _declared(),
    )

    with pytest.raises(CertificationError, match="on_flag"):
        run.evaluate(tid, scores=1)

    assert blade.calls == []
    assert _blade_reports(run.ledger) == []
    assert run.ledger.status(tid) == "registered"


# ---------------------------------------------------------------------------
# 3e. Report validation
# ---------------------------------------------------------------------------


def test_report_missing_flagged_raises_certification_error(tmp_path: Path):
    from harness.run import CertificationError

    bad = {"blade": "dummy", "statistics": {}, "evidence": {}, "params": {}}
    blade = DummyBlade(name="dummy", report=bad)
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)
    tid = run.propose("claim", {}, {}, _declared())

    with pytest.raises(CertificationError):
        run.evaluate(tid, scores=1)

    assert run.ledger.status(tid) == "registered"
    assert _blade_reports(run.ledger) == []


def test_report_blade_name_mismatch_raises_certification_error(tmp_path: Path):
    from harness.run import CertificationError

    mismatched = _ok_report("other")
    blade = DummyBlade(name="dummy", report=mismatched)
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)
    tid = run.propose("claim", {}, {}, _declared())

    with pytest.raises(CertificationError, match="blade"):
        run.evaluate(tid, scores=1)

    assert run.ledger.status(tid) == "registered"
    assert _blade_reports(run.ledger) == []


# ---------------------------------------------------------------------------
# 3f. append_blade_calibration validation + round-trip
# ---------------------------------------------------------------------------


def test_append_blade_calibration_rejects_fpr_outside_open_unit_interval(tmp_path: Path):
    from harness.blades import append_blade_calibration

    run = _create(tmp_path)
    kwargs = dict(
        seed_root=1,
        null_recipe={"g": "n"},
        thresholds={"x": 1.0},
        calibration_fingerprint="fp",
    )
    with pytest.raises(ValueError):
        append_blade_calibration(
            run.ledger, target_fpr={"per_blade": 0.0, "joint": 0.05}, **kwargs
        )
    with pytest.raises(ValueError):
        append_blade_calibration(
            run.ledger, target_fpr={"per_blade": 0.01, "joint": 1.0}, **kwargs
        )
    with pytest.raises(ValueError):
        append_blade_calibration(
            run.ledger, target_fpr={"per_blade": 0.01}, **kwargs
        )
    with pytest.raises(ValueError):
        append_blade_calibration(
            run.ledger, target_fpr={"joint": 0.05}, **kwargs
        )
    from harness.blades import find_blade_calibration

    assert find_blade_calibration(run.ledger) is None


def test_append_blade_calibration_round_trips_via_find(tmp_path: Path):
    from harness.blades import BLADE_CALIBRATION_KIND, find_blade_calibration

    run = _create(tmp_path)
    did = _calibrate(run.ledger)
    assert isinstance(did, str) and did
    payload = find_blade_calibration(run.ledger)
    assert payload is not None
    assert payload["kind"] == BLADE_CALIBRATION_KIND
    assert payload["seed_root"] == 7
    assert payload["null_recipe"] == {"generator": "gaussian"}
    assert payload["target_fpr"] == {"per_blade": 0.01, "joint": 0.05}
    assert payload["thresholds"] == {"dummy": 1.96}
    assert payload["calibration_fingerprint"] == "fp-test-v0.3-00"


# ---------------------------------------------------------------------------
# 3g. No-blades default
# ---------------------------------------------------------------------------


def test_create_and_open_blades_parameter_defaults_to_none():
    from harness.run import CertifiedRun

    create_param = inspect.signature(CertifiedRun.create).parameters["blades"]
    open_param = inspect.signature(CertifiedRun.open).parameters["blades"]
    assert create_param.default is None
    assert open_param.default is None
    assert create_param.kind is inspect.Parameter.KEYWORD_ONLY
    assert open_param.kind is inspect.Parameter.KEYWORD_ONLY


def test_create_without_blades_evaluate_records_without_calibration(tmp_path: Path):
    run = _create(tmp_path)
    tid = run.propose("claim", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    assert run.ledger.status(tid) == "evaluated"
    assert _blade_reports(run.ledger) == []


# ---------------------------------------------------------------------------
# Rework-01 R1: JSON-boundary pre-check; atomic report batch
# ---------------------------------------------------------------------------


def test_np_int64_in_statistics_raises_with_zero_reports_then_retry_is_clean(
    tmp_path: Path,
):
    from harness.run import CertificationError

    good = DummyBlade(name="good")
    bad_report = _ok_report("npint")
    bad_report["statistics"] = {"n": np.int64(3)}
    bad = DummyBlade(name="npint", report=bad_report)
    run = _create(tmp_path, blades=[good, bad])
    _calibrate(run.ledger)
    tid = run.propose("claim", {}, {}, _declared())

    with pytest.raises(CertificationError, match="npint|JSON|serializ"):
        run.evaluate(tid, scores=1)

    assert run.ledger.status(tid) == "registered"
    assert _blade_reports(run.ledger) == []

    bad.report = _ok_report("npint")
    run.evaluate(tid, scores=1)
    reports = _blade_reports(run.ledger)
    assert len(reports) == 2
    assert [p["report"]["blade"] for p in reports] == ["good", "npint"]
    assert run.ledger.status(tid) == "evaluated"


def test_nan_in_statistics_raises_with_zero_reports_on_chain(tmp_path: Path):
    from harness.run import CertificationError

    good = DummyBlade(name="good")
    bad_report = _ok_report("nanny")
    bad_report["statistics"] = {"corr": float("nan")}
    bad = DummyBlade(name="nanny", report=bad_report)
    run = _create(tmp_path, blades=[good, bad])
    _calibrate(run.ledger)
    tid = run.propose("claim", {}, {}, _declared())

    with pytest.raises(CertificationError, match="nanny|JSON|serializ|NaN|nan"):
        run.evaluate(tid, scores=1)

    assert run.ledger.status(tid) == "registered"
    assert _blade_reports(run.ledger) == []


# ---------------------------------------------------------------------------
# Rework-01 R2: protocol violations at attach time
# ---------------------------------------------------------------------------


class _NamelessBlade:
    def run(self, trial_id, spec, params, declared, series):
        return _ok_report("nameless")


class _NoRunBlade:
    name = "norun"


def test_nameless_blade_refused_at_create(tmp_path: Path):
    from harness.run import CertificationError, CertifiedRun

    with pytest.raises(CertificationError, match="name"):
        CertifiedRun.create(
            tmp_path / "ledger.jsonl",
            _run_config(),
            _policy(),
            FakeEvaluator(),
            blades=[_NamelessBlade()],
        )


def test_blade_without_callable_run_refused_at_open(tmp_path: Path):
    from harness.run import CertificationError, CertifiedRun

    run = _create(tmp_path)
    with pytest.raises(CertificationError, match="run"):
        CertifiedRun.open(run.path, FakeEvaluator(), blades=[_NoRunBlade()])


# ---------------------------------------------------------------------------
# Rework-01 R3: screened trials are terminal
# ---------------------------------------------------------------------------


def test_screened_trial_refuses_second_evaluate_including_post_judge(tmp_path: Path):
    from harness.run import CertificationError

    blade = DummyBlade(name="dummy")
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)
    tid_a = run.propose("claim-A", {"name": "A"}, {}, _declared())
    tid_b = run.propose(
        "claim-B",
        {"name": "B", "blades": {"dummy": {"on_flag": "screen"}}},
        {},
        _declared(),
    )
    blade.flag_ids = {tid_b}
    run.evaluate(tid_a, scores={"i": 0})
    run.evaluate(tid_b, scores={"i": 1})
    n_reports = len(_blade_reports(run.ledger))
    assert n_reports == 2
    assert run.ledger.status(tid_b) == "registered"

    with pytest.raises(CertificationError, match="screened"):
        run.evaluate(tid_b, scores={"i": 2})
    assert len(_blade_reports(run.ledger)) == n_reports

    run.judge([Application("fdr_by", {"q": 0.1})])
    with pytest.raises(CertificationError, match="screened"):
        run.evaluate(tid_b, scores={"i": 3})
    assert len(_blade_reports(run.ledger)) == n_reports


# ---------------------------------------------------------------------------
# Rework-01 R4: duplicate blade names
# ---------------------------------------------------------------------------


def test_duplicate_blade_names_refused_at_create(tmp_path: Path):
    from harness.run import CertificationError, CertifiedRun

    with pytest.raises(CertificationError, match="duplicate"):
        CertifiedRun.create(
            tmp_path / "ledger.jsonl",
            _run_config(),
            _policy(),
            FakeEvaluator(),
            blades=[DummyBlade(name="dup"), DummyBlade(name="dup")],
        )


# ---------------------------------------------------------------------------
# Rework-01 R5: empty roster == no roster
# ---------------------------------------------------------------------------


def test_empty_blades_roster_evaluates_without_calibration(tmp_path: Path):
    run = _create(tmp_path, blades=[])
    tid = run.propose("claim", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    assert run.ledger.status(tid) == "evaluated"
    assert _blade_reports(run.ledger) == []


# ---------------------------------------------------------------------------
# Rework-01 R6: calibration uniqueness + report linkage
# ---------------------------------------------------------------------------


def test_blade_report_payload_carries_calibration_id(tmp_path: Path):
    blade = DummyBlade(name="dummy")
    run = _create(tmp_path, blades=[blade])
    cal_id = _calibrate(run.ledger)
    tid = run.propose("claim", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    reports = _blade_reports(run.ledger)
    assert len(reports) == 1
    assert reports[0]["calibration_id"] == cal_id
    assert "calibration_id" not in reports[0]["report"]


def test_second_blade_calibration_append_refused(tmp_path: Path):
    from harness.blades import append_blade_calibration

    run = _create(tmp_path)
    first = _calibrate(run.ledger)
    assert first
    with pytest.raises(ValueError, match="already|exist|unique"):
        append_blade_calibration(
            run.ledger,
            seed_root=8,
            null_recipe={"generator": "gaussian"},
            target_fpr={"per_blade": 0.01, "joint": 0.05},
            thresholds={"dummy": 2.0},
            calibration_fingerprint="fp-second",
        )
