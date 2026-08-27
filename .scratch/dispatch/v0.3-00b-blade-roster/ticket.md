# Ticket: v0.3-00b — pin the blade roster on chain (close the screen-stickiness gap)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained. Do not invent scope beyond it.

## Context

The v0.3-00 blade plumbing (merged at your base) was adversarially reviewed;
the panel proved with probes that **screening is attachment-conditional and
non-sticky**: reopen the ledger via `CertifiedRun.open(path, evaluator)` with
the default `blades=None` and a previously screened trial can be evaluated,
enter derived scope, and seal+verify green; a blade-less `create()` silently
ignores a spec's `on_flag: screen` declaration. Root cause: run_config and
aggregation policy are pinned on chain and cross-checked, the blade roster is
not. The frozen design's addendum (committed at your base,
`.scratch/v0.3/blades-design-draft-v2.md` §1.4) rules:

> 新增 declaration kind=`blade_roster`（首次带刀 evaluate 前上链：阵容名单+
> 各刀 params 指纹），`open()` 时 fail-closed 交叉核验：链上有 roster 而未挂
> 等价阵容 → 拒绝 evaluate；链上无 roster 而 spec 含 screen 声明 → 拒绝
> record。沿 §1.1 declaration 承载原则，ledger/replay/verify 仍零改动。

Read `harness/blades.py` and `harness/run.py` at your base first — the
declaration kinds, `_apply_blades`, `_normalize_blades`, and the screened-
trial terminality guard all already exist; you are extending that machinery.

## Contract (frozen)

1. `harness/blades.py`:
   - `BLADE_ROSTER_KIND = "blade_roster"`.
   - `roster_entry(blade) -> dict`: `{"name": blade.name, "params_fingerprint":
     sha256 hex of canonical JSON (sorted keys, compact separators) of
     `getattr(blade, "roster_params", {})`}`. Blades without `roster_params`
     fingerprint the empty dict — the in-flight gates blades stay valid
     unmodified.
   - `append_blade_roster(ledger, blades) -> str`: payload
     `{"kind": BLADE_ROSTER_KIND, "roster": [roster_entry(b), ...]}` (order =
     attachment order). Refuse (ValueError) if a blade_roster declaration
     already exists.
   - `find_blade_roster(ledger) -> list[dict] | None`: roster list of the
     FIRST blade_roster declaration, else None.
2. `harness/run.py` wiring (all failures = `CertificationError`, raised
   BEFORE any declaration append or record in that evaluate call):
   a. **Auto-pin**: in `_apply_blades`, after the calibration check and
      before running blades: if no roster on chain → append it (derived from
      the attached roster). If a roster IS on chain → verify equivalence
      (same length, same (name, fingerprint) sequence, in order); mismatch →
      refuse.
   b. **Bladed-history lock**: in `evaluate()`, when `self._blades is None`
      but a blade_roster declaration exists on chain → refuse ("ledger has a
      pinned blade roster; reopen with the equivalent blades").
   c. **Screen-declaration lock**: in `evaluate()`, when `self._blades is
      None` and no roster on chain, but THIS trial's spec declares
      `on_flag: "screen"` for any blade name → refuse to record ("spec
      declares screening but no blades attached").
   d. No other behavior changes; ledger/verify untouched (declarations only).
3. `tests/test_blades_roster.py` (red-first TDD; crib fixtures from
   `tests/test_blades_harness.py` — copy, don't import or modify it):
   a. Panel replay P3 (the headline): bladed run screens trial B →
      `open()` WITHOUT blades → `evaluate(B)` refused; reopen WITH the
      equivalent blade → still refused by the screened-terminality guard
      (registered + report exists) — B stays out of scope either way; the
      run seals+verifies with only the innocent trial judged.
   b. Panel replay P3b: bladeless `create()`, trial spec declares screen →
      `evaluate` refused, nothing recorded.
   c. Auto-pin: first bladed evaluate appends exactly one blade_roster
      declaration whose roster matches the attached blades; second evaluate
      appends no duplicate.
   d. Mismatch: reopen with a different blade name (or a blade with
      different `roster_params`) → refused; reopen with an equivalent
      fresh instance (same name, same/absent roster_params) → accepted.
   e. `append_blade_roster` uniqueness → ValueError on second.
   f. End-to-end: bladed run with roster+calibration+reports on chain →
      judge → seal → `harness.verify.verify(path)` passes.
   g. Bladeless runs with no roster and no screen declarations behave
      exactly as before (regression: existing suite must stay green).

## Hard constraints (iron laws — violations = rejected delivery)

1. `court/` untouched; ledger/replay/verify ZERO changes — declarations only.
2. Deterministic fingerprints (sorted-keys canonical JSON, sha256 hexdigest;
   stdlib hashlib+json only).
3. English; TDD red run recorded in the receipt.
4. File ownership — modify/create ONLY: `harness/blades.py`,
   `harness/run.py`, `tests/test_blades_roster.py`. Do NOT touch `gates/`
   (three sibling deliveries are being merged), `tests/test_blades_harness.py`,
   court/, scripts/, any other file.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m pytest tests/test_blades_roster.py -v` → exit 0.
2. `python3 -m pytest tests/test_blades_harness.py -q` → exit 0 (the v0.3-00
   suite is the regression net for your wiring changes).
3. `python3 -m pytest -q` → exit 0. Known environment caveat: 3 wall-clock
   perf tests (test_adapter_kernel_perf.py ×2, test_sharpe_perf.py ×1) can
   fail on a loaded machine and fail identically at base — if they fail,
   re-run just those three and report both results honestly.
4. `ruff check .` → exit 0.
5. TDD red recorded. 6. Ownership diff = exactly the three files.

## Out of scope

- Roster amendment/rotation flows (a pinned roster is immutable for the
  ledger's lifetime in v0.3; changing blades = new run).
- gates/ blades, calibration content, null museum.

## Delivery protocol

1. Fresh git worktree; work here only; write files incrementally; act early,
   keep responses short.
2. Run every AC yourself; record real exit codes. Honest `partial` beats
   dishonest `done`.
3. Commit ALL work:
   `git add -A && git commit -m "v0.3-00b: pin blade roster on chain (screen stickiness)"`.
4. Final output = ONLY the JSON receipt (schema appended below by the
   dispatch bridge). `ticket_id` = `v0.3-00b`.
