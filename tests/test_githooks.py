"""Bypass red-tests for candidate B — git pre-commit/pre-merge-commit hook enforcement.

Written BEFORE the implementation (CR-08). The bypass set was enumerated by a 4-lens
workflow (hook-layer / skill-range / acknowledge / mechanics), 66 vectors, frozen in
`.scratch/githooks/bypass-enum-raw.json`. Each test plants a concrete bypass and asserts the
enforcement BITES — or, for a DECLARED HOLE (local hooks are bypassable by construction),
asserts the NORMAL path fires and documents the hole rather than pretending to prevent it.

Two layers under test:
  1. `harness.anti_pattern_gate --staged` — scans the STAGED index blob, not the working tree.
  2. `.githooks/pre-commit` + `pre-merge-commit` — wire both gates, fail-closed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_HARDROLL = "sr = r.mean() / r.std(ddof=1) * __import__('numpy').sqrt(252)\n"


def _run(args, cwd, **kw):
    env = {**os.environ, "PYTHONPATH": str(REPO), "PATH": os.environ.get("PATH", "")}
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, **kw)


def _git(repo, *args, check=True):
    r = _run(["git", *args], repo)
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr}")
    return r


@pytest.fixture()
def repo(tmp_path):
    """A fresh git repo with main + the harness importable via PYTHONPATH."""
    rp = tmp_path / "repo"
    rp.mkdir()
    _git(rp, "init", "-q", "-b", "main")
    _git(rp, "config", "user.email", "t@example.com")
    _git(rp, "config", "user.name", "t")
    (rp / "seed.txt").write_text("seed\n")
    _git(rp, "add", "-A")
    _git(rp, "commit", "-qm", "seed")
    return rp


def _antipattern_staged(repo):
    """Run the gate in --staged mode from the repo root; return the CompletedProcess."""
    return _run([sys.executable, "-m", "harness.anti_pattern_gate", "--staged"], repo)


# ----------------------------- --staged mode -------------------------------


def test_staged_scans_index_not_worktree(repo):  # BLOCKER V1/AP-WORKTREE
    f = repo / "factor.py"
    f.write_text(_HARDROLL)
    _git(repo, "add", "factor.py")
    f.write_text("clean = 1\n")  # worktree now clean, INDEX still has the hand-roll
    r = _antipattern_staged(repo)
    assert r.returncode == 1, f"must scan STAGED blob, not clean disk:\n{r.stdout}\n{r.stderr}"


def test_staged_no_python_files_passes(repo):  # V6/AP-EMPTY-ARGS
    (repo / "notes.md").write_text("# hi\n")
    _git(repo, "add", "notes.md")
    r = _antipattern_staged(repo)
    assert r.returncode == 0, f"a commit with no staged .py must not false-block:\n{r.stderr}"


def test_staged_nonutf8_py_fails_closed(repo):  # V11/AP-NONUTF8
    f = repo / "weird.py"
    f.write_bytes(b"sr = r.mean()/r.std()\xff\xfe # bad bytes\n")
    _git(repo, "add", "weird.py")
    r = _antipattern_staged(repo)
    assert r.returncode == 1, "a staged .py that can't be decoded must fail closed, not skip"


def test_staged_reuse_ok_in_index_exempts(repo):  # acknowledge over staged content
    f = repo / "factor.py"
    f.write_text(_HARDROLL.rstrip("\n") + "  # reuse-ok: reuses court.sharpe pending refactor\n")
    _git(repo, "add", "factor.py")
    assert _antipattern_staged(repo).returncode == 0


def test_staged_clean_index_passes(repo):
    f = repo / "factor.py"
    f.write_text("from court import sharpe\nx = sharpe(r)\n")
    _git(repo, "add", "factor.py")
    assert _antipattern_staged(repo).returncode == 0


def test_staged_rename_new_path_scanned(repo):  # V17 (rename)
    (repo / "a.py").write_text("clean = 1\n")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-qm", "a")
    (repo / "a.py").write_text(_HARDROLL)
    _git(repo, "add", "a.py")
    r = _antipattern_staged(repo)
    assert r.returncode == 1, "a modified staged .py must be scanned"


# ----------------------------- hook wiring ---------------------------------


def _stage_repo_infra(repo):
    """Copy the hooks, installer, harness package, and skill-review-gate into the temp repo."""
    import shutil

    shutil.copytree(REPO / ".githooks", repo / ".githooks")
    shutil.copytree(REPO / "harness", repo / "harness")
    (repo / "scripts").mkdir(exist_ok=True)
    shutil.copy(REPO / "scripts" / "install-hooks.sh", repo / "scripts" / "install-hooks.sh")
    shutil.copy(REPO / "scripts" / "skill-review-gate.sh",
                repo / "scripts" / "skill-review-gate.sh")


def _install_hooks(repo):
    _stage_repo_infra(repo)
    r = _run(["bash", "scripts/install-hooks.sh"], repo)
    assert r.returncode == 0, f"install-hooks failed: {r.stderr}"


def _commit(repo, msg="c", extra_args=()):
    return _run(["git", "commit", *extra_args, "-m", msg], repo)


def test_hook_blocks_unacked_hardroll(repo):  # end-to-end pre-commit
    _install_hooks(repo)
    (repo / "factor.py").write_text(_HARDROLL)
    _git(repo, "add", "factor.py")
    r = _commit(repo)
    assert r.returncode != 0, "pre-commit must block a staged hand-roll"


def test_hook_allows_acked_hardroll(repo):
    _install_hooks(repo)
    (repo / "factor.py").write_text(
        _HARDROLL.rstrip("\n") + "  # reuse-ok: reuses court.sharpe pending refactor\n"
    )
    _git(repo, "add", "factor.py")
    assert _commit(repo).returncode == 0


def test_hook_no_verify_is_a_declared_hole(repo):  # V10/V19 declared-hole
    _install_hooks(repo)
    (repo / "factor.py").write_text(_HARDROLL)
    _git(repo, "add", "factor.py")
    # --no-verify bypasses local hooks BY DESIGN; we document, not prevent.
    r = _commit(repo, extra_args=("--no-verify",))
    assert r.returncode == 0, "--no-verify bypasses (declared hole); enforcement is server-side CI"


def test_hook_index_vs_worktree_blocks(repo):  # BLOCKER through the real hook
    _install_hooks(repo)
    f = repo / "factor.py"
    f.write_text(_HARDROLL)
    _git(repo, "add", "factor.py")
    f.write_text("clean = 1\n")  # clean disk, dirty index
    assert _commit(repo).returncode != 0, "hook must scan staged blob, not clean worktree"


def test_hook_fails_closed_when_gate_errors(repo):  # BLOCKER V2/fail-open
    _install_hooks(repo)
    # break the harness so the gate raises on import; the hook MUST block, never fail open
    (repo / "harness" / "anti_pattern_gate.py").write_text("raise RuntimeError('boom')\n")
    (repo / "factor.py").write_text("x = 1\n")
    _git(repo, "add", "factor.py")
    r = _commit(repo)
    assert r.returncode != 0, "a crashing gate must fail CLOSED (block), never fail open"


def test_hook_nonexecutable_is_caught_by_installer(repo):  # V2-nonexec
    _stage_repo_infra(repo)
    (repo / ".githooks" / "pre-commit").chmod(0o644)  # strip exec bit
    _run(["bash", "scripts/install-hooks.sh"], repo)
    # after install, the hook must be executable (git silently ignores non-exec hooks)
    assert os.access(repo / ".githooks" / "pre-commit", os.X_OK), "installer must chmod +x"


# ----------------------------- skill-review at pre-commit ------------------


def _add_skill(repo, name, body="# skill\n"):
    d = repo / ".claude" / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(body)
    _git(repo, "add", str((d / "SKILL.md").relative_to(repo)))


def _add_review(repo, fname, body):
    d = repo / ".scratch" / "reflow" / "meta-reviews"
    d.mkdir(parents=True, exist_ok=True)
    (d / fname).write_text(body)
    _git(repo, "add", str((d / fname).relative_to(repo)))


def test_hook_blocks_unreviewed_skill(repo):  # BLOCKER V3/SR-HEAD-DEFAULT
    _install_hooks(repo)
    _add_skill(repo, "new-skill")
    r = _commit(repo, "add skill")
    assert r.returncode != 0, "a staged skill with no naming review must block at pre-commit"


def test_hook_allows_skill_with_costaged_review(repo):
    _install_hooks(repo)
    _add_skill(repo, "new-skill")
    _add_review(repo, "new-skill-review.md", "review of new-skill: looks fine\n")
    assert _commit(repo, "skill+review").returncode == 0


def test_hook_skill_gate_uses_staged_tree_not_HEAD(repo):  # V4/off-by-one
    # If the hook diffed main..HEAD it would miss the staged (uncommitted) skill entirely.
    _install_hooks(repo)
    _add_skill(repo, "sneaky")
    r = _commit(repo, "sneaky skill only")
    assert r.returncode != 0, "staged skill must be visible to the gate (write-tree, not HEAD)"


# ---------------- grok RP-1 (githook-review) fixes — V17 family + trunk ----


def test_staged_uppercase_py_suffix_scanned(repo):  # grok: case-sensitive suffix leak
    f = repo / "Factor.PY"
    f.write_text(_HARDROLL)
    _git(repo, "add", "Factor.PY")
    assert _antipattern_staged(repo).returncode == 1, "a staged .PY hand-roll must be scanned"


def test_staged_symlink_py_fails_closed(repo):  # grok: mode-120000 .py carrier
    (repo / "hidden").mkdir()
    (repo / "hidden" / "real.py").write_text(_HARDROLL)  # target (could be an excluded dir)
    os.symlink("hidden/real.py", repo / "link.py")
    _git(repo, "add", "link.py")
    assert _antipattern_staged(repo).returncode == 1, "a staged .py symlink cannot be linted"


def test_hook_trunk_renamed_blocks_unreviewed_skill(repo):  # grok: hard-coded 'main' bypass
    _install_hooks(repo)
    _git(repo, "branch", "-m", "main", "trunk-x")  # main no longer exists
    _add_skill(repo, "sneaky2")
    r = _commit(repo, "skill after trunk rename")
    assert r.returncode != 0, "renaming main must not silently skip skill-review for a staged skill"


def test_hook_blocks_staged_court_market_import(repo):  # candidate A wired into the hook
    _install_hooks(repo)
    (repo / "court").mkdir()
    (repo / "court" / "leak.py").write_text("import qlib\n")
    _git(repo, "add", "court/leak.py")
    r = _commit(repo, "court imports qlib")
    assert r.returncode != 0, "pre-commit must block a staged court/ market import (iron law #2)"
