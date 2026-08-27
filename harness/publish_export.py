"""Publish-export: build the desensitized public snapshot tree from tracked files only.

Design (frozen in .scratch/publish/bypass-enumeration.md):

- Enumerates `git ls-files -z` — tracked files only, never a working-dir copy
  (location-V2: cp -r ships untracked/gitignored secrets wholesale).
- Refuses tracked symlinks (location-V10).
- Excludes any file whose basename casefolds to timeline.md (mechanics-V13), plus the
  exact tracked paths in EXCLUDED_PATHS (whole-file exclusion, manifest-disclosed).
- Applies the private [rewrite] rules (literal -> visible marker) to every decodable
  text file, in rules-file order; pure Python, no sed droppings (mechanics-V5).
- Injects a redaction manifest into PUBLISHING.md between the PUBLISH-MANIFEST markers:
  file + marker + count only — the original string never appears (V6/V7 manifest
  self-leak). Archive-zone contextual-term counts are disclosed as per-file totals,
  never the terms themselves.
- Refuses to wipe an output dir that doesn't look like a previous export.

The export is NOT the gate: harness/publish_audit.py must PASS on the result before push.
Exit codes: 0 ok, 2 error.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from harness.publish_audit import (
    DEFAULT_RULES,
    MANIFEST_BEGIN,
    MANIFEST_END,
    Rules,
    _zone_is_archive,
    load_rules,
)


class ExportError(Exception):
    pass


# Whole-file exclusions by exact tracked path, same mechanism as the timeline.md
# basename rule: excluded before rewrite, listed in the PUBLISHING.md manifest's
# "files excluded" line. For archive-zone evidence artifacts that trip a [hard]
# rule inside encoded payloads (where a [rewrite] cannot reach) — the original
# stays untouched in the private repo; the snapshot simply does not carry it.
EXCLUDED_PATHS: frozenset[str] = frozenset(
    {
        ".scratch/dispatch/v0.3-00-blade-plumbing/ticket.md",
    }
)


@dataclass
class ExportResult:
    manifest_rewrites: dict[str, dict[str, int]] = field(default_factory=dict)
    excluded: list[str] = field(default_factory=list)
    binaries: list[str] = field(default_factory=list)
    archive_framing: dict[str, int] = field(default_factory=dict)
    files_exported: int = 0


def _git_lines(source: Path, *args: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(source), *args], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise ExportError(f"git {' '.join(args)} failed in {source}: {proc.stderr.strip()}")
    return proc.stdout.split("\0") if "-z" in args else proc.stdout.splitlines()


def _tracked_files(source: Path) -> list[str]:
    files = [f for f in _git_lines(source, "ls-files", "-z") if f]
    symlinks = [
        line.split("\t", 1)[1]
        for line in _git_lines(source, "ls-files", "-s")
        if line.startswith("120000 ")
    ]
    if symlinks:
        raise ExportError(f"tracked symlinks refused: {symlinks}")
    return files


def _prepare_out(out: Path) -> None:
    if out.exists():
        entries = list(out.iterdir())
        if entries and not (out / "PUBLISHING.md").exists():
            raise ExportError(
                f"refusing to wipe {out}: non-empty and not a previous export "
                "(no PUBLISHING.md)"
            )
        shutil.rmtree(out)
    out.mkdir(parents=True)


def _build_manifest(res: ExportResult) -> str:
    lines: list[str] = []
    lines.append(f"- files exported: **{res.files_exported}**")
    lines.append(f"- files excluded: {', '.join('`' + e + '`' for e in res.excluded) or 'none'}")
    if res.manifest_rewrites:
        lines.append("- visible redactions (file — marker × count):")
        for rel in sorted(res.manifest_rewrites):
            for marker, count in sorted(res.manifest_rewrites[rel].items()):
                lines.append(f"  - `{rel}` — {marker} × {count}")
    else:
        lines.append("- visible redactions: none")
    if res.archive_framing:
        lines.append(
            "- archive-zone framing-term hits (terms not reproduced here; "
            "policy above):"
        )
        for rel in sorted(res.archive_framing):
            lines.append(f"  - `{rel}` — {res.archive_framing[rel]} hits")
    if res.binaries:
        lines.append(
            "- binary files shipped (raw-byte scanned by the audit): "
            + ", ".join("`" + b + "`" for b in sorted(res.binaries))
        )
    return "\n".join(lines)


def _inject_manifest(out: Path, res: ExportResult) -> None:
    pub = out / "PUBLISHING.md"
    if not pub.exists():
        raise ExportError("source tree has no PUBLISHING.md — cannot record the manifest")
    text = pub.read_text(encoding="utf-8")
    if MANIFEST_BEGIN not in text or MANIFEST_END not in text:
        raise ExportError("PUBLISHING.md lacks PUBLISH-MANIFEST markers")
    head, rest = text.split(MANIFEST_BEGIN, 1)
    _, tail = rest.split(MANIFEST_END, 1)
    pub.write_text(
        head + MANIFEST_BEGIN + "\n" + _build_manifest(res) + "\n" + MANIFEST_END + tail,
        encoding="utf-8",
    )


def export_snapshot(source: Path, out: Path, rules_path: Path) -> ExportResult:
    source, out = Path(source), Path(out)
    rules: Rules = load_rules(Path(rules_path))
    if out.resolve() == source.resolve() or out.resolve() in source.resolve().parents:
        raise ExportError(f"output dir {out} would clobber the source tree")

    files = _tracked_files(source)
    _prepare_out(out)

    res = ExportResult()
    for rel in files:
        src = source / rel
        if Path(rel).name.casefold() == "timeline.md" or rel in EXCLUDED_PATHS:
            res.excluded.append(rel)
            continue
        data = src.read_bytes()
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            text: str | None = data.decode("utf-8") if b"\x00" not in data else None
        except UnicodeDecodeError:
            text = None
        if text is None:
            dst.write_bytes(data)
            res.binaries.append(rel)
            res.files_exported += 1
            continue
        counts: dict[str, int] = {}
        for lit, marker in rules.rewrite:
            n = text.count(lit)
            if n:
                counts[marker] = counts.get(marker, 0) + n
                text = text.replace(lit, marker)
        if counts:
            res.manifest_rewrites[rel] = counts
        if _zone_is_archive(rel):
            hits = sum(text.casefold().count(term.casefold()) for term in rules.framing)
            if hits:
                res.archive_framing[rel] = hits
        dst.write_text(text, encoding="utf-8")
        res.files_exported += 1

    _inject_manifest(out, res)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=".")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules", default=str(DEFAULT_RULES))
    args = ap.parse_args(argv)
    try:
        res = export_snapshot(Path(args.source), Path(args.out), Path(args.rules))
    except Exception as exc:  # noqa: BLE001 - CLI boundary, everything is fatal here
        print(f"publish-export: ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        f"publish-export: {res.files_exported} files -> {args.out}; "
        f"excluded {len(res.excluded)}; rewrites in {len(res.manifest_rewrites)} files; "
        f"{len(res.binaries)} binaries"
    )
    print("publish-export: now run harness/publish_audit.py on the output before ANY push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
