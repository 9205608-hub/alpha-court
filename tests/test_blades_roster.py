"""Blade roster pinning: on-chain stickiness for the attached blade lineup.

Ticket v0.3-00b. Fixtures copied from tests/test_blades_harness.py (do not
import or modify that module). Dummy blades here are deterministic stand-ins.
"""

from __future__ import annotations

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

# sha256("{}") — empty roster_params canonical JSON (sorted keys, compact).
_EMPTY_PARAMS_FP = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
# sha256('{"x":1}') — compact sorted-keys JSON of {"x": 1}.
_X1_PARAMS_FP = "5041bf1f713df204784353e82f6a4a535931cb64f1f4b4a5aeaffcb720918b22"


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
        roster_params: dict | None = None,
    ) -> None:
        self.name = name
        self.flag_ids = flag_ids or set()
        self.report = report
        self.calls: list[str] = []
        if roster_params is not None:
            self.roster_params = roster_params

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
        calibration_fingerprint="fp-test-v0.3-00b",
    )


def _blade_reports(ledger) -> list[dict]:
    from harness.blades import BLADE_REPORT_KIND

    out: list[dict] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_REPORT_KIND:
            out.append(payload)
    return out


def _roster_payloads(ledger) -> list[dict]:
    from harness.blades import BLADE_ROSTER_KIND

    out: list[dict] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_ROSTER_KIND:
            out.append(payload)
    return out


def _n_declarations(ledger) -> int:
    return len(list(ledger.declarations()))


# ---------------------------------------------------------------------------
# 3a. Panel replay P3 — bladeless reopen cannot pull a screened trial in
# ---------------------------------------------------------------------------


def test_p3_bladeless_open_refuses_screened_trial_equivalent_reopen_stays_terminal(
    tmp_path: Path,
):
    from harness.run import CertificationError, CertifiedRun
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

    path = run.path
    n_decls = _n_declarations(run.ledger)

    bare = CertifiedRun.open(path, FakeEvaluator())
    with pytest.raises(CertificationError, match="pinned blade roster"):
        bare.evaluate(tid_b, scores={"i": 2})
    assert bare.ledger.status(tid_b) == "registered"
    assert _n_declarations(bare.ledger) == n_decls

    twin = DummyBlade(name="dummy")
    reopened = CertifiedRun.open(path, FakeEvaluator(), blades=[twin])
    with pytest.raises(CertificationError, match="screened"):
        reopened.evaluate(tid_b, scores={"i": 3})
    assert reopened.ledger.status(tid_b) == "registered"
    assert _n_declarations(reopened.ledger) == n_decls

    judgment = run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()
    report = verify(path)
    assert len(judgment.verdict_ids) == 1
    assert len(run.ledger.verdicts()) == 1
    assert report.n_verdicts == 1
    assert run.ledger.status(tid_b) == "registered"


# ---------------------------------------------------------------------------
# 3b. Panel replay P3b — bladeless create cannot ignore a screen declaration
# ---------------------------------------------------------------------------


def test_p3b_bladeless_create_refuses_spec_screen_declaration(tmp_path: Path):
    from harness.run import CertificationError

    run = _create(tmp_path)
    tid = run.propose(
        "claim",
        {"name": "B", "blades": {"dummy": {"on_flag": "screen"}}},
        {},
        _declared(),
    )
    n_decls = _n_declarations(run.ledger)

    with pytest.raises(CertificationError, match="screening but no blades attached"):
        run.evaluate(tid, scores=1)

    assert run.ledger.status(tid) == "registered"
    assert run.ledger.trials([tid])[0].series is None
    assert _blade_reports(run.ledger) == []
    assert _roster_payloads(run.ledger) == []
    assert _n_declarations(run.ledger) == n_decls


# ---------------------------------------------------------------------------
# 3c. Auto-pin
# ---------------------------------------------------------------------------


def test_auto_pin_first_bladed_evaluate_appends_exactly_one_matching_roster(tmp_path: Path):
    from harness.blades import find_blade_roster

    blade = DummyBlade(name="dummy")
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)
    assert find_blade_roster(run.ledger) is None

    tid_a = run.propose("claim-A", {"name": "A"}, {}, _declared())
    tid_b = run.propose("claim-B", {"name": "B"}, {}, _declared())
    run.evaluate(tid_a, scores={"i": 0})

    payloads = _roster_payloads(run.ledger)
    assert len(payloads) == 1
    assert payloads[0]["kind"] == "blade_roster"
    assert payloads[0]["roster"] == [
        {"name": "dummy", "params_fingerprint": _EMPTY_PARAMS_FP},
    ]
    assert find_blade_roster(run.ledger) == payloads[0]["roster"]

    run.evaluate(tid_b, scores={"i": 1})
    assert len(_roster_payloads(run.ledger)) == 1


# ---------------------------------------------------------------------------
# 3d. Mismatch vs equivalent fresh instance
# ---------------------------------------------------------------------------


def test_reopen_mismatch_refused_equivalent_instance_accepted(tmp_path: Path):
    from harness.blades import roster_entry
    from harness.run import CertificationError, CertifiedRun

    blade = DummyBlade(name="dummy")
    assert roster_entry(blade) == {
        "name": "dummy",
        "params_fingerprint": _EMPTY_PARAMS_FP,
    }
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)
    tid = run.propose("claim", {"name": "A"}, {}, _declared())
    run.evaluate(tid, scores={"i": 0})
    path = run.path
    n_decls = _n_declarations(run.ledger)

    renamed = DummyBlade(name="other")
    mismatch_name = CertifiedRun.open(path, FakeEvaluator(), blades=[renamed])
    tid_name = mismatch_name.propose("claim-name", {"name": "N"}, {}, _declared())
    with pytest.raises(CertificationError):
        mismatch_name.evaluate(tid_name, scores=1)
    assert mismatch_name.ledger.status(tid_name) == "registered"
    assert renamed.calls == []
    assert _n_declarations(mismatch_name.ledger) == n_decls

    paramed = DummyBlade(name="dummy", roster_params={"x": 1})
    assert roster_entry(paramed) == {
        "name": "dummy",
        "params_fingerprint": _X1_PARAMS_FP,
    }
    mismatch_params = CertifiedRun.open(path, FakeEvaluator(), blades=[paramed])
    tid_params = mismatch_params.propose("claim-params", {"name": "P"}, {}, _declared())
    with pytest.raises(CertificationError):
        mismatch_params.evaluate(tid_params, scores=1)
    assert mismatch_params.ledger.status(tid_params) == "registered"
    assert paramed.calls == []

    twin = DummyBlade(name="dummy")
    equivalent = CertifiedRun.open(path, FakeEvaluator(), blades=[twin])
    tid_ok = equivalent.propose("claim-ok", {"name": "OK"}, {}, _declared())
    equivalent.evaluate(tid_ok, scores=1)
    assert equivalent.ledger.status(tid_ok) == "evaluated"
    assert twin.calls == [tid_ok]


# ---------------------------------------------------------------------------
# 3e. append_blade_roster uniqueness
# ---------------------------------------------------------------------------


def test_append_blade_roster_uniqueness_raises_on_second(tmp_path: Path):
    from harness.blades import append_blade_roster, find_blade_roster

    run = _create(tmp_path)
    blade = DummyBlade(name="dummy")
    first = append_blade_roster(run.ledger, [blade])
    assert isinstance(first, str) and first
    assert find_blade_roster(run.ledger) == [
        {"name": "dummy", "params_fingerprint": _EMPTY_PARAMS_FP},
    ]
    with pytest.raises(ValueError, match="already|exist|unique"):
        append_blade_roster(run.ledger, [blade])
    assert len(_roster_payloads(run.ledger)) == 1


# ---------------------------------------------------------------------------
# 3f. End-to-end: roster + calibration + reports → judge → seal → verify
# ---------------------------------------------------------------------------


def test_bladed_run_with_roster_calibration_reports_seals_and_verifies(tmp_path: Path):
    from harness.blades import find_blade_calibration, find_blade_roster
    from harness.verify import verify

    blade = DummyBlade(name="dummy")
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)
    tid = run.propose("claim", {"name": "A"}, {}, _declared())
    run.evaluate(tid, scores=1)

    assert find_blade_roster(run.ledger) == [
        {"name": "dummy", "params_fingerprint": _EMPTY_PARAMS_FP},
    ]
    assert find_blade_calibration(run.ledger) is not None
    assert len(_blade_reports(run.ledger)) == 1

    judgment = run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()
    report = verify(tmp_path / "ledger.jsonl")
    assert len(judgment.verdict_ids) == 1
    assert report.n_verdicts == 1


# ---------------------------------------------------------------------------
# 3g. Bladeless regression: no roster, no screen declaration
# ---------------------------------------------------------------------------


def test_bladeless_run_without_screen_records_as_before(tmp_path: Path):
    from harness.blades import find_blade_roster

    run = _create(tmp_path)
    tid = run.propose("claim", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    assert run.ledger.status(tid) == "evaluated"
    assert find_blade_roster(run.ledger) is None
    assert _blade_reports(run.ledger) == []
    assert _roster_payloads(run.ledger) == []
