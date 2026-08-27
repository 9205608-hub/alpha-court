"""Publish-audit gate: scan a candidate public snapshot tree for leaks before push.

Design (frozen in .scratch/publish/bypass-enumeration.md, 4-lens enumeration, 56 vectors):

- The gate carries ZERO sensitive literals (location-V3: the gate must not be the
  carrier). Every pattern loads from a private rules file (docs/private/publish-rules.txt,
  gitignored, never shipped), fail-closed.
- Hard patterns fail EVERYWHERE; framing patterns fail in the living zone and are
  counted as warnings in the archive zone (.scratch/** + the disclosure-boundary doc),
  disclosed rather than silently exempted. No other suppression mechanism exists.
- Every [rewrite] source literal is ALSO hard-banned in the output (the audit is the
  safety net: a skipped/partial export rewrite must not slip a rewrite-only literal
  through — grok RP-1 blocker on the personal home path).
- Every file is scanned through a decode battery (raw; \\uXXXX x2; \\UXXXXXXXX; CSS/JS
  \\XXXX and \\xXX hex; percent; HTML entities; base64; punycode; quoted-printable;
  UTF-7; NFKC/NFKD; zero-width strip; condensed) with casefolded SUBSTRING matching —
  no word boundaries (pinyin hides inside identifiers).
- Binary files are raw-byte scanned (hard AND framing needles); PNG text chunks
  (tEXt / zTXt / compressed iTXt) are parsed and decompressed. Archive/compressed
  containers (gzip/zip/xz/bz2/…) are refused, not inflated. Unreadable/undecodable
  files are findings, never skips.
- Structural checks: TIMELINE basename (casefold), docs/private, symlinks, PUBLISHING.md
  manifest populated, scanned-count floor (vacuous-PASS guard), export-tree shape guard.
- Rules fail closed on missing/empty/undecodable, on the TODO marker, AND unless the
  owner has added the PUBLISH-RULES-CONFIRMED affirmation (absence of TODO is not
  affirmation — grok RP-1 blocker on prior-employer coverage).
- PASS writes a content-hash receipt; the push step re-verifies it (TOCTOU bind).

Exit codes: 0 pass, 1 findings, 2 usage / fail-closed rules errors.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import html
import json
import quopri
import re
import struct
import sys
import unicodedata
import zlib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_RULES = Path("docs/private/publish-rules.txt")
DEFAULT_MIN_FILES = 100
MANIFEST_BEGIN = "<!-- PUBLISH-MANIFEST:BEGIN -->"
MANIFEST_END = "<!-- PUBLISH-MANIFEST:END -->"
MANIFEST_PLACEHOLDER = "_Not yet generated"
ARCHIVE_ZONE_PREFIXES = (".scratch/",)
ARCHIVE_ZONE_FILES = ("docs/case-study-disclosure-boundary.md",)
TODO_MARKER = "TODO-FILL-BY-OWNER"
# Positive owner affirmation that prior-employer names are filled. Absence of the
# TODO marker is NOT affirmation (grok RP-1 blocker) — the owner must add this line.
CONFIRM_SENTINEL = "PUBLISH-RULES-CONFIRMED"

_UNESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_UNESCAPE8_RE = re.compile(r"\\U([0-9a-fA-F]{8})")
_CSSHEX_RE = re.compile(r"\\([0-9a-fA-F]{2,6})\s?")
_XHEX_RE = re.compile(r"\\x([0-9a-fA-F]{2})")
_PCT_RE = re.compile(r"%[0-9a-fA-F]{2}")
_B64_RE = re.compile(r"[A-Za-z0-9+/]{8,}={0,2}")
_PUNY_RE = re.compile(r"\bxn--[a-z0-9-]+", re.IGNORECASE)
# Cf = format chars (zero-width & friends); we flag every one of them.
_CONDENSE_STRIP = set("*_`~ \t\r\n-|")
# Archive/compressed containers have no place in a source snapshot; refused, not inflated.
_ARCHIVE_MAGIC = (b"\x1f\x8b", b"PK\x03\x04", b"PK\x05\x06", b"\xfd7zXZ\x00", b"BZh", b"7z\xbc\xaf")
_ARCHIVE_SUFFIXES = (".gz", ".zip", ".whl", ".tar", ".tgz", ".xz", ".bz2", ".7z", ".rar", ".jar")


class RulesError(Exception):
    """The private rules file is missing, unfinished, or unusable (fail closed)."""


class AuditUsageError(Exception):
    """The audited path does not look like an export tree (wrong-tree guard)."""


@dataclass
class Rules:
    hard: list[str]
    framing: list[str]
    rewrite: list[tuple[str, str]]


@dataclass
class Finding:
    path: str
    kind: str
    detail: str


@dataclass
class AuditReport:
    ok: bool = True
    findings: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    files_walked: int = 0


# ------------------------------------------------------------------ rules


def load_rules(path: Path) -> Rules:
    path = Path(path)
    if not path.exists():
        raise RulesError(f"rules file missing: {path} (fail closed — no rules, no publish)")
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RulesError(f"rules file undecodable: {exc}") from exc
    if any(
        ln.strip().lstrip("#").strip().startswith(TODO_MARKER) for ln in text.splitlines()
    ):
        raise RulesError(
            f"rules file still has a {TODO_MARKER} entry — owner must fill and remove those lines"
        )
    if not any(
        ln.strip().lstrip("#").strip() == CONFIRM_SENTINEL for ln in text.splitlines()
    ):
        raise RulesError(
            f"rules file lacks the {CONFIRM_SENTINEL} affirmation — the owner must add it "
            "AFTER filling prior-employer names (absence of the TODO marker is not affirmation)"
        )
    hard: list[str] = []
    framing: list[str] = []
    rewrite: list[tuple[str, str]] = []
    section = None
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or line == CONFIRM_SENTINEL:
            continue
        if line in ("[hard]", "[framing]", "[rewrite]"):
            section = line[1:-1]
            continue
        if section == "hard":
            hard.append(line)
        elif section == "framing":
            framing.append(line)
        elif section == "rewrite":
            if " => " not in line:
                raise RulesError(f"rules line {lineno}: rewrite entry needs 'literal => marker'")
            lit, marker = line.split(" => ", 1)
            lit, marker = lit.strip(), marker.strip()
            if not lit or not marker:
                raise RulesError(f"rules line {lineno}: empty literal or marker")
            rewrite.append((lit, marker))
        else:
            raise RulesError(f"rules line {lineno}: entry before any [section] header")
    if not hard:
        raise RulesError("rules [hard] section is empty (fail closed)")
    if not framing:
        raise RulesError("rules [framing] section is empty (fail closed)")
    return Rules(hard=hard, framing=framing, rewrite=rewrite)


# ---------------------------------------------------------------- helpers


def _sub_hex(pattern: re.Pattern, text: str) -> str:
    def _one(m: re.Match) -> str:
        try:
            return chr(int(m.group(1), 16))
        except (ValueError, OverflowError):
            return m.group(0)

    return pattern.sub(_one, text)


def _unescape_pass(text: str) -> str:
    return _UNESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


def _pct_decode(text: str) -> str:
    def _one(m: re.Match) -> str:
        return bytes([int(m.group(0)[1:], 16)]).decode("latin1")

    # decode byte-wise then attempt utf-8 repair on the whole string
    raw = _PCT_RE.sub(_one, text)
    try:
        return raw.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return raw


def _strip_format_chars(text: str) -> tuple[str, bool]:
    kept = []
    had = False
    for ch in text:
        if unicodedata.category(ch) == "Cf":
            had = True
            continue
        kept.append(ch)
    return "".join(kept), had


def _condense(text: str) -> str:
    return "".join(ch for ch in text if ch not in _CONDENSE_STRIP)


def _base64_decodes(text: str) -> list[str]:
    out: list[str] = []
    for m in _B64_RE.finditer(text):
        chunk = m.group(0)
        try:
            raw = base64.b64decode(chunk + "=" * (-len(chunk) % 4), validate=True)
        except (binascii.Error, ValueError):
            continue
        try:
            out.append(raw.decode("utf-8"))
        except UnicodeDecodeError:
            out.append(raw.decode("latin1"))
    return out


def _punycode_decodes(text: str) -> list[str]:
    out: list[str] = []
    for m in _PUNY_RE.finditer(text):
        label = m.group(0)[4:]
        try:
            out.append(label.encode("ascii").decode("punycode"))
        except (UnicodeError, ValueError):
            continue
    return out


def _quopri_decode(text: str) -> str:
    try:
        return quopri.decodestring(text.encode("latin1")).decode("utf-8", errors="replace")
    except (ValueError, UnicodeEncodeError):
        return text


def _utf7_decode(text: str) -> str:
    try:
        return text.encode("ascii").decode("utf-7")
    except (UnicodeError, ValueError):
        return text


def _text_variants(text: str) -> tuple[list[str], bool]:
    """All derived renderings for pattern matching + whether format chars were present."""
    stripped, had_zw = _strip_format_chars(text)
    collapsed = text.replace("\\\\", "\\")  # double-escaped \\uXXXX -> \uXXXX first
    u1 = _unescape_pass(text)
    u2 = _unescape_pass(_unescape_pass(collapsed))
    u8 = _sub_hex(_UNESCAPE8_RE, text)
    css = _sub_hex(_CSSHEX_RE, text)  # CSS/JS backslash-hex escapes (no 'u' prefix)
    xhex = _sub_hex(_XHEX_RE, text)  # \xE4\xB9\x9D byte escapes
    bases = [
        text,
        stripped,
        u1,
        u2,
        u8,
        css,
        xhex,
        _pct_decode(text),
        html.unescape(text),
        _quopri_decode(text),
        _utf7_decode(text),
    ]
    bases.extend(_base64_decodes(text))
    bases.extend(_punycode_decodes(text))
    variants = list(bases)
    variants.extend(unicodedata.normalize("NFKC", b) for b in bases)
    variants.extend(unicodedata.normalize("NFKD", b) for b in bases)
    return variants, had_zw


def _match_patterns(patterns: list[str], variants: list[str]) -> list[str]:
    hits = []
    folded = [v.casefold() for v in variants]
    for pat in patterns:
        p = pat.casefold()
        if any(p in v for v in folded):
            hits.append(pat)
    return hits


def _binary_needles(patterns: list[str]) -> list[bytes]:
    needles = []
    for pat in patterns:
        for variant in {pat, pat.lower(), pat.upper(), pat.casefold()}:
            for enc in ("utf-8", "utf-16-le", "utf-16-be"):
                try:
                    needles.append((variant.encode(enc), pat))
                except UnicodeEncodeError:
                    continue
    return needles


def _binary_hits(patterns: list[str], data: bytes) -> list[str]:
    return sorted({pat for needle, pat in _binary_needles(patterns) if needle in data})


def _png_text_payloads(data: bytes) -> list[str]:
    """Extract text carried in PNG tEXt/zTXt/iTXt chunks (decompressing zTXt/iTXt)."""
    out: list[str] = []
    i = 8
    while i + 8 <= len(data):
        (length,) = struct.unpack(">I", data[i : i + 4])
        typ = data[i + 4 : i + 8]
        payload = data[i + 8 : i + 8 + length]
        if typ == b"tEXt":
            out.append(payload.replace(b"\x00", b" ").decode("latin1", errors="replace"))
        elif typ == b"zTXt":
            key, _, rest = payload.partition(b"\x00")
            out.append(key.decode("latin1", errors="replace"))
            if rest[:1] == b"\x00":
                try:
                    out.append(zlib.decompress(rest[1:]).decode("utf-8", errors="replace"))
                except zlib.error:
                    out.append("<zTXt-undecompressable>")
        elif typ == b"iTXt":
            # keyword\0 compflag(1) compmethod(1) lang\0 translated\0 text
            keyword, _, rest = payload.partition(b"\x00")
            out.append(keyword.decode("utf-8", errors="replace"))
            comp_flag = rest[:1]
            body = rest[3:] if len(rest) >= 3 else b""
            _lang, _, rest2 = body.partition(b"\x00")
            _trans, _, textbytes = rest2.partition(b"\x00")
            if comp_flag == b"\x01":
                try:
                    out.append(zlib.decompress(textbytes).decode("utf-8", errors="replace"))
                except zlib.error:
                    out.append("<iTXt-undecompressable>")
            else:
                out.append(textbytes.decode("utf-8", errors="replace"))
        elif typ == b"IEND":
            break
        i += 12 + length
    return out


def _zone_is_archive(rel: str) -> bool:
    return rel.startswith(ARCHIVE_ZONE_PREFIXES) or rel in ARCHIVE_ZONE_FILES


# ------------------------------------------------------------------ audit


def _check_manifest(tree: Path, report: AuditReport) -> None:
    pub = tree / "PUBLISHING.md"
    text = pub.read_text(encoding="utf-8", errors="replace")
    if MANIFEST_BEGIN not in text or MANIFEST_END not in text:
        report.findings.append(
            Finding("PUBLISHING.md", "manifest", "manifest markers missing from PUBLISHING.md")
        )
        return
    body = text.split(MANIFEST_BEGIN, 1)[1].split(MANIFEST_END, 1)[0]
    if MANIFEST_PLACEHOLDER in body or not body.strip():
        report.findings.append(
            Finding("PUBLISHING.md", "manifest", "manifest not populated (placeholder present)")
        )


def audit_tree(tree: Path, rules: Rules, min_files: int = DEFAULT_MIN_FILES) -> AuditReport:
    tree = Path(tree)
    if not tree.is_dir():
        raise AuditUsageError(f"not a directory (is this really an export tree?): {tree}")
    if not (tree / "README.md").exists() or not (tree / "PUBLISHING.md").exists():
        raise AuditUsageError(
            f"{tree} does not look like an export tree (README.md/PUBLISHING.md missing) — "
            "refusing to audit the wrong tree"
        )
    if (tree / ".git").exists():
        raise AuditUsageError(f"{tree} contains .git — audit the raw export tree before git init")

    report = AuditReport()
    _check_manifest(tree, report)

    # Every [rewrite] source literal must ALSO be treated as hard-banned in the output:
    # the audit is the safety net, and the whole point of a rewrite rule is that the
    # original must not survive to the public tree (grok RP-1 blocker: home path was
    # rewrite-only, so a skipped/partial rewrite would pass the audit).
    hard_patterns = list(dict.fromkeys(rules.hard + [lit for lit, _ in rules.rewrite]))

    def _framing_entry(rel: str, kind: str, pat: str) -> None:
        entry = Finding(rel, kind, pat)
        (report.warnings if _zone_is_archive(rel) else report.findings).append(entry)

    entries = sorted(p for p in tree.rglob("*"))
    for p in entries:
        rel = p.relative_to(tree).as_posix()
        if p.is_symlink():
            report.findings.append(Finding(rel, "symlink", "symlinks are refused in exports"))
            continue
        if p.is_dir():
            if rel == "docs/private" or rel.startswith("docs/private/"):
                report.findings.append(Finding(rel, "private-dir", "docs/private in export"))
            continue
        report.files_walked += 1

        # structural: TIMELINE anywhere, any case; docs/private files
        if p.name.casefold() == "timeline.md":
            report.findings.append(Finding(rel, "timeline", "internal work log in export"))
        if rel.casefold().startswith("docs/private/"):
            report.findings.append(Finding(rel, "private-dir", "docs/private file in export"))

        # filename scan (same patterns, casefolded substring)
        for pat in _match_patterns(hard_patterns, [rel]):
            report.findings.append(Finding(rel, "hard-pattern-filename", pat))
        for pat in _match_patterns(rules.framing, [rel]):
            _framing_entry(rel, "framing-filename", pat)

        # content scan
        try:
            data = p.read_bytes()
        except OSError as exc:
            report.findings.append(Finding(rel, "unreadable", f"cannot read: {exc}"))
            continue

        # archives/compressed containers carry sensitive bytes opaquely — refused, not
        # inflated (a source snapshot has no business shipping them).
        if data[:6].startswith(_ARCHIVE_MAGIC) or p.suffix.lower() in _ARCHIVE_SUFFIXES:
            report.findings.append(
                Finding(rel, "archive", "compressed/archive container refused in export")
            )
            report.files_scanned += 1
            continue

        text: str | None = None
        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            try:
                text = data.decode("utf-16")
            except UnicodeDecodeError:
                text = None
        if text is None and b"\x00" not in data:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = None

        if text is None:
            # binary path: raw needles (hard AND framing) + PNG text chunks; never skipped
            texts = _png_text_payloads(data) if data.startswith(b"\x89PNG\r\n\x1a\n") else []
            hits = set(_binary_hits(hard_patterns, data))
            hits.update(_match_patterns(hard_patterns, texts) if texts else [])
            for pat in sorted(hits):
                report.findings.append(Finding(rel, "hard-pattern-binary", pat))
            fram = set(_binary_hits(rules.framing, data))
            fram.update(_match_patterns(rules.framing, texts) if texts else [])
            for pat in sorted(fram):
                _framing_entry(rel, "framing-binary", pat)
            report.files_scanned += 1
            continue

        variants, had_zw = _text_variants(text)
        if had_zw:
            report.findings.append(
                Finding(rel, "zero-width", "zero-width/format characters present")
            )
        for pat in _match_patterns(hard_patterns, variants + [_condense(text)]):
            report.findings.append(Finding(rel, "hard-pattern", pat))
        for pat in _match_patterns(rules.framing, variants):
            _framing_entry(rel, "framing", pat)
        report.files_scanned += 1

    if report.files_scanned != report.files_walked:
        report.findings.append(
            Finding(
                ".",
                "coverage",
                f"scanned {report.files_scanned} != walked {report.files_walked}",
            )
        )
    if report.files_scanned < min_files:
        report.findings.append(
            Finding(
                ".",
                "floor",
                f"files_scanned {report.files_scanned} < min_files {min_files} floor "
                "(vacuous-PASS guard)",
            )
        )
    report.ok = not report.findings
    return report


# ---------------------------------------------------------------- receipt


def _tree_hash(tree: Path) -> tuple[str, int]:
    tree = Path(tree)
    h = hashlib.sha256()
    count = 0
    for p in sorted(tree.rglob("*")):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(tree).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue  # receipt must survive the post-audit `git init` in the push flow
        h.update(rel.encode("utf-8") + b"\x00")
        h.update(hashlib.sha256(p.read_bytes()).digest())
        count += 1
    return h.hexdigest(), count


def write_receipt(tree: Path, receipt: Path) -> None:
    digest, count = _tree_hash(tree)
    Path(receipt).write_text(
        json.dumps({"tree_sha256": digest, "file_count": count, "tree": str(Path(tree))}),
        encoding="utf-8",
    )


def verify_receipt(tree: Path, receipt: Path) -> bool:
    try:
        data = json.loads(Path(receipt).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    digest, count = _tree_hash(tree)
    return data.get("tree_sha256") == digest and data.get("file_count") == count


# -------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tree", required=True, help="export tree to audit")
    ap.add_argument("--rules", default=str(DEFAULT_RULES))
    ap.add_argument("--min-files", type=int, default=DEFAULT_MIN_FILES)
    ap.add_argument("--receipt", default=None, help="write PASS receipt here")
    args = ap.parse_args(argv)

    try:
        rules = load_rules(Path(args.rules))
    except RulesError as exc:
        print(f"publish-audit: RULES ERROR (fail closed): {exc}", file=sys.stderr)
        return 2
    try:
        report = audit_tree(Path(args.tree), rules, min_files=args.min_files)
    except AuditUsageError as exc:
        print(f"publish-audit: USAGE ERROR: {exc}", file=sys.stderr)
        return 2

    for w in report.warnings:
        print(f"WARN  {w.path}: {w.kind}: {w.detail}")
    for f in report.findings:
        print(f"FAIL  {f.path}: {f.kind}: {f.detail}")
    print(
        f"publish-audit: scanned {report.files_scanned}/{report.files_walked} files, "
        f"{len(report.findings)} findings, {len(report.warnings)} archive-zone warnings"
    )
    if not report.ok:
        return 1
    if args.receipt:
        write_receipt(Path(args.tree), Path(args.receipt))
        print(f"publish-audit: PASS receipt -> {args.receipt}")
    print("publish-audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
