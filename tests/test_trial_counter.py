"""Bypass red-tests for the 工位二 trial-count reconciliation gate.

Written BEFORE the implementation (CR-08: write the bypass red-test first). Each
``test_bypass_*`` encodes a way the gate could be evaded; a naive or absent gate
fails them. In particular ``test_bypass_kernel_restart_accumulates`` **cannot** be
passed by an in-memory counter — it runs the second batch in a fresh subprocess,
so only a file-backed count survives (the exact "where does the counter live"
problem that kept this tooth [DESIGNED]).

The ``test_honest_limit_*`` cases pin what the gate deliberately does NOT do, so
the limits can't be silently forgotten.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from harness import trial_counter as tc


def _fork(i: int) -> dict:
    return {"horizon": f"{i}d", "universe": "csi300"}


def test_reconcile_pass_when_honest(tmp_path: Path) -> None:
    """Happy path (the one I over-rely on): honest N within budget -> ok."""
    for i in range(10):
        tc.record_trial(tmp_path, _fork(i))
    r = tc.reconcile(tmp_path, declared_k=12, reported_n=10)
    assert r.actual == 10
    assert r.ok is True
    assert r.over_budget is False and r.under_reported is False


def test_bypass_underreport_flagged(tmp_path: Path) -> None:
    """B1 (the core bypass): ran 40, declared/reported 12 -> must flag both."""
    for i in range(40):
        tc.record_trial(tmp_path, _fork(i))
    r = tc.reconcile(tmp_path, declared_k=12, reported_n=12)
    assert r.actual == 40
    assert r.over_budget is True
    assert r.under_reported is True
    assert r.ok is False


def test_bypass_kernel_restart_accumulates(tmp_path: Path) -> None:
    """B2 (the discriminating bypass): a kernel restart must NOT reset the count.

    Batch 1 runs in-process; batch 2 runs in a FRESH subprocess. An in-memory
    counter reports only one batch's 20 (a dead process's memory is gone) — never
    40. Only a file-backed count survives the restart.
    """
    for i in range(20):
        tc.record_trial(tmp_path, _fork(i))

    pkg_parent = Path(tc.__file__).resolve().parents[1]
    code = (
        "from harness import trial_counter as tc\n"
        "import pathlib\n"
        f"d = pathlib.Path({str(tmp_path)!r})\n"
        "for i in range(20, 40):\n"
        "    tc.record_trial(d, {'horizon': f'{i}d', 'universe': 'csi300'})\n"
    )
    env = {**os.environ, "PYTHONPATH": str(pkg_parent)}
    res = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr

    assert tc.count_trials(tmp_path) == 40, "count must survive a kernel restart"
    r = tc.reconcile(tmp_path, declared_k=12, reported_n=20)
    assert r.under_reported is True  # you said 20 but 40 ran across the restart


def test_honest_limit_signflip_is_lower_bound(tmp_path: Path) -> None:
    """B3 limit: the raw count is a LOWER BOUND — sign-flip arms aren't auto-counted."""
    for i in range(12):
        tc.record_trial(tmp_path, _fork(i))
    # 12 evaluate calls count as 12, even if each was read at both signs (true = 24):
    assert tc.count_trials(tmp_path) == 12
    # declaring arms reflects the doubling explicitly (one call, two arms):
    d2 = tmp_path / "s2"
    tc.record_trial(d2, _fork(0), arms=2)
    assert tc.count_trials(d2) == 2


def test_honest_limit_unrecorded_is_invisible(tmp_path: Path) -> None:
    """B3 limit: a NIH evaluation never routed through the counter is invisible."""
    for i in range(5):
        tc.record_trial(tmp_path, _fork(i))
    # ...three more evaluations computed by hand, never recorded...
    assert tc.count_trials(tmp_path) == 5  # only what it is given


def test_bypass_empty_dir_phantom_n(tmp_path: Path) -> None:
    """B4 (grok RP-1 caught this): an empty/absent ledger must NOT certify N > 0.

    Reconcile against a dir with no trials while claiming you ran 12 → the gate
    must refuse, not print PASS on a phantom N.
    """
    r = tc.reconcile(tmp_path, declared_k=12, reported_n=12)
    assert r.actual == 0
    assert r.no_evidence is True
    assert r.ok is False


def test_bypass_sharding_is_a_stated_limit(tmp_path: Path) -> None:
    """B5 (grok RP-1): sharding across session dirs evades the count — a stated LIMIT.

    The counter sees one session_dir; splitting a 40-trial search across two dirs
    lets each reconcile pass. This test PINS the limit so it can't be forgotten —
    the honest fix is discipline (one canonical session_dir), not code.
    """
    s1, s2 = tmp_path / "s1", tmp_path / "s2"
    for i in range(20):
        tc.record_trial(s1, _fork(i))
        tc.record_trial(s2, _fork(i))
    assert tc.reconcile(s1, 20, 20).ok is True
    assert tc.reconcile(s2, 20, 20).ok is True  # each looks clean; true N is 40


def test_malformed_ledger_fails_loud(tmp_path: Path) -> None:
    """A corrupt / tampered ledger line fails LOUD, not a silent miscount."""
    (tmp_path / tc.COUNT_FILE_NAME).write_text('{"fork": {}, "arms": 2.9}\n')
    with pytest.raises(tc.TrialCountError):
        tc.count_trials(tmp_path)
