"""Bypass red-tests for the CONFIRM-time budget gate (`harness/confirm_gate.py`).

Written BEFORE the implementation (CR-08). The bypass set was enumerated by a 3-lens
workflow focused on the project's recurring **fail-open-on-degenerate-input** bug class
(trial_counter once PASSed on an empty ledger; the anti-pattern gate's own examples/ made
its self-scan always fail). The lens found a catastrophic one: `json.loads` accepts the
`NaN` token by default, and `NaN < actual` / `NaN > 0` are both False, so an un-validated
gate certifies ANY N against a 100-trial ledger.

Every degenerate / malformed / dishonest prereg MUST be refused (fail-closed); only a
verified-honest prereg passes. `test_*_limit` cases pin what the gate inherits from
trial_counter and cannot catch.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness import confirm_gate as cg
from harness import trial_counter as tc


def _session(d: Path, n: int) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        tc.record_trial(d, {"i": i})
    return d


def _prereg(tmp: Path, content, name: str = "prereg.json") -> Path:
    p = tmp / name
    p.write_text(content if isinstance(content, str) else json.dumps(content))
    return p


def _ok(prereg_path) -> bool:
    return cg.check_prereg(prereg_path).ok


# ---------- honest preregs: MUST pass ----------

def test_honest_prereg_passes(tmp_path: Path):
    s = _session(tmp_path / "s", 12)
    assert _ok(_prereg(tmp_path, {"reported_n": 12, "session_dir": str(s)}))


def test_over_declaring_is_allowed(tmp_path: Path):
    s = _session(tmp_path / "s", 40)
    assert _ok(_prereg(tmp_path, {"reported_n": 100, "session_dir": str(s)}))


# ---------- reported_n degenerate: MUST refuse (session has 1 real trial, so a >=1
# numeric-degenerate value would pass reconcile unless validated) ----------

def test_reported_n_degenerate_all_refused(tmp_path: Path):
    sd = json.dumps(str(_session(tmp_path / "s", 1)))

    def _pr(n_literal: str) -> str:  # a raw prereg JSON with the given reported_n literal
        return '{"reported_n": ' + n_literal + ', "session_dir": ' + sd + "}"

    cases = {
        "NaN": _pr("NaN"),
        "Infinity": _pr("Infinity"),
        "float": _pr("5.7"),
        "bool_true": _pr("true"),
        "numeric_string": _pr('"5"'),
        "null": _pr("null"),
        "negative": _pr("-5"),
        "container": _pr("[5]"),
        "zero": _pr("0"),
        "missing_key": '{"session_dir": ' + sd + "}",
    }
    leaked = [name for name, txt in cases.items() if _ok(_prereg(tmp_path, txt, "p.json"))]
    assert not leaked, f"fail-open on degenerate reported_n: {leaked}"


# ---------- session_dir degenerate: MUST refuse ----------

def test_session_dir_degenerate_all_refused(tmp_path: Path):
    a_file = tmp_path / "afile"
    a_file.write_text("x")
    cases = {
        "missing_key": {"reported_n": 5},
        "empty_string": {"reported_n": 5, "session_dir": ""},
        "nonexistent": {"reported_n": 5, "session_dir": str(tmp_path / "nope")},
        "is_a_file": {"reported_n": 5, "session_dir": str(a_file)},
        "null": {"reported_n": 5, "session_dir": None},
    }
    leaked = [name for name, obj in cases.items() if _ok(_prereg(tmp_path, obj, "p.json"))]
    assert not leaked, f"fail-open on degenerate session_dir: {leaked}"


# ---------- prereg-file degenerate: MUST refuse ----------

def test_prereg_file_degenerate_all_refused(tmp_path: Path):
    (tmp_path / "empty.json").write_text("")
    (tmp_path / "bad.json").write_text("{not json,,,")
    (tmp_path / "array.json").write_text("[1, 2, 3]")
    (tmp_path / "adir").mkdir()
    assert not _ok(tmp_path / "empty.json")
    assert not _ok(tmp_path / "bad.json")
    assert not _ok(tmp_path / "array.json")
    assert not _ok(tmp_path / "adir")
    assert not _ok(tmp_path / "does-not-exist.json")


# ---------- the real dishonest cases the gate exists to catch ----------

def test_relative_session_dir_refused(tmp_path: Path, monkeypatch):
    """A relative session_dir is cwd-dependent (could read the wrong ledger) — require absolute."""
    _session(tmp_path / "s", 4)
    monkeypatch.chdir(tmp_path)
    assert not _ok(_prereg(tmp_path, {"reported_n": 4, "session_dir": "s"}))


def test_non_pathlike_prereg_refused():
    """The API boundary must fail-closed (refuse), not TypeError, on a non-path argument."""
    for bad in (None, 123, ["x"]):
        assert cg.check_prereg(bad).ok is False


def test_under_reporting_refused(tmp_path: Path):
    s = _session(tmp_path / "s", 40)
    assert not _ok(_prereg(tmp_path, {"reported_n": 12, "session_dir": str(s)}))


def test_phantom_n_empty_ledger_refused(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()  # existing dir, no ledger
    assert not _ok(_prereg(tmp_path, {"reported_n": 12, "session_dir": str(empty)}))


def test_corrupt_ledger_fails_closed_not_open(tmp_path: Path):
    s = tmp_path / "s"
    s.mkdir()
    (s / tc.COUNT_FILE_NAME).write_text('{"fork": {}, "arms": 2.9}\n')  # corrupt line
    r = cg.check_prereg(_prereg(tmp_path, {"reported_n": 5, "session_dir": str(s)}))
    assert r.ok is False  # a TrialCountError must REFUSE, never be swallowed as a pass


# ---------- inherited trial_counter limits (pinned: these PASS but are dishonest) ----------

def test_winner_only_recording_is_an_inherited_limit(tmp_path: Path):
    """Recording only the winner (not the 39 abandoned forks) understates N — the gate
    can only see the ledger (trial_counter's NIH-invisible limit), so this passes."""
    s = _session(tmp_path / "s", 1)  # only the winner recorded
    assert _ok(_prereg(tmp_path, {"reported_n": 1, "session_dir": str(s)}))
