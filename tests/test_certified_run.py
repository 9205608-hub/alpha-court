"""Tests for CertifiedRun (ticket v0.2-07 / prereg-gate.md).

Red-first bypass coverage: scope-shrink (API + wild verdict), post-hoc
direction flip (three prongs), and seal/judge lifecycle fail-closed paths.
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from court.judge import Application
from court.ledger import DeclaredProtocol, SeConvention, Window

# ---------------------------------------------------------------------------
# Shared fixtures / fakes
# ---------------------------------------------------------------------------

INDEX = ("d1", "d2", "d3", "d4", "d5")
VALUES_A = (0.01, -0.02, 0.03, 0.01, -0.01)
VALUES_B = (0.02, 0.01, -0.01, 0.02, 0.00)
VALUES_C = (-0.01, 0.00, 0.01, -0.02, 0.03)


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
    """Adapter-identity lock; keys overlap fake evaluator meta (prereg-gate §3)."""
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
    """Mirror adapters/qlib_cn.py:_meta shape for ticket-11 drop-in."""
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
    """Deterministic evaluator; series keyed by call order or forced values."""

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
                (INDEX, VALUES_C),
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
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_create_on_existing_nonempty_file_raises(tmp_path: Path):
    from harness.run import CertifiedRun

    path = tmp_path / "ledger.jsonl"
    path.write_text('{"type":"x"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="[Ee]xisting|non-empty|foreign"):
        CertifiedRun.create(path, _run_config(), _policy(), FakeEvaluator())


def test_create_run_config_empty_raises(tmp_path: Path):
    from harness.run import CertifiedRun

    with pytest.raises(ValueError):
        CertifiedRun.create(tmp_path / "l.jsonl", {}, _policy(), FakeEvaluator())


def test_create_run_config_non_dict_raises(tmp_path: Path):
    from harness.run import CertifiedRun

    with pytest.raises(ValueError):
        CertifiedRun.create(tmp_path / "l.jsonl", ["not", "a", "dict"], _policy(), FakeEvaluator())  # type: ignore[arg-type]


def test_create_writes_run_config_and_policy_as_first_events(tmp_path: Path):
    run = _create(tmp_path)
    decls = run.ledger.declarations()
    assert len(decls) >= 2
    assert decls[0].payload.get("kind") == "run_config"
    assert decls[0].payload["config"] == _run_config()
    assert decls[1].payload.get("kind") == "aggregation_policy"
    # raw line order: run_config is event #1
    lines = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").strip().split("\n")
    e0 = json.loads(lines[0])
    assert e0["type"] == "declaration"
    assert e0["payload"]["kind"] == "run_config"


# ---------------------------------------------------------------------------
# Bypass: scope-shrink
# ---------------------------------------------------------------------------


def test_bypass_scope_shrink_api_has_no_scope_parameter():
    """On the certified path there is no scope parameter at all."""
    from harness.run import CertifiedRun

    sig = inspect.signature(CertifiedRun.judge)
    assert "scope" not in sig.parameters


def test_bypass_scope_shrink_wild_verdict_fails_seal_and_verify(tmp_path: Path):
    """Wild append_verdict after judge: seal refuses; hand-crafted seal fails verify."""
    from harness.verify import CertificationError, verify

    run = _create(tmp_path)
    for i, stmt in enumerate(["a", "b", "c"]):
        tid = run.propose(stmt, {"name": f"f{i}"}, {}, _declared())
        run.evaluate(tid, scores={"dummy": i})

    judgment = run.judge([Application("fdr_by", {"q": 0.1})])
    # Smuggle an extra wild verdict onto the same ledger
    scope = [
        t.trial_id
        for t in run.ledger.trials()
        if run.ledger.status(t.trial_id) in ("evaluated", "judged")
    ]
    run.ledger.append_verdict(
        "noise_control",
        scope,
        {},
        {"null": True},
        {tid: "pass" for tid in scope},
        role="informational",
    )
    # Certified seal refuses (judgment verdict_ids ≠ all chain verdicts)
    with pytest.raises(ValueError, match="verdict_ids|judgment|ALL verdict"):
        run.seal()

    # Hand-craft a seal that only lists the certified judgment's verdict_ids
    # (the pre-judgment wild-smuggle path for verify inv 7 / 7.5).
    led = run.ledger
    policy_pair = __import__(
        "harness.aggregation_policy", fromlist=["read_declared_policy"]
    ).read_declared_policy(led)
    assert policy_pair is not None
    did, pol = policy_pair
    pol_payload = next(
        d.payload for d in led.declarations() if d.declaration_id == did
    )
    head_before = led.chain_head
    led.append_seal(
        {
            "kind": "seal",
            "chain_head": head_before,
            "scope": scope,
            "verdict_ids": list(judgment.verdict_ids),
            "policy_declaration_id": did,
            "policy": pol_payload,
            "anchor_ref": None,
        }
    )
    with pytest.raises(
        CertificationError, match="verdict|invariant 7|judgment|7\\.5|wild"
    ):
        verify(tmp_path / "ledger.jsonl")


# ---------------------------------------------------------------------------
# Bypass: post-hoc direction flip (three prongs)
# ---------------------------------------------------------------------------


def test_bypass_direction_flip_mixed_scope_raises_before_verdict(tmp_path: Path):
    """(a) propose greater + less → judge homogeneity raises E2E, no verdicts."""
    run = _create(tmp_path)
    t1 = run.propose("long", {}, {}, _declared(direction="greater"))
    t2 = run.propose("short", {}, {}, _declared(direction="less"))
    run.evaluate(t1, scores=1)
    run.evaluate(t2, scores=2)
    with pytest.raises(ValueError, match="direction|homogeneous|mixed"):
        run.judge([Application("fdr_by", {"q": 0.1})])
    assert run.ledger.verdicts() == []


def test_bypass_direction_flip_byte_tamper_breaks_chain(tmp_path: Path):
    """(b) flip declared.direction in file → verify fails (chain/content hash)."""
    from harness.verify import CertificationError, verify

    run = _create(tmp_path)
    tid = run.propose("claim", {}, {}, _declared(direction="greater"))
    run.evaluate(tid, scores=1)
    run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()

    path = tmp_path / "ledger.jsonl"
    raw = path.read_text(encoding="utf-8")
    flipped = raw.replace("greater", "less", 1)
    assert flipped != raw
    path.write_text(flipped, encoding="utf-8")

    with pytest.raises(CertificationError, match="event_hash|prev_hash|chain|mismatch"):
        verify(path)


def test_bypass_direction_second_evaluate_raises(tmp_path: Path):
    """(c) second evaluate on same trial → court series-exists immutability."""
    run = _create(tmp_path)
    tid = run.propose("claim", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    with pytest.raises(ValueError, match="already evaluated"):
        run.evaluate(tid, scores=2)


# ---------------------------------------------------------------------------
# Happy path + lifecycle
# ---------------------------------------------------------------------------


def test_happy_path_e2e_create_propose_evaluate_judge_seal_verify(tmp_path: Path):
    from harness.verify import verify

    run = _create(tmp_path)
    tids = []
    for i in range(3):
        tid = run.propose(f"claim-{i}", {"factor": f"f{i}"}, {"p": i}, _declared())
        tids.append(tid)
        run.evaluate(tid, scores={"i": i})

    battery = [Application("fdr_by", {"q": 0.1})]
    judgment = run.judge(battery)
    assert len(judgment.verdict_ids) == 1
    # judgment declaration on chain after successful judge
    jdecls = [
        d
        for d in run.ledger.declarations()
        if isinstance(d.payload, dict) and d.payload.get("kind") == "judgment"
    ]
    assert len(jdecls) == 1
    assert jdecls[0].payload["verdict_ids"] == list(judgment.verdict_ids)
    assert jdecls[0].payload["battery"] == [
        {"statistic": "fdr_by", "params": {"q": 0.1}}
    ]
    seal_id = run.seal()
    assert seal_id.startswith("s-")

    report = verify(tmp_path / "ledger.jsonl")
    assert report.n_trials == 3
    assert report.n_verdicts == 1
    assert report.policy_id == "unanimous-discriminating-v1"
    assert report.chain_head == report.seal_event_hash
    assert len(report.chain_head) == 64
    manifest = json.loads((tmp_path / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["chain_head"] == report.chain_head
    assert manifest["seal_event_hash"] == report.seal_event_hash


def test_registered_but_unevaluated_excluded_from_scope_visible_on_chain(tmp_path: Path):
    run = _create(tmp_path)
    t1 = run.propose("a", {}, {}, _declared())
    t2 = run.propose("b", {}, {}, _declared())  # file-drawer
    run.evaluate(t1, scores=1)
    judgment = run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()
    seal = run.ledger.seal()
    assert seal is not None
    assert t1 in seal.payload["scope"]
    assert t2 not in seal.payload["scope"]
    # visible on chain
    trial_ids = {t.trial_id for t in run.ledger.trials()}
    assert t2 in trial_ids
    assert run.ledger.status(t2) == "registered"
    assert judgment.verdict_ids


def test_second_judge_raises(tmp_path: Path):
    run = _create(tmp_path)
    tid = run.propose("a", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    run.judge([Application("fdr_by", {"q": 0.1})])
    with pytest.raises(ValueError, match="once|already|judge"):
        run.judge([Application("fdr_by", {"q": 0.1})])


def test_seal_without_judge_raises(tmp_path: Path):
    run = _create(tmp_path)
    tid = run.propose("a", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    with pytest.raises(ValueError, match="judge"):
        run.seal()


def test_post_seal_propose_and_evaluate_raise(tmp_path: Path):
    run = _create(tmp_path)
    tid = run.propose("a", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()
    with pytest.raises(ValueError, match="seal"):
        run.propose("b", {}, {}, _declared())
    with pytest.raises(ValueError, match="seal"):
        run.evaluate(tid, scores=99)


def test_judge_failure_consumes_judge_and_blocks_seal(tmp_path: Path):
    """If court.judge raises mid-battery, judge is consumed; cannot seal."""
    run = _create(tmp_path)
    t1 = run.propose("a", {}, {}, _declared())
    t2 = run.propose("b", {}, {}, _declared())
    run.evaluate(t1, scores=1)
    run.evaluate(t2, scores=2)
    # fdr_by succeeds; dsr missing required params → raises after first verdict
    with pytest.raises(ValueError):
        run.judge(
            [
                Application("fdr_by", {"q": 0.1}),
                Application("dsr", {}),  # missing selected_trial_id / confidence
            ]
        )
    assert len(run.ledger.verdicts()) >= 1  # orphan verdict(s)
    # No judgment declaration on a bricked run
    kinds = [
        d.payload.get("kind")
        for d in run.ledger.declarations()
        if isinstance(d.payload, dict)
    ]
    assert "judgment" not in kinds
    with pytest.raises(ValueError):
        run.judge([Application("fdr_by", {"q": 0.1})])  # second call
    with pytest.raises(ValueError, match="judge|seal|consumed|failed"):
        run.seal()


def test_mid_battery_brick_open_refuses_seal(tmp_path: Path):
    """F-1: mid-battery brick cannot be revived via open()+seal (rework-01)."""
    from harness.run import CertificationError, CertifiedRun

    run = _create(tmp_path)
    t1 = run.propose("a", {}, {}, _declared())
    t2 = run.propose("b", {}, {}, _declared())
    run.evaluate(t1, scores=1)
    run.evaluate(t2, scores=2)
    with pytest.raises(ValueError):
        run.judge(
            [
                Application("fdr_by", {"q": 0.1}),
                Application("dsr", {}),
            ]
        )
    assert len(run.ledger.verdicts()) >= 1

    run2 = CertifiedRun.open(tmp_path / "ledger.jsonl", FakeEvaluator())
    with pytest.raises(ValueError, match="once|already|judge"):
        run2.judge([Application("fdr_by", {"q": 0.1})])
    with pytest.raises(
        CertificationError,
        match="judged run incomplete: verdicts without a judgment event",
    ):
        run2.seal()


def test_evaluate_meta_conflict_with_run_config_raises(tmp_path: Path):
    from harness.run import CertificationError

    ev = FakeEvaluator(meta_overrides={"label_expr": "DIFFERENT_LABEL"})
    run = _create(tmp_path, evaluator=ev)
    tid = run.propose("a", {}, {}, _declared())
    with pytest.raises(CertificationError, match="label_expr|conformance|run_config"):
        run.evaluate(tid, scores=1)


def test_propose_hypothesis_id_vs_statement(tmp_path: Path):
    run = _create(tmp_path)
    # statement path
    t1 = run.propose("fresh claim text", {}, {}, _declared())
    assert t1.startswith("t-")
    # re-use hypothesis id
    hid = run.ledger.trials([t1])[0].hypothesis_id
    assert re.fullmatch(r"h-\d{6}", hid)
    t2 = run.propose(hid, {}, {}, _declared())
    assert run.ledger.trials([t2])[0].hypothesis_id == hid
    # unknown hypothesis id shape → court's ValueError
    with pytest.raises(ValueError):
        run.propose("h-999999", {}, {}, _declared())


def test_open_sealed_raises(tmp_path: Path):
    from harness.run import CertificationError, CertifiedRun

    run = _create(tmp_path)
    tid = run.propose("a", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()
    with pytest.raises(CertificationError, match="seal"):
        CertifiedRun.open(tmp_path / "ledger.jsonl", FakeEvaluator())


def test_open_recovers_judged_state_allows_seal(tmp_path: Path):
    from harness.run import CertifiedRun

    run = _create(tmp_path)
    tid = run.propose("a", {}, {}, _declared())
    run.evaluate(tid, scores=1)
    run.judge([Application("fdr_by", {"q": 0.1})])
    # re-open before seal
    run2 = CertifiedRun.open(tmp_path / "ledger.jsonl", FakeEvaluator())
    with pytest.raises(ValueError, match="once|already|judge"):
        run2.judge([Application("fdr_by", {"q": 0.1})])
    sid = run2.seal()
    assert sid.startswith("s-")


def test_module_docstring_names_section6_boundaries():
    from harness import run as run_mod

    doc = run_mod.__doc__ or ""
    # Four §6 honest boundaries (prereg-gate v3 §6)
    assert "pre-seal" in doc.lower() or "truncat" in doc.lower()
    assert "off-path" in doc.lower() or "pre-screen" in doc.lower()
    assert "in-process" in doc.lower() or "forger" in doc.lower()
    assert "sibling" in doc.lower()


def test_judgment_payload_unknown_verdict_id_fails_closed(tmp_path):
    """A judgment declaration referencing a verdict absent from the chain is
    tampering/corruption, not something to skip silently (v0.2-12 slice C)."""
    import pytest as _pytest

    from court.ledger import DeclaredProtocol, Ledger, Series, Window
    from harness.run import CertificationError, _judgment_from_payload

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(
        hid,
        {},
        {},
        DeclaredProtocol(
            metric="returns",
            window=Window(start="2020-01-01", end="2020-12-31"),
            periods_per_year=252.0,
        ),
    )
    ledger.record(tid, Series(index=("d1", "d2", "d3"), values=(1.0, 2.0, 3.0)))
    vid = ledger.append_verdict("dsr", [tid], {}, {}, {tid: "pass"})

    good = _judgment_from_payload({"verdict_ids": [vid]}, ledger)
    assert set(good.decisions.keys()) == {vid}

    with _pytest.raises(CertificationError, match="unknown verdict_id"):
        _judgment_from_payload({"verdict_ids": [vid, "v-999999"]}, ledger)
