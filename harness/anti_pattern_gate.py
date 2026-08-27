"""工位三 anti-pattern grep gate — a **high-recall cheap knife** for hand-rolled duplicates
of audited functionality (`backtest-reuse-guard`'s reuse lint; advisory + manual).

It scans factor/research `.py` code and flags lines that re-implement something the audited
oracle already provides — a "validation bypass" (a private statistic hands you a friendlier,
unreviewed number than `court`). It is advisory: you run it against your factor code; it does
not block anything and is not wired into pre-commit/CI (that stays [DESIGNED]).

DESIGN — anchor to code structure, and strip strings/comments with `tokenize`, so it does not
cry wolf on the audited `court` source, a legitimate *call* to court, a comment, a docstring,
or a config string (a bare-token grep's fatal flaw — a gate that cries wolf gets ignored):
- patterns anchor to a `def`, an inline mean/std/annualization, or a named correlation — never
  a bare `sharpe` / `n_trials` / `pbo` token (those are court's own API surface);
- exclusion is by path **component** (`court/`, `adapters/`, `tests/`, `harness/`, `examples/`,
  `gates/`, `docs/`) — NOT a substring (this repo lives under `alpha-court/`, so a substring
  exclusion on "court" would silently skip the whole tree);
- `tokenize` blanks string + comment spans (handles escapes, single- and multi-line
  docstrings, config strings) before matching, so a docstring mention can't bark and a
  trailing/escaped comment can't suppress code.

HONEST LIMITS — a line grep structurally cannot catch these (pinned in the tests):
- **precision, not just recall**: a `.corr(` / `.corrwith(` used for feature orthogonality or a
  price-volume factor, and a `cumprod`/`cumsum` diagnostic curve, are flagged too — the gate
  surfaces *candidates a human must justify or reuse-away*, it is not a precise auto-reject;
- hand-*expanded* arithmetic carries no token: a DIY Pearson, and — the worst duplicate the
  skill names — a Sharpe **standard error** dropping the skew/kurtosis correction, are invisible;
- aliased/renamed defs (`def risk_adjusted` / `def sortino` / a `lambda`), import-aliased calls
  (`pearsonr as pr; pr(...)` — the *import* is caught, the alias call is not), multi-line-split
  formulas, semantic synonyms (`phi`, `num_trials`), and DSL/config strings;
- a hand-rolled equity **for-loop** over dates (the `dates` iteration is common for legit
  loading, so a bare date-loop would cry wolf; only the vectorized `equity=…cumprod` is caught);
- `.ipynb` notebooks are **not scanned** — but the skip is reported (`skipped_notebooks`);
- it is manual (you can just not run it).
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import tokenize
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

DEFAULT_EXCLUDE = frozenset(
    {"court", "adapters", "tests", "harness", "gates", "docs", "examples", "out", "build",
     "dist", "site-packages", "node_modules", "__pycache__", ".git", ".venv", "venv"}
)

_MEAN = re.compile(r"\.mean\s*\(|\bmean\s*\(")
_STD = re.compile(r"\.std\s*\(|\bnp\.std\s*\(|\bnp\.var\s*\(")
_ANN = re.compile(r"\bsqrt\s*\(|\b(?:24[0-9]|25[0-9])\s*\*\*\s*0?\.5\b")
_STAT_DEF = re.compile(
    r"\bdef\s+\w*(?:pbo|cscv|deflat|dsr|fdr|bhy|empirical_null|noise_control|"
    r"expected_max|reality_check|newey|t_stat|p_from_t)\w*\s*\(",
    re.I,
)


def _sharpe_inline(code: str) -> bool:
    # a Sharpe = mean OVER std, annualized — all three, so a bare vol `std*sqrt(252)` is not it.
    return bool(_MEAN.search(code) and _STD.search(code) and _ANN.search(code))


# (name, remedy, matcher) — matcher(code) is truthy on a hand-roll.
_PATTERNS: list[tuple[str, str, Callable[[str], object]]] = [
    ("hand-rolled Sharpe (def)", "court.sharpe.sharpe_ratio",
     re.compile(r"\bdef\s+\w*sharpe\w*\s*\(", re.I).search),
    ("hand-rolled Sharpe (inline mean/std * annualization)", "court.sharpe", _sharpe_inline),
    ("correlation used as an IC", 'the adapter\'s Spearman evaluate(scores, "ic")',
     re.compile(r"\bcorrcoef\b|\.corr(?:with)?\s*\(|\b(?:spearmanr|pearsonr|kendalltau)\b").search),
    ("hand-rolled equity curve", "vectorbt / openalgo",
     re.compile(r"\b(?:equity|pnl|nav)\w*\s*=.*\.cum(?:prod|sum)\s*\(", re.I).search),
    ("hand-rolled court statistic (def)", "court.{sharpe,dsr,pbo,fdr,noise,tstats}",
     _STAT_DEF.search),
]


class Finding(NamedTuple):
    path: str
    lineno: int
    pattern: str
    remedy: str
    line: str


class ScanResult(NamedTuple):
    findings: list[Finding]
    skipped_notebooks: int


def _strip_comment_fallback(line: str) -> str:
    """Line-based #-strip (used only if tokenize fails on non-parseable text)."""
    q = None
    esc = False
    for i, ch in enumerate(line):
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
        elif q:
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
        elif ch == "#":
            return line[:i]
    return line


def _blank_strings_and_comments(text: str) -> list[str] | None:
    """Return lines with STRING and COMMENT token spans blanked to spaces (tokenize-based).

    This is the honest fix for docstring / config-string / escaped-comment false-positives:
    only real code survives to be matched. Returns None if the text does not tokenize.
    """
    lines = text.splitlines()
    grid = [list(ln) for ln in lines]
    blank = {tokenize.STRING, tokenize.COMMENT}
    if hasattr(tokenize, "FSTRING_MIDDLE"):
        blank.add(tokenize.FSTRING_MIDDLE)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type not in blank:
                continue
            (sr, sc), (er, ec) = tok.start, tok.end
            for r in range(sr, er + 1):
                idx = r - 1
                if idx >= len(grid):
                    continue
                c0 = sc if r == sr else 0
                c1 = ec if r == er else len(grid[idx])
                for c in range(c0, min(c1, len(grid[idx]))):
                    grid[idx][c] = " "
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return None
    return ["".join(row) for row in grid]


# `reuse-ok:` anywhere in the comment token (search, not anchored) so a second comment such as
# `# type: ignore  # reuse-ok: <reason>` still exempts; a non-empty reason is still required.
_REUSE_OK_RE = re.compile(r"reuse-ok:\s*(\S.*)$")


def _reuse_ok_lines(text: str) -> dict[int, str]:
    """Physical line numbers carrying a real trailing `# reuse-ok: <non-empty reason>` COMMENT.

    Uses tokenize so the marker counts ONLY as a genuine comment token — a `# reuse-ok:`
    sitting inside a string literal grants no exemption (ACK-01). An empty/whitespace reason
    is not accepted (the `\\S` in the pattern, ACK-04). Exemption is per-physical-line, so a
    top-of-file blanket cannot cover a later line (ACK-02/07). If the file does not tokenize,
    no line is exempted (fail-closed for the escape hatch, ACK-05).
    """
    acked: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                m = _REUSE_OK_RE.search(tok.string.strip())
                if m:
                    acked[tok.start[0]] = m.group(1).strip()
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return {}
    return acked


def scan_text(text: str, path: str = "<text>") -> list[Finding]:
    """Scan source text; return findings. Strings/comments are blanked before matching.

    A flagged physical line is exempted iff it carries a real trailing
    `# reuse-ok: <reason>` comment with a non-empty reason (see `_reuse_ok_lines`). The gate
    cannot judge whether the reason is *substantive* — that stays a human's/RP-1's job
    (CR-08 ceiling); it only raises the bar from silent hand-roll to a named reason on the line.
    """
    original = text.splitlines()
    code_lines = _blank_strings_and_comments(text)
    if code_lines is None:
        code_lines = [_strip_comment_fallback(ln) for ln in original]
    acked = _reuse_ok_lines(text)
    findings: list[Finding] = []
    for lineno, code in enumerate(code_lines, 1):
        if not code.strip():
            continue
        if lineno in acked:
            continue
        for name, remedy, matcher in _PATTERNS:
            if matcher(code):
                disp = original[lineno - 1].strip() if lineno - 1 < len(original) else code.strip()
                findings.append(Finding(path, lineno, name, remedy, disp))
    return findings


def _excluded(path: Path, exclude_dirs: frozenset[str]) -> bool:
    return bool(set(path.parts) & exclude_dirs) or any(p.startswith(".") for p in path.parts)


def _iter_py_files(root: Path, exclude_dirs: frozenset[str]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not d.startswith(".")]
        for fn in filenames:
            yield Path(dirpath) / fn


def scan_paths(paths, *, exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE) -> ScanResult:
    """Scan files/dirs. Non-.py is ignored; .ipynb is counted (skipped, not scanned).

    A directly-passed file inside an excluded dir is skipped too, so passing `court/x.py`
    behaves like the tree walk (audited source is never flagged).
    """
    findings: list[Finding] = []
    skipped_notebooks = 0
    for p in paths:
        p = Path(p)
        if p.is_file():
            if _excluded(p, exclude_dirs):
                continue
            candidates = [p]
        else:
            candidates = list(_iter_py_files(p, exclude_dirs))
        for f in candidates:
            if f.suffix == ".ipynb":
                skipped_notebooks += 1
                continue
            if f.suffix != ".py":
                continue
            try:
                findings.extend(scan_text(f.read_text(encoding="utf-8"), str(f)))
            except (OSError, UnicodeDecodeError):
                continue
    return ScanResult(findings, skipped_notebooks)


def scan_tree(root, *, exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE) -> list[Finding]:
    """Convenience: scan a directory tree, return findings only."""
    return scan_paths([root], exclude_dirs=exclude_dirs).findings


def _staged_paths(repo_root: Path) -> list[str]:
    """Repo-relative paths of ADDED/COPIED/MODIFIED/RENAMED files in the git index (null-safe)."""
    import subprocess

    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only",
         "--diff-filter=ACMR", "-z"],
        cwd=repo_root, capture_output=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"git diff --cached failed: {out.stderr.decode('utf-8', 'replace')}")
    return [p for p in out.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def _read_staged_blob(repo_root: Path, rel: str) -> bytes:
    import subprocess

    out = subprocess.run(
        ["git", "show", f":{rel}"], cwd=repo_root, capture_output=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"git show :{rel} failed: {out.stderr.decode('utf-8', 'replace')}")
    return out.stdout


def _staged_mode(repo_root: Path, rel: str) -> str | None:
    """The git index mode for a staged path ('100644', '100755', '120000'=symlink), or None."""
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-s", "-z", "--", rel], cwd=repo_root, capture_output=True,
    )
    rec = out.stdout.split(b"\0", 1)[0].decode("utf-8", "replace")
    return rec.split(" ", 1)[0] if rec else None


def scan_staged(repo_root, *, exclude_dirs: frozenset[str] = DEFAULT_EXCLUDE) -> ScanResult:
    """Scan the STAGED index content (not the working tree) of a git repo.

    Reads each staged blob with `git show :path` — so a hand-roll staged then reverted on
    disk is still caught (the working-tree/index split, enum V1). Exclusions apply to the
    repo-relative path. The `.py`/`.ipynb` suffix test is case-insensitive (a `.PY` on a
    case-insensitive filesystem is still Python — grok RP-1). A staged `.py` that is a symlink
    (index mode 120000) FAILS CLOSED — its blob is a path string, not source we can lint, so it
    cannot be used to smuggle a hand-roll past the scan (grok RP-1). A staged `.py` whose blob
    is not valid UTF-8 FAILS CLOSED (enum V11). A staged `.ipynb` is counted+noted, not scanned
    (declared limit, enum V5). No staged `.py` → clean PASS (enum V6/empty-args).
    """
    repo_root = Path(repo_root)
    findings: list[Finding] = []
    skipped_notebooks = 0
    for rel in _staged_paths(repo_root):
        path = Path(rel)
        if _excluded(path, exclude_dirs):
            continue
        suffix = path.suffix.lower()
        if suffix == ".ipynb":
            skipped_notebooks += 1
            continue
        if suffix != ".py":
            continue
        if _staged_mode(repo_root, rel) == "120000":
            findings.append(
                Finding(rel, 0, "staged .py is a symlink (cannot lint its target — blocking)",
                        "commit real .py source, not a symlink", "<symlink>")
            )
            continue
        blob = _read_staged_blob(repo_root, rel)
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(
                Finding(rel, 0, "staged .py is not valid UTF-8 (cannot lint — blocking)",
                        "commit decodable UTF-8 source", "<undecodable staged blob>")
            )
            continue
        findings.extend(scan_text(text, rel))
    return ScanResult(findings, skipped_notebooks)


def _main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="harness.anti_pattern_gate")
    p.add_argument("paths", nargs="*", help="factor/research .py files or dirs to scan")
    p.add_argument("--staged", action="store_true",
                   help="scan the git index (staged blobs) of the CWD's repo, not paths")
    args = p.parse_args(argv)

    if args.staged:
        if args.paths:
            p.error("--staged takes no path arguments (it scans the index)")
        result = scan_staged(Path.cwd())
    elif not args.paths:
        p.error("give paths to scan, or --staged")
    else:
        result = scan_paths(args.paths)
    if result.skipped_notebooks:
        print(
            f"anti-pattern-gate: NOTE — {result.skipped_notebooks} .ipynb notebook(s) not scanned "
            "(export cells to .py, or scan them by hand)",
            file=sys.stderr,
        )
    if not result.findings:
        print("anti-pattern-gate: PASS — no hand-rolled duplicates found")
        return 0
    print(
        f"anti-pattern-gate: FAIL — {len(result.findings)} candidate hand-roll(s) "
        "(reuse the audited oracle, or justify each):",
        file=sys.stderr,
    )
    for f in result.findings:
        print(f"  {f.path}:{f.lineno}: {f.pattern} → reuse {f.remedy}", file=sys.stderr)
        print(f"      {f.line}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
