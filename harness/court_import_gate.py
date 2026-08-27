"""Static AST gate for iron law #2: court/ must not import market-specific code.

The validation kernel (`court/`: DSR/PBO/BHY/empirical-null) is market-agnostic — calendars,
price limits, universe defs, and data feeds live in `adapters/`. This gate reads the SOURCE
(not the runtime) and complements the existing import-time dynamic smoke test, which only sees
imports that execute at `import court` time and so misses lazy / TYPE_CHECKING / non-qlib /
importlib imports.

ALLOWLIST (design decision, `.scratch/court-import/design-decisions.md`): a `court/**/*.py`
module may import ONLY:
  - the stdlib (`sys.stdlib_module_names` of the running interpreter),
  - `__future__`,
  - court itself (`court`, `court.*`, and in-package relative imports),
  - exactly the modules in ALLOWED_THIRD_PARTY below (court's real deps — numpy, scipy).
Anything else is a violation. Stronger than a blocklist: any NEW market lib is caught
automatically. Adding a legit non-market dep is a DELIBERATE one-line edit here (a checkpoint,
not a wall).

HONEST CEILING (do not oversell — enum V01/V09/V13): this proves court does not *import* market
code. It does NOT prove court is semantically market-agnostic. Coupling with no import node — a
qlib calendar object passed into `judge()`, a hard-coded 252 / 10% price-limit constant, market
data read from a hard-coded path — is structurally outside an import gate (the anti-pattern gate,
the import-time smoke, and code review cover those angles).

WHAT IS FLAGGED (coarse, because court has no legitimate use for them): `exec`/`eval`/`compile`
and the code-loaders `spec_from_file_location`/`SourceFileLoader`/`run_module`/`run_path` in any
spelling (bare, attribute, or a tracked rebind); dynamic imports `__import__`/`import_module`
(any receiver + rebind chains) with a literal arg checked and a non-literal arg flagged.

DECLARED LIMITS (out of static reach — labelled, not silently missed): deep call indirection
(`getattr(builtins, "__import__")(...)`, `vars(importlib)["import_module"](...)`,
`functools.partial(...)`, `operator.methodcaller(...)`); `exec`/`eval` of a source *string*
(the string is not re-parsed); `.pyx`/`.pyi`/`.so` non-`.py` carriers; a third-party package
that *shadows* a top-level name of stdlib/court/numpy/scipy (names are trusted, not provenance);
and `sys.stdlib_module_names` is the running interpreter's set (version-dependent — the dev's
own python is the reference).

Exit codes: 0 clean, 1 violations, 2 usage.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Court's only legitimate third-party dependencies. Numerical, not market-specific.
# To add one (e.g. the day court genuinely needs pandas), append it here CONSCIOUSLY — that
# deliberate edit is the point of an allowlist.
ALLOWED_THIRD_PARTY = frozenset({"numpy", "scipy"})

_STDLIB = frozenset(sys.stdlib_module_names)
_IMPORT_FUNCS = frozenset({"__import__", "import_module"})  # + tracked aliases, per file
_EXEC_FUNCS = frozenset({"exec", "eval", "compile"})  # + tracked aliases, per file
# stdlib code-loaders that import-by-path without an import node — court has no reason to use them.
_LOADER_ATTRS = frozenset({"spec_from_file_location", "SourceFileLoader", "run_module", "run_path"})


@dataclass
class Violation:
    path: str
    lineno: int
    module: str
    reason: str


def _top_level(module: str) -> str:
    return module.split(".", 1)[0]


def _pkg_parts(path: str) -> list[str]:
    """Package parts of a court file: 'court/x.py' -> ['court']; 'court/sub/x.py' -> [..]."""
    parts = Path(path).parts
    return list(parts[:-1])  # drop the filename


def _allowed(top: str) -> bool:
    return (
        top in ("court", "__future__", "__main__")
        or top in ALLOWED_THIRD_PARTY
        or top in _STDLIB
    )


def _resolve_relative(pkg: list[str], level: int, tail: str) -> str:
    """Resolve a relative import to its absolute TOP-LEVEL name.

    `level` is the number of leading dots; `tail` is the module (for `from .x`) or an imported
    name (for `from . import x`). A file in package `court` at level 1 stays in court; level >= 2
    climbs to a sibling of court (e.g. `adapters`) and escapes the kernel.
    """
    climbed = pkg[: len(pkg) - (level - 1)] if level - 1 <= len(pkg) else []
    abs_parts = [*climbed, *tail.split(".")] if tail else list(climbed)
    return abs_parts[0] if abs_parts else (tail.split(".", 1)[0] if tail else "court")


def _is_of_kind(node: ast.AST, names: frozenset[str], aliases: set[str]) -> bool:
    """Does this expr resolve to one of `names` — as `builtins.X` / `mod.X` (Attribute), the bare
    name, or a tracked rebind alias? Covers builtins.__import__, il.import_module, builtins.exec."""
    if isinstance(node, ast.Attribute) and node.attr in names:
        return True
    if isinstance(node, ast.Name) and (node.id in names or node.id in aliases):
        return True
    return False


def _tracked_aliases(tree: ast.AST) -> tuple[set[str], set[str]]:
    """(import_aliases, exec_aliases) — names rebound to __import__/import_module and exec/eval/
    compile, via `from importlib import import_module as X` / `from builtins import __import__ as X`
    OR a simple assignment `X = <it>` / `X = mod.<it>` / `X = <alias>`. Fixpoint catches chains."""
    imp: set[str] = set()
    exe: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                bound = a.asname or a.name
                if a.name in _IMPORT_FUNCS and node.module in ("importlib", "builtins"):
                    imp.add(bound)
                if a.name in _EXEC_FUNCS and node.module == "builtins":
                    exe.add(bound)
    for _ in range(8):  # bounded fixpoint; a deep rebind chain in court is pathological anyway
        grew = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for pool, names in ((imp, _IMPORT_FUNCS), (exe, _EXEC_FUNCS)):
                if _is_of_kind(node.value, names, pool):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name) and tgt.id not in pool:
                            pool.add(tgt.id)
                            grew = True
        if not grew:
            break
    return imp, exe


def _dynamic_import_target(node: ast.Call, import_aliases: set[str]) -> tuple[bool, str | None]:
    """(is_dynamic_import, literal_module_or_None). __import__/import_module, any spelling."""
    if not _is_of_kind(node.func, _IMPORT_FUNCS, import_aliases):
        return False, None
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return True, node.args[0].value
    return True, None  # non-literal arg — cannot resolve; court should not dynamic-import at all


def check_source(text: str, path: str = "court/<probe>.py") -> list[Violation]:
    """Parse a court source, return import-boundary violations. Fails CLOSED on any parse error."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        return [Violation(path, getattr(exc, "lineno", 0) or 0, "<unparseable>",
                          f"court file does not parse ({type(exc).__name__}) — failing closed")]

    pkg = _pkg_parts(path)
    import_aliases, exec_aliases = _tracked_aliases(tree)
    out: list[Violation] = []

    def flag(lineno: int, module: str, reason: str) -> None:
        out.append(Violation(path, lineno, module, reason))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:  # `import a, b` -> every alias, on alias.name (not asname)
                top = _top_level(a.name)
                if not _allowed(top):
                    flag(node.lineno, a.name, f"forbidden import '{a.name}' (top-level '{top}')")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                top = _top_level(node.module or "")
                if not _allowed(top):
                    flag(node.lineno, node.module or "?", f"forbidden import from '{node.module}'")
            elif node.module is not None:
                top = _resolve_relative(pkg, node.level, node.module)
                if not _allowed(top):
                    flag(node.lineno, node.module,
                         f"relative import escapes court to '{top}' "
                         f"(from {'.' * node.level}{node.module})",
                    )
            else:  # from ... import name1, name2  (module is None — the names carry the target)
                for a in node.names:
                    top = _resolve_relative(pkg, node.level, a.name)
                    if not _allowed(top):
                        flag(node.lineno, a.name,
                             f"relative import escapes court to '{top}' "
                             f"(from {'.' * node.level} import {a.name})",
                        )
        elif isinstance(node, ast.Call):
            func = node.func
            if _is_of_kind(func, _EXEC_FUNCS, exec_aliases):  # exec/eval/compile, any spelling
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "exec")
                flag(node.lineno, name,
                     f"'{name}(...)' in court — cannot verify what it loads (no exec/eval here)")
                continue
            loader = None
            if isinstance(func, ast.Attribute) and func.attr in _LOADER_ATTRS:
                loader = func.attr
            elif isinstance(func, ast.Name) and func.id in _LOADER_ATTRS:
                loader = func.id
            if loader:
                flag(node.lineno, loader,
                     f"'{loader}(...)' loads code by path in court (market code -> adapters/)")
                continue
            is_dyn, lit = _dynamic_import_target(node, import_aliases)
            if is_dyn:
                if lit is None:
                    flag(node.lineno, "<dynamic>",
                         "dynamic import with a non-literal argument — court must not do this",
                    )
                else:
                    top = _top_level(lit)
                    if not _allowed(top):
                        flag(node.lineno, lit, f"dynamic import of forbidden module '{lit}'")
    return out


def scan_court(root: Path) -> list[Violation]:
    """Recursively scan a court/ tree. A symlinked file OR directory fails CLOSED — os.walk does
    not descend a symlinked dir (followlinks=False), so `court/sub -> ../adapters` would be an
    invisible market carrier; we flag it instead of walking past it (grok RP-1)."""
    root = Path(root)
    out: list[Violation] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dp = Path(dirpath)
        for d in sorted(dirnames):
            if (dp / d).is_symlink():
                rel = (dp / d).relative_to(root.parent).as_posix()
                out.append(Violation(rel, 0, "<symlink-dir>",
                                     "symlinked directory under court/ — target unverifiable"))
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            f = dp / fn
            rel = f.relative_to(root.parent).as_posix()
            if f.is_symlink():
                out.append(Violation(rel, 0, "<symlink>", "symlinked court/ file — unverifiable"))
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                out.append(Violation(rel, 0, "<unreadable>", "court file unreadable — fail closed"))
                continue
            out.extend(check_source(text, rel))
    return out


def _staged_court_paths(repo_root: Path) -> list[str]:
    import subprocess

    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only",
         "--diff-filter=ACMR", "-z"],
        cwd=repo_root, capture_output=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"git diff --cached failed: {out.stderr.decode('utf-8', 'replace')}")
    paths = out.stdout.decode("utf-8", "surrogateescape").split("\0")
    # every staged path under court/ (not only .py): a symlinked dir stages as one mode-120000
    # entry with no .py suffix, and must still be flagged (grok RP-1).
    return [p for p in paths if p and p.startswith("court/")]


def _staged_mode(repo_root: Path, rel: str) -> str | None:
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-s", "-z", "--", rel], cwd=repo_root, capture_output=True
    )
    rec = out.stdout.split(b"\0", 1)[0].decode("utf-8", "replace")
    return rec.split(" ", 1)[0] if rec else None


def scan_staged(repo_root) -> list[Violation]:
    """Scan STAGED court/**/*.py blobs (git show :path), not the working tree (B's V1)."""
    import subprocess

    repo_root = Path(repo_root)
    out: list[Violation] = []
    for rel in _staged_court_paths(repo_root):
        if _staged_mode(repo_root, rel) == "120000":  # symlink (file OR dir) staged under court/
            out.append(Violation(rel, 0, "<symlink>", "staged court/ symlink — unverifiable"))
            continue
        if not rel.endswith(".py"):
            continue  # a non-.py, non-symlink staged file under court/ carries no imports to check
        blob = subprocess.run(["git", "show", f":{rel}"], cwd=repo_root, capture_output=True)
        if blob.returncode != 0:
            out.append(Violation(rel, 0, "<unreadable>", "unreadable staged blob — fail closed"))
            continue
        try:
            text = blob.stdout.decode("utf-8")
        except UnicodeDecodeError:
            out.append(Violation(rel, 0, "<non-utf8>", "staged court not UTF-8 — fail closed"))
            continue
        out.extend(check_source(text, rel))
    return out


def _report(violations: list[Violation]) -> int:
    if not violations:
        print("court-import-gate: PASS — court/ imports only stdlib/__future__/court/numpy/scipy")
        return 0
    print(f"court-import-gate: FAIL — {len(violations)} import-boundary violation(s) in court/:",
          file=sys.stderr)
    for v in violations:
        print(f"  {v.path}:{v.lineno}: {v.reason}", file=sys.stderr)
    print("  court/ must stay market-agnostic (iron law #2); market code belongs in adapters/.",
          file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="harness.court_import_gate", description=__doc__)
    ap.add_argument("--staged", action="store_true", help="scan staged court/ blobs in the repo")
    ap.add_argument("--court", default="court", help="path to the court/ package (./court)")
    args = ap.parse_args(argv)
    if args.staged:
        return _report(scan_staged(Path.cwd()))
    root = Path(args.court)
    if not root.is_dir():
        print(f"court-import-gate: USAGE — {root} is not a directory", file=sys.stderr)
        return 2
    return _report(scan_court(root))


if __name__ == "__main__":
    raise SystemExit(main())
