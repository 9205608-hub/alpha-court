"""Bypass red-tests for harness.publish_audit — written BEFORE the implementation (CR-08).

Every sensitive token in this file is FAKE (玄光资本 / Nebulight / xuanguang / FAKEACR /
JOBWORD): test files are tracked and ship in the public snapshot, so no real pattern may
appear here. The gate is pattern-agnostic machinery, so fake-token tests exercise it fully.

Vector ids reference .scratch/publish/bypass-enumeration.md.
"""

from __future__ import annotations

import quopri
import struct
import zlib
from pathlib import Path

import pytest

from harness.publish_audit import (
    RulesError,
    audit_tree,
    load_rules,
    verify_receipt,
    write_receipt,
)

# ---------------------------------------------------------------- fixtures

RULES_TEXT = """\
# fake rules for tests
PUBLISH-RULES-CONFIRMED
[hard]
玄光资本
Nebulight
xuanguang
FAKEACR
fake@example.com

[framing]
JOBWORD

[rewrite]
玄光资本 => [REDACTED-EMPLOYER]
Nebulight => [REDACTED-EMPLOYER]
/Users/fakeuser => [HOME]
"""

MANIFEST_OK = (
    "# pub\n\n<!-- PUBLISH-MANIFEST:BEGIN -->\n- generated\n<!-- PUBLISH-MANIFEST:END -->\n"
)


@pytest.fixture()
def rules_file(tmp_path: Path) -> Path:
    p = tmp_path / "rules.txt"
    p.write_text(RULES_TEXT, encoding="utf-8")
    return p


@pytest.fixture()
def rules(rules_file: Path):
    return load_rules(rules_file)


def make_tree(tmp_path: Path) -> Path:
    """Minimal clean export-shaped tree."""
    tree = tmp_path / "export"
    (tree / "court").mkdir(parents=True)
    (tree / "README.md").write_text("# clean\n", encoding="utf-8")
    (tree / "PUBLISHING.md").write_text(MANIFEST_OK, encoding="utf-8")
    (tree / "court" / "kernel.py").write_text("x = 1\n", encoding="utf-8")
    return tree


def run(tree: Path, rules) -> AuditReport:  # noqa: F821 - type from module under test
    return audit_tree(tree, rules, min_files=1)


def assert_bites(tree: Path, rules, needle: str = "") -> None:
    report = run(tree, rules)
    assert not report.ok, "gate PASSED on a poisoned tree"
    if needle:
        blob = " | ".join(f"{f.path}:{f.kind}:{f.detail}" for f in report.findings)
        assert needle in blob, f"expected finding mentioning {needle!r}, got: {blob}"


# ------------------------------------------------------- happy path first


def test_clean_tree_passes(tmp_path, rules):
    report = run(make_tree(tmp_path), rules)
    assert report.ok
    assert report.files_scanned >= 3


# ------------------------------------------------- hard patterns / decoding


def test_raw_token_in_content_bites(tmp_path, rules):
    tree = make_tree(tmp_path)
    (tree / "doc.md").write_text("about 玄光资本 fund\n", encoding="utf-8")
    assert_bites(tree, rules, "doc.md")


def test_json_uxxxx_escape_bites(tmp_path, rules):  # encoding-V1
    tree = make_tree(tmp_path)
    esc = "\\" + "u7384" + "\\" + "u5149" + "\\" + "u8d44" + "\\" + "u672c"
    (tree / "r.json").write_text('{"k": "' + esc + '"}', encoding="utf-8")
    assert_bites(tree, rules, "r.json")


def test_double_escaped_bites(tmp_path, rules):  # encoding-V14
    tree = make_tree(tmp_path)
    esc = "\\\\" + "u7384" + "\\\\" + "u5149" + "\\\\" + "u8d44" + "\\\\" + "u672c"
    (tree / "n.json").write_text('{"t": "' + esc + '"}', encoding="utf-8")
    assert_bites(tree, rules, "n.json")


def test_percent_encoding_bites(tmp_path, rules):  # encoding-V9
    tree = make_tree(tmp_path)
    (tree / "u.md").write_text("see https://x.test/?q=%E7%8E%84%E5%85%89%E8%B5%84%E6%9C%AC\n")
    assert_bites(tree, rules, "u.md")


def test_html_entities_bite(tmp_path, rules):  # encoding-V10
    tree = make_tree(tmp_path)
    (tree / "h.md").write_text("&#x7384;&#x5149;&#x8d44;&#x672c; renders the name\n")
    assert_bites(tree, rules, "h.md")


def test_zero_width_splice_bites(tmp_path, rules):  # encoding-V7
    tree = make_tree(tmp_path)
    zwsp = "\u200b"
    (tree / "z.md").write_text(zwsp.join("玄光资本") + "\n", encoding="utf-8")
    assert_bites(tree, rules, "z.md")


def test_any_zero_width_char_is_itself_a_finding(tmp_path, rules):  # encoding-V7
    tree = make_tree(tmp_path)
    (tree / "w.md").write_text("innocent\u200b text\n", encoding="utf-8")
    assert_bites(tree, rules, "zero-width")


def test_fullwidth_latin_bites(tmp_path, rules):  # encoding-V8 (NFKC)
    tree = make_tree(tmp_path)
    (tree / "f.md").write_text("Ｎｅｂｕｌｉｇｈｔ shipped it\n", encoding="utf-8")
    assert_bites(tree, rules, "f.md")


def test_markdown_splice_bites(tmp_path, rules):  # encoding-V13
    tree = make_tree(tmp_path)
    (tree / "m.md").write_text("玄**光**资`本` did X\n", encoding="utf-8")
    assert_bites(tree, rules, "m.md")


def test_pinyin_inside_identifier_bites(tmp_path, rules):  # encoding-V5
    tree = make_tree(tmp_path)
    (tree / "k.json").write_text('{"missing_muscle_for_xuanguang": 1}', encoding="utf-8")
    assert_bites(tree, rules, "k.json")


def test_case_variants_bite(tmp_path, rules):  # mechanics-V8
    tree = make_tree(tmp_path)
    (tree / "c.md").write_text("NEBULIGHT and NebuLight and nebulight\n")
    assert_bites(tree, rules, "c.md")


def test_utf16_file_bites(tmp_path, rules):  # location-V13
    tree = make_tree(tmp_path)
    (tree / "s.md").write_bytes("玄光资本 inside utf-16\n".encode("utf-16"))
    assert_bites(tree, rules, "s.md")


# ------------------------------------------------------------ carriers


def test_dot_directory_is_scanned(tmp_path, rules):  # encoding-V2 / mechanics-V3
    tree = make_tree(tmp_path)
    hidden = tree / ".scratch" / "reviews"
    hidden.mkdir(parents=True)
    (hidden / "raw.json").write_text('{"x": "玄光资本"}', encoding="utf-8")
    assert_bites(tree, rules, "raw.json")


def test_dotfile_is_scanned(tmp_path, rules):  # encoding-V2
    tree = make_tree(tmp_path)
    (tree / ".notes.md").write_text("玄光资本\n", encoding="utf-8")
    assert_bites(tree, rules, ".notes.md")


def test_filename_leak_bites(tmp_path, rules):  # location-V4 / mechanics-V9
    tree = make_tree(tmp_path)
    (tree / "nebulight-notes.md").write_text("clean content\n", encoding="utf-8")
    assert_bites(tree, rules, "nebulight-notes.md")


def test_nul_byte_binary_still_scanned(tmp_path, rules):  # location-V5
    tree = make_tree(tmp_path)
    (tree / "b.bin").write_bytes(b"\x00\x01" + "玄光资本".encode() + b"\x00")
    assert_bites(tree, rules, "b.bin")


def test_invalid_json_not_skipped(tmp_path, rules):  # encoding-V4
    tree = make_tree(tmp_path)
    (tree / "broken.json").write_text('prelude line\n{"t": "玄光资本"}', encoding="utf-8")
    assert_bites(tree, rules, "broken.json")


def _png_with_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00")
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(chunk_type, payload)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def test_png_text_chunk_bites(tmp_path, rules):  # location-V9
    tree = make_tree(tmp_path)
    (tree / "fig.png").write_bytes(_png_with_chunk(b"tEXt", b"Comment\x00made at Nebulight"))
    assert_bites(tree, rules, "fig.png")


def test_png_ztxt_compressed_chunk_bites(tmp_path, rules):  # location-V9
    tree = make_tree(tmp_path)
    payload = b"Comment\x00" + b"\x00" + zlib.compress("courtesy of 玄光资本".encode())
    (tree / "fig.png").write_bytes(_png_with_chunk(b"zTXt", payload))
    assert_bites(tree, rules, "fig.png")


def test_symlink_is_refused(tmp_path, rules):  # location-V10
    tree = make_tree(tmp_path)
    (tree / "link.md").symlink_to(tmp_path / "outside.md")
    assert_bites(tree, rules, "symlink")


# ------------------------------------------------------------ structure


def test_timeline_presence_bites_any_case(tmp_path, rules):  # mechanics-V13
    tree = make_tree(tmp_path)
    (tree / "docs").mkdir()
    (tree / "docs" / "timeline.md").write_text("internal log\n", encoding="utf-8")
    assert_bites(tree, rules, "timeline")


def test_docs_private_presence_bites(tmp_path, rules):  # mechanics-V10
    tree = make_tree(tmp_path)
    (tree / "docs" / "private").mkdir(parents=True)
    (tree / "docs" / "private" / "x.md").write_text("secret\n", encoding="utf-8")
    assert_bites(tree, rules, "docs/private")


def test_manifest_placeholder_bites(tmp_path, rules):  # mechanics-V11
    tree = make_tree(tmp_path)
    (tree / "PUBLISHING.md").write_text(
        "<!-- PUBLISH-MANIFEST:BEGIN -->\n_Not yet generated_\n<!-- PUBLISH-MANIFEST:END -->\n",
        encoding="utf-8",
    )
    assert_bites(tree, rules, "PUBLISHING.md")


def test_manifest_markers_missing_bites(tmp_path, rules):  # mechanics-V11
    tree = make_tree(tmp_path)
    (tree / "PUBLISHING.md").write_text("# no markers here\n", encoding="utf-8")
    assert_bites(tree, rules, "PUBLISHING.md")


def test_wrong_tree_shape_is_usage_error(tmp_path, rules):  # mechanics-V2
    empty = tmp_path / "not-an-export"
    empty.mkdir()
    with pytest.raises(Exception) as exc:
        audit_tree(empty, rules, min_files=1)
    assert "export" in str(exc.value).lower()


def test_vacuous_pass_guard(tmp_path, rules):  # mechanics-V2
    tree = make_tree(tmp_path)
    report = audit_tree(tree, rules, min_files=9999)
    assert not report.ok
    assert any("min_files" in f.detail or "floor" in f.detail for f in report.findings)


def test_unreadable_file_is_a_finding_not_a_skip(tmp_path, rules):  # mechanics-V6
    tree = make_tree(tmp_path)
    bad = tree / "locked.md"
    bad.write_text("fine\n", encoding="utf-8")
    bad.chmod(0)
    try:
        assert_bites(tree, rules, "locked.md")
    finally:
        bad.chmod(0o644)


# ------------------------------------------------------------ zones


def test_framing_token_in_living_zone_bites(tmp_path, rules):  # semantic-SL-02
    tree = make_tree(tmp_path)
    (tree / "docs").mkdir(exist_ok=True)
    (tree / "docs" / "guide.md").write_text("JOBWORD in a living doc\n", encoding="utf-8")
    assert_bites(tree, rules, "guide.md")


def test_framing_token_in_archive_zone_warns_not_fails(tmp_path, rules):  # semantic-SL-02
    tree = make_tree(tmp_path)
    arch = tree / ".scratch" / "reflow"
    arch.mkdir(parents=True)
    (arch / "old-review.md").write_text("JOBWORD quoted in an archived review\n")
    report = run(tree, rules)
    assert report.ok, [f"{f.path}:{f.kind}" for f in report.findings]
    assert any("JOBWORD" in w.detail or "framing" in w.kind for w in report.warnings)


def test_hard_token_in_archive_zone_still_bites(tmp_path, rules):  # no zone for hard
    tree = make_tree(tmp_path)
    arch = tree / ".scratch"
    arch.mkdir()
    (arch / "old.md").write_text("玄光资本\n", encoding="utf-8")
    assert_bites(tree, rules, "old.md")


# ------------------------------------------- grok RP-1 (publish-gate-review) fixes


def test_rewrite_only_literal_is_also_hard(tmp_path, rules):  # RP-1 BLOCKER 1
    # /Users/fakeuser is in [rewrite] only; the audit (safety net) must still bite a
    # tree that contains it, in case export rewrite is skipped/partial/variant-spelled.
    tree = make_tree(tmp_path)
    (tree / "leak.md").write_text("path is /Users/fakeuser/secret\n", encoding="utf-8")
    assert_bites(tree, rules, "leak.md")


def test_rules_no_todo_but_unconfirmed_fails_closed(tmp_path):  # RP-1 BLOCKER 2
    # Stripping the TODO marker without POSITIVELY confirming prior-employers are filled
    # must still fail closed — absence-of-TODO is not affirmation.
    p = tmp_path / "r.txt"
    p.write_text("[hard]\n玄光资本\n[framing]\nJOBWORD\n[rewrite]\nx => y\n", encoding="utf-8")
    with pytest.raises(RulesError):
        load_rules(p)


def test_png_itxt_compressed_bites(tmp_path, rules):  # RP-1 major (iTXt flag=1)
    tree = make_tree(tmp_path)
    import zlib as _zlib

    text = _zlib.compress("shot at 玄光资本".encode())
    # iTXt: keyword\0 compflag(1) compmethod(1) lang\0 translated\0 <compressed text>
    payload = b"Comment\x00" + b"\x01" + b"\x00" + b"en\x00" + b"\x00" + text
    (tree / "fig.png").write_bytes(_png_with_chunk(b"iTXt", payload))
    assert_bites(tree, rules, "fig.png")


def test_u8_escape_bites(tmp_path, rules):  # RP-1 major (\UXXXXXXXX 8-digit)
    tree = make_tree(tmp_path)
    esc = "".join("\\" + "U" + f"{ord(c):08x}" for c in "玄光资本")
    (tree / "u8.md").write_text('{"t": "' + esc + '"}', encoding="utf-8")
    assert_bites(tree, rules, "u8.md")


def test_framing_in_binary_bites_living_zone(tmp_path, rules):  # RP-1 major
    tree = make_tree(tmp_path)
    (tree / "docs").mkdir(exist_ok=True)
    (tree / "docs" / "b.dat").write_bytes(b"\x00" + "JOBWORD".encode("utf-16-le") + b"\x00")
    assert_bites(tree, rules, "b.dat")


def test_archive_in_tree_refused(tmp_path, rules):  # RP-1 major (gzip/zip opaque)
    import gzip as _gzip

    tree = make_tree(tmp_path)
    (tree / "blob.gz").write_bytes(_gzip.compress("玄光资本".encode()))
    assert_bites(tree, rules, "blob.gz")


def test_base64_of_any_hard_token_bites(tmp_path, rules):  # RP-1 minor (b64 generic)
    import base64 as _b64

    tree = make_tree(tmp_path)
    blob = _b64.b64encode(b"Nebulight").decode("ascii")
    (tree / "b.md").write_text(f"payload={blob}\n", encoding="utf-8")
    assert_bites(tree, rules, "b.md")


def test_css_hex_escape_bites(tmp_path, rules):  # RP-1 minor (CSS backslash-hex, no-u)
    tree = make_tree(tmp_path)
    (tree / "s.css").write_text('content: "\\7384 \\5149 \\8d44 \\672c";\n', encoding="utf-8")
    assert_bites(tree, rules, "s.css")


def test_punycode_bites(tmp_path, rules):  # RP-1 minor
    tree = make_tree(tmp_path)
    puny = "xn--" + "玄光资本".encode("punycode").decode("ascii")
    (tree / "p.md").write_text(f"host: {puny}.example\n", encoding="utf-8")
    assert_bites(tree, rules, "p.md")


def test_quoted_printable_bites(tmp_path, rules):  # RP-1 minor
    tree = make_tree(tmp_path)
    qp = quopri.encodestring("玄光资本".encode()).decode("ascii")
    (tree / "q.eml").write_text(f"Subject: {qp}\n", encoding="utf-8")
    assert_bites(tree, rules, "q.eml")


def test_utf7_bites(tmp_path, rules):  # RP-1 minor
    tree = make_tree(tmp_path)
    u7 = "玄光资本".encode("utf-7").decode("ascii")
    (tree / "u7.md").write_text(f"name: {u7}\n", encoding="utf-8")
    assert_bites(tree, rules, "u7.md")


# ------------------------------------------------------ rules fail-closed


def test_rules_missing_fails_closed(tmp_path):  # mechanics-V1
    with pytest.raises(RulesError):
        load_rules(tmp_path / "nope.txt")


def test_rules_comment_only_fails_closed(tmp_path):  # location-V12
    p = tmp_path / "r.txt"
    p.write_text("# only comments\n\n[hard]\n# nothing\n[framing]\n[rewrite]\n")
    with pytest.raises(RulesError):
        load_rules(p)


def test_rules_todo_marker_fails_closed(tmp_path):
    p = tmp_path / "r.txt"
    p.write_text(RULES_TEXT + "\n# TODO-FILL-BY-OWNER: real names\n", encoding="utf-8")
    with pytest.raises(RulesError):
        load_rules(p)


def test_rules_doc_mentioning_marker_still_loads(tmp_path):
    # The marker check must fire on an unfilled TODO ENTRY, not on documentation that
    # merely names the marker — else a rules file that explains its own fail-closed
    # behaviour can never pass (found in real use).
    doc = "# fail-closed while a TODO-FILL-BY-OWNER entry remains\n" + RULES_TEXT
    p = tmp_path / "r.txt"
    p.write_text(doc, encoding="utf-8")
    rules = load_rules(p)  # must NOT raise
    assert rules.hard


def test_rules_bom_crlf_still_match(tmp_path):  # encoding-V3
    p = tmp_path / "r.txt"
    p.write_bytes(b"\xef\xbb\xbf" + RULES_TEXT.replace("\n", "\r\n").encode("utf-8"))
    rules = load_rules(p)
    tree = make_tree(tmp_path)
    (tree / "d.md").write_text("玄光资本\n", encoding="utf-8")
    report = audit_tree(tree, rules, min_files=1)
    assert not report.ok


# ------------------------------------------------------ receipt binding


def test_receipt_roundtrip_and_tamper_detection(tmp_path, rules):  # mechanics-V7
    tree = make_tree(tmp_path)
    receipt = tmp_path / "receipt.json"
    report = run(tree, rules)
    assert report.ok
    write_receipt(tree, receipt)
    assert verify_receipt(tree, receipt)
    (tree / "README.md").write_text("# tampered after audit\n", encoding="utf-8")
    assert not verify_receipt(tree, receipt)


def test_receipt_survives_git_init(tmp_path, rules):  # push-flow binding
    tree = make_tree(tmp_path)
    receipt = tmp_path / "receipt.json"
    write_receipt(tree, receipt)
    gitdir = tree / ".git" / "objects"
    gitdir.mkdir(parents=True)
    (gitdir / "blob").write_bytes(b"\x00fake")
    assert verify_receipt(tree, receipt)


# ------------------------------------------------------------- exit codes


def test_main_exit_codes(tmp_path, rules_file):  # mechanics-V6: codes must not be swallowed
    from harness.publish_audit import main

    tree = make_tree(tmp_path)
    args = ["--rules", str(rules_file), "--min-files", "1"]
    assert main(["--tree", str(tree), *args]) == 0
    (tree / "bad.md").write_text("玄光资本\n", encoding="utf-8")
    assert main(["--tree", str(tree), *args]) == 1
    assert main(["--tree", str(tmp_path / "no-such"), *args]) == 2
    bad_rules = ["--tree", str(tree), "--rules", str(tmp_path / "no-rules"), "--min-files", "1"]
    assert main(bad_rules) == 2
