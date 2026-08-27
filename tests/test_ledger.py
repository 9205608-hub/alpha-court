"""Behavioral tests for court/ledger.py (ticket v0.1-08a).

Maps to court-kernel-spec.md §7 (test_ledger.py rows) and §5.7 fail-closed table;
semantics from trial-ledger.md §5–7.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from court.ledger import (
    DeclaredProtocol,
    Ledger,
    LedgerCorruptionError,
    SeConvention,
    Series,
    Window,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


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


def _open_fresh(tmp_path: Path) -> Ledger:
    return Ledger.open(tmp_path / "ledger.jsonl")


def _register_evaluated(
    ledger: Ledger,
    *,
    statement: str = "claim",
    series: Series | None = None,
) -> tuple[str, str]:
    hid = ledger.register_hypothesis(statement)
    tid = ledger.register(hid, {"kind": "momentum"}, {"lookback": 5}, _declared())
    ledger.record(tid, series if series is not None else _series())
    return hid, tid


# ---------------------------------------------------------------------------
# Happy path / status derivation / series by value
# ---------------------------------------------------------------------------


def test_register_record_append_verdict_happy_path(tmp_path: Path) -> None:
    """register → record → append_verdict; ids sequential; records intact."""
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("momentum works")
    assert hid == "h-000001"

    tid = ledger.register(
        hid,
        {"construction": "mom"},
        {"lookback": 20},
        _declared(metric="ic", direction="greater"),
    )
    assert tid == "t-000001"
    assert ledger.status(tid) == "registered"

    s = _series()
    ledger.record(tid, s)
    assert ledger.status(tid) == "evaluated"

    got = ledger.series(tid)
    assert got.index == s.index
    assert got.values == s.values

    trials = ledger.trials()
    assert len(trials) == 1
    assert trials[0].trial_id == tid
    assert trials[0].hypothesis_id == hid
    assert trials[0].series == s
    assert trials[0].evaluated_at is not None
    # No derived statistics on the trial record (contract §5.2).
    assert not hasattr(trials[0], "sharpe")
    assert not hasattr(trials[0], "p_value")

    vid = ledger.append_verdict(
        statistic="dsr",
        scope=[tid],
        params={"confidence": 0.95},
        computed={"sr_star": 0.1},
        decisions={tid: "reject"},
        engine_version="0.1.0.dev0",
    )
    assert vid == "v-000001"
    assert ledger.status(tid) == "judged"

    verdicts = ledger.verdicts()
    assert len(verdicts) == 1
    assert verdicts[0].verdict_id == vid
    assert verdicts[0].decisions[tid] == "reject"
    assert verdicts[0].engine_version == "0.1.0.dev0"


def test_status_only_three_states_no_abandoned(tmp_path: Path) -> None:
    """Status is only registered | evaluated | judged (no abandoned)."""
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("x")
    tid = ledger.register(hid, {}, {}, _declared())
    assert ledger.status(tid) == "registered"
    ledger.record(tid, _series())
    assert ledger.status(tid) == "evaluated"
    ledger.append_verdict("noise_control", [tid], {}, {}, {tid: "pass"})
    assert ledger.status(tid) == "judged"
    # Unevaluated second trial stays registered forever — file-drawer datum.
    tid2 = ledger.register(hid, {"a": 1}, {}, _declared())
    assert ledger.status(tid2) == "registered"


def test_series_stored_by_value_returned_intact(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    _, tid = _register_evaluated(
        ledger,
        series=_series(["a", "b"], [1.5, -2.5]),
    )
    got = ledger.series(tid)
    assert got == Series(index=("a", "b"), values=(1.5, -2.5))
    # Mutating caller-side lists must not affect stored record (by-value).
    labels = ["x", "y"]
    vals = [0.1, 0.2]
    s = Series(index=tuple(labels), values=tuple(vals))
    hid = ledger.register_hypothesis("y")
    tid2 = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid2, s)
    assert ledger.series(tid2).index == ("x", "y")


# ---------------------------------------------------------------------------
# Physical line order
# ---------------------------------------------------------------------------


def test_trial_line_precedes_evaluation_line(tmp_path: Path) -> None:
    """Physical registration-before-evaluation (trial-ledger.md §6 invariant 2)."""
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {"k": 1}, {"p": 2}, _declared())
    ledger.record(tid, _series())

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    types = [json.loads(line)["type"] for line in lines]
    assert types == ["hypothesis", "trial", "evaluation"]
    trial_idx = types.index("trial")
    eval_idx = types.index("evaluation")
    assert trial_idx < eval_idx
    assert json.loads(lines[eval_idx])["trial_id"] == tid


# ---------------------------------------------------------------------------
# matrix alignment
# ---------------------------------------------------------------------------


def test_matrix_label_for_label_and_column_order(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    labels = ["t0", "t1", "t2"]
    _, tid1 = _register_evaluated(ledger, series=_series(labels, [0.1, 0.2, 0.3]))
    _, tid2 = _register_evaluated(ledger, series=_series(labels, [0.4, 0.5, 0.6]))

    index, mat = ledger.matrix([tid2, tid1])  # reverse argument order
    assert index == tuple(labels)
    assert mat.dtype == np.float64
    assert mat.shape == (3, 2)
    np.testing.assert_array_equal(mat[:, 0], [0.4, 0.5, 0.6])
    np.testing.assert_array_equal(mat[:, 1], [0.1, 0.2, 0.3])


def test_matrix_misaligned_index_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    _, tid1 = _register_evaluated(ledger, series=_series(["a", "b"], [0.1, 0.2]))
    _, tid2 = _register_evaluated(ledger, series=_series(["a", "c"], [0.3, 0.4]))
    with pytest.raises(ValueError):
        ledger.matrix([tid1, tid2])


def test_matrix_unknown_or_unevaluated_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.matrix([tid])  # registered but not evaluated
    with pytest.raises(ValueError):
        ledger.matrix(["t-999999"])


# ---------------------------------------------------------------------------
# Fail-closed: register
# ---------------------------------------------------------------------------


def test_register_unknown_hypothesis_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    with pytest.raises(ValueError):
        ledger.register("h-000099", {}, {}, _declared())


def test_register_malformed_declared_protocol(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("c")

    with pytest.raises(ValueError):
        ledger.register(hid, {}, {}, _declared(metric="sharpe"))

    with pytest.raises(ValueError):
        ledger.register(hid, {}, {}, _declared(direction="both"))

    with pytest.raises(ValueError):
        ledger.register(
            hid,
            {},
            {},
            _declared(se=SeConvention(kind="newey_west", lags=None)),
        )

    with pytest.raises(ValueError):
        ledger.register(
            hid,
            {},
            {},
            _declared(se=SeConvention(kind="newey_west", lags=-1)),
        )

    with pytest.raises(ValueError):
        ledger.register(
            hid,
            {},
            {},
            _declared(se=SeConvention(kind="iid", lags=3)),
        )

    with pytest.raises(ValueError):
        ledger.register(hid, {}, {}, _declared(periods_per_year=0.0))

    with pytest.raises(ValueError):
        ledger.register(hid, {}, {}, _declared(periods_per_year=-1.0))

    with pytest.raises(ValueError):
        ledger.register(
            hid,
            {},
            {},
            _declared(se=SeConvention(kind="hac", lags=1)),
        )


def test_register_non_json_serializable_spec_params(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("c")
    with pytest.raises(ValueError):
        ledger.register(hid, {"fn": lambda x: x}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.register(hid, {}, {"x": float("nan")}, _declared())
    with pytest.raises(ValueError):
        ledger.register(hid, {}, {"obj": object()}, _declared())


# ---------------------------------------------------------------------------
# Fail-closed: record
# ---------------------------------------------------------------------------


def test_record_unknown_trial_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    with pytest.raises(ValueError):
        ledger.record("t-000099", _series())


def test_record_duplicate_evaluation_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    _, tid = _register_evaluated(ledger)
    with pytest.raises(ValueError):
        ledger.record(tid, _series())


def test_record_length_mismatch_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(tid, Series(index=("a", "b"), values=(1.0,)))


def test_record_empty_series_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(tid, Series(index=(), values=()))


def test_record_duplicate_index_labels_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(tid, Series(index=("a", "a"), values=(1.0, 2.0)))


def test_record_non_finite_values_raises(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(tid, Series(index=("a",), values=(float("nan"),)))
    tid2 = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(tid2, Series(index=("a",), values=(float("inf"),)))
    tid3 = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.record(tid3, Series(index=("a",), values=(float("-inf"),)))


# ---------------------------------------------------------------------------
# Fail-closed: append_verdict / series / status
# ---------------------------------------------------------------------------


def test_append_verdict_unknown_ids_and_bad_decisions(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    _, tid = _register_evaluated(ledger)

    with pytest.raises(ValueError):
        ledger.append_verdict("dsr", ["t-999999"], {}, {}, {"t-999999": "pass"})

    with pytest.raises(ValueError):
        ledger.append_verdict("dsr", [tid], {}, {}, {tid: "maybe"})

    with pytest.raises(ValueError):
        ledger.append_verdict("dsr", [tid], {}, {}, {"t-999999": "pass"})

    with pytest.raises(ValueError):
        ledger.append_verdict("", [tid], {}, {}, {tid: "pass"})

    with pytest.raises(ValueError):
        ledger.append_verdict("dsr", [], {}, {}, {})

    with pytest.raises(ValueError):
        ledger.append_verdict("dsr", [tid], {"x": object()}, {}, {tid: "pass"})

    with pytest.raises(ValueError):
        ledger.append_verdict("dsr", [tid], {}, {"y": float("nan")}, {tid: "pass"})


def test_series_and_status_unknown_or_unevaluated(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    with pytest.raises(ValueError):
        ledger.series("t-000099")
    with pytest.raises(ValueError):
        ledger.status("t-000099")

    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    with pytest.raises(ValueError):
        ledger.series(tid)  # not yet evaluated


def test_trials_scope_and_verdicts_filter(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    _, tid1 = _register_evaluated(ledger)
    _, tid2 = _register_evaluated(ledger)
    ledger.append_verdict("dsr", [tid1], {}, {}, {tid1: "pass"})
    ledger.append_verdict("pbo_cscv", [tid1, tid2], {}, {}, {tid2: "reject"})

    scoped = ledger.trials(scope=[tid2])
    assert [t.trial_id for t in scoped] == [tid2]

    all_v = ledger.verdicts()
    assert len(all_v) == 2
    only1 = ledger.verdicts(trial_id=tid1)
    assert len(only1) == 2  # both verdicts mention tid1 in scope
    only2 = ledger.verdicts(trial_id=tid2)
    assert len(only2) == 1
    assert only2[0].statistic == "pbo_cscv"


# ---------------------------------------------------------------------------
# Persistence / replay
# ---------------------------------------------------------------------------


def test_close_reopen_replays_equal_records(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("persist me")
    tid = ledger.register(
        hid,
        {"k": "v"},
        {"n": 3},
        _declared(metric="ic", direction="less", se=SeConvention(kind="newey_west", lags=2)),
    )
    s = _series(["p1", "p2"], [0.05, -0.01])
    ledger.record(tid, s)
    vid = ledger.append_verdict(
        "fdr_by",
        [tid],
        {"q": 0.05},
        {"k_star": 0},
        {tid: "reject"},
        engine_version="0.1.0.dev0",
    )
    trials_before = ledger.trials()
    verdicts_before = ledger.verdicts()
    status_before = ledger.status(tid)

    ledger2 = Ledger.open(path)
    assert ledger2.trials() == trials_before
    assert ledger2.verdicts() == verdicts_before
    assert ledger2.status(tid) == status_before
    assert ledger2.series(tid) == s
    assert ledger2.verdicts()[0].verdict_id == vid


def test_torn_final_line_discarded_and_next_append_works(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid, _series())

    # Append a torn (unparseable) final line.
    with path.open("a", encoding="utf-8") as f:
        f.write('{"type": "verdict", "at": "torn')  # incomplete JSON

    ledger2 = Ledger.open(path)
    # Torn line discarded; prior records intact.
    assert len(ledger2.trials()) == 1
    assert ledger2.status(tid) == "evaluated"
    # Next append works.
    vid = ledger2.append_verdict("dsr", [tid], {}, {}, {tid: "pass"})
    assert vid == "v-000001"
    text = path.read_text(encoding="utf-8")
    assert "torn" not in text
    for line in text.strip().splitlines():
        json.loads(line)  # every remaining line is valid JSON


def test_midfile_corruption_raises_ledger_corruption_error(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    ledger.register_hypothesis("c")
    good = path.read_text(encoding="utf-8")
    # Insert unparseable line in the middle, then a valid-looking trailing line.
    path.write_text(good + "NOT JSON\n" + good, encoding="utf-8")
    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_duplicate_evaluation_on_replay_raises_corruption(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("c")
    tid = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid, _series())

    # Manually append a second evaluation event for the same trial.
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    eval_line = [ln for ln in lines if json.loads(ln)["type"] == "evaluation"][0]
    with path.open("a", encoding="utf-8") as f:
        f.write(eval_line + "\n")

    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_unknown_reference_on_replay_raises_corruption(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    Ledger.open(path)  # create empty file
    # Trial event referencing a non-existent hypothesis.
    event = {
        "type": "trial",
        "at": "2020-01-01T00:00:00+00:00",
        "trial_id": "t-000001",
        "hypothesis_id": "h-000099",
        "spec": {},
        "params": {},
        "declared": {
            "metric": "returns",
            "window": {"start": "a", "end": "b"},
            "periods_per_year": 252.0,
            "direction": "two-sided",
            "se": {"kind": "iid", "lags": None},
        },
        "source_ref": None,
    }
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(LedgerCorruptionError):
        Ledger.open(path)


def test_sequential_ids_across_types(tmp_path: Path) -> None:
    ledger = _open_fresh(tmp_path)
    assert ledger.register_hypothesis("a") == "h-000001"
    assert ledger.register_hypothesis("b") == "h-000002"
    hid = "h-000001"
    assert ledger.register(hid, {}, {}, _declared()) == "t-000001"
    assert ledger.register(hid, {}, {}, _declared()) == "t-000002"


# ---------------------------------------------------------------------------
# v0.2-12 slice A: byte-exact torn-line recovery
# ---------------------------------------------------------------------------


def _legacy_hypothesis_line(statement: str, *, ensure_ascii: bool = True) -> str:
    event = {
        "type": "hypothesis",
        "at": "2020-01-01T00:00:00+00:00",
        "hypothesis_id": "h-000001",
        "statement": statement,
    }
    return json.dumps(event, ensure_ascii=ensure_ascii) + "\n"


def test_torn_recovery_byte_exact_with_non_ascii_intact_line(tmp_path: Path) -> None:
    """A raw non-ASCII byte in an INTACT line must not skew the truncate offset.

    Character-counted spans undercount multi-byte UTF-8; a torn-final-line
    truncate must remove EXACTLY the torn tail, never bytes of intact data.
    """
    path = tmp_path / "ledger.jsonl"
    intact = _legacy_hypothesis_line("ππππππ non-ascii", ensure_ascii=False)
    intact_bytes = intact.encode("utf-8")
    torn = b'{"type": "hypothesis", "at": "torn'
    path.write_bytes(intact_bytes + torn)

    ledger = Ledger.open(path)
    # The intact event survived replay...
    assert ledger.register("h-000001", {}, {}, _declared()) == "t-000001"
    # ...and the file was truncated to EXACTLY the intact prefix.
    reread = Path(str(path)).read_bytes()
    assert reread.startswith(intact_bytes[: len(intact_bytes) - 1])
    assert reread[: len(intact_bytes)] == intact_bytes


def test_torn_multibyte_tail_recovers_instead_of_crashing(tmp_path: Path) -> None:
    """A torn write that cuts a UTF-8 sequence in half must be recoverable.

    Decoding the whole file up front raises UnicodeDecodeError before recovery
    can run; byte-exact recovery treats the undecodable final line as torn.
    """
    path = tmp_path / "ledger.jsonl"
    intact = _legacy_hypothesis_line("clean")
    torn = b'{"type": "hypothesis", "at": "x' + "π".encode()[:1]
    path.write_bytes(intact.encode("utf-8") + torn)

    ledger = Ledger.open(path)
    assert path.read_bytes() == intact.encode("utf-8")
    assert ledger.register("h-000001", {}, {}, _declared()) == "t-000001"


def test_storage_lines_are_pure_ascii(tmp_path: Path) -> None:
    """Pin the ensure_ascii=True storage invariant recovery silently relied on."""
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("π-statement")
    raw = path.read_bytes()
    assert all(b < 128 for b in raw), "storage lines must be pure ASCII"
    assert b"\\u03c0" in raw  # the non-ASCII char is escaped, not raw
    # Replay round-trips.
    ledger2 = Ledger.open(path)
    assert ledger2.register(hid, {}, {}, _declared()) == "t-000001"


# ---------------------------------------------------------------------------
# v0.2-12 slice B: replay/write validation symmetry
# ---------------------------------------------------------------------------


def _legacy_events_prefix() -> list[dict]:
    """Hypothesis + trial as raw legacy (unchained) events, valid literals."""
    return [
        {
            "type": "hypothesis",
            "at": "2020-01-01T00:00:00+00:00",
            "hypothesis_id": "h-000001",
            "statement": "c",
        },
        {
            "type": "trial",
            "at": "2020-01-01T00:00:01+00:00",
            "trial_id": "t-000001",
            "hypothesis_id": "h-000001",
            "spec": {},
            "params": {},
            "declared": {
                "metric": "returns",
                "window": {"start": "2020-01-01", "end": "2020-12-31"},
                "periods_per_year": 252.0,
                "direction": "two-sided",
                "se": {"kind": "iid", "lags": None},
            },
            "source_ref": None,
        },
    ]


def _write_legacy(path: Path, events: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
    )


def _legacy_verdict(**overrides) -> dict:
    event = {
        "type": "verdict",
        "at": "2020-01-01T00:00:02+00:00",
        "verdict_id": "v-000001",
        "statistic": "dsr",
        "scope": ["t-000001"],
        "params": {},
        "computed": {},
        "decisions": {"t-000001": "pass"},
        "engine_version": None,
    }
    event.update(overrides)
    return event


def test_replay_rejects_invalid_declared_metric(tmp_path: Path) -> None:
    """Replay must run the same declared-literal validation as the write path."""
    path = tmp_path / "ledger.jsonl"
    events = _legacy_events_prefix()
    events[1]["declared"]["metric"] = "banana"
    _write_legacy(path, events)
    with pytest.raises(LedgerCorruptionError, match="banana"):
        Ledger.open(path)


def test_replay_rejects_invalid_decision_value(tmp_path: Path) -> None:
    """Write path enforces decisions in {'pass','reject'}; replay must too."""
    path = tmp_path / "ledger.jsonl"
    events = [*_legacy_events_prefix(), _legacy_verdict(decisions={"t-000001": "maybe"})]
    _write_legacy(path, events)
    with pytest.raises(LedgerCorruptionError, match="maybe"):
        Ledger.open(path)


def test_replay_rejects_invalid_role(tmp_path: Path) -> None:
    """Write path enforces the role domain; replay must not accept garbage."""
    path = tmp_path / "ledger.jsonl"
    events = [*_legacy_events_prefix(), _legacy_verdict(role="banana")]
    _write_legacy(path, events)
    with pytest.raises(LedgerCorruptionError, match="role"):
        Ledger.open(path)


def test_append_verdict_rejects_decision_outside_scope(tmp_path: Path) -> None:
    """decisions ⊆ scope, enforced BEFORE anything durable is written."""
    path = tmp_path / "ledger.jsonl"
    ledger = Ledger.open(path)
    hid = ledger.register_hypothesis("c")
    t1 = ledger.register(hid, {}, {}, _declared())
    t2 = ledger.register(hid, {}, {}, _declared())
    ledger.record(t1, _series())
    ledger.record(t2, _series())
    before = path.read_bytes()
    with pytest.raises(ValueError, match="scope"):
        ledger.append_verdict("dsr", [t1], {}, {}, {t2: "pass"})
    assert path.read_bytes() == before, "nothing may hit disk on validation failure"


def test_replay_rejects_decision_outside_scope(tmp_path: Path) -> None:
    """Replay side of the decisions ⊆ scope invariant (fail-closed symmetric)."""
    path = tmp_path / "ledger.jsonl"
    events = _legacy_events_prefix()
    events.append(
        {
            "type": "trial",
            "at": "2020-01-01T00:00:01+00:00",
            "trial_id": "t-000002",
            "hypothesis_id": "h-000001",
            "spec": {},
            "params": {},
            "declared": events[1]["declared"],
            "source_ref": None,
        }
    )
    events.append(_legacy_verdict(scope=["t-000001"], decisions={"t-000002": "pass"}))
    _write_legacy(path, events)
    with pytest.raises(LedgerCorruptionError, match="scope"):
        Ledger.open(path)


# ---------------------------------------------------------------------------
# v0.2-12 slice D: parent-directory fsync on create
# ---------------------------------------------------------------------------


def test_create_fsyncs_parent_directory(tmp_path: Path, monkeypatch) -> None:
    """The create path must fsync the parent dir, or the directory entry (and
    the "registration timestamp durable on disk" promise, §7.1) can be lost."""
    import os as _os
    import stat as _stat

    import court.ledger as ledger_mod

    dir_syncs: list[int] = []
    real_fsync = _os.fsync

    def spy(fd: int) -> None:
        if _stat.S_ISDIR(_os.fstat(fd).st_mode):
            dir_syncs.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(ledger_mod.os, "fsync", spy)
    Ledger.open(tmp_path / "sub" / "ledger.jsonl")
    assert dir_syncs, "creating the ledger file never fsynced its parent directory"


# ---------------------------------------------------------------------------
# v0.2-12 RP-1 remediation: series + verdict-emptiness replay symmetry
# (grok RP-1 findings 0/1 on 610f9f82 — probes B5-B13 reproduced by referee)
# ---------------------------------------------------------------------------


def _legacy_evaluation(series: dict) -> dict:
    return {
        "type": "evaluation",
        "at": "2020-01-01T00:00:02+00:00",
        "trial_id": "t-000001",
        "series": series,
    }


@pytest.mark.parametrize(
    "series",
    [
        {"index": ["d1", "d2"], "values": [1.0]},  # length mismatch
        {"index": [], "values": []},  # empty
        {"index": ["d1"], "values": [float("nan")]},  # non-finite
        {"index": ["d1", "d1"], "values": [1.0, 2.0]},  # duplicate labels
    ],
    ids=["len-mismatch", "empty", "nan", "dup-labels"],
)
def test_replay_rejects_invalid_series(tmp_path: Path, series: dict) -> None:
    """record() runs _validate_series; replay must run the same validator."""
    path = tmp_path / "ledger.jsonl"
    _write_legacy(path, [*_legacy_events_prefix(), _legacy_evaluation(series)])
    with pytest.raises(LedgerCorruptionError, match="series"):
        Ledger.open(path)


def test_replay_rejects_empty_verdict_scope(tmp_path: Path) -> None:
    """append_verdict rejects empty scope; replay must too."""
    path = tmp_path / "ledger.jsonl"
    events = [
        *_legacy_events_prefix(),
        _legacy_evaluation({"index": ["d1"], "values": [1.0]}),
        _legacy_verdict(scope=[], decisions={}),
    ]
    _write_legacy(path, events)
    with pytest.raises(LedgerCorruptionError, match="scope"):
        Ledger.open(path)


def test_replay_rejects_empty_verdict_statistic(tmp_path: Path) -> None:
    """append_verdict rejects empty statistic; replay must too."""
    path = tmp_path / "ledger.jsonl"
    events = [
        *_legacy_events_prefix(),
        _legacy_evaluation({"index": ["d1"], "values": [1.0]}),
        _legacy_verdict(statistic=""),
    ]
    _write_legacy(path, events)
    with pytest.raises(LedgerCorruptionError, match="statistic"):
        Ledger.open(path)
