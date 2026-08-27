"""CONFIRM-time budget gate — wires the trial-counter into the pre-registration step.

The `research-session-protocol` skill's [DESIGNED] budget gate, now built. At CONFIRM
(when you freeze a pre-registration for the confirmatory study), it reads a small prereg
JSON — `{"reported_n": N, "session_dir": "<the EXPLORE search's trial-counter dir>"}` — and
**refuses to open the prereg** unless the N you will hand the validator covers the trials you
actually ran: it reconciles `reported_n` against `harness.trial_counter`'s session count and
blocks silent-N inflation (`reported_n < actual`) and a phantom N (empty ledger).
Over-declaring (`reported_n > actual`) is conservative and allowed.

**Fail-closed on every degenerate input** — the recurring bug this project keeps hitting is a
gate that fails *open* on malformed input. So a missing/unreadable/malformed prereg, a
non-object JSON, a `reported_n` that is not a finite int ≥ 1 (rejecting the catastrophic
`NaN`/`Infinity` tokens `json` accepts by default, plus float/bool/str/None/negative/0/missing),
a missing/empty/relative/nonexistent/non-directory `session_dir`, or a corrupt ledger
(`TrialCountError`) all **REFUSE**, never silently certify.

What it adds beyond `trial_counter reconcile` (a CLI over the same check): the strict
`reported_n` / `session_dir` **validation** reconcile does not do, and the prereg-artifact
wiring. It is DISTINCT from `scripts/prereg-gate.sh` (which checks git-commit *ordering*, not
N). Advisory + manual: it does not enforce the EXPLORE-time budget K (that is trial_counter's
job) and does not stop you appending trials after it passes (a point-in-time check). It
verifies the count on the **named** `session_dir` — it cannot check you named the *right*
ledger: a decoy directory (or a symlink to one) with an honest-looking small N passes, an
inherited trial_counter shard/identity limit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

from harness import trial_counter


class ConfirmResult(NamedTuple):
    ok: bool
    reason: str
    reported_n: object  # the raw value read (for diagnostics); None if unavailable
    actual: int  # trials on the ledger, or -1 if it could not be counted


def _refuse(reason: str, reported_n: object = None, actual: int = -1) -> ConfirmResult:
    return ConfirmResult(False, reason, reported_n, actual)


def _reject_nonfinite(token: str) -> float:
    raise ValueError(f"non-finite JSON literal {token!r} is not an allowed reported_n")


def check_prereg(prereg_path) -> ConfirmResult:
    """Verify a CONFIRM pre-registration against its session trial count. Fail-closed."""
    try:
        p = Path(prereg_path)
    except TypeError:
        return _refuse("prereg path must be a str or PathLike")
    if not p.is_file():
        return _refuse(f"prereg artifact is not a readable file: {prereg_path}")
    try:
        raw = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _refuse(f"cannot read prereg: {exc}")
    if not raw.strip():
        return _refuse("prereg is empty")
    try:
        prereg = json.loads(raw, parse_constant=_reject_nonfinite)
    except (json.JSONDecodeError, ValueError) as exc:
        return _refuse(f"prereg is not valid JSON: {exc}")
    if not isinstance(prereg, dict):
        return _refuse("prereg must be a JSON object")

    if "reported_n" not in prereg:
        return _refuse("prereg is missing 'reported_n'")
    n = prereg["reported_n"]
    # bool is an int subclass — reject it; require a finite non-negative int >= 1.
    if isinstance(n, bool) or not isinstance(n, int):
        return _refuse(f"'reported_n' must be an int, got {type(n).__name__}", n)
    if n < 1:
        return _refuse(f"'reported_n' must be >= 1 (a CONFIRM ran trials), got {n}", n)

    sd = prereg.get("session_dir")
    if not isinstance(sd, str) or not sd.strip():
        return _refuse("prereg is missing a non-empty 'session_dir'", n)
    sdp = Path(sd)
    if not sdp.is_absolute():
        return _refuse(f"session_dir must be absolute (a relative path is cwd-dependent): {sd}", n)
    if not sdp.is_dir():
        return _refuse(f"session_dir is not an existing directory: {sd}", n)

    try:
        r = trial_counter.reconcile(sdp, declared_k=n, reported_n=n)
    except trial_counter.TrialCountError as exc:
        return _refuse(f"session ledger is corrupt (fail-closed): {exc}", n)
    except (OSError, UnicodeDecodeError) as exc:
        return _refuse(f"cannot read session ledger: {exc}", n)

    if not r.ok:  # under-report + phantom (over_budget ≡ under_reported here, declared_k=n)
        why = []
        if r.no_evidence:
            why.append("empty ledger — cannot certify a reported N > 0 (phantom N)")
        if r.under_reported or r.over_budget:
            why.append(f"reported N={n} understates {r.actual} trials on the ledger")
        return _refuse("; ".join(why) or "reconcile failed", n, r.actual)

    return ConfirmResult(True, f"reported N={n} covers {r.actual} recorded trials", n, r.actual)


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="harness.confirm_gate")
    p.add_argument("prereg", help="path to the CONFIRM prereg JSON (reported_n + session_dir)")
    args = p.parse_args(argv)
    r = check_prereg(args.prereg)
    if r.ok:
        print(f"confirm-gate: PASS — {r.reason}")
        return 0
    print(f"confirm-gate: REFUSE — {r.reason}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
