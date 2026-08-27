"""Identity-degeneracy and pool-redundancy blades (ticket v0.3-01).

Written first under TDD; implementation follows. Integration fixtures are
copied from tests/test_blades_harness.py (do not import that module).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from gates.identity_degeneracy import IdentityDegeneracyBlade
from gates.pool_redundancy import PoolRedundancyBlade

N = 80
MIN_OVERLAP = 30
RHO_MAX = 0.9
RHO_POOL = 0.9


def _labels(n: int) -> tuple[str, ...]:
    return tuple(f"d{i:04d}" for i in range(n))


def _as_ref(
    index: tuple[str, ...], values: np.ndarray
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    return index, tuple(float(v) for v in values)


def _series(index: tuple[str, ...], values: np.ndarray) -> SimpleNamespace:
    return SimpleNamespace(index=index, values=tuple(float(v) for v in values))


def _run(blade: Any, series: Any) -> dict:
    return blade.run("t-1", {}, {}, None, series)


def _lag2_copy(source: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    candidate = np.empty(source.shape[0], dtype=np.float64)
    candidate[:2] = rng.normal(size=2)
    candidate[2:] = source[:-2]
    return candidate


# ---------------------------------------------------------------------------
# a. Hand-built vectors: lag-copy flags; independent noise does not
# ---------------------------------------------------------------------------


def test_lag_copy_of_ref_flags_at_lag_two() -> None:
    rng = np.random.default_rng(11)
    index = _labels(N)
    source = rng.normal(size=N)
    candidate = _lag2_copy(source, rng)
    blade = IdentityDegeneracyBlade(
        refs={"source": _as_ref(index, source)},
        rho_max=RHO_MAX,
        k=5,
        min_overlap=MIN_OVERLAP,
    )
    report = _run(blade, _series(index, candidate))
    assert report["blade"] == "identity_degeneracy"
    assert report["flagged"] is True
    stats = report["statistics"]
    assert stats["max_abs_spearman"] == pytest.approx(1.0, abs=1e-12)
    assert stats["argmax_ref"] == "source"
    assert stats["argmax_lag"] == 2
    assert stats["n_effective_hypotheses"] == 1 * (2 * 5 + 1)
    assert stats["n_pairs_evaluated"] == 11
    assert report["params"] == {
        "rho_max": RHO_MAX,
        "k": 5,
        "min_overlap": MIN_OVERLAP,
        "n_refs": 1,
    }


def test_independent_noise_is_not_flagged() -> None:
    rng = np.random.default_rng(12)
    index = _labels(N)
    ref = rng.normal(size=N)
    candidate = rng.normal(size=N)
    blade = IdentityDegeneracyBlade(
        refs={"noise_ref": _as_ref(index, ref)},
        rho_max=RHO_MAX,
        k=5,
        min_overlap=MIN_OVERLAP,
    )
    report = _run(blade, _series(index, candidate))
    assert report["flagged"] is False
    assert report["statistics"]["max_abs_spearman"] < RHO_MAX
    assert report["statistics"]["max_abs_spearman"] is not None


# ---------------------------------------------------------------------------
# b. Second-max correctness on two related refs
# ---------------------------------------------------------------------------


def test_second_max_with_two_related_refs() -> None:
    rng = np.random.default_rng(13)
    index = _labels(N)
    source = rng.normal(size=N)
    candidate = _lag2_copy(source, rng)
    blade = IdentityDegeneracyBlade(
        refs={
            "source": _as_ref(index, source),
            "twin": _as_ref(index, candidate),
        },
        rho_max=RHO_MAX,
        k=5,
        min_overlap=MIN_OVERLAP,
    )
    report = _run(blade, _series(index, candidate))
    stats = report["statistics"]
    assert report["flagged"] is True
    assert stats["max_abs_spearman"] == pytest.approx(1.0, abs=1e-12)
    assert stats["second_max_abs_spearman"] == pytest.approx(1.0, abs=1e-12)
    assert stats["n_effective_hypotheses"] == 2 * 11
    assert (stats["argmax_ref"], stats["argmax_lag"]) in {("source", 2), ("twin", 0)}


# ---------------------------------------------------------------------------
# c. min_overlap skip counting; all-skipped → not flagged, None statistic
# ---------------------------------------------------------------------------


def test_overlap_29_is_skipped_and_counted() -> None:
    rng = np.random.default_rng(14)
    index = _labels(29)
    ref = rng.normal(size=29)
    candidate = rng.normal(size=29)
    blade = IdentityDegeneracyBlade(
        refs={"short": _as_ref(index, ref)},
        rho_max=RHO_MAX,
        k=5,
        min_overlap=MIN_OVERLAP,
    )
    report = _run(blade, _series(index, candidate))
    assert report["evidence"]["n_skipped_insufficient_overlap"] == 11
    assert report["statistics"]["n_pairs_evaluated"] == 0


def test_all_pairs_skipped_not_flagged_with_none_statistic() -> None:
    rng = np.random.default_rng(15)
    index = _labels(29)
    ref = rng.normal(size=29)
    candidate = rng.normal(size=29)
    blade = IdentityDegeneracyBlade(
        refs={"short": _as_ref(index, ref)},
        rho_max=RHO_MAX,
        k=1,
        min_overlap=MIN_OVERLAP,
    )
    report = _run(blade, _series(index, candidate))
    assert report["flagged"] is False
    assert report["statistics"]["max_abs_spearman"] is None
    assert report["statistics"]["second_max_abs_spearman"] is None
    assert report["statistics"]["argmax_ref"] is None
    assert report["statistics"]["argmax_lag"] is None
    assert "reason" in report["evidence"]


# ---------------------------------------------------------------------------
# d. Constant ref: skipped, not NaN, JSON-serializable
# ---------------------------------------------------------------------------


def test_constant_ref_skipped_report_json_serializable() -> None:
    rng = np.random.default_rng(16)
    index = _labels(N)
    candidate = rng.normal(size=N)
    noise_ref = rng.normal(size=N)
    constant = np.full(N, 3.14)
    blade = IdentityDegeneracyBlade(
        refs={
            "constant": _as_ref(index, constant),
            "noise": _as_ref(index, noise_ref),
        },
        rho_max=RHO_MAX,
        k=5,
        min_overlap=MIN_OVERLAP,
    )
    report = _run(blade, _series(index, candidate))
    dumped = json.dumps(report, allow_nan=False)
    assert dumped
    assert report["evidence"]["n_skipped_degenerate"] == 11
    assert report["statistics"]["n_pairs_evaluated"] == 11
    assert report["statistics"]["max_abs_spearman"] is not None
    assert not isinstance(report["statistics"]["max_abs_spearman"], float) or (
        report["statistics"]["max_abs_spearman"] == report["statistics"]["max_abs_spearman"]
    )


# ---------------------------------------------------------------------------
# e. Pool blade: pearson/spearman divergence; flag on either measure
# ---------------------------------------------------------------------------


def test_pool_reports_both_measures_and_flags_on_spearman() -> None:
    index = _labels(N)
    member = np.linspace(-3.0, 3.0, N)
    candidate = np.exp(member)
    blade = PoolRedundancyBlade(
        pool={"exp_base": _as_ref(index, member)},
        rho_pool=RHO_POOL,
        min_overlap=MIN_OVERLAP,
    )
    report = _run(blade, _series(index, candidate))
    stats = report["statistics"]
    assert report["blade"] == "pool_redundancy"
    assert stats["max_abs_spearman"] == pytest.approx(1.0, abs=1e-12)
    assert stats["max_abs_pearson"] < stats["max_abs_spearman"]
    assert stats["max_abs_pearson"] < RHO_POOL
    assert stats["max_abs_spearman"] >= RHO_POOL
    assert report["flagged"] is True
    assert stats["top5_abs_spearman"][0][0] == "exp_base"
    assert stats["top5_abs_pearson"][0][0] == "exp_base"
    assert stats["n_members_evaluated"] == 1
    assert report["params"]["rho_pool"] == RHO_POOL
    assert report["params"]["n_pool"] == 1


# ---------------------------------------------------------------------------
# g. Determinism (before integration, which needs more fixtures)
# ---------------------------------------------------------------------------


def test_identity_report_is_deterministic() -> None:
    rng = np.random.default_rng(17)
    index = _labels(N)
    source = rng.normal(size=N)
    candidate = _lag2_copy(source, rng)
    refs = {"source": _as_ref(index, source)}
    a = IdentityDegeneracyBlade(refs=refs, rho_max=RHO_MAX, k=5, min_overlap=MIN_OVERLAP)
    b = IdentityDegeneracyBlade(refs=refs, rho_max=RHO_MAX, k=5, min_overlap=MIN_OVERLAP)
    series = _series(index, candidate)
    assert _run(a, series) == _run(b, series)
    assert _run(a, series) == _run(a, series)


def test_pool_report_is_deterministic() -> None:
    index = _labels(N)
    member = np.linspace(-3.0, 3.0, N)
    candidate = np.exp(member)
    pool = {"exp_base": _as_ref(index, member)}
    a = PoolRedundancyBlade(pool=pool, rho_pool=RHO_POOL, min_overlap=MIN_OVERLAP)
    series = _series(index, candidate)
    assert _run(a, series) == _run(a, series)


# ---------------------------------------------------------------------------
# f. Integration smoke — fixtures copied from tests/test_blades_harness.py
# ---------------------------------------------------------------------------


INDEX = _labels(N)
VALUES_A = tuple(float(v) for v in np.linspace(0.01, 0.02, N))
VALUES_B = tuple(float(v) for v in np.linspace(-0.01, 0.01, N))


def _window():
    from court.ledger import Window

    return Window(start="2020-01-01", end="2020-12-31")


def _declared(*, direction: str = "two-sided", metric: str = "returns"):
    from court.ledger import DeclaredProtocol, SeConvention

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
        thresholds={"identity_degeneracy": RHO_MAX},
        calibration_fingerprint="fp-test-v0.3-01",
    )


def _blade_reports(ledger) -> list[dict]:
    from harness.blades import BLADE_REPORT_KIND

    out: list[dict] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_REPORT_KIND:
            out.append(payload)
    return out


def test_certified_run_screens_lag_copy_and_records_innocent(tmp_path: Path) -> None:
    rng = np.random.default_rng(18)
    index = _labels(N)
    source = rng.normal(size=N)
    planted = _lag2_copy(source, rng)
    innocent = rng.normal(size=N)
    blade = IdentityDegeneracyBlade(
        refs={"source": _as_ref(index, source)},
        rho_max=RHO_MAX,
        k=5,
        min_overlap=MIN_OVERLAP,
    )
    evaluator = FakeEvaluator(
        series_queue=[
            (index, tuple(float(v) for v in planted)),
            (index, tuple(float(v) for v in innocent)),
        ]
    )
    run = _create(tmp_path, blades=[blade], evaluator=evaluator)
    _calibrate(run.ledger)

    tid_planted = run.propose(
        "claim-planted",
        {"blades": {"identity_degeneracy": {"on_flag": "screen"}}},
        {},
        _declared(),
    )
    tid_innocent = run.propose("claim-innocent", {"name": "innocent"}, {}, _declared())

    run.evaluate(tid_planted, scores={"i": 0})
    run.evaluate(tid_innocent, scores={"i": 1})

    assert run.ledger.status(tid_planted) == "registered"
    assert run.ledger.status(tid_innocent) == "evaluated"

    reports = _blade_reports(run.ledger)
    planted_reports = [p for p in reports if p.get("trial_id") == tid_planted]
    assert len(planted_reports) == 1
    planted_report = planted_reports[0]["report"]
    assert planted_report["blade"] == "identity_degeneracy"
    assert planted_report["flagged"] is True
    assert planted_report["statistics"]["argmax_lag"] == 2

    innocent_reports = [p for p in reports if p.get("trial_id") == tid_innocent]
    assert len(innocent_reports) == 1
    assert innocent_reports[0]["report"]["flagged"] is False
