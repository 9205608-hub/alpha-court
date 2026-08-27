"""Bypass red-tests for harness.publish_export — written BEFORE the implementation (CR-08).

Fake tokens only (see test_publish_audit.py header for why).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.publish_export import ExportError, export_snapshot

RULES_TEXT = """\
PUBLISH-RULES-CONFIRMED
[hard]
玄光资本
Nebulight

[framing]
JOBWORD

[rewrite]
玄光资本 => [REDACTED-EMPLOYER]
Nebulight => [REDACTED-EMPLOYER]
/Users/fakeuser => [HOME]
"""

PUBLISHING_TEMPLATE = (
    "# pub\n\n<!-- PUBLISH-MANIFEST:BEGIN -->\n"
    "_Not yet generated — populated by export._\n"
    "<!-- PUBLISH-MANIFEST:END -->\n"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture()
def source_repo(tmp_path: Path) -> Path:
    """A fake tracked source repo with poison + internals + an untracked secret."""
    repo = tmp_path / "src"
    (repo / "court").mkdir(parents=True)
    (repo / ".scratch").mkdir()
    (repo / "README.md").write_text("# proj\n", encoding="utf-8")
    (repo / "PUBLISHING.md").write_text(PUBLISHING_TEMPLATE, encoding="utf-8")
    (repo / "court" / "kernel.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "TIMELINE.md").write_text("internal log, stays home\n", encoding="utf-8")
    (repo / ".scratch" / "review.json").write_text(
        '{"who": "玄光资本", "path": "/Users/fakeuser/Desktop/x", "note": "JOBWORD context"}',
        encoding="utf-8",
    )
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    # untracked + gitignored secrets must never ship
    (repo / "untracked-secret.md").write_text("玄光资本 raw\n", encoding="utf-8")
    (repo / "docs" / "private").mkdir(parents=True)
    (repo / "docs" / "private" / "charter.md").write_text("private\n", encoding="utf-8")
    return repo


@pytest.fixture()
def rules_file(tmp_path: Path) -> Path:
    p = tmp_path / "rules.txt"
    p.write_text(RULES_TEXT, encoding="utf-8")
    return p


def do_export(source_repo: Path, tmp_path: Path, rules_file: Path):
    out = tmp_path / "out"
    res = export_snapshot(source_repo, out, rules_file)
    return out, res


def test_untracked_files_never_ship(source_repo, tmp_path, rules_file):  # location-V2
    out, _ = do_export(source_repo, tmp_path, rules_file)
    assert not (out / "untracked-secret.md").exists()
    assert not (out / "docs" / "private").exists()


def test_timeline_excluded_case_insensitive(source_repo, tmp_path, rules_file):  # V13
    lower = source_repo / "docs"
    lower.mkdir(exist_ok=True)
    (lower / "Timeline.md").write_text("copy\n", encoding="utf-8")
    _git(source_repo, "add", "-A")
    _git(source_repo, "commit", "-qm", "add copy")
    out, res = do_export(source_repo, tmp_path, rules_file)
    assert not (out / "TIMELINE.md").exists()
    assert not (out / "docs" / "Timeline.md").exists()
    assert any("TIMELINE.md" in e for e in res.excluded)


def test_excluded_paths_never_ship_and_are_disclosed(source_repo, tmp_path, rules_file,
                                                     monkeypatch):
    import harness.publish_export as pe

    rel = ".scratch/dispatch/v0.3-00-blade-plumbing/ticket.md"
    victim = source_repo / rel
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.write_text("archive-zone artifact\n", encoding="utf-8")
    _git(source_repo, "add", "-A")
    _git(source_repo, "commit", "-qm", "add excluded-path artifact")
    monkeypatch.setattr(pe, "EXCLUDED_PATHS", frozenset({rel}))
    out, res = do_export(source_repo, tmp_path, rules_file)
    assert not (out / rel).exists()
    assert rel in res.excluded  # manifest discloses the exclusion


def test_rewrite_applied_with_visible_marker(source_repo, tmp_path, rules_file):
    out, _ = do_export(source_repo, tmp_path, rules_file)
    text = (out / ".scratch" / "review.json").read_text(encoding="utf-8")
    assert "玄光资本" not in text
    assert "[REDACTED-EMPLOYER]" in text
    assert "/Users/fakeuser" not in text
    assert "[HOME]" in text


def test_manifest_populated_without_original_strings(
    source_repo, tmp_path, rules_file
):  # V6/V7 manifest self-leak
    out, res = do_export(source_repo, tmp_path, rules_file)
    pub = (out / "PUBLISHING.md").read_text(encoding="utf-8")
    assert "PUBLISH-MANIFEST:BEGIN" in pub and "PUBLISH-MANIFEST:END" in pub
    assert "_Not yet generated" not in pub
    assert "[REDACTED-EMPLOYER]" in pub  # marker + counts are itemized
    assert "玄光资本" not in pub  # the original string never appears
    assert res.manifest_rewrites  # non-empty accounting


def test_archive_zone_framing_counts_disclosed(source_repo, tmp_path, rules_file):
    out, _ = do_export(source_repo, tmp_path, rules_file)
    pub = (out / "PUBLISHING.md").read_text(encoding="utf-8")
    assert "framing" in pub.lower() or "语境" in pub


def test_no_backup_droppings(source_repo, tmp_path, rules_file):  # mechanics-V5
    out, _ = do_export(source_repo, tmp_path, rules_file)
    droppings = [
        p for p in out.rglob("*") if p.suffix in {".bak", ".orig", ".tmp"} or p.name.endswith("~")
    ]
    assert droppings == []


def test_tracked_symlink_refused(source_repo, tmp_path, rules_file):  # location-V10
    (source_repo / "link.md").symlink_to(source_repo / "README.md")
    _git(source_repo, "add", "-A")
    _git(source_repo, "commit", "-qm", "symlink")
    with pytest.raises(ExportError):
        do_export(source_repo, tmp_path, rules_file)


def test_export_refuses_nongit_source(tmp_path, rules_file):  # location-V2
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "a.md").write_text("x\n", encoding="utf-8")
    with pytest.raises(ExportError):
        export_snapshot(plain, tmp_path / "o", rules_file)


def test_export_refuses_to_wipe_arbitrary_dir(source_repo, tmp_path, rules_file):
    out = tmp_path / "precious"
    out.mkdir()
    (out / "unrelated.txt").write_text("do not delete me\n", encoding="utf-8")
    with pytest.raises(ExportError):
        export_snapshot(source_repo, out, rules_file)
    assert (out / "unrelated.txt").exists()


def test_reexport_is_idempotent(source_repo, tmp_path, rules_file):
    out1, res1 = do_export(source_repo, tmp_path, rules_file)
    res2 = export_snapshot(source_repo, out1, rules_file)
    text = (out1 / ".scratch" / "review.json").read_text(encoding="utf-8")
    assert text.count("[REDACTED-EMPLOYER]") == 1  # no double-rewrite accumulation
    assert res1.manifest_rewrites == res2.manifest_rewrites
