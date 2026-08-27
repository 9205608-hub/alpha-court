# Ticket: v0.2-12 — kernel robustness nits batch (TDD, red first, per-slice)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

A batch of robustness fixes from the v0.1/v0.2 audits. Each slice is small and
independent; each follows red → green. The common disease is **asymmetric
strictness**: the write path validates, the replay path trusts; or two
construction paths hand-copy state and silently diverge. All design decisions
below are frozen by the commander — implement, do not re-litigate.

**Compatibility guard (read first):** committed artifacts
(`examples/killer_demo/out/ledger.jsonl` and everything the test suite replays)
were produced by the validating write path and must still replay green under
every new fail-closed check. If any new validator reds on a committed artifact,
STOP that slice and report it honestly in the receipt (an honest `partial`
beats a dishonest `done`) — do NOT edit the artifact and do NOT weaken the
validator silently.

**Frozen serialization (do not touch):** storage-line serialization in
`court/ledger.py::_append_event` is frozen — insertion order, default
`ensure_ascii` (=True), `allow_nan=False`, hash fields appended last. The hash
path (`canonical_json`, `content_hash`, `link_event_hash`) is chain-frozen from
ticket 06. No slice may alter any byte any existing writer emits.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality. Do NOT build idea/factor generation.
2. `court/` must not import any market-specific code or library (no qlib, no
   pandas). Market specifics live in `adapters/` only. A pre-commit AST gate
   and `tests/test_court_import_gate.py` enforce this — keep them green.
3. Code, docstrings, comments: English.
4. **File ownership boundary — your final committed diff may touch ONLY:**
   `court/ledger.py`, `court/judge.py`, `adapters/qlib_cn.py`,
   `harness/verify.py`, `harness/run.py`, `harness/aggregation_policy.py`,
   and test files under `tests/`. Nothing else.

## Task — slices A through H

### Slice A — byte-exact torn-line recovery (court/ledger.py)

Current `Ledger.open()` recovery (pasted from base):

```python
raw = path.read_text(encoding="utf-8")
...
parts = raw.split("\n")
content_parts = parts if not raw.endswith("\n") else parts[:-1]

line_spans: list[tuple[int, int, str]] = []
pos = 0
for part in content_parts:
    start = pos
    end = pos + len(part)          # <-- CHARACTER count of a decoded str
    line_spans.append((start, end, part))
    pos = end + 1
...
                ledger._truncate_to(start)   # <-- BYTE offset into the file
```

`len(part)` counts characters; `_truncate_to` truncates bytes. This is only
correct because storage lines happen to be pure ASCII (default
`ensure_ascii=True`). Two live failure modes:

- A file containing a non-ASCII byte in an INTACT line (foreign writer,
  hand-edit, future serialization slip) makes every later offset wrong — a
  torn-final-line truncate then corrupts intact data.
- A torn write that cuts a multi-byte UTF-8 sequence in half makes
  `path.read_text(encoding="utf-8")` itself raise `UnicodeDecodeError` —
  recovery crashes before it starts.

**Frozen design:** make recovery byte-exact. Read `path.read_bytes()`, split
on `b"\n"`, compute spans in bytes, decode each line individually
(`part.decode("utf-8")`); a line that fails to decode is treated exactly like
a line that fails `json.loads` (torn if final → truncate; corruption if
mid-file). Truncate offsets are then byte-precise by construction. Do not
change `_truncate_to`.

Red tests first (in `tests/test_ledger.py`):

1. Hand-craft a ledger file (bytes, legacy/unchained events are fine) whose
   intact line contains a raw non-ASCII character, followed by a torn partial
   final line. Assert `Ledger.open()` truncates EXACTLY the torn tail: the
   intact event survives replay and the file content afterwards is exactly the
   intact prefix. (Red today: char-offset truncate lands mid-line.)
2. Hand-craft a file whose torn final line ends mid-multibyte-sequence
   (e.g. first byte of a 2-byte UTF-8 char). Assert `Ledger.open()` recovers
   (truncates the torn line) instead of raising. (Red today:
   `UnicodeDecodeError` escapes.)
3. Write-path pin: append an event whose payload contains non-ASCII text
   (e.g. a hypothesis statement with `"π"`), read the raw file bytes, assert
   the stored line is pure ASCII (the `\uXXXX` escape survives). This pins the
   `ensure_ascii=True` invariant the recovery used to silently depend on.

### Slice B — replay/write validation symmetry (court/ledger.py)

The write side validates; replay trusts. Current asymmetries, all to be closed
by adding the symmetric check to `_apply_event` (which serves both replay
`corrupt_on_error=True` → `LedgerCorruptionError`, and post-append
`corrupt_on_error=False` → `ValueError`, via the existing `_err` helper):

1. **Declared literals**: `register_trial` calls `_validate_declared` before
   writing; replay's trial branch calls only `_declared_from_dict` (no
   validation) — a forged chain with `"metric": "banana"` replays fine.
   Fix: validate the reconstructed `DeclaredProtocol` in the trial branch via
   the same `_validate_declared`, routed through `_err`.
2. **Decision values**: `append_verdict` checks every decision ∈
   {"pass", "reject"} (`_VALID_DECISIONS`); replay's verdict branch does not.
   Fix: symmetric check in the verdict branch.
3. **Role domain**: `append_verdict` checks
   `role in (None, "discriminating", "informational")`; replay stores
   `event.get("role")` raw — `"banana"` replays fine. Fix: symmetric check.
4. **decisions ⊆ scope**: enforced on NEITHER side today (both sides only
   check that decisions keys are known trials). The judge maintains it by
   construction, so committed artifacts satisfy it. Fix: enforce
   `set(decisions) ⊆ set(scope)` in BOTH `append_verdict` (pre-write, clean
   `ValueError` — validation must run BEFORE `_append_event` so nothing
   invalid ever hits disk) and `_apply_event`'s verdict branch.
5. **verdicts() dead clause**: with invariant 4 enforced,
   `Ledger.verdicts(trial_id)`'s filter
   `if trial_id in v.scope or trial_id in v.decisions` has a provably dead
   second disjunct. Remove it and state the `decisions ⊆ scope` invariant in
   the docstring.

Red tests first: for each of 1–3, hand-craft a ledger file (or use an
in-memory append then a byte-level edit + reopen for the chained case — a
LEGACY/unchained file is simpler and sufficient: no hash to recompute) whose
event carries the invalid literal, assert `Ledger.open()` raises
`LedgerCorruptionError` (red today: replays fine). For 4: write side —
`append_verdict` with a decision key outside scope must raise `ValueError`
(red today: accepted); replay side — hand-crafted event, expect
`LedgerCorruptionError`. Keep the error messages specific (name the field and
the offending value).

### Slice C — Judgment.decisions keyed by verdict_id (court/judge.py + harness/run.py)

Current (pasted from base, `court/judge.py`):

```python
class Judgment(NamedTuple):
    """Summary of a judge run: verdict ids and per-statistic decisions (§5.8)."""

    verdict_ids: tuple[str, ...]
    decisions: dict[str, dict[str, str]]  # statistic -> {trial_id: "pass"|"reject"}
...
        verdict_ids.append(vid)
        decisions_out[app.statistic] = dict(decisions)
```

Two applications of the same statistic in one config silently overwrite each
other's summary entry (docstring even admits it). **Frozen design:** key
`decisions` by **verdict_id** (collision-free by construction, joins
`verdict_ids` exactly): `decisions_out[vid] = dict(decisions)`. Update the
type comment and docstring; delete the "later applications overwrite" caveat.

Same change in `harness/run.py::_judgment_from_payload` (pasted from base):

```python
    decisions: dict[str, dict[str, str]] = {}
    by_id = {v.verdict_id: v for v in ledger.verdicts()}
    for vid in vids:
        v = by_id.get(vid)
        if v is not None:
            decisions[v.statistic] = dict(v.decisions)
    return Judgment(verdict_ids=tuple(str(x) for x in vids), decisions=decisions)
```

Two fixes here: (a) key by verdict_id, consistent with the new Judgment
contract; (b) the `if v is not None: ...` silently SKIPS a judgment-payload
verdict_id that is missing from the chain — that is replay leniency again. A
well-formed certified ledger always contains the referenced verdicts; a
missing one means tampering or corruption. **Frozen design:** raise
`CertificationError("judgment payload references unknown verdict_id ...")`
instead of skipping.

Red tests first: (i) judge() with the same statistic twice in one config —
assert the returned Judgment carries BOTH applications' decisions (red today:
one entry, overwritten); (ii) a judgment payload referencing a verdict_id not
on the chain → `CertificationError` (red today: silently skipped). No
production caller reads `Judgment.decisions` by statistic key (verified at
base: only tests do) — update those tests.

### Slice D — parent-directory fsync on ledger create (court/ledger.py)

`Ledger.open()` create path (pasted from base):

```python
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            return cls(path)
```

Content writes fsync the file, but the CREATE never fsyncs the parent
directory — after a crash the directory entry (and thus the "registration
timestamp durable on disk" promise, contract §7.1) can be lost. **Frozen
design:** after `touch()`, open the parent directory read-only and fsync it
(`os.open(dir, os.O_RDONLY)` → `os.fsync` → `os.close`). Create path only —
appends and truncates do not change the directory entry.

Red test first: monkeypatch-wrap `os.fsync` to record which file descriptors
get fsynced during a fresh `Ledger.open()` create, resolving each fd via
`os.fstat` mode; assert at least one fsynced fd is a DIRECTORY (red today:
only file fds ever reach fsync — on create, none).

### Slice E — shared finalizer for the two evaluator constructors (adapters/qlib_cn.py)

`QlibCNFactorEvaluator.__init__` and `QlibCNFactorEvaluator.from_panels`
each hand-set the same 10 instance attributes (`_cfg`, `_synthetic`,
`_qlib_version`, `_eval_dates`, `_eval_index`, `_instruments`, `_labels`,
`_pit_mask`, `_calendar_end`, `_n_instruments_measured`). They have ALREADY
diverged once — the exact failure mode the audit predicted:

```python
# __init__:
self._n_instruments_measured = int(self._pit_mask.any(axis=0).sum())
# from_panels:
obj._n_instruments_measured = n            # total columns, ignores pit_mask
```

With a partial `pit_mask`, the synthetic path reports total columns while the
production path reports mask-active columns. **Frozen design:** extract one
private finalizer (e.g. `_finalize(...)`) that both constructors call; it sets
every instance attribute in one place and computes `_eval_index` and
`_n_instruments_measured` (from the pit mask — the `__init__` semantics,
which are the correct ones) internally. Behavior change is EXACTLY ONE case:
`from_panels` with a partial mask now reports mask-active count; everything
else stays bit-identical (all-ones mask: `any(axis=0).sum() == n`).

Red test first (qlib-free — `from_panels` needs no qlib): build a small panel
with a partial pit_mask, assert `_n_instruments_measured` (or its public
surface if one exists) equals the mask-active column count (red today: equals
total columns). If an existing test froze the buggy value, report it in the
receipt rather than deleting it silently.

### Slice F — verify CLI: OSError from anchor construction escapes (harness/verify.py)

Current `main` (pasted from base):

```python
    try:
        backend = _parse_anchor_arg(ns.anchor)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
```

`_parse_anchor_arg` constructs `FileAnchor(rest)`, whose `__init__` does
`mkdir`/`touch`; a malformed path like `file:/dev/null/foo` raises
`FileExistsError`/`NotADirectoryError` (OSError subclasses) — an uncaught
traceback instead of the clean exit-1 message. **Frozen design:** widen to
`except (ValueError, OSError)`. One line plus test.

Red test first: `main(["<any ledger path>", "--anchor", "file:/dev/null/foo"])`
must RETURN 1 with a message on stderr, not raise (red today: raises).

### Slice G — AggregationPolicy.params stored by reference (harness/aggregation_policy.py)

Construction enforces `params == {}`, but the caller's dict is stored by
reference — mutating it AFTER construction bypasses the invariant
(`to_payload` hardcodes `{}` and `apply` never reads params, so real harm ≈ 0;
still, the invariant should hold on the object). **Frozen design:** store a
fresh empty dict (or `MappingProxyType({})` — worker's choice, consistent with
how the dataclass is declared) so post-construction mutation of the caller's
dict cannot alter `policy.params`.

Red test first: `p = {}` → construct policy with `params=p` → `p["x"] = 1` →
assert `policy.params == {}` (red today: aliased).

### Slice H — tighten two weak match="metric" assertions (tests only)

Two caller-form tests assert errors with `pytest.raises(..., match="metric")`
— a regex so loose it matches the wrong error. They are at
`tests/test_judge_direction.py:274` and `tests/test_judge_direction.py:295`
(verified at base). Tighten each to a distinctive fragment of the actual
expected message (e.g. the "judge's ruling, not a caller choice" wording, or
the "unknown pbo_cscv metric" prefix — read the code path each test actually
exercises and match its real message). Test-only slice; no production change.

## Acceptance criteria

The referee will re-run every one of these independently in your worktree.
Record each command with its real exit code in your receipt.

1. `python3 -m pytest -q` — full suite green. Baseline at your base commit is
   **542 passed, 2 skipped** (system python3, no qlib — the 2 skips are
   expected). After your change: all previous tests plus your new ones green,
   0 failures. If a pre-existing test conflicts with a frozen design above,
   update it and list every such test in the receipt with one line of why.
2. `ruff check .` — clean.
3. Per-slice RED evidence: for each slice A–H the receipt's command list
   includes at least one red run (real command, real nonzero exit code)
   executed BEFORE that slice's implementation, and the matching green run
   after.
4. `python3 -m pytest tests/test_killer_demo.py tests/test_certified_run.py tests/test_harness_verify.py tests/test_ledger.py tests/test_ledger_chain.py tests/test_judge.py -q`
   — green (the replay-compatibility surface for slices A–D).
5. `python3 -m harness.court_import_gate --court court` — PASS (court gained
   no new imports).

## Out of scope

- The hash path (`canonical_json` / `content_hash` / `link_event_hash`) and
  any byte the writer emits (Slice A changes only how RECOVERY reads).
- `harness/__init__.py` lazy imports (evaluated and deferred by the
  commander); `scripts/dispatch_receipt.py` trailing newline (keep);
  `_resolve_pbo_metric` post-resolution registry recheck (keep — it guards
  future registry/base-metric drift); the N-single-queries
  `ledger.trials([tid])[0]` pattern (keep); `AggregationPolicy.from_payload`
  unknown-key tolerance (keep — the seal-vs-declaration verbatim comparison
  in `harness/verify.py` already pins payload bytes; disclosed, not fixed).
- Any new public API beyond the frozen `Judgment.decisions` re-keying.
- Docs, README, CI.

## Operational notes

- Environment: system `python3` (3.12.8), `pytest`, `ruff` on PATH; numpy
  2.4.4 / scipy 1.17.1; qlib NOT installed (2 expected skips); pandas is
  available for `adapters/` tests (never for `court/`). No network; install
  nothing.
- Full suite ~95s; nothing here needs detach-and-poll.
- Write files incrementally (avoid one giant single-shot emission).
- Work slice by slice; commit once at the end is fine, but keep per-slice red
  evidence in the receipt.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-12: <summary>"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
