# Candidate A — static AST court-import boundary gate: pinned decisions (2026-07-13)

Enforces iron law #2: `court/` (market-agnostic validation kernel) must not import market code.
Complements the existing IMPORT-TIME dynamic smoke (`test_court_market_agnostic`), which only
sees imports that actually execute at `import court` time — it misses lazy / TYPE_CHECKING /
non-qlib / importlib imports. This STATIC gate reads the source, not the runtime.

## Decisions (user /grilling)

- **ALLOWLIST** (not blocklist): a `court/**/*.py` module may import ONLY
  (a) stdlib (`sys.stdlib_module_names`), (b) `__future__`, (c) court itself
  (`court`, `court.*`, and in-package relative imports), (d) exactly `{numpy, scipy}`
  (court's only real third-party deps — verified; not even pandas). Anything else = violation.
  Stronger than a blocklist: any NEW market lib (baostock/akshare/unknown) is caught automatically.
- **Deploy**: a pytest test (static, over `court/`) + wired into the pre-commit hook over STAGED
  `court/**/*.py` blobs (reuse candidate B's staged-scan: `git show :path`, not the working tree).

## Resolution rules (to implement)

- Walk the WHOLE ast tree (imports inside functions / classes / `if TYPE_CHECKING:` /
  `try/except ImportError:` / conditionals are all seen — that's the dynamic smoke's blind spot).
- `import a.b.c` / `import qlib as q` → top-level = `a` / `qlib`. Exact top-level match against
  the allowlist (NOT prefix — `numpy_finance`/`courtside` must NOT be allowed by `numpy`/`court`).
- Relative imports: resolve against the file's package depth (grok RP-1: "level ≥ 2 escapes" is
  only true at package depth 1). A `court/x.py` (pkg `court`): `from .y` = court (allow),
  `from ..adapters` (level 2) escapes to the sibling top-level `adapters` (violation). A
  `court/sub/deep/x.py` (pkg `court.sub.deep`): `from ...adapters` (level 3) resolves to
  `court.adapters` — still WITHIN court (allow); escaping needs level 4. The escape level is
  package-depth + 1; resolve the absolute top-level and check it, don't hard-code a level threshold.
- Dynamic imports: `__import__("qlib")` and `importlib.import_module("qlib")` (and an aliased
  `import_module`) — a string-literal arg is resolved + checked; a NON-literal / computed arg is a
  VIOLATION (court has no business doing dynamic imports at all — fail-closed, not a blind spot).
- Parse failure (SyntaxError) → FAIL-CLOSED (a `court/*.py` that won't parse → violation), never a
  silent skip (mirrors B's non-utf8 discipline).
- Recurse subdirs of `court/` (a future `court/sub/market.py` is scanned); don't hard-code a file list.

## Declared limits (AST cannot see — label, don't pretend)

- Market code COPIED/pasted into `court/` with no import (hand-rolled) — not an import, so not this
  gate's job (the anti-pattern gate + the import-time smoke + code review cover structural coupling).
- `exec(...)` / `importlib.util.spec_from_file_location(...)` / `sys.path` manipulation then import —
  the AST sees the call but cannot resolve what it loads. Flag the *presence* of these in court as
  suspicious? (decide after enum) vs pure declared-limit.
- A `court/adapters/` subpackage imported as `court.adapters` is allowed by name, but its own files
  are scanned recursively, so a forbidden import inside it is still caught; only hand-rolled market
  logic there escapes (same as the copied-code limit).
- `sys.stdlib_module_names` is the RUNNING python's set — a stdlib module absent on an older/newer
  interpreter could false-flag/allow inconsistently (rare; the dev's own python is the reference).

## Methodology
enum-first (4-lens workflow) → bypass red-tests FIRST (CR-08) → implement → fresh grok RP-1.
