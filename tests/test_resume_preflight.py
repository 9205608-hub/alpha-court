"""Bypass red-tests for `scripts/resume-worker.sh` — the CR-13 tooth.

Written BEFORE the implementation (CR-08). Context: `bridge-isolation-failure`
recurrence #2 — the original dispatch worktree was deleted between rework-01 and
rework-02, and a raw `grok --resume` (no preflight, no tripwire) let the worker
land its delivery directly on the production branch in the commander's checkout.
The v0.2 role-reversal meta-review's top-criticism #3: "反复发不能停在散文".

Enumerated bypass set (multi-lens: input-shape / identity / escape-surface /
TOCTOU / transport), each mapped to a test or a declared hole:
  V01 receipt missing/empty worktree_path        -> fail-closed (no guessing)
  V02 worktree_path = commander checkout          -> allowlist-prefix reject
  V03 worktree_path inside repo (.claude/worktrees session tree) -> same reject
  V04 worktree deleted (dir missing)              -> reject, "re-dispatch fresh"
  V05 dir exists but is not a git worktree        -> reject
  V06 dir is a worktree of a DIFFERENT repo       -> common-dir mismatch reject
  V07/V08 rework note relative / missing / empty  -> reject
  V09 commander tree dirty (contract freeze)      -> reject (mirror dispatch.sh)
  V10 downstream `| head` SIGPIPE (CR-04 class)   -> trap '' PIPE, file outputs
  V11 worker escapes into commander checkout mid-run -> post-flight TRIPWIRE
      (detection-not-prevention, stated: a rogue worker with absolute paths can
      write anywhere; the tripwire makes it loud instead of silent)
  V12 output raw-rework-NN.json already exists    -> refuse overwrite
  V13 session id absent (no raw sibling, no override) -> reject
  V14 symlinked worktree_path escaping the allowlist -> canonicalize BEFORE
      prefix check (symlink-carrier lesson from the court-import gate)
Post-RP-1 additions (grok review 2026-07-20, C/revise — findings adopted):
  V11b/c/d same-basename & substring tripwire exemptions  -> CLOSED (pathspec
      exact excludes; commander self-probe found the class in parallel, grok
      supplied the subdir + substring variants)
  V14b/c case-twin escape / case-flip false-reject on case-insensitive FS
      -> CLOSED (containment by inode identity via samefile ancestor-walk,
      not byte prefixes)
  V01b/V13c non-string worktree_path / sessionId type confusion -> CLOSED

Declared-not-defended (post-RP-1 honest list): grok CLI internals; worktree
recreated with wrong base (resume semantics accept the historical base by
protocol); worker writes outside both trees to unrelated paths; worker
write-then-DELETE inside the checkout during the run (no status diff remains at
post-flight — the tripwire sees residue, not history).
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "resume-worker.sh"


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {args} failed: {r.stderr}"
    return r.stdout.strip()


@pytest.fixture()
def world(tmp_path: Path):
    """Fake commander repo + dispatch root + stub grok on PATH."""
    repo = tmp_path / "commander-repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    droot = tmp_path / "dispatch-worktrees"
    droot.mkdir()
    wt = droot / "v-test-20260101-000000"
    _git(repo, "worktree", "add", "-q", "-b", "dispatch/v-test", str(wt))

    ddir = tmp_path / "dispatch-artifacts"
    ddir.mkdir()
    receipt = ddir / "receipt-20260101-000000.json"
    receipt.write_text(json.dumps({"worktree_path": str(wt), "branch": "dispatch/v-test"}))
    raw = ddir / "raw-20260101-000000.json"
    raw.write_text(json.dumps({"sessionId": "0000-fake-session"}))
    note = ddir / "rework-09.md"
    note.write_text("# rework\nfix things\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "grok"
    stub.write_text(
        "#!/bin/bash\n"
        'echo "{\\"argv\\": \\"$*\\"}"\n'
        'printf "%s\\n" "$*" > "$STUB_LOG"\n'
        '[ -n "${STUB_ESCAPE_WRITE:-}" ] && echo rogue > "$STUB_ESCAPE_WRITE"\n'
        "exit ${STUB_EXIT:-0}\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)

    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "DISPATCH_WORKTREE_ROOT": str(droot),
        "STUB_LOG": str(tmp_path / "stub.log"),
    }
    return {
        "repo": repo, "droot": droot, "wt": wt, "ddir": ddir,
        "receipt": receipt, "raw": raw, "note": note, "env": env,
        "stub_log": tmp_path / "stub.log", "tmp": tmp_path,
    }


def _run(world, *extra_env, receipt=None, note=None):
    env = dict(world["env"])
    for kv in extra_env:
        env.update(kv)
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt or world["receipt"]), str(note or world["note"])],
        cwd=world["repo"], env=env, capture_output=True, text=True,
    )


def test_happy_path_invokes_resume_and_persists_raw(world):
    r = _run(world)
    assert r.returncode == 0, r.stderr
    argv = world["stub_log"].read_text()
    assert "--resume 0000-fake-session" in argv
    assert f"--prompt-file {world['note']}" in argv
    out_raw = world["ddir"] / "raw-rework-09.json"
    assert out_raw.exists() and out_raw.stat().st_size > 0


def test_v01_missing_worktree_path_fails_closed(world):
    world["receipt"].write_text(json.dumps({"branch": "dispatch/v-test"}))
    r = _run(world)
    assert r.returncode == 2
    assert "re-dispatch" in (r.stderr + r.stdout).lower()


def test_v02_worktree_is_commander_checkout_rejected(world):
    world["receipt"].write_text(json.dumps({"worktree_path": str(world["repo"])}))
    r = _run(world)
    assert r.returncode == 2


def test_v03_worktree_inside_repo_rejected(world):
    inner = world["repo"] / ".claude" / "worktrees" / "session-x"
    inner.mkdir(parents=True)
    _git(world["repo"], "worktree", "add", "-q", "-b", "dispatch/v-in", str(inner / "wt"))
    world["receipt"].write_text(json.dumps({"worktree_path": str(inner / "wt")}))
    r = _run(world)
    assert r.returncode == 2


def test_v04_deleted_worktree_says_redispatch(world):
    subprocess.run(["rm", "-rf", str(world["wt"])], check=True)
    r = _run(world)
    assert r.returncode == 2
    assert "re-dispatch" in (r.stderr + r.stdout).lower()


def test_v05_plain_dir_not_a_worktree_rejected(world):
    plain = world["droot"] / "plain"
    plain.mkdir()
    world["receipt"].write_text(json.dumps({"worktree_path": str(plain)}))
    r = _run(world)
    assert r.returncode == 2


def test_v06_worktree_of_other_repo_rejected(world):
    other = world["tmp"] / "other-repo"
    other.mkdir()
    _git(other, "init", "-q", "-b", "main")
    _git(other, "config", "user.email", "t@t")
    _git(other, "config", "user.name", "t")
    (other / "f").write_text("x")
    _git(other, "add", "-A")
    _git(other, "commit", "-qm", "i")
    owt = world["droot"] / "other-wt"
    _git(other, "worktree", "add", "-q", str(owt))
    world["receipt"].write_text(json.dumps({"worktree_path": str(owt)}))
    r = _run(world)
    assert r.returncode == 2


def test_v07_relative_note_rejected(world):
    r = subprocess.run(
        ["bash", str(SCRIPT), str(world["receipt"]), "rework-09.md"],
        cwd=world["repo"], env=world["env"], capture_output=True, text=True,
    )
    assert r.returncode == 2


def test_v09_dirty_commander_tree_rejected(world):
    (world["repo"] / "README.md").write_text("dirty\n")
    r = _run(world)
    assert r.returncode == 2
    assert "freeze" in (r.stderr + r.stdout).lower() or "dirty" in (r.stderr + r.stdout).lower()


def test_v10_sigpipe_still_persists_raw(world):
    cmd = (
        f"bash {SCRIPT} {world['receipt']} {world['note']} | head -c 5"
    )
    r = subprocess.run(
        ["bash", "-c", cmd], cwd=world["repo"], env=world["env"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert (world["ddir"] / "raw-rework-09.json").exists()


def test_v11_tripwire_on_commander_checkout_write(world):
    r = _run(world, {"STUB_ESCAPE_WRITE": str(world["repo"] / "rogue.txt")})
    assert r.returncode == 2
    assert "tripwire" in (r.stderr + r.stdout).lower()


def test_v11b_same_basename_elsewhere_still_trips(world):
    """Commander self-probe (2026-07-20, parallel to the grok RP-1): the naive
    tripwire filtered status lines by output BASENAME, so a worker writing a
    same-named file anywhere in the commander checkout was silently exempted."""
    r = _run(world, {"STUB_ESCAPE_WRITE": str(world["repo"] / "raw-rework-09.json")})
    assert r.returncode == 2
    assert "tripwire" in (r.stderr + r.stdout).lower()


def test_v11c_same_basename_in_subdir_still_trips(world):
    """grok RP-1 blocker variant: same-named file under an existing tracked dir."""
    sub = world["repo"] / "court"
    sub.mkdir()
    r = _run(world, {"STUB_ESCAPE_WRITE": str(sub / "raw-rework-09.json")})
    assert r.returncode == 2


def test_v11d_substring_name_still_trips(world):
    """grok RP-1 blocker variant: filename merely CONTAINING the output name."""
    r = _run(world, {"STUB_ESCAPE_WRITE": str(world["repo"] / "evil-raw-rework-09.json.bak")})
    assert r.returncode == 2


def _fs_case_insensitive(tmp_path: Path) -> bool:
    probe = tmp_path / "CaseProbeXyz"
    probe.write_text("x")
    return (tmp_path / "caseprobexyz").exists()


def test_v14b_case_twin_escape_rejected(world):
    """grok RP-1 major: on a case-insensitive FS, a case-twin DISPATCH_WORKTREE_ROOT
    aimed at the commander repo + a case-twin worktree_path defeats byte-prefix
    checks (realpath does not case-normalize) and resumes INSIDE the checkout."""
    if not _fs_case_insensitive(world["tmp"]):
        pytest.skip("requires case-insensitive filesystem")
    evil = world["repo"] / "evil-wt"
    _git(world["repo"], "worktree", "add", "-q", "-b", "dispatch/v-evil", str(evil))
    twist = str(world["repo"]).replace("commander-repo", "COMMANDER-REPO")
    world["receipt"].write_text(json.dumps({"worktree_path": twist + "/evil-wt"}))
    r = _run(world, {"DISPATCH_WORKTREE_ROOT": twist})
    assert r.returncode == 2


def test_v14c_case_flipped_legit_droot_accepted(world):
    """grok RP-1 major (inverse): a case-variant spelling of the REAL dispatch
    root must not false-reject — identity is inode, not bytes."""
    if not _fs_case_insensitive(world["tmp"]):
        pytest.skip("requires case-insensitive filesystem")
    twist = str(world["droot"]).replace("dispatch-worktrees", "DISPATCH-WORKTREES")
    r = _run(world, {"DISPATCH_WORKTREE_ROOT": twist})
    assert r.returncode == 0, r.stderr


def test_v01b_non_string_worktree_path_typed_error(world):
    world["receipt"].write_text(json.dumps({"worktree_path": ["/a", "/b"]}))
    r = _run(world)
    assert r.returncode == 2
    assert "not a string" in (r.stderr + r.stdout).lower()


def test_v13c_non_string_session_id_rejected(world):
    world["raw"].write_text(json.dumps({"sessionId": {"x": 1}}))
    r = _run(world)
    assert r.returncode == 2
    assert "session" in (r.stderr + r.stdout).lower()


def test_v12_existing_output_refused(world):
    (world["ddir"] / "raw-rework-09.json").write_text("old")
    r = _run(world)
    assert r.returncode == 2
    assert (world["ddir"] / "raw-rework-09.json").read_text() == "old"


def test_v13_no_session_id_fails_closed(world):
    world["raw"].unlink()
    r = _run(world)
    assert r.returncode == 2


def test_v13b_env_override_supplies_session(world):
    world["raw"].unlink()
    r = _run(world, {"RESUME_SESSION_ID": "env-session-42"})
    assert r.returncode == 0, r.stderr
    assert "--resume env-session-42" in world["stub_log"].read_text()


def test_v14_symlink_escape_canonicalized_and_rejected(world):
    link = world["droot"] / "sneaky"
    link.symlink_to(world["repo"])
    world["receipt"].write_text(json.dumps({"worktree_path": str(link)}))
    r = _run(world)
    assert r.returncode == 2


def test_worker_nonzero_exit_propagates(world):
    r = _run(world, {"STUB_EXIT": "7"})
    assert r.returncode == 7
