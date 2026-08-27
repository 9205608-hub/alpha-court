"""Evidence-layer tests for court/ledger.py (ticket v0.2-06).

Covers source_ref, attestation, hash chain, legacy compatibility,
declaration/seal events. Design contract: docs/design/prereg-gate.md §3–§7.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
from pathlib import Path

import pytest

from court.ledger import (
    DeclarationRecord,
    DeclaredProtocol,
    Ledger,
    LedgerCorruptionError,
    SealRecord,
    Series,
    Window,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KILLER_LEDGER = (
    Path(__file__).resolve().parents[1] / "examples" / "killer_demo" / "out" / "ledger.jsonl"
)


def _window() -> Window:
    return Window(start="2020-01-01", end="2020-12-31")


def _declared(**kwargs) -> DeclaredProtocol:
    base = dict(
        metric="returns",
        window=_window(),
        periods_per_year=252.0,
    )
    base.update(kwargs)
    return DeclaredProtocol(**base)


def _series(labels: list[str] | None = None, values: list[float] | None = None) -> Series:
    if labels is None:
        labels = ["d1", "d2", "d3"]
    if values is None:
        values = [0.01, -0.02, 0.03]
    return Series(index=tuple(labels), values=tuple(values))


def _attestation(**overrides) -> dict:
    base: dict = {
        "metric": "returns",
        "window": {"start": "2020-01-01", "end": "2020-12-31"},
        "n_evaluation_dates": 3,
        "universe": "opaque-u",
        "adapter_version": "0.0.1",
    }
    base.update(overrides)
    return base


def _pretransform(obj):
    if isinstance(obj, float) and not isinstance(obj, bool):
        return struct.pack("<d", obj).hex()
    if isinstance(obj, dict):
        return {k: _pretransform(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_pretransform(v) for v in obj]
    if isinstance(obj, tuple):
        return [_pretransform(v) for v in obj]
    return obj


def _canonical_json(obj) -> str:
    return json.dumps(
        _pretransform(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _content_hash(event: dict) -> str:
    content = {k: v for k, v in event.items() if k not in ("at", "prev_hash", "event_hash")}
    return hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()


def _event_hash(prev_hash: str, content_hash: str) -> str:
    return hashlib.sha256((prev_hash + content_hash).encode("ascii")).hexdigest()


def _read_events(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(ln) for ln in lines if ln]


# ---------------------------------------------------------------------------
# 1. source_ref
# ---------------------------------------------------------------------------


def test_source_ref_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(
        hid, {"k": 1}, {"p": 2}, _declared(), source_ref="adapters/qlib_cn#abc"
    )
    rec = ledger.trials()[0]
    assert rec.source_ref == "adapters/qlib_cn#abc"
    assert rec.trial_id == tid

    ledger2 = Ledger.open(path)
    assert ledger2.trials()[0].source_ref == "adapters/qlib_cn#abc"
    trial_evt = [e for e in _read_events(path) if e["type"] == "trial"][0]
    assert trial_evt["source_ref"] == "adapters/qlib_cn#abc"


def test_source_ref_default_none(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    assert ledger.trials()[0].source_ref is None
    assert tid == "t-000001"
    trial_evt = [e for e in _read_events(path) if e["type"] == "trial"][0]
    assert trial_evt["source_ref"] is None


def test_source_ref_non_str_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    with pytest.raises(ValueError, match="source_ref"):
        ledger.register(hid, {}, {}, _declared(), source_ref={"path": "x"})  # type: ignore[arg-type]
    assert path.read_text(encoding="utf-8").count("\n") == 1  # only hypothesis


# ---------------------------------------------------------------------------
# 1b. non-str dict keys on the hash path (rework-01)
# ---------------------------------------------------------------------------


def test_register_int_keys_in_spec_raises_and_writes_nothing(tmp_path: Path) -> None:
    """Int keys would make write/replay hashes diverge — reject at write time."""
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    head_before = ledger.chain_head
    n_lines_before = len(path.read_text(encoding="utf-8").strip().splitlines())

    with pytest.raises(ValueError, match="key"):
        ledger.register(hid, {"nested": {2: "x", 10: "y"}}, {}, _declared())

    assert ledger.chain_head == head_before
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == n_lines_before
    # Ledger still usable after rejection.
    tid = ledger.register(hid, {"nested": {"2": "x", "10": "y"}}, {}, _declared())
    assert tid.startswith("t-")
    ledger2 = Ledger.open(path)
    assert ledger2.chain_head == ledger.chain_head


def test_register_mixed_type_keys_raises_value_error_not_type_error(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    with pytest.raises(ValueError):
        ledger.register(hid, {1: "a", "b": 2}, {}, _declared())  # type: ignore[dict-item]


def test_register_int_keys_in_params_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    with pytest.raises(ValueError, match="key"):
        ledger.register(hid, {}, {"lookbacks": {5: True}}, _declared())


def test_attestation_nested_non_str_key_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    att = _attestation()
    att["opaque"] = {1: "nested-int-key"}
    with pytest.raises(ValueError, match="key"):
        ledger.record(tid, _series(), attestation=att)
    # Still unevaluated / usable.
    ledger.record(tid, _series(), attestation=_attestation())
    assert ledger.trials()[0].series is not None


def test_declaration_and_seal_non_str_key_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    with pytest.raises(ValueError, match="key"):
        ledger.append_declaration({"cfg": {0: "x"}})
    with pytest.raises(ValueError, match="key"):
        ledger.append_seal({"ids": {1: "v"}})
    # Still usable (id counters may have advanced on failed attempts).
    did = ledger.append_declaration({"cfg": {"0": "x"}})
    assert did.startswith("d-")
    assert len(ledger.declarations()) == 1
    assert path.read_text(encoding="utf-8").count('"type":"declaration"') == 1


def test_str_key_nested_dicts_round_trip_chain(tmp_path: Path) -> None:
    """Control: nested str-key dicts still hash-verify across reopen."""
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(
        hid,
        {"nested": {"2": "x", "10": "y"}},
        {"p": {"a": 1}},
        _declared(),
    )
    ledger.record(
        tid,
        _series(),
        attestation=_attestation(extra={"u": {"k": 1}}),
    )
    ledger.append_declaration({"run_config": {"universe": "u1", "n": 2}})
    head = ledger.chain_head
    ledger2 = Ledger.open(path)
    assert ledger2.chain_head == head
    assert ledger2.trials()[0].spec == {"nested": {"2": "x", "10": "y"}}


# ---------------------------------------------------------------------------
# 2. attestation
# ---------------------------------------------------------------------------


def test_attestation_stored_and_replayed(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    att = _attestation()
    ledger.record(tid, _series(), attestation=att)

    rec = ledger.trials()[0]
    assert rec.attestation == att
    eval_evt = [e for e in _read_events(path) if e["type"] == "evaluation"][0]
    assert eval_evt["attestation"] == att

    ledger2 = Ledger.open(path)
    assert ledger2.trials()[0].attestation == att


def test_attestation_none_legal(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid, _series())  # no attestation
    assert ledger.trials()[0].attestation is None
    eval_evt = [e for e in _read_events(path) if e["type"] == "evaluation"][0]
    assert "attestation" not in eval_evt or eval_evt.get("attestation") is None
    ledger2 = Ledger.open(path)
    assert ledger2.trials()[0].attestation is None


def test_attestation_metric_mismatch_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared(metric="returns"))
    with pytest.raises(ValueError):
        ledger.record(tid, _series(), attestation=_attestation(metric="ic"))


def test_attestation_window_mismatch_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(
            tid,
            _series(),
            attestation=_attestation(window={"start": "2019-01-01", "end": "2019-12-31"}),
        )


def test_attestation_window_extra_keys_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(
            tid,
            _series(),
            attestation=_attestation(
                window={"start": "2020-01-01", "end": "2020-12-31", "extra": 1}
            ),
        )


def test_attestation_n_evaluation_dates_mismatch_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(tid, _series(), attestation=_attestation(n_evaluation_dates=99))


def test_attestation_missing_metric_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    att = _attestation()
    del att["metric"]
    with pytest.raises(ValueError):
        ledger.record(tid, _series(), attestation=att)


def test_attestation_missing_window_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    att = _attestation()
    del att["window"]
    with pytest.raises(ValueError):
        ledger.record(tid, _series(), attestation=att)


def test_attestation_non_serializable_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(
            tid,
            _series(),
            attestation=_attestation(bad=float("nan")),
        )
    with pytest.raises(ValueError):
        ledger.record(
            tid,
            _series(),
            attestation=_attestation(fn=lambda x: x),  # type: ignore[dict-item]
        )


def test_attestation_violation_on_replay_is_corruption(tmp_path: Path) -> None:
    """Hand-crafted evaluation with bad attestation → LedgerCorruptionError."""
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid, _series(), attestation=_attestation())

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    # Drop evaluation; append a hand-crafted bad one (no chain fields → rewrite as
    # a legacy-style tamper after truncating to pre-eval). For a chained ledger we
    # rebuild the evaluation line without valid hashes so open fails either on
    # chain or attestation — pin attestation path by rewriting full file legacy.
    events = [json.loads(ln) for ln in lines]
    # Build a legacy (hashless) file with bad attestation.
    legacy_events = []
    for e in events:
        if e["type"] == "evaluation":
            e = dict(e)
            e["attestation"] = _attestation(metric="ic")  # mismatch vs declared returns
        # strip hash fields to make a homogeneous legacy file
        e = {k: v for k, v in e.items() if k not in ("prev_hash", "event_hash")}
        legacy_events.append(e)
    path.write_text(
        "".join(
            json.dumps(e, allow_nan=False, separators=(",", ":")) + "\n" for e in legacy_events
        ),
        encoding="utf-8",
    )
    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


# ---------------------------------------------------------------------------
# 3. Hash chain
# ---------------------------------------------------------------------------


def test_fresh_ledger_events_carry_hashes_and_stable_chain_head(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    assert ledger.chain_head == "0" * 64

    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid, _series())

    events = _read_events(path)
    assert all("prev_hash" in e and "event_hash" in e for e in events)

    # Verify linkage from genesis.
    prev = "0" * 64
    for e in events:
        assert e["prev_hash"] == prev
        ch = _content_hash(e)
        eh = _event_hash(prev, ch)
        assert e["event_hash"] == eh
        prev = eh

    head = ledger.chain_head
    assert head == prev
    assert head is not None and len(head) == 64

    ledger2 = Ledger.open(path)
    assert ledger2.chain_head == head


def test_content_hash_determinism() -> None:
    """Same content twice → same content hash (canonical_json path)."""
    a = {
        "type": "hypothesis",
        "hypothesis_id": "h-000001",
        "statement": "x",
        "periods_per_year": 252.0,
        "nested": {"b": 1, "a": 2.5},
    }
    b = {
        "nested": {"a": 2.5, "b": 1},
        "periods_per_year": 252.0,
        "statement": "x",
        "hypothesis_id": "h-000001",
        "type": "hypothesis",
    }
    assert _content_hash(a) == _content_hash(b)


def test_tamper_midfile_content_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    ledger.register_hypothesis("claim")
    ledger.register_hypothesis("claim2")
    events = _read_events(path)
    # Edit first event statement without updating hashes.
    events[0]["statement"] = "TAMPERED"
    path.write_text(
        "".join(json.dumps(e, allow_nan=False, separators=(",", ":")) + "\n" for e in events),
        encoding="utf-8",
    )
    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_flip_type_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    ledger.register(hid, {}, {}, _declared())
    events = _read_events(path)
    # Flip trial → declaration without rehashing.
    for e in events:
        if e["type"] == "trial":
            e["type"] = "declaration"
            break
    path.write_text(
        "".join(json.dumps(e, allow_nan=False, separators=(",", ":")) + "\n" for e in events),
        encoding="utf-8",
    )
    # Must be the chain (type is in content), not a later schema crash.
    with pytest.raises(LedgerCorruptionError, match="event_hash mismatch"):
        Ledger.open(path)


def test_reorder_midfile_lines_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    ledger.register_hypothesis("a")
    ledger.register_hypothesis("b")
    ledger.register_hypothesis("c")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    # Swap first two mid-file relative order (indices 0 and 1).
    lines[0], lines[1] = lines[1], lines[0]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_delete_midfile_line_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    ledger.register_hypothesis("a")
    ledger.register_hypothesis("b")
    ledger.register_hypothesis("c")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    # Delete middle line; remaining lines keep old prev_hash links.
    del lines[1]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_suffix_truncation_passes_replay_honesty_boundary(tmp_path: Path) -> None:
    """Pre-seal suffix deletion is undetectable by design.

    docs/design/prereg-gate.md §6: deleting a whole suffix of intact lines
    is undetectable pre-seal; the chain only proves order-consistency of the
    surviving prefix. This test ASSERTS that such truncation PASSES replay.
    """
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    ledger.register_hypothesis("a")
    ledger.register_hypothesis("b")
    ledger.register_hypothesis("c")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    # Drop the final intact line (suffix truncation).
    path.write_text(lines[0] + "\n" + lines[1] + "\n", encoding="utf-8")
    # Must succeed — honesty boundary, not a bug.
    ledger2 = Ledger.open(path)
    assert len(ledger2.chain_head) == 64  # still chained
    # Only two hypotheses survive.
    assert ledger2.chain_head == json.loads(lines[1])["event_hash"]


def test_torn_final_line_truncates_and_next_append_links(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    head_before_torn = ledger.chain_head

    with path.open("a", encoding="utf-8") as f:
        f.write('{"type":"evaluation","at":"torn')

    ledger2 = Ledger.open(path)
    assert ledger2.chain_head == head_before_torn
    ledger2.record(tid, _series())
    events = _read_events(path)
    last = events[-1]
    assert last["type"] == "evaluation"
    assert last["prev_hash"] == head_before_torn
    assert last["event_hash"] == _event_hash(head_before_torn, _content_hash(last))
    assert ledger2.chain_head == last["event_hash"]


# ---------------------------------------------------------------------------
# 4. Legacy compatibility
# ---------------------------------------------------------------------------



def _make_legacy_copy(src: Path, dest: Path) -> None:
    """Synthesize a legacy (pre-v0.2, hashless) ledger file from a chained one.

    The committed killer-demo ledger became chained at the v0.2-08 regeneration,
    so legacy semantics are tested against a stripped copy (same events, no
    hash fields) — the on-disk shape every pre-v0.2 artifact had.
    """
    lines = src.read_text(encoding="utf-8").strip().splitlines()
    out = []
    for line in lines:
        evt = json.loads(line)
        evt.pop("prev_hash", None)
        evt.pop("event_hash", None)
        out.append(json.dumps(evt, allow_nan=False, separators=(",", ":")))
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")

def test_killer_demo_ledger_replays_chained(tmp_path: Path) -> None:
    """Copy of examples/killer_demo/out/ledger.jsonl replays WITH chain verification.

    Since the v0.2-08 regeneration the committed artifact is chained; opening it
    verifies the full hash chain and chain_head equals the last event_hash.
    (Legacy semantics are covered by the synthesized-fixture tests below.)
    """
    assert _KILLER_LEDGER.is_file(), f"missing committed killer ledger: {_KILLER_LEDGER}"
    dest = tmp_path / "ledger.jsonl"
    shutil.copy(_KILLER_LEDGER, dest)
    ledger = Ledger.open(dest)
    last = json.loads(dest.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert ledger.chain_head == last["event_hash"]
    assert len(ledger.trials()) > 0


def test_stripped_killer_demo_ledger_replays_legacy(tmp_path: Path) -> None:
    """The stripped (hashless) copy replays as legacy: chain_head is None."""
    dest = tmp_path / "ledger.jsonl"
    _make_legacy_copy(_KILLER_LEDGER, dest)
    ledger = Ledger.open(dest)
    assert ledger.chain_head is None
    assert len(ledger.trials()) > 0


def test_append_to_legacy_stays_hashless(tmp_path: Path) -> None:
    dest = tmp_path / "ledger.jsonl"
    _make_legacy_copy(_KILLER_LEDGER, dest)
    ledger = Ledger.open(dest)
    assert ledger.chain_head is None
    n_before = len(dest.read_text(encoding="utf-8").strip().splitlines())
    hid = ledger.register_hypothesis("extra claim after legacy open")
    assert hid.startswith("h-")
    lines = dest.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == n_before + 1
    new_evt = json.loads(lines[-1])
    assert "event_hash" not in new_evt
    assert "prev_hash" not in new_evt
    assert ledger.chain_head is None


def test_mixed_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    # First event hashless (legacy), second with hashes.
    e1 = {
        "type": "hypothesis",
        "at": "2020-01-01T00:00:00+00:00",
        "hypothesis_id": "h-000001",
        "statement": "a",
    }
    e2 = {
        "type": "hypothesis",
        "at": "2020-01-01T00:00:01+00:00",
        "hypothesis_id": "h-000002",
        "statement": "b",
        "prev_hash": "0" * 64,
        "event_hash": "a" * 64,
    }
    path.write_text(
        json.dumps(e1, separators=(",", ":"))
        + "\n"
        + json.dumps(e2, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_mixed_file_chained_then_hashless_raises(tmp_path: Path) -> None:
    """Reverse mixed direction: first event hashed, later event hashless."""
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    ledger.register_hypothesis("a")
    events = _read_events(path)
    assert "event_hash" in events[0]
    # Append a hashless second event by hand.
    e2 = {
        "type": "hypothesis",
        "at": "2020-01-01T00:00:01+00:00",
        "hypothesis_id": "h-000002",
        "statement": "b",
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(e2, separators=(",", ":")) + "\n")
    with pytest.raises(LedgerCorruptionError, match="mixed"):
        Ledger.open(path)


def test_empty_after_torn_truncation_is_chained(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text('{"type":"hypothesis","at":"torn', encoding="utf-8")
    ledger = Ledger.open(path)
    assert ledger.chain_head == "0" * 64
    ledger.register_hypothesis("after empty")
    events = _read_events(path)
    assert len(events) == 1
    assert "event_hash" in events[0]


# ---------------------------------------------------------------------------
# 5. declaration / seal
# ---------------------------------------------------------------------------


def test_declaration_and_seal_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    did = ledger.append_declaration({"run_config": {"universe": "u1"}, "n": 1})
    assert did == "d-000001"
    decls = ledger.declarations()
    assert len(decls) == 1
    assert isinstance(decls[0], DeclarationRecord)
    assert decls[0].declaration_id == did
    assert decls[0].payload == {"run_config": {"universe": "u1"}, "n": 1}
    assert decls[0].created_at

    sid = ledger.append_seal({"chain_head_pin": "x", "verdict_ids": []})
    assert sid == "s-000001"
    seal = ledger.seal()
    assert isinstance(seal, SealRecord)
    assert seal is not None
    assert seal.seal_id == sid
    assert seal.payload == {"chain_head_pin": "x", "verdict_ids": []}

    ledger2 = Ledger.open(path)
    assert len(ledger2.declarations()) == 1
    assert ledger2.declarations()[0].payload == {"run_config": {"universe": "u1"}, "n": 1}
    assert ledger2.seal() is not None
    assert ledger2.seal().seal_id == sid


def test_second_seal_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    ledger.append_seal({"ok": True})
    with pytest.raises(ValueError):
        ledger.append_seal({"again": True})


def test_mutating_appends_after_seal_raise(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid, _series())
    ledger.append_declaration({"cfg": 1})
    ledger.append_seal({"done": True})

    with pytest.raises(ValueError):
        ledger.register_hypothesis("after")
    with pytest.raises(ValueError):
        ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        # need unevaluated trial for record — use bogus id; seal check first
        ledger.record("t-000099", _series())
    with pytest.raises(ValueError):
        ledger.append_verdict("dsr", [tid], {}, {}, {tid: "pass"})
    with pytest.raises(ValueError):
        ledger.append_declaration({"x": 1})
    with pytest.raises(ValueError):
        ledger.append_seal({"x": 1})


def test_event_after_seal_on_open_raises(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    ledger.append_declaration({"a": 1})
    ledger.append_seal({"s": 1})
    head = ledger.chain_head
    assert head is not None

    # Hand-craft a post-seal event with valid chain linkage so only seal-final
    # rule fires (not hash mismatch).
    content = {
        "type": "declaration",
        "declaration_id": "d-000002",
        "payload": {"after": True},
    }
    ch = _content_hash(content)
    eh = _event_hash(head, ch)
    post = {
        "type": "declaration",
        "at": "2020-01-01T00:00:00+00:00",
        "declaration_id": "d-000002",
        "payload": {"after": True},
        "prev_hash": head,
        "event_hash": eh,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(post, allow_nan=False, separators=(",", ":")) + "\n")

    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_torn_tail_after_seal_truncates_not_corruption(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    sid = ledger.append_seal({"s": 1})
    with path.open("a", encoding="utf-8") as f:
        f.write('{"type":"declaration","at":"torn')
    ledger2 = Ledger.open(path)
    assert ledger2.seal() is not None
    assert ledger2.seal().seal_id == sid


def test_declaration_non_serializable_raises(tmp_path: Path) -> None:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    with pytest.raises(ValueError):
        ledger.append_declaration({"x": float("nan")})
    with pytest.raises(ValueError):
        ledger.append_seal({"x": object()})


def test_declaration_seal_work_on_legacy(tmp_path: Path) -> None:
    dest = tmp_path / "ledger.jsonl"
    _make_legacy_copy(_KILLER_LEDGER, dest)
    ledger = Ledger.open(dest)
    did = ledger.append_declaration({"note": "legacy"})
    assert did == "d-000001"
    # seal closes the file
    sid = ledger.append_seal({"legacy_seal": True})
    assert sid == "s-000001"
    events = _read_events(dest)
    last_two = events[-2:]
    for e in last_two:
        assert "event_hash" not in e
    ledger2 = Ledger.open(dest)
    assert ledger2.chain_head is None
    assert ledger2.declarations()[-1].declaration_id == did
    assert ledger2.seal() is not None
