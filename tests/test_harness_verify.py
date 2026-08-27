"""Tests for harness.verify and anchor backends (ticket v0.2-07).

Invariant order and three bypass traces; honesty test for pre-seal
truncation window (prereg-gate v3 §6 — assert replay PASSES).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from court.judge import Application
from court.ledger import DeclaredProtocol, Ledger, SeConvention, Series, Window

# Reuse fakes from certified-run tests via local copies (no cross-import of
# test modules required by pytest collection order).

INDEX = ("d1", "d2", "d3", "d4", "d5")
VALUES = (0.01, -0.02, 0.03, 0.01, -0.01)


def _window() -> Window:
    return Window(start="2020-01-01", end="2020-12-31")


def _declared(*, direction: str = "two-sided") -> DeclaredProtocol:
    return DeclaredProtocol(
        metric="returns",
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


def _meta(**overrides: Any) -> dict[str, Any]:
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
        "metric": "returns",
        "metric_params": {"quantile": 0.2},
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
    def __init__(self, n: int = 3) -> None:
        self._n = n
        self._i = 0

    def evaluate(self, scores: Any, metric: str) -> FakeEvalResult:
        self._i += 1
        vals = tuple(float(v) + 0.001 * self._i for v in VALUES)
        return FakeEvalResult(
            index=list(INDEX),
            values=np.asarray(vals, dtype=np.float64),
            meta=_meta(metric=metric),
        )


def _policy():
    from harness.aggregation_policy import AggregationPolicy

    return AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )


def _sealed_run(tmp_path: Path, n_trials: int = 2, anchor=None):
    from harness.run import CertifiedRun

    path = tmp_path / "ledger.jsonl"
    run = CertifiedRun.create(
        path, _run_config(), _policy(), FakeEvaluator(n=n_trials), anchor=anchor
    )
    for i in range(n_trials):
        tid = run.propose(f"claim-{i}", {}, {}, _declared())
        run.evaluate(tid, scores=i)
    run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()
    return path


# ---------------------------------------------------------------------------
# Bypass: trace tampering
# ---------------------------------------------------------------------------


def test_bypass_trace_tamper_mid_file_byte_fails_verify(tmp_path: Path):
    from harness.verify import CertificationError, verify

    path = _sealed_run(tmp_path)
    text = path.read_text(encoding="utf-8")
    # Mutate a content-hashed field (not `at` / hash envelope — those are
    # excluded from content_hash per prereg-gate.md §4.1). Flip a statement.
    if "claim-0" not in text:
        raise AssertionError("expected claim-0 in sealed ledger for tamper test")
    path.write_text(text.replace("claim-0", "claim-X", 1), encoding="utf-8")
    with pytest.raises(CertificationError):
        verify(path)


def test_bypass_trace_delete_seal_fails_verify_while_open_replays(tmp_path: Path):
    """Delete seal → verify fails ('no seal'); bare Ledger.open still replays.

    Honesty boundary: truncation makes it UNCERTIFIED, not undetectably
    certified — prereg-gate v3 §6.
    """
    from harness.verify import CertificationError, verify

    path = _sealed_run(tmp_path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    assert json.loads(lines[-1])["type"] == "seal"
    # drop seal line
    path.write_text("".join(lines[:-1]), encoding="utf-8")

    # bare open still works (uncertified calculator state)
    led = Ledger.open(path)
    assert led.seal() is None
    assert len(led.trials()) >= 1

    with pytest.raises(CertificationError, match="seal|no seal"):
        verify(path)


def test_honesty_pre_seal_truncation_replay_passes(tmp_path: Path):
    """On UNSEALED certified ledger, delete last evaluation → bare replay PASSES.

    Disclosed §6 window — assert it passes so the boundary stays on the record
    (prereg-gate v3 §6).
    """
    from harness.run import CertifiedRun

    path = tmp_path / "ledger.jsonl"
    run = CertifiedRun.create(path, _run_config(), _policy(), FakeEvaluator())
    t1 = run.propose("a", {}, {}, _declared())
    t2 = run.propose("b", {}, {}, _declared())
    run.evaluate(t1, scores=1)
    run.evaluate(t2, scores=2)
    # do NOT seal

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    # last event should be evaluation of t2
    assert json.loads(lines[-1])["type"] == "evaluation"
    path.write_text("".join(lines[:-1]), encoding="utf-8")

    # ASSERT bare replay passes with zero warnings (the disclosed window)
    led = Ledger.open(path)
    statuses = [led.status(t.trial_id) for t in led.trials()]
    assert "evaluated" in statuses
    # one evaluation truncated away — still a valid unsealed ledger prefix
    assert led.seal() is None


# ---------------------------------------------------------------------------
# Verify invariants
# ---------------------------------------------------------------------------


def test_verify_happy_path(tmp_path: Path):
    from harness.verify import verify

    path = _sealed_run(tmp_path, n_trials=3)
    report = verify(path)
    assert report.n_trials == 3
    assert report.n_verdicts == 1
    assert report.policy_id == "unanimous-discriminating-v1"
    assert report.chain_head == report.seal_event_hash


def test_verify_trailing_garbage_fails_invariant_1(tmp_path: Path):
    from harness.verify import CertificationError, verify

    path = _sealed_run(tmp_path)
    with path.open("a", encoding="utf-8") as f:
        f.write("not-json-garbage\n")
    with pytest.raises(CertificationError, match="complete|envelope|raw|invariant 1|parse"):
        verify(path)


def test_verify_missing_final_newline_fails_invariant_1(tmp_path: Path):
    from harness.verify import CertificationError, verify

    path = _sealed_run(tmp_path)
    raw = path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    path.write_text(raw.rstrip("\n"), encoding="utf-8")
    with pytest.raises(CertificationError, match="newline|complete|invariant 1"):
        verify(path)


def test_verify_legacy_missing_envelope_fails_invariant_1(tmp_path: Path):
    """Pure legacy (no hash fields) dies on invariant 1 missing envelope keys."""
    from harness.verify import CertificationError, verify

    path = tmp_path / "legacy.jsonl"
    events = [
        {
            "type": "hypothesis",
            "at": "2020-01-01T00:00:00+00:00",
            "hypothesis_id": "h-000001",
            "statement": "x",
        },
    ]
    path.write_text(
        "".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events),
        encoding="utf-8",
    )
    with pytest.raises(CertificationError, match="invariant 1.*envelope|envelope keys"):
        verify(path)


def test_verify_blank_hash_fields_fails_invariant_2(tmp_path: Path):
    """Hash keys present but blank → reaches invariant 2 (uncertified: no chain)."""
    from harness.verify import CertificationError, verify

    path = tmp_path / "blank_hash.jsonl"
    event = {
        "type": "hypothesis",
        "at": "2020-01-01T00:00:00+00:00",
        "hypothesis_id": "h-000001",
        "statement": "x",
        "prev_hash": "",
        "event_hash": "",
    }
    path.write_text(json.dumps(event, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(CertificationError, match="uncertified: no chain"):
        verify(path)


def test_verify_policy_after_verdict_fails_invariant_4(tmp_path: Path):
    """Hand-crafted: policy declaration after a verdict → inv 4 (⚠-1 handoff)."""
    from harness.aggregation_policy import AggregationPolicy
    from harness.verify import CertificationError, verify

    path = tmp_path / "ledger.jsonl"
    led = Ledger.open(path)
    # run_config first
    led.append_declaration({"kind": "run_config", "config": _run_config()})
    hid = led.register_hypothesis("claim")
    tid = led.register(hid, {}, {}, _declared())
    led.record(
        tid,
        Series(index=INDEX, values=VALUES),
        attestation=_meta(),
    )
    # verdict BEFORE policy (wild ordering)
    led.append_verdict("fdr_by", [tid], {"q": 0.1}, {}, {tid: "reject"}, role="discriminating")
    # late policy
    pol = AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )
    did = led.append_declaration(pol.to_payload())
    head_before = led.chain_head
    led.append_seal(
        {
            "kind": "seal",
            "chain_head": head_before,
            "scope": [tid],
            "verdict_ids": [led.verdicts()[0].verdict_id],
            "policy_declaration_id": did,
            "policy": pol.to_payload(),
            "anchor_ref": None,
        }
    )
    with pytest.raises(CertificationError, match="order|policy|verdict|invariant 4"):
        verify(path)


def test_verify_smuggled_policy_key_fails_invariant_5(tmp_path: Path):
    """Seal policy payload with smuggled key ≠ on-chain declaration (⚠-2)."""
    from harness.verify import CertificationError, verify

    path = _sealed_run(tmp_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    seal = json.loads(lines[-1])
    # smuggle a key into the seal's policy copy only
    seal["payload"]["policy"] = dict(seal["payload"]["policy"])
    seal["payload"]["policy"]["smuggled"] = "launder"
    # re-hash seal line so chain envelope stays consistent would defeat the
    # test — we want inv 5 (payload equality), so recompute hashes for the
    # seal line only to pass inv 1–3 and fail on 5.
    from court.ledger import content_hash, link_event_hash

    prev = seal["prev_hash"]
    # strip hash fields, recompute
    body = {k: v for k, v in seal.items() if k not in ("prev_hash", "event_hash")}
    # at stays; content_hash excludes at/prev_hash/event_hash
    ch = content_hash(body)
    seal["event_hash"] = link_event_hash(prev, ch)
    lines[-1] = json.dumps(seal, separators=(",", ":"), ensure_ascii=False)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(CertificationError, match="policy|payload|invariant 5|equal"):
        verify(path)


def test_verify_manifest_mismatch_fails_invariant_6(tmp_path: Path):
    from harness.verify import CertificationError, verify

    path = _sealed_run(tmp_path)
    manifest_path = tmp_path / "run_manifest.json"
    man = json.loads(manifest_path.read_text(encoding="utf-8"))
    man["chain_head"] = "0" * 64
    manifest_path.write_text(json.dumps(man), encoding="utf-8")
    with pytest.raises(CertificationError, match="manifest|chain_head|invariant 6"):
        verify(path)


def test_verify_handcrafted_conflicting_attestation_fails_invariant_8(tmp_path: Path):
    """Evaluation attestation conflicts with run_config → inv 8."""
    from harness.aggregation_policy import AggregationPolicy
    from harness.verify import CertificationError, verify

    path = tmp_path / "ledger.jsonl"
    led = Ledger.open(path)
    led.append_declaration({"kind": "run_config", "config": _run_config()})
    pol = AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )
    did = led.append_declaration(pol.to_payload())
    hid = led.register_hypothesis("claim")
    tid = led.register(hid, {}, {}, _declared())
    bad_meta = _meta(label_expr="TAMPERED_LABEL_EXPR")
    # court only checks metric/window vs declared — label_expr conflict is harness
    led.record(tid, Series(index=INDEX, values=VALUES), attestation=bad_meta)
    led.append_verdict("fdr_by", [tid], {"q": 0.1}, {}, {tid: "reject"}, role="discriminating")
    vid = led.verdicts()[0].verdict_id
    led.append_declaration(
        {
            "kind": "judgment",
            "battery": [{"statistic": "fdr_by", "params": {"q": 0.1}}],
            "verdict_ids": [vid],
        }
    )
    head_before = led.chain_head
    led.append_seal(
        {
            "kind": "seal",
            "chain_head": head_before,
            "scope": [tid],
            "verdict_ids": [vid],
            "policy_declaration_id": did,
            "policy": pol.to_payload(),
            "anchor_ref": None,
        }
    )
    with pytest.raises(
        CertificationError,
        match="attestation|run_config|conformance|invariant 8|label_expr",
    ):
        verify(path)


def test_verify_orphan_verdicts_seal_without_judgment_fails(tmp_path: Path):
    """Hand-crafted: orphan verdicts + seal, no judgment event → verify raises."""
    from harness.aggregation_policy import AggregationPolicy
    from harness.verify import CertificationError, verify

    path = tmp_path / "ledger.jsonl"
    led = Ledger.open(path)
    led.append_declaration({"kind": "run_config", "config": _run_config()})
    pol = AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )
    did = led.append_declaration(pol.to_payload())
    hid = led.register_hypothesis("claim")
    tid = led.register(hid, {}, {}, _declared())
    led.record(tid, Series(index=INDEX, values=VALUES), attestation=_meta())
    led.append_verdict("fdr_by", [tid], {"q": 0.1}, {}, {tid: "reject"}, role="discriminating")
    vid = led.verdicts()[0].verdict_id
    # deliberately NO judgment declaration
    head_before = led.chain_head
    led.append_seal(
        {
            "kind": "seal",
            "chain_head": head_before,
            "scope": [tid],
            "verdict_ids": [vid],
            "policy_declaration_id": did,
            "policy": pol.to_payload(),
            "anchor_ref": None,
        }
    )
    with pytest.raises(CertificationError, match="judgment|7\\.5|invariant 7"):
        verify(path)


def test_verify_two_policy_declarations_fails(tmp_path: Path):
    """Exactly one aggregation_policy on the chain (rework-01 FIX 3)."""
    from harness.aggregation_policy import AggregationPolicy
    from harness.verify import CertificationError, verify

    path = tmp_path / "ledger.jsonl"
    led = Ledger.open(path)
    led.append_declaration({"kind": "run_config", "config": _run_config()})
    pol = AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )
    did = led.append_declaration(pol.to_payload())
    # second policy (hand-crafted; declare_policy would refuse)
    led.append_declaration(pol.to_payload())
    hid = led.register_hypothesis("claim")
    tid = led.register(hid, {}, {}, _declared())
    led.record(tid, Series(index=INDEX, values=VALUES), attestation=_meta())
    led.append_verdict("fdr_by", [tid], {"q": 0.1}, {}, {tid: "reject"}, role="discriminating")
    vid = led.verdicts()[0].verdict_id
    led.append_declaration(
        {
            "kind": "judgment",
            "battery": [{"statistic": "fdr_by", "params": {"q": 0.1}}],
            "verdict_ids": [vid],
        }
    )
    head_before = led.chain_head
    led.append_seal(
        {
            "kind": "seal",
            "chain_head": head_before,
            "scope": [tid],
            "verdict_ids": [vid],
            "policy_declaration_id": did,
            "policy": pol.to_payload(),
            "anchor_ref": None,
        }
    )
    with pytest.raises(
        CertificationError,
        match="exactly one|aggregation_policy|policy declaration",
    ):
        verify(path)


# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------


def test_noop_anchor_pin_verify_roundtrip():
    from harness.anchor import NoopAnchor

    a = NoopAnchor()
    assert a.ref_before_seal() is None
    ref = a.pin("abc" * 10 + "ab")  # 32 chars not required
    assert ref == "noop"
    assert a.verify("anything") is True


def test_file_anchor_pin_verify_roundtrip(tmp_path: Path):
    from harness.anchor import FileAnchor

    path = tmp_path / "anchors.jsonl"
    a = FileAnchor(path)
    assert path.exists()  # created at construction (prereg-gate §4.2)
    pre = a.ref_before_seal()
    assert pre is not None
    head = "a" * 64
    ref = a.pin(head)
    assert ref == str(path)
    assert a.verify(head) is True
    assert a.verify("b" * 64) is False


def test_file_anchor_on_certified_run(tmp_path: Path):
    from harness.anchor import FileAnchor
    from harness.verify import verify

    anchor_path = tmp_path / "ext_anchor.jsonl"
    path = _sealed_run(tmp_path, anchor=FileAnchor(anchor_path))
    report = verify(path, anchor=FileAnchor(anchor_path))
    assert report.anchor_ref is not None
    assert anchor_path.exists()


def test_git_anchor_pin_verify_roundtrip(tmp_path: Path):
    from harness.anchor import GitAnchor

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    # initial commit so later pins have a parent-optional clean tree
    (repo / "README").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=t@t", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    a = GitAnchor(repo, committer_name="test", committer_email="t@t")
    assert a.ref_before_seal() is None
    head = "c" * 64
    sha = a.pin(head)
    assert isinstance(sha, str) and len(sha) >= 7
    assert a.verify(head) is True
    assert a.verify("d" * 64) is False


def test_anchor_deleted_manifest_empty_backend_raises(tmp_path: Path):
    """Finding A(a): rm run_manifest.json; backend that did not pin → raises.

    Old fail-open: missing manifest skipped the anchor check entirely, so even
    an empty backend would pass. After rework-01 the backend is always
    consulted when supplied.
    """
    from harness.anchor import FileAnchor
    from harness.verify import CertificationError, verify

    anchor_path = tmp_path / "ext_anchor.jsonl"
    path = _sealed_run(tmp_path, anchor=FileAnchor(anchor_path))
    man = tmp_path / "run_manifest.json"
    assert man.is_file()
    man.unlink()
    empty = FileAnchor(tmp_path / "empty_anchor.jsonl")
    with pytest.raises(
        CertificationError,
        match="anchor supplied but does not attest the recomputed head",
    ):
        verify(path, anchor=empty)
    # Matching backend still PASSES without the manifest (query-by-head).
    report = verify(path, anchor=FileAnchor(anchor_path))
    assert report.chain_head


def test_anchor_blanked_manifest_ref_empty_backend_raises(tmp_path: Path):
    """Finding A(b): manifest present but anchor_ref null; empty backend raises."""
    from harness.anchor import FileAnchor
    from harness.verify import CertificationError, verify

    anchor_path = tmp_path / "ext_anchor.jsonl"
    path = _sealed_run(tmp_path, anchor=FileAnchor(anchor_path))
    man_path = tmp_path / "run_manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["anchor_ref"] = None
    man_path.write_text(json.dumps(man), encoding="utf-8")
    empty = FileAnchor(tmp_path / "empty_anchor.jsonl")
    with pytest.raises(
        CertificationError,
        match="anchor supplied but does not attest the recomputed head",
    ):
        verify(path, anchor=empty)
    # Matching backend still PASSES (never gated on manifest ref).
    report = verify(path, anchor=FileAnchor(anchor_path))
    assert report.anchor_ref is None


def test_anchor_forged_chain_not_attested_by_original_pin(tmp_path: Path):
    """Finding A(c): forge chain; FileAnchor that pinned ORIGINAL head fails."""
    from harness.anchor import FileAnchor
    from harness.verify import CertificationError, verify

    anchor_path = tmp_path / "ext_anchor.jsonl"
    _sealed_run(tmp_path, anchor=FileAnchor(anchor_path))
    original_anchor = FileAnchor(anchor_path)
    # Pin original, then verify a different sealed run against that pin —
    # forged/other head is not attested by the original FileAnchor.
    other = tmp_path / "other"
    other.mkdir()
    other_path = _sealed_run(other, n_trials=1)  # different chain head
    with pytest.raises(
        CertificationError,
        match="anchor supplied but does not attest the recomputed head",
    ):
        verify(other_path, anchor=original_anchor)


def test_anchor_honest_matching_backend_passes(tmp_path: Path):
    """Finding A(d): honest run with matching FileAnchor PASSES."""
    from harness.anchor import FileAnchor
    from harness.verify import verify

    anchor_path = tmp_path / "ext_anchor.jsonl"
    path = _sealed_run(tmp_path, anchor=FileAnchor(anchor_path))
    report = verify(path, anchor=FileAnchor(anchor_path))
    assert report.anchor_ref is not None


def test_cli_exit_codes(tmp_path: Path):
    path = _sealed_run(tmp_path)
    good = subprocess.run(
        [sys.executable, "-m", "harness.verify", str(path)],
        capture_output=True,
        text=True,
    )
    assert good.returncode == 0, good.stderr
    assert good.stdout
    # without --anchor, report says merely reported
    assert "reported" in good.stdout or '"anchor_status"' in good.stdout

    # break seal
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(lines[:-1]), encoding="utf-8")
    bad = subprocess.run(
        [sys.executable, "-m", "harness.verify", str(path)],
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1
    assert bad.stderr


# ---------------------------------------------------------------------------
# rework-02: battery cross-check, judgment position, CLI anchors
# ---------------------------------------------------------------------------


def _rehash_events(events: list[dict]) -> list[dict]:
    """Full-chain reforge helper: recompute prev_hash/event_hash for every line."""
    from court.ledger import content_hash, link_event_hash

    genesis = "0" * 64
    head = genesis
    out: list[dict] = []
    for ev in events:
        body = {k: v for k, v in ev.items() if k not in ("prev_hash", "event_hash")}
        ch = content_hash(body)
        eh = link_event_hash(head, ch)
        body["prev_hash"] = head
        body["event_hash"] = eh
        out.append(body)
        head = eh
    return out


def _write_events(path: Path, events: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(e, separators=(",", ":"), ensure_ascii=False) for e in events)
        + "\n",
        encoding="utf-8",
    )


def test_verify_shrunk_judgment_battery_fails_invariant_75(tmp_path: Path):
    """rework-02 FIX 1: judgment.battery multiset must match verdict statistics."""
    from court.judge import Application
    from harness.run import CertifiedRun
    from harness.verify import CertificationError, verify

    path = tmp_path / "ledger.jsonl"
    run = CertifiedRun.create(path, _run_config(), _policy(), FakeEvaluator(n=2))
    for i in range(2):
        tid = run.propose(f"claim-{i}", {}, {}, _declared())
        run.evaluate(tid, scores=i)
    # two-gate battery → two verdicts
    run.judge(
        [
            Application("fdr_by", {"q": 0.1}),
            Application("fdr_bh", {"q": 0.1}),
        ]
    )
    run.seal()

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    # Shrink battery to one statistic while leaving both verdicts intact.
    for ev in events:
        if (
            ev.get("type") == "declaration"
            and isinstance(ev.get("payload"), dict)
            and ev["payload"].get("kind") == "judgment"
        ):
            ev["payload"] = dict(ev["payload"])
            ev["payload"]["battery"] = [{"statistic": "fdr_by", "params": {"q": 0.1}}]
            break
    else:
        raise AssertionError("judgment declaration not found")

    # Seal's chain_head points at pre-seal head — after rehash of all lines the
    # seal payload.chain_head must equal recomputed head of events[:-1].
    events = _rehash_events(events)
    seal = events[-1]
    seal_payload = dict(seal["payload"])
    # recompute head before seal
    pre = _rehash_events(events[:-1])
    seal_payload["chain_head"] = pre[-1]["event_hash"] if pre else "0" * 64
    events[-1] = {**seal, "payload": seal_payload}
    events = _rehash_events(events)
    # drop/update manifest so inv 6 doesn't fire on head mismatch
    man = tmp_path / "run_manifest.json"
    if man.is_file():
        man.unlink()
    _write_events(path, events)

    with pytest.raises(
        CertificationError,
        match="invariant 7.5: judgment battery does not match verdict statistics",
    ):
        verify(path)


def test_verify_judgment_before_verdict_fails_invariant_4(tmp_path: Path):
    """rework-02 FIX 2: judgment raw index must be after every verdict."""
    from harness.aggregation_policy import AggregationPolicy
    from harness.verify import CertificationError, verify

    path = tmp_path / "ledger.jsonl"
    led = Ledger.open(path)
    led.append_declaration({"kind": "run_config", "config": _run_config()})
    pol = AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )
    did = led.append_declaration(pol.to_payload())
    hid = led.register_hypothesis("claim")
    tid = led.register(hid, {}, {}, _declared())
    led.record(tid, Series(index=INDEX, values=VALUES), attestation=_meta())
    # Write judgment BEFORE the verdict (wrong order).
    led.append_declaration(
        {
            "kind": "judgment",
            "battery": [{"statistic": "fdr_by", "params": {"q": 0.1}}],
            "verdict_ids": [],  # filled after — actually need matching vids
        }
    )
    # We need a proper hand-craft: re-open raw and reorder after writing both.
    led.append_verdict("fdr_by", [tid], {"q": 0.1}, {}, {tid: "reject"}, role="discriminating")
    vid = led.verdicts()[0].verdict_id

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    # Fix judgment payload verdict_ids and ensure judgment sits before verdict
    j_idx = next(
        i
        for i, e in enumerate(events)
        if e.get("type") == "declaration"
        and isinstance(e.get("payload"), dict)
        and e["payload"].get("kind") == "judgment"
    )
    v_idx = next(i for i, e in enumerate(events) if e.get("type") == "verdict")
    events[j_idx]["payload"] = {
        "kind": "judgment",
        "battery": [{"statistic": "fdr_by", "params": {"q": 0.1}}],
        "verdict_ids": [vid],
    }
    # If judgment is already before verdict, keep; else swap
    if j_idx > v_idx:
        events[j_idx], events[v_idx] = events[v_idx], events[j_idx]
    # Append seal
    events = _rehash_events(events)
    head_before = events[-1]["event_hash"]
    seal = {
        "type": "seal",
        "at": "2020-01-01T00:00:00+00:00",
        "seal_id": "s-000001",
        "payload": {
            "kind": "seal",
            "chain_head": head_before,
            "scope": [tid],
            "verdict_ids": [vid],
            "policy_declaration_id": did,
            "policy": pol.to_payload(),
            "anchor_ref": None,
        },
    }
    events.append(seal)
    events = _rehash_events(events)
    # Fix seal chain_head after final rehash of pre-seal
    pre = _rehash_events(events[:-1])
    events[-1]["payload"] = dict(events[-1]["payload"])
    events[-1]["payload"]["chain_head"] = pre[-1]["event_hash"]
    events = _rehash_events(events)
    _write_events(path, events)

    with pytest.raises(
        CertificationError,
        match="invariant 4|judgment|after.*verdict|verdict.*before",
    ):
        verify(path)


def test_cli_anchor_file_attests_exit_0(tmp_path: Path):
    """rework-02 FIX 3: --anchor file:<path> verifies when pin matches."""
    from harness.anchor import FileAnchor

    anchor_path = tmp_path / "ext.jsonl"
    path = _sealed_run(tmp_path, anchor=FileAnchor(anchor_path))
    good = subprocess.run(
        [
            sys.executable,
            "-m",
            "harness.verify",
            str(path),
            "--anchor",
            f"file:{anchor_path}",
        ],
        capture_output=True,
        text=True,
    )
    assert good.returncode == 0, good.stderr
    assert "verified" in good.stdout


def test_cli_anchor_file_does_not_attest_exit_1(tmp_path: Path):
    """rework-02 FIX 3: --anchor file:<path> exit 1 when empty backend."""
    path = _sealed_run(tmp_path)
    empty = tmp_path / "empty.jsonl"
    empty.touch()
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "harness.verify",
            str(path),
            "--anchor",
            f"file:{empty}",
        ],
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1
    assert bad.stderr


def test_cli_anchor_git_attests_and_rejects(tmp_path: Path):
    """rework-02 FIX 3: --anchor git:<repo> exit 0 when pinned, 1 otherwise."""
    from court.judge import Application
    from harness.anchor import GitAnchor
    from harness.run import CertifiedRun

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "README").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=t@t", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    ledger = tmp_path / "ledger.jsonl"
    run = CertifiedRun.create(
        ledger,
        _run_config(),
        _policy(),
        FakeEvaluator(n=1),
        anchor=GitAnchor(repo, committer_name="test", committer_email="t@t"),
    )
    tid = run.propose("claim", {}, {}, _declared())
    run.evaluate(tid, scores=0)
    run.judge([Application("fdr_by", {"q": 0.1})])
    run.seal()

    good = subprocess.run(
        [
            sys.executable,
            "-m",
            "harness.verify",
            str(ledger),
            "--anchor",
            f"git:{repo}",
        ],
        capture_output=True,
        text=True,
    )
    assert good.returncode == 0, good.stderr
    assert "verified" in good.stdout

    other = tmp_path / "other_repo"
    other.mkdir()
    subprocess.run(["git", "init"], cwd=other, check=True, capture_output=True)
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "harness.verify",
            str(ledger),
            "--anchor",
            f"git:{other}",
        ],
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1
    assert bad.stderr


def test_main_malformed_file_anchor_path_exits_1_not_traceback(capsys):
    """FileAnchor construction raises OSError subclasses on malformed paths
    (e.g. a parent that is not a directory); main must catch them like the
    ValueError parse errors — clean exit 1, message on stderr (v0.2-12 F)."""
    from harness.verify import main

    rc = main(["does-not-matter.jsonl", "--anchor", "file:/dev/null/foo"])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.strip(), "expected a diagnostic on stderr"
