# Ticket: v0.2-09 — Aggregation policy: explicit harness object, declaration-event pre-registration, single code path

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

v0.1 audit debt: **the aggregation rule is hard-coded at the demo layer**
(`examples/killer_demo/aggregate.py`; the judge itself correctly never
aggregates — kernel ruling G1). v0.2's pre-registration gate needs the
aggregation/selection policy to be a **pre-registration object**: per
`docs/design/prereg-gate.md` (v3, committed in your worktree) §4.2 the run
seal carries the policy id, and §7's ticket-09 bullet: *"the
aggregation/selection policy is a pre-registration object: it must be a
declaration event on the chain **before the first verdict** (or locked at run
creation), so 'discriminating-only aggregation' (ticket 03) cannot be
cherry-picked post-hoc."*

Landed context you build on (both merged): ticket 06 gave the ledger
court-opaque `declaration` events (`Ledger.append_declaration(payload) ->
"d-000001"`, `Ledger.declarations() -> list[DeclarationRecord]`, payloads
uninterpreted by court) and the content hash-chain. Ticket 08 gave
role-aware verdicts (`VerdictRecord.role ∈ {None, "discriminating",
"informational"}`) and made `examples/killer_demo/aggregate.py`
role-aware: `_is_discriminating(v) = getattr(v, "role", None) !=
"informational"`, unanimous over discriminating verdicts only, `None` /
missing attribute counts as discriminating (legacy artifacts ruling).

The seal-side cross-check ("policy at seal == the declared policy") is
**ticket 07's** job, not yours. Your job: make the policy an explicit,
serializable, declarable object with ONE implementation of the rule, and
kill the demo's private code path — without changing a single byte of demo
OUTPUT.

Current code facts (verified at this base):
- `harness/__init__.py` docstring still says "Empty in v0.1" (the package
  now also hosts exactly three unrelated session-governance modules:
  `trial_counter.py`, `confirm_gate.py`, `anti_pattern_gate.py` — do not
  touch them).
- `examples/killer_demo/aggregate.py` exports `verdicts_deciding`,
  `trial_survives`, `gates_faced_passed`, `survivor_ids`, `survivor_count`,
  `aggregate_sweep_rows`; imported by `run.py:28`, `report.py:9`,
  `sweep.py:13`, `tests/test_killer_demo.py:16`, and
  `tests/test_judge_direction.py:27-30` (same public names — the re-export
  keeps all five sites working).
- `Ledger.verdicts()` (court/ledger.py:918) lists verdict records;
  `Ledger.append_declaration` / `.declarations()` exist per ticket 06.
- The killer-demo committed artifacts live in `examples/killer_demo/out/`
  (`ledger.jsonl`, `report.md`, `figure.png/svg`, `run_config.json`).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality; do NOT build idea generation.
2. `court/` is NOT yours to touch at all in this ticket. `harness/` may
   import `court` (it is the governance layer above it); `court/` must
   never import `harness` or market code.
3. Fail-closed: violated preconditions raise `ValueError`; never repair,
   coerce, or silently drop.
4. Code, docstrings, comments: English.
5. TDD contractual: failing tests FIRST (red run recorded in the receipt
   `self_test` with its real exit code), then green.
6. File ownership — you may modify ONLY: (new) `harness/aggregation_policy.py`;
   `harness/__init__.py` (docstring + exports only);
   `examples/killer_demo/aggregate.py` (thin delegation, see Task 3);
   (new) `tests/test_aggregation_policy.py`. Do NOT touch `court/`,
   `adapters/`, `docs/`, other `harness/` modules, other demo modules
   (`run.py`/`report.py`/`sweep.py` keep importing from
   `examples.killer_demo.aggregate` unchanged), other test files, or
   `examples/killer_demo/out/`.
7. **Demo OUTPUT is frozen**: the demo's behavior, its ledger events, its
   `run_config.json`, report bytes — everything under `out/` must be
   byte-identically reproducible before/after your change. This ticket is a
   *where-the-logic-lives* refactor plus new harness machinery for future
   certified runs; the demo (an uncertified calculator use) does NOT start
   writing declaration events. (The conflict-matrix ruling: demo artifacts
   regenerate ONCE, after ticket 08 — never again for 09.)

**Tracked build artifact warning (do this or you will fail AC-5):**
`alpha_court.egg-info/` is git-tracked; your AC-1 `pip install -e` will
regenerate it. It is NOT yours — before committing, run
`git checkout -- alpha_court.egg-info/` so `git add -A` stays inside your
four owned files.

## Task

### 1. `AggregationPolicy` object (`harness/aggregation_policy.py`, new)

A frozen dataclass with:
- `policy_id: str` — non-empty; the canonical v0.2 instance is
  `"unanimous-discriminating-v1"`;
- `rule: str` — literal `"unanimous-discriminating"` (the only rule in
  v0.2; any other value raises at construction — no speculative registry);
- `params: dict` — must be `{}` in v0.2 (raise otherwise; reserved).

Payload round-trip:
- `to_payload(self) -> dict` → `{"kind": "aggregation_policy",
  "policy_id": ..., "rule": ..., "params": {}}`;
- `AggregationPolicy.from_payload(payload: dict)` → validates `kind`,
  required keys, value constraints (fail-closed `ValueError`).

### 2. Pre-registration surface (same module)

- `declare_policy(ledger, policy) -> str` (returns the declaration id):
  appends the payload as a court-opaque `declaration` event via
  `ledger.append_declaration`. It does NOT inspect the ledger's
  chained/legacy mode — chain requirements are the seal-side's business
  (ticket 07).
  **Fail-closed ordering (prereg-gate §7):** raises `ValueError` if
  `ledger.verdicts()` is non-empty (the policy must precede the first
  verdict) or if a policy declaration already exists on that ledger (one
  policy per ledger; re-declaration is post-hoc cherry-picking).
- `read_declared_policy(ledger) -> tuple[str, AggregationPolicy] | None`:
  scans `ledger.declarations()` for payloads with
  `kind == "aggregation_policy"`; returns `(declaration_id, policy)`;
  `None` if absent; **more than one → raise** (corrupt pre-registration).
- These functions are consumed by ticket 07's certified `Run` (it will put
  the policy on the chain at run creation and cross-check at seal). Your
  tests exercise them against raw `Ledger` instances.

### 3. One implementation of the rule (kill the second code path)

- Move the role-aware aggregation logic (the 08 versions of
  `verdicts_deciding`, `trial_survives`, `gates_faced_passed`,
  `survivor_ids`, `survivor_count`) into `harness/aggregation_policy.py` as
  the implementation of `rule == "unanimous-discriminating"`, exposed both
  as module-level functions and via
  `apply_policy(policy, trial_ids, verdicts) -> dict` (returns
  `{"survivor_ids": [...], "n_survivors": int}`; validates the policy is a
  known rule).
- `examples/killer_demo/aggregate.py` becomes a **thin delegation module**:
  it imports those functions from `harness.aggregation_policy` and
  re-exports them under the exact same names (declare `__all__` — plain
  re-export imports trip ruff F401), so `run.py` / `report.py` /
  `sweep.py` / existing tests keep working unchanged.
  (`aggregate_sweep_rows` STAYS in the demo module — pinned: it aggregates
  sweep-row dicts for the §7.4 calibration appendix, not verdict records.) Behavior must be IDENTICAL — the existing
  `tests/test_killer_demo.py` aggregation tests must pass unmodified.
- Semantics preserved exactly (08's, do not "improve"): deciding = verdict
  whose `decisions` includes the trial; discriminating =
  `getattr(v, "role", None) != "informational"`; a trial with no deciding
  discriminating verdict does NOT survive (no free pass); unknown role
  strings count as discriminating.

### 4. `harness/__init__.py`

Update the stale "Empty in v0.1" docstring to name the certified-path
modules landing in v0.2 (aggregation policy here; Run/seal in ticket 07)
and the pre-existing session-governance modules; export `AggregationPolicy`,
`declare_policy`, `read_declared_policy`, `apply_policy`.

### 5. Tests (red first; new file `tests/test_aggregation_policy.py` —
all your tests live there; no other test file may be created)

Cover at least:
- policy construction guards (empty policy_id / unknown rule / non-empty
  params each raise); payload round-trip; `from_payload` rejects wrong
  `kind`, missing keys, junk types;
- `declare_policy` on a fresh ledger → declaration event readable back via
  `read_declared_policy` (id + equal policy), and the event chains (the
  ledger's `chain_head` advances);
- `declare_policy` AFTER a verdict exists → raises (build a tiny ledger
  with one judged trial);
- duplicate declaration → raises; two different policies → second raises;
  `read_declared_policy` on a hand-built ledger with two policy
  declarations → raises;
- `apply_policy` equivalence: same fixture cases as the demo aggregation
  semantics (informational reject cannot kill; discriminating reject
  kills; `None`-role counts; missing-attribute stub counts; no-free-pass);
  and `apply_policy` output matches `survivor_ids`/`survivor_count`
  called directly;
- unknown rule reaching `apply_policy` (constructed via dataclass bypass:
  `object.__new__` + `object.__setattr__` — `from_payload` correctly cannot
  produce one) → raises, never silently passes everything;
- the demo delegation: `examples.killer_demo.aggregate.trial_survives is
  harness.aggregation_policy.trial_survives` (identity — proves single
  code path).

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,demo]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_aggregation_policy.py -v` → exit 0; ≥ 12 NEW tests including the ordering guard (declare-after-verdict raises) and the single-code-path identity test
3. `.venv/bin/python -m pytest` → exit 0 (qlib-dependent tests may skip; nothing else may fail — zero regressions; full suite ~30 min, run once at the end; `tests/test_killer_demo.py` aggregation tests unmodified and green)
4. `.venv/bin/ruff check .` → exit 0 (verified satisfiable at this base by the commander)
5. Before your FIRST commit, record `BASE=$(git rev-parse HEAD)`. Then
   `git diff --stat $BASE..HEAD` touches ONLY the four files of hard
   constraint 6, and `git diff $BASE..HEAD -- examples/killer_demo/out/`
   is empty
6. TDD evidence in the receipt: at least one recorded pytest command with a
   non-zero exit code from the red phase, before the green run

## Out of scope

- The certified `Run` / seal / anchor and the seal-side policy cross-check
  (ticket 07); the `run_config` adapter-lock declaration event (07).
- Any demo behavior/output change (hard constraint 7); regeneration.
- A policy/rule registry beyond the single v0.2 rule (YAGNI — rejected in
  design review).
- `court/` changes of any kind.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and
   its real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-09: aggregation policy — harness object, declaration pre-registration, single code path"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced
   by the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.2-09`

## Operational notes

- Write files INCREMENTALLY (several smaller edits — max_tokens killed a
  v0.1 dispatch that emitted one giant file).
- Full pytest ≈ 30 min — once, at the end; inner loop on your new test
  file + `tests/test_killer_demo.py`.
- The venv in AC-1 is the only environment change allowed.
