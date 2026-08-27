"""工位二 session trial-count reconciliation — a **file-backed** counter.

Counts every factor evaluation you actually ran in a research session and
reconciles it against the K you declared and the N you report downstream, so an
inflated search cannot be silently under-reported (the `research-session-protocol`
skill's [DESIGNED] tooth, now built as a **file-backed counter + a manual
reconcile helper** — not an auto-firing gate).

**Not `court.Ledger`.** This writes a `session-trial-count.jsonl` that only *counts
your search*; it is a different thing from `court`'s trial `Ledger` (the registered
hypotheses/trials the judge reads, see `docs/design/trial-ledger.md`). Don't conflate
the session count with the court ledger.

**File-backed on purpose.** The count lives on disk, not in memory, so it survives a
Jupyter **kernel restart** — an in-memory counter resets and under-reports across
restarts, the exact bypass this exists to stop (see the subprocess red-test in
`tests/test_trial_counter.py`, which a naive in-memory draft fails).

HONEST LIMITS (stated, and red-tested where a test can pin them):
- It counts trials you *record*; a NIH evaluation you never route through here is
  invisible — that is `backtest-reuse-guard` (工位三)'s job (reuse the adapter so the
  call is countable).
- The raw count is a **lower bound** on multiplicity: a variant read at both signs is
  two arms (禁赢学 rule 5) but one call. Declare the doubling with ``arms=``.
- It reconciles **one** `session_dir`. Sharding a search across dirs, pointing at a
  fresh empty dir, or wiping the file all evade the count (each is a form of "not
  recording"). Use a single canonical `session_dir`; the tool stops you *forgetting*,
  not you *actively editing the count out* — tamper-evidence needs git, like the reflow
  inbox. A self-honesty aid, not an adversary-proof gate (same posture as
  `skill-review-gate`).
- An **empty** ledger cannot certify a reported N > 0: reconcile returns *no evidence*,
  not PASS (it refuses to greenlight a phantom N). A corrupt/tampered line fails **loud**
  (`TrialCountError`), never a silent miscount.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

COUNT_FILE_NAME = "session-trial-count.jsonl"


class TrialCountError(Exception):
    """A session trial-count file is malformed / tampered (fail loud, not miscount)."""


def _count_file(session_dir) -> Path:
    return Path(session_dir) / COUNT_FILE_NAME


def _valid_arms(arms) -> bool:
    # bool is a subclass of int — reject it and floats explicitly (strict positive int).
    return isinstance(arms, int) and not isinstance(arms, bool) and arms >= 1


def record_trial(session_dir, fork: dict, *, arms: int = 1) -> None:
    """Append one evaluated trial to the session count file (creates dir/file).

    ``fork`` identifies the trial (e.g. the data tag + fork coordinates — the replay
    identity, not a seed). ``arms`` records sign-flip / multi-arm doubling explicitly
    (default 1 = the honest lower bound).
    """
    if not _valid_arms(arms):
        raise ValueError(f"arms must be a positive int, got {arms!r}")
    path = _count_file(session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"fork": fork, "arms": int(arms)}, sort_keys=True) + "\n")


def count_trials(session_dir) -> int:
    """Sum ``arms`` over the session count file on disk (0 if none). Survives restarts.

    A malformed line or non-positive-int ``arms`` raises ``TrialCountError`` — a
    tampered file fails loud rather than miscounting silently.
    """
    path = _count_file(session_dir)
    if not path.exists():
        return 0
    total = 0
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                arms = json.loads(line)["arms"]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise TrialCountError(f"{path}:{lineno}: malformed trial-count line") from exc
            if not _valid_arms(arms):
                raise TrialCountError(f"{path}:{lineno}: arms must be a positive int, got {arms!r}")
            total += arms
    return total


class ReconcileResult(NamedTuple):
    declared_k: int
    reported_n: int
    actual: int
    over_budget: bool
    under_reported: bool
    no_evidence: bool
    ok: bool


def reconcile(session_dir, declared_k: int, reported_n: int) -> ReconcileResult:
    """Flag under-reporting, over-budget, or a phantom N.

    ``over_budget``    = trials on the ledger exceed the declared budget K.
    ``under_reported`` = the N you hand downstream is smaller than what you ran.
    ``no_evidence``    = you claim N > 0 but the ledger is empty (cannot certify).
    Reporting N *above* an existing count is the conservative direction (makes the
    downstream correction stricter) and is allowed; only these three understate the
    multiplicity you owe the court.
    """
    actual = count_trials(session_dir)
    over = actual > declared_k
    under = reported_n < actual
    no_evidence = actual == 0 and reported_n > 0
    return ReconcileResult(
        declared_k, reported_n, actual, over, under, no_evidence, not (over or under or no_evidence)
    )


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="harness.trial_counter")
    sub = p.add_subparsers(dest="cmd", required=True)
    rc = sub.add_parser("reconcile", help="check a session count against declared K / reported N")
    rc.add_argument("session_dir")
    rc.add_argument("--declared-k", type=int, required=True)
    rc.add_argument("--reported-n", type=int, required=True)
    ct = sub.add_parser("count", help="print the trial count on a session ledger")
    ct.add_argument("session_dir")
    args = p.parse_args(argv)

    try:
        if args.cmd == "count":
            print(count_trials(args.session_dir))
            return 0
        r = reconcile(args.session_dir, args.declared_k, args.reported_n)
    except TrialCountError as exc:
        print(f"trial-counter: FAIL — {exc}", file=sys.stderr)
        return 1

    summary = f"ran {r.actual}, declared K={r.declared_k}, reported N={r.reported_n}"
    if r.ok:
        print(f"trial-counter: PASS — {summary}")
        return 0
    print(f"trial-counter: FAIL — {summary}", file=sys.stderr)
    if r.no_evidence:
        print("  no evidence: ledger is empty; cannot certify a reported N > 0", file=sys.stderr)
    if r.over_budget:
        print("  over budget: actual trials exceed declared K", file=sys.stderr)
    if r.under_reported:
        print("  under-reported: reported N < trials you ran (silent-N inflation)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
