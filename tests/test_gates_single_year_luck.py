"""Red-first tests for SingleYearLuckBlade and its intra-blade calibration script.

Ticket v0.3-03. Integration fixtures copied from tests/test_blades_harness.py
(do not import that module).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from court.ledger import DeclaredProtocol, SeConvention, Window
from gates.single_year_luck import SingleYearLuckBlade

REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_SCRIPT = REPO_ROOT / "scripts" / "blade_calibration_syl.py"


def _series(values, blocks) -> tuple[Any, dict]:
    vals = tuple(float(v) for v in values)
    idx = tuple(str(i) for i in range(len(vals)))
    return SimpleNamespace(index=idx, values=vals), {"blocks": list(blocks)}


def _run(values, blocks, **kwargs) -> dict:
    series, params = _series(values, blocks)
    blade = SingleYearLuckBlade(**kwargs) if kwargs else SingleYearLuckBlade(p_min=0.01)
    return blade.run("t0", {}, params, None, series)


# ---------------------------------------------------------------------------
# 3a. LOBO hand vectors
# ---------------------------------------------------------------------------


def test_lobo_one_block_carries_the_sign_is_flagged() -> None:
    """4 blocks: +10 vs three −1. Total=7, LOBO_min=7−10=−3 → flagged."""
    report = _run((10.0, -1.0, -1.0, -1.0), (0, 1, 2, 3), p_min=0.01, n_perm=100, seed=0)
    assert report["blade"] == "single_year_luck"
    assert report["statistics"]["total"] == 7.0
    assert report["statistics"]["lobo_min"] == -3.0
    assert report["statistics"]["lobo_argmin"] == 0
    assert report["flagged"] is True


def test_lobo_balanced_blocks_min_is_positive() -> None:
    report = _run((1.0, 1.0, 1.0, 1.0), (0, 1, 2, 3), p_min=0.01, n_perm=100, seed=0)
    assert report["statistics"]["lobo_min"] == 3.0
    assert report["statistics"]["lobo_min"] > 0
    assert report["flagged"] is False


# ---------------------------------------------------------------------------
# 3b. HHI arithmetic
# ---------------------------------------------------------------------------


def test_hhi_hand_case_is_exact() -> None:
    """Contributions 2, 1, 1, 0 → Σ|C|=4 → HHI = (1/2)^2 + 2*(1/4)^2 + 0 = 0.375."""
    report = _run((2.0, 1.0, 1.0, 0.0), (0, 1, 2, 3), p_min=0.01, n_perm=100, seed=0)
    assert report["statistics"]["contributions"] == {
        "0": 2.0,
        "1": 1.0,
        "2": 1.0,
        "3": 0.0,
    }
    assert report["statistics"]["hhi"] == 0.375


# ---------------------------------------------------------------------------
# 3c. HHI-p planted concentration vs iid
# ---------------------------------------------------------------------------


def test_hhi_p_planted_concentration_is_small() -> None:
    values = (10.0,) * 10 + (1.0,) * 30
    blocks = (0,) * 10 + (1,) * 10 + (2,) * 10 + (3,) * 10
    report = _run(values, blocks, p_min=0.01, n_perm=200, seed=0)
    assert report["statistics"]["hhi_p"] < 0.05


def test_hhi_p_iid_noise_is_not_small() -> None:
    rng = np.random.default_rng(0)
    values = rng.standard_normal(80)
    blocks = (0,) * 20 + (1,) * 20 + (2,) * 20 + (3,) * 20
    report = _run(values, blocks, p_min=0.01, n_perm=200, seed=1)
    assert report["statistics"]["hhi_p"] > 0.2


# ---------------------------------------------------------------------------
# 3d. Degenerate HHI
# ---------------------------------------------------------------------------


def test_degenerate_zero_contributions_hhi_none_not_flagged_json_ok() -> None:
    report = _run((0.0, 0.0, 0.0, 0.0), (0, 1, 2, 3), p_min=0.01, n_perm=100, seed=0)
    assert report["statistics"]["hhi"] is None
    assert report["statistics"]["hhi_p"] is None
    assert report["flagged"] is False
    json.dumps(report, allow_nan=False)


# ---------------------------------------------------------------------------
# 3e. Input validation — never raise
# ---------------------------------------------------------------------------


def test_missing_blocks_unevaluable_no_raise() -> None:
    series, _ = _series((1.0, 2.0, 3.0, 4.0), (0, 1, 2, 3))
    blade = SingleYearLuckBlade(p_min=0.01, n_perm=100)
    report = blade.run("t0", {}, {}, None, series)
    assert report["flagged"] is False
    assert report["evidence"]["evaluable"] is False
    assert "blocks" in str(report["evidence"]).lower()


def test_length_mismatch_unevaluable_no_raise() -> None:
    series, _ = _series((1.0, 2.0, 3.0, 4.0), (0, 1, 2, 3))
    blade = SingleYearLuckBlade(p_min=0.01, n_perm=100)
    report = blade.run("t0", {}, {"blocks": [0, 1]}, None, series)
    assert report["flagged"] is False
    assert report["evidence"]["evaluable"] is False
    assert "length" in str(report["evidence"]).lower()


def test_single_block_unevaluable_no_raise() -> None:
    report = _run((1.0, 2.0, 3.0, 4.0), (7, 7, 7, 7), p_min=0.01, n_perm=100, min_blocks=2)
    assert report["flagged"] is False
    assert report["evidence"]["evaluable"] is False
    assert "block" in str(report["evidence"]).lower()


# ---------------------------------------------------------------------------
# 3f. Determinism
# ---------------------------------------------------------------------------


def test_same_seed_identical_report_including_hhi_p() -> None:
    values = (10.0, -1.0, 2.0, 0.5)
    blocks = (0, 1, 2, 3)
    a = _run(values, blocks, p_min=0.01, n_perm=200, seed=42)
    b = _run(values, blocks, p_min=0.01, n_perm=200, seed=42)
    assert a == b
    assert a["statistics"]["hhi_p"] == b["statistics"]["hhi_p"]


# ---------------------------------------------------------------------------
# 3g. Calibration script smoke
# ---------------------------------------------------------------------------


def _calibration_cmd(out: Path | None = None) -> list[str]:
    cmd = [
        sys.executable,
        str(CALIBRATION_SCRIPT),
        "--seed-root",
        "7",
        "--n-null",
        "50",
        "--n-obs",
        "40",
        "--n-blocks",
        "4",
        "--target-fpr",
        "0.01",
        "--n-perm",
        "200",
    ]
    if out is not None:
        cmd.extend(["--out", str(out)])
    return cmd


def test_calibration_script_smoke_exit_zero_json_and_byte_identical(tmp_path: Path) -> None:
    env = os.environ.copy()
    pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(REPO_ROOT) if not pp else str(REPO_ROOT) + os.pathsep + pp

    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"
    r1 = subprocess.run(_calibration_cmd(out_a), env=env, capture_output=True, text=True)
    r2 = subprocess.run(_calibration_cmd(out_b), env=env, capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    payload = json.loads(out_a.read_text(encoding="utf-8"))
    assert "chosen_p_min" in payload or payload.get("downgrade") is True
    if payload.get("downgrade") is not True:
        assert payload["chosen_p_min"] is not None
    assert out_a.read_bytes() == out_b.read_bytes()


# ---------------------------------------------------------------------------
# 3h. Integration smoke (fixtures copied from tests/test_blades_harness.py)
# ---------------------------------------------------------------------------

INDEX = ("d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7")
CONC_VALUES = (5.0, 5.0, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5)
BAL_VALUES = (1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
BLOCKS_8 = [0, 0, 1, 1, 2, 2, 3, 3]


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
                (INDEX, CONC_VALUES),
                (INDEX, BAL_VALUES),
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
        thresholds={"single_year_luck": 0.01},
        calibration_fingerprint="fp-test-v0.3-03",
    )


def _blade_reports(ledger) -> list[dict]:
    from harness.blades import BLADE_REPORT_KIND

    out: list[dict] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_REPORT_KIND:
            out.append(payload)
    return out


def test_integration_concentrated_screens_balanced_records(tmp_path: Path) -> None:
    blade = SingleYearLuckBlade(p_min=0.01, n_perm=100, seed=0)
    run = _create(tmp_path, blades=[blade])
    _calibrate(run.ledger)

    tid_conc = run.propose(
        "claim-concentrated",
        {"name": "conc", "blades": {"single_year_luck": {"on_flag": "screen"}}},
        {"blocks": list(BLOCKS_8)},
        _declared(),
    )
    tid_bal = run.propose(
        "claim-balanced",
        {"name": "bal", "blades": {"single_year_luck": {"on_flag": "screen"}}},
        {"blocks": list(BLOCKS_8)},
        _declared(),
    )

    run.evaluate(tid_conc, scores={"i": 0})
    run.evaluate(tid_bal, scores={"i": 1})

    assert run.ledger.status(tid_conc) == "registered"
    assert run.ledger.status(tid_bal) == "evaluated"

    reports = _blade_reports(run.ledger)
    conc_reports = [p for p in reports if p.get("trial_id") == tid_conc]
    assert len(conc_reports) == 1
    assert conc_reports[0]["report"]["flagged"] is True
    assert conc_reports[0]["report"]["blade"] == "single_year_luck"
    bal_reports = [p for p in reports if p.get("trial_id") == tid_bal]
    assert len(bal_reports) == 1
    assert bal_reports[0]["report"]["flagged"] is False
