# Ticket: v0.2-04 — decoupling guard upgrade: blacklist → whitelist in test_smoke

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

Iron law 4 of this project: `court/` (the market-agnostic validation kernel)
must never import market-specific code. The **executable guard for this law is
weaker than the law itself**. The current guard, `tests/test_smoke.py`, is
pasted here in full (this is the exact file at your base commit):

```python
"""Smoke tests for the engineering scaffold."""

from __future__ import annotations

import subprocess
import sys


def test_packages_importable() -> None:
    """All scaffold packages import successfully."""
    import adapters
    import court
    import gates
    import harness

    assert court is not None
    assert harness is not None
    assert gates is not None
    assert adapters is not None


def test_court_market_agnostic() -> None:
    """Importing court must not pull in qlib or adapters (iron law 4)."""
    code = """
import sys

import court

assert court is not None
qlib_modules = [name for name in sys.modules if name == "qlib" or name.startswith("qlib.")]
assert not qlib_modules, f"qlib modules leaked into sys.modules: {qlib_modules}"
adapters_modules = [
    name for name in sys.modules if name == "adapters" or name.startswith("adapters.")
]
assert not adapters_modules, f"adapters modules imported with court: {adapters_modules}"
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"subprocess failed (exit {result.returncode}):\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
```

The problem: the subprocess assertion is a **two-name blacklist** (`qlib*`,
`adapters*`). If `court` ever accidentally imported `tushare`, `akshare`,
`baostock`, `pandas`, or any other third-party library, this test would still
pass. The guard must become a **positive whitelist**.

**Commander decisions, frozen for this ticket (do not re-litigate):**

- The whitelist is: `sys.stdlib_module_names` ∪ `{"court", "numpy", "scipy"}`.
- `pandas` is NOT in the whitelist. Verified at your base commit: `court/`
  imports only stdlib + numpy + scipy (grep over `court/*.py` shows third-party
  imports are exactly `numpy`, `scipy.stats`). If court ever needs pandas,
  widening the whitelist is a deliberate one-line future change.
- The comparison is over **top-level module names newly added to
  `sys.modules` by `import court`**: snapshot `set(sys.modules)` BEFORE the
  import (inside the same subprocess), import court, diff, then map each new
  name to its top level via `name.split(".")[0]`. Snapshotting before the
  import is what keeps interpreter-startup modules (site hooks such as
  `_distutils_hack`, encodings, etc.) out of the diff — do not skip it.
- The legacy blacklist assertions (qlib / adapters) stay in place as
  redundancy; the whitelist becomes the primary guard.
- Python is 3.12 (`sys.stdlib_module_names` exists; guaranteed ≥ 3.10).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality (the project reuses qlib; the court
   kernel only consumes return/IC series).
2. Do NOT build idea/factor generation logic (generation side is a stub).
3. `court/` must not import any market-specific code or library. Market
   specifics live in `adapters/` only. (This ticket STRENGTHENS the guard for
   this law; it must not touch `court/` itself.)
4. Code, docstrings, comments: English.
5. **File ownership boundary: your final committed diff may touch ONLY
   `tests/test_smoke.py`.** Any other committed change = rejected delivery.
   (Temporary uncommitted edits for local falsification checks are allowed —
   see AC-4 — but must be reverted before commit.)

## Task

TDD, red first. All work in `tests/test_smoke.py` only.

1. **Extract a pure helper** in `tests/test_smoke.py`, e.g.
   `_whitelist_violations(new_top_level: set[str]) -> set[str]`, which returns
   the subset of `new_top_level` not in the whitelist
   (`sys.stdlib_module_names` ∪ `{"court", "numpy", "scipy"}`). Write its unit
   test FIRST and run it against the not-yet-existing helper — record that RED
   run (real command, real nonzero exit code) for your receipt. The unit test
   must cover at least: a market lib name (e.g. `"akshare"`) → flagged; a
   stdlib name (e.g. `"json"`) → not flagged; `"numpy"`/`"scipy"`/`"court"` →
   not flagged.
2. **Add one demonstration that the old blacklist misses what the whitelist
   catches**: an assertion (same unit-test level is fine) that the name
   `"akshare"` passes the legacy blacklist predicate (not qlib*, not
   adapters*) yet is flagged by `_whitelist_violations`. This is the executable
   record of WHY this ticket exists.
3. **Rewire the subprocess integration test**: the subprocess snapshots
   `sys.modules` before `import court`, imports court, and prints the set of
   newly-added top-level names as JSON to stdout (keep the legacy qlib/adapters
   assertions inside the subprocess as redundancy). The parent test parses the
   JSON and asserts `_whitelist_violations(new_top_level) == set()` with a
   failure message that names the offending modules. Keep the existing
   subprocess-failure diagnostics (returncode/stdout/stderr in the assert
   message).
4. Green: all tests in `tests/test_smoke.py` pass; full suite passes; ruff
   clean.

## Acceptance criteria

The referee will re-run every one of these independently in your worktree.
Record each command with its real exit code in your receipt.

1. `python3 -m pytest tests/test_smoke.py -q` — all green (existing 2 tests
   plus your new ones).
2. `python3 -m pytest -q` — full suite green. Baseline at your base commit is
   **542 passed, 2 skipped** (system python3, no qlib installed — the 2 skips
   are expected and are not yours to fix). After your change: same, plus your
   new tests, 0 failures.
3. `ruff check .` — clean.
4. **Falsification check (run it, report it, then revert it):** temporarily
   add a whitelist-violating third-party import at the top of
   `court/__init__.py` — use `import pytest` (pytest is installed and is
   neither stdlib nor numpy/scipy). Run
   `python3 -m pytest tests/test_smoke.py -q`: your whitelist test MUST FAIL
   (this proves the guard catches what the blacklist cannot — note the legacy
   blacklist assertions alone would have stayed green). Then revert with
   `git checkout -- court/__init__.py` and re-run to green. Record both runs
   (fail exit code, then green exit code) in your receipt. Do NOT commit the
   injection; your committed diff is `tests/test_smoke.py` only
   (verify with `git show --stat HEAD` before writing the receipt).
5. RED evidence: the receipt's command list includes the step-1 red run
   (unit test failing before the helper existed) with its real exit code.

## Out of scope

- Any change to `court/`, `harness/`, `adapters/`, `gates/`, `scripts/`,
  `pyproject.toml`, or any test file other than `tests/test_smoke.py`.
- Widening the whitelist (e.g. pandas) "for the future".
- Refactoring the existing two tests beyond what step 3 requires.
- CI configuration, docs, README.

## Operational notes

- Environment: system `python3` (3.12.8), `pytest`, `ruff` are on PATH in your
  worktree. numpy 2.4.4 / scipy 1.17.1 installed. qlib is NOT installed (hence
  the 2 expected skips). No network access needed; do not install anything.
- The full suite takes ~95s. Everything else here is seconds. No command in
  this ticket needs detach-and-poll.
- Write files incrementally (avoid one giant single-shot emission).

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-04: <summary>"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
