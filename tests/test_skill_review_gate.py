"""Bypass red-tests for the tightened skill-review-gate.

Written BEFORE the fix (CR-08). The original gate FAILs iff a range changes a SKILL.md but
adds NO meta-reviews/* file — a RANGE-level co-presence check that an UNRELATED review in the
range satisfies (the logged false-PASS: two new skills passed on a co-present case-study
review that never named them). A 2-lens enumeration then showed a naive "grep the review for
the skill name" is itself weak (substring `research`⊂`research-session-protocol`; a stale
review dragged into range by a no-op touch). So the fixed gate requires, per changed skill,
that the skill's `<name>` appears **word-bounded** in a review's **added** lines.

Honest residual limits (stated, not tested as blocked): a common-word skill name, an omnibus
review that incidentally lists the name, and actively pasting the name into a fake review all
still pass — verifying a review is *about* the skill is RP-1's / a human's job.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[1] / "scripts" / "skill-review-gate.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "README").write_text("base\n")
    _git(r, "add", ".")
    _git(r, "commit", "-qm", "base")
    return r


def _commit(repo: Path, files: dict[str, str | None], msg: str) -> None:
    for path, content in files.items():
        p = repo / path
        if content is None:  # delete
            _git(repo, "rm", "-q", path)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(repo, "add", path)
    _git(repo, "commit", "-qm", msg)


def _gate(repo: Path, base: str = "HEAD~1", head: str = "HEAD") -> int:
    return subprocess.run(
        ["bash", str(GATE), base, head], cwd=repo, capture_output=True, text=True
    ).returncode


def _skill(name: str) -> str:
    return f".claude/skills/{name}/SKILL.md"


def _review(name: str) -> str:
    return f".scratch/reflow/meta-reviews/{name}-review-raw.json"


def test_no_skill_change_passes(repo: Path):
    _commit(repo, {"docs/x.md": "hi"}, "non-skill")
    assert _gate(repo) == 0


def test_skill_change_no_review_fails(repo: Path):
    _commit(repo, {_skill("foo"): "# foo\nbody\n"}, "skill only")
    assert _gate(repo) == 1


def test_covering_review_passes(repo: Path):
    _commit(repo, {_skill("foo"): "# foo\n", _review("foo"): '{"skill": "foo"}\n'}, "skill+review")
    assert _gate(repo) == 0


def test_unrelated_review_now_fails(repo: Path):
    """THE fix: a review that never names the changed skill must NOT satisfy the gate."""
    _commit(
        repo, {_skill("foo"): "#\n", _review("bar"): '{"skill": "bar"}\n'}, "foo + review bar"
    )
    assert _gate(repo) == 1


def test_multiple_skills_partial_review_fails(repo: Path):
    _commit(
        repo,
        {_skill("foo"): "# foo\n", _skill("baz"): "# baz\n", _review("foo"): '{"skill": "foo"}\n'},
        "two skills, one review",
    )
    assert _gate(repo) == 1  # baz is uncovered


def test_substring_name_not_matched(repo: Path):
    """A review naming 'foobar' must NOT cover a change to the 'foo' skill (word boundary)."""
    _commit(
        repo, {_skill("foo"): "#\n", _review("foobar"): '{"skill": "foobar"}\n'}, "foo/foobar"
    )
    assert _gate(repo) == 1


def test_deleted_skill_needs_no_review(repo: Path):
    _commit(repo, {_skill("foo"): "# foo\n", _review("foo"): '{"skill": "foo"}\n'}, "add foo")
    _commit(repo, {_skill("foo"): None}, "delete foo skill")
    assert _gate(repo) == 0  # deleting a skill does not require a review


def test_diff_header_path_token_not_matched(repo: Path):
    """A skill named like a diff-header path token ('json') must NOT be covered by the
    `+++ b/....json` header of an unrelated review (grok RP-1: the +++ leak)."""
    _commit(
        repo, {_skill("json"): "#\n", _review("x"): '{"unrelated": "no name"}\n'}, "json"
    )
    assert _gate(repo) == 1


def test_regex_metachar_name_is_literal(repo: Path):
    """A skill name with a regex metachar ('foo.bar') is matched literally — a review saying
    'fooXbar' must NOT cover it (grok RP-1: unescaped name in grep -E)."""
    _commit(
        repo, {_skill("foo.bar"): "#\n", _review("y"): '{"note": "fooXbar"}\n'}, "metachar"
    )
    assert _gate(repo) == 1


def test_reversed_range_not_silent_pass(repo: Path):
    """A reversed base/head must refuse (exit 2), not silently PASS 'no skill change'."""
    _commit(repo, {_skill("foo"): "#\n"}, "skill only")
    assert _gate(repo, "HEAD~1", "HEAD") == 1  # forward: uncovered skill fails
    assert _gate(repo, "HEAD", "HEAD~1") == 2  # reversed: refuse, not a silent green


def test_stale_review_touch_does_not_cover(repo: Path):
    """An old review already naming 'foo', dragged into range by a no-op touch, must not cover
    a fresh 'foo' change — coverage is judged on ADDED lines, not head content."""
    _commit(repo, {_review("foo"): '{"skill": "foo"}\n'}, "old review on base")
    _commit(
        repo,
        {_skill("foo"): "# foo\n", _review("foo"): '{"skill": "foo"}\n\n'},  # touch: +blank line
        "skill + touch old review",
    )
    assert _gate(repo) == 1  # the touch added only a blank line, naming nothing
