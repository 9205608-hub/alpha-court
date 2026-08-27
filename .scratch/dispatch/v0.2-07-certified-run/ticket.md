# Ticket: v0.2-07 — The pre-registration gate itself: CertifiedRun, seal, anchor backends, `verify`

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

This is the ticket the whole of v0.2 exists for. The court kernel derives
multiplicity N from the judged **scope**; if the agent controls scope, it
controls N — the core self-deception. The design contract is
`docs/design/prereg-gate.md` (v3, committed in your worktree) — **read all
of it**; §3 (architecture), §4 (hash chain & seal & anchor), §5 (fail-closed
list), §6 (honest boundaries), §9 (deliverables) are binding. The issue file
`.scratch/v0.2/issues/07-prereg-gate-enforcement.md` (with its two amendment
sections, including the **09 收货交接注记** — two probe-panel findings your
`verify` MUST close) is binding too. Where this ticket pins something more
precisely, this ticket wins.

Landed context you build on (all merged):
- **06**: the ledger has a content hash-chain (chained files verify on
  replay; `Ledger.chain_head`), court-opaque `declaration`/`seal` events
  (`append_declaration(payload) -> "d-…"`, `append_seal(payload) -> "s-…"`,
  `declarations()`, `seal()`; seal must be the FINAL event — every mutating
  append after a seal raises, replay of any event after a seal raises),
  `record(trial_id, series, attestation=None)` with court-side shallow
  checks (metric/window vs declared, `n_evaluation_dates` vs len), and
  `register(..., source_ref=None)`.
- **08**: verdicts carry `role`; the judge enforces direction-homogeneous
  scopes and direction-aware gate forms.
- **09**: `harness.aggregation_policy` — `AggregationPolicy`,
  `declare_policy(ledger, policy) -> declaration_id` (raises if any verdict
  exists or a policy is already declared), `read_declared_policy(ledger)`,
  `apply_policy(policy, trial_ids, verdicts)`.

Current code facts (verified at this base):
- `court/ledger.py` read/write surface: `trials(scope=None)`, `series(tid)`,
  `matrix(ids)`, `verdicts(tid=None)`, `status(tid)` ∈
  {registered, evaluated, judged}, `declarations()`, `seal()`,
  `chain_head` (property; genesis `"0"*64` for an empty chained ledger),
  `append_declaration:809`, `append_seal:829`. `canonical_json`,
  `content_hash`, `link_event_hash` are public module-level functions in
  `court.ledger` — **this ticket formally claims them for `verify`**.
- `court.judge(ledger, scope, config)` still accepts a caller scope (pure
  calculator use stays legal); `Application(statistic, params)`.
- The sanctioned adapter shape (`adapters/qlib_cn.py:556`):
  `evaluate(scores, metric) -> EvalResult` where `EvalResult` is a frozen
  dataclass with `.index: list[str]`, `.values: np.ndarray`,
  `.meta: dict` (metric / window / universe / n_evaluation_dates /
  data_version / adapter_version / qlib_version / config{provider_uri,
  label_expr, quantile, min_cross_section, …}). **You do NOT import
  adapters/** — the evaluator is an injected dependency with exactly this
  duck-typed surface; your tests use a fake evaluator producing
  deterministic series + attestation dicts. Real qlib wiring is ticket 11.
- `harness/` hosts `aggregation_policy.py` (09) plus three unrelated
  session-governance modules (`trial_counter.py`, `confirm_gate.py`,
  `anti_pattern_gate.py`) — do not touch those three.

## Hard constraints (project iron laws — violations = rejected delivery)

1. No backtesting functionality; no idea generation.
2. `court/` and `adapters/` are NOT yours to touch at all. `harness/` may
   import `court`; `harness/` must NOT import `adapters` or any market
   library (the evaluator is injected).
3. Fail-closed: caller errors raise `ValueError`; verification failures
   raise `CertificationError` (a new exception in `harness/run.py`); never
   repair, coerce, or silently drop.
4. **No security theater** (prereg-gate v3 §6, binding): the seal certifies
   protocol-consistency and ORDER of recorded events — not provenance
   authenticity. Do NOT add in-process nonces/HMACs/signing; do NOT assert
   "in-process cannot call court" anywhere (uncertified calculator use is
   legitimate; the missing/invalid seal is the detection).
5. Code, docstrings, comments: English. Cite `prereg-gate.md` sections in
   docstrings.
6. TDD contractual: failing tests FIRST (red run recorded in the receipt
   `self_test` with its real exit code), then green.
7. File ownership — you may modify ONLY: (new) `harness/run.py`,
   (new) `harness/anchor.py`, (new) `harness/verify.py`,
   `harness/__init__.py` (docstring + exports only), (new)
   `tests/test_certified_run.py`, (new) `tests/test_harness_verify.py`.
   Nothing else — not `court/`, `adapters/`, `docs/`, `examples/`, other
   `harness/` modules, other test files.

**Tracked build artifact warning (do this or you will fail AC-5):**
`alpha_court.egg-info/` is git-tracked; your AC-1 `pip install -e` will
regenerate it. Before committing, run `git checkout -- alpha_court.egg-info/`.

## Task

### 1. `CertifiedRun` (`harness/run.py`)

Construction — `CertifiedRun.create(path, run_config: dict, policy:
AggregationPolicy, evaluator, anchor: AnchorBackend | None = None) ->
CertifiedRun`:
- opens a FRESH ledger at `path` (an existing non-empty file → `ValueError`
  — a certified run never adopts a foreign ledger);
- appends the **`run_config` declaration** as the FIRST chain event:
  payload `{"kind": "run_config", "config": <run_config verbatim>}`.
  `run_config` must be a non-empty JSON-serializable dict (raise otherwise);
  it locks the adapter identity — universe, provider_uri, label_expr,
  quantile, min_cross_section, data tag, versions (prereg-gate v3 §3, audit
  D7). The harness does NOT interpret its keys beyond conformance (below);
- declares the aggregation policy via `harness.aggregation_policy.
  declare_policy` (second chain event);
- `open(path, evaluator, anchor=None)` re-attaches to an existing
  UNSEALED certified ledger (replay verifies the chain; missing
  run_config/policy declarations → `CertificationError`; an already-sealed
  or legacy/chainless file → `CertificationError`). **Judged-state
  recovery (pinned):** if the reopened ledger already contains ANY verdict
  events, `judge` is considered consumed (calling it again → `ValueError`)
  and `seal()` is allowed — the Judgment is rebuilt from the chain's
  verdict events (`verdict_ids` in event order).

The loop (the agent NEVER passes a scope at any point):
- `propose(statement_or_hypothesis_id, spec, params, declared,
  source_ref=None) -> trial_id` — registers hypothesis (when given a
  statement) + trial. **Discrimination rule (pinned):** an argument
  matching `^h-\d{6}$` is treated as an existing hypothesis id (an
  unknown one → court's ValueError bubbles up); anything else is a new
  statement. Sealed → the ledger already raises; surface it.
- `evaluate(trial_id, scores) -> None` — calls
  `evaluator.evaluate(scores, declared.metric)` for THAT trial's declared
  metric; builds the attestation from `result.meta`; **conformance
  (fail-closed `CertificationError`)**: every key of `result.meta` that
  also exists in `run_config` must be EQUAL (raw `==` on the values —
  covers universe / versions / config; nested dicts compare raw); then
  `ledger.record(trial_id, Series(index=tuple(result.index),
  values=tuple(result.values)), attestation=result.meta)` (court re-checks
  metric/window/shape). A bare record without attestation is impossible on
  this path by construction.
- `judge(config: Sequence[Application]) -> Judgment` — derives
  `scope = [every trial whose status is "evaluated" or "judged", in
  registration order]` (registered-but-unevaluated keep file-drawer
  semantics — visible on chain, not in N; prereg-gate v3 §8); empty scope →
  `ValueError`; runs `court.judge(ledger, scope, config)`; stores the
  judgment for the seal. May be called at most once per run (second call →
  `ValueError`; one Run = one family = one judge = one seal). **Failure
  semantics (pinned):** if `court.judge` raises for ANY reason, the run's
  single `judge` is still consumed and the run can never be sealed —
  court.judge appends verdicts per-application, so a mid-battery failure
  leaves orphan verdicts that no seal could cover (verify invariant 7);
  fail-closed bricking is the correct outcome, documented in the docstring
  and covered by a test.
- `seal() -> str` — requires a prior `judge()` (else `ValueError`).
  Appends the seal event with payload:
  `{"kind": "seal", "chain_head": <the chain head IMMEDIATELY BEFORE this
  seal event — the state it certifies>, "scope": [...], "verdict_ids":
  [...], "policy_declaration_id": "d-…", "policy": <the policy payload
  verbatim as it appears on chain>, "anchor_ref": <str | None>}`.
  **Verbatim means (pinned):** the `policy` copy is taken from
  `ledger.declarations()` — the matching `DeclarationRecord.payload` dict
  as replayed — NEVER re-serialized from an `AggregationPolicy` object
  (`from_payload` tolerates-and-drops unknown keys; an object round-trip
  would silently launder a smuggled key and your own seal would then fail
  verify invariant 5). `read_declared_policy` returns
  `(declaration_id, AggregationPolicy)` — use it for the id, not the
  payload.
  `anchor_ref` is non-None only if the backend can mint a reference BEFORE
  the seal line is written (FileAnchor can; GitAnchor cannot — prereg-gate
  v3 §4.2 ordering). AFTER the seal is durably written, call
  `anchor.pin(chain_head_after_seal)` (pin the FINAL head, seal included)
  and write `run_manifest.json` next to the ledger:
  `{"chain_head": <final head>, "seal_event_hash": …, "anchor_ref":
  <manifest side, see §2 pinned mapping>, "sealed_at": …,
  "env": {"python": …, "numpy": …, "scipy": …, "court": court.__version__}}`
  (env versions per prereg-gate §4.2). Note `seal_event_hash` ≡ the final
  chain head (the last line's event_hash IS the head) — deliberately
  redundant cross-checks. No anchor backend → manifest
  `anchor_ref: null` (still a valid tamper-EVIDENT run; the anchor only
  hardens against full-rewrite).

### 2. Anchor backends (`harness/anchor.py`)

`AnchorBackend` protocol: `pin(chain_head: str) -> str` (returns the
anchor_ref), `verify(chain_head: str, anchor_ref: str) -> bool`, and
`ref_before_seal() -> str | None` (None for backends that anchor after the
fact). **Pinned mapping:** the seal event's `anchor_ref` =
`ref_before_seal()` (FileAnchor: the anchor file's path, created at
backend construction so the referenced artifact exists before the seal —
prereg-gate §4.2's "never reference an artifact that does not yet exist";
NoopAnchor and GitAnchor: None); the manifest's `anchor_ref` =
`pin(final_head)`'s return value; `VerificationReport.anchor_ref` reports
the manifest side. Implement:
- `NoopAnchor` — pin returns `"noop"`, verify always True (tests/dev);
- `FileAnchor(path)` — appends `{chain_head, at}` JSON lines to an anchor
  file OUTSIDE the ledger; verify = the head appears in the file;
- `GitAnchor(repo_dir)` — `subprocess` calls `git` only when invoked (no
  import-time dependency): pin = commit a one-line anchor file
  `anchors/<head>.txt` in `repo_dir` and return the commit SHA; verify =
  `git cat-file` the SHA and check the head. Tested against a `git init`
  tmp repo only.

### 3. `verify` (`harness/verify.py` + CLI)

`verify(path, anchor: AnchorBackend | None = None) -> VerificationReport`
(frozen dataclass: chain_head,
seal_event_hash, n_trials, n_verdicts, policy_id, anchor_ref) — raises
`CertificationError` naming the FIRST violated invariant. Verification is
**replay + recompute only — no adapter re-run, no cross-machine head
reproduction** (prereg-gate v3 §4.1/§9). It must check, in this order:

1. the file replays (`Ledger.open` on a COPY — verify never mutates; a
   torn tail would be truncated by open, so verify reads raw bytes FIRST
   and applies the crisp completeness rule (pinned): the file's final byte
   is the `\n` terminating the seal line; every line parses as a JSON
   dict carrying the full chain envelope (`type`, `at`, `prev_hash`,
   `event_hash`). Trailing blank lines, an envelope-less final JSON line,
   or a missing final newline all fail invariant 1 — `Ledger.open` would
   silently truncate several of these, which is exactly why verify checks
   raw bytes before replay;
2. the ledger is chained (legacy → fail: "uncertified: no chain");
3. a seal exists and is the FINAL raw line (re-check at the raw-line
   level, not just via replay);
4. **raw event order** (⚠-1 of the 09 handoff — the read surfaces
   `declarations()`/`verdicts()` do NOT expose interleaving; you must walk
   the raw JSONL lines): the `run_config` declaration is event #1; the
   policy declaration precedes the first `verdict` event; every
   `evaluation` precedes the seal;
5. the seal's `policy` payload equals the on-chain policy declaration
   payload by **raw dict equality** (⚠-2 — never object-level/
   re-serialized comparison; smuggled keys must be caught);
6. the seal's `chain_head` equals the recomputed head over all events
   BEFORE the seal; the manifest (if present next to the file) matches the
   final head and seal_event_hash;
7. the seal's `scope` equals the derived registered-and-evaluated set;
   its `verdict_ids` equal ALL verdict events on the chain (a wild
   `court.judge` verdict smuggled onto the ledger → fail);
8. every evaluation event carries an attestation and its run_config-
   overlapping keys still match the run_config declaration (cheap raw
   re-check);
9. if the manifest carries an `anchor_ref` and a backend is supplied to
   `verify(path, anchor=...)`, `anchor.verify(final_head, anchor_ref)`
   must return True (no backend supplied → anchor is reported, not
   verified).

CLI: `python -m harness.verify <ledger.jsonl>` → prints the report, exit 0;
any `CertificationError` → message to stderr, exit 1.

### 4. Exports (`harness/__init__.py`)

Add `CertifiedRun`, `CertificationError`, `verify`, `VerificationReport`,
`NoopAnchor`, `FileAnchor`, `GitAnchor`. Update the docstring (Run/seal now
IN this package).

### 5. Tests (red first; `tests/test_certified_run.py` for the run loop,
`tests/test_harness_verify.py` for verify/anchors — no other new files)

The three bypasses from the issue MUST each have a red-first test proving
the gate closes them:
- **scope-shrink**: on the certified path there is no scope parameter at
  all (API-level test) AND a wild verdict appended via direct
  `court.judge`/`append_verdict` on the certified ledger before sealing →
  `verify` fails on invariant 7;
- **post-hoc direction flip** (three implementable prongs — a second
  propose cannot target an existing trial since `register` mints fresh
  ids, so the lock is enforced elsewhere): (a) propose t1(greater) +
  t2(less), evaluate both, `CertifiedRun.judge()` derives the mixed scope →
  court's homogeneity guard raises (E2E, before any verdict lands);
  (b) flip one byte of a trial event's `declared.direction` in the file →
  replay/verify fails on the chain; (c) a second `evaluate` on the same
  trial → court raises (series-exists immutability, asserted through the
  certified path);
- **trace tampering**: mutate one mid-file byte of a sealed ledger →
  `verify` raises; delete the seal line → `verify` raises ("no seal") while
  bare `Ledger.open` still replays (the honesty boundary: truncation makes
  it UNCERTIFIED, not undetectably-certified — comment pointing at
  prereg-gate v3 §6). PLUS the pre-seal honesty test the issue mandates:
  on an UNSEALED certified ledger, delete the last evaluation event →
  bare replay passes with zero warnings — ASSERT it passes (the disclosed
  §6 window, on the record). `harness/run.py`'s module docstring must name
  all four §6 boundaries (pre-seal truncation window, off-path
  pre-screening, in-process forgery, sibling runs).

Also cover: create-on-existing-file raises; run_config non-dict/empty
raises; happy path E2E (create → propose×3 → evaluate×3 with a fake
evaluator → judge (fdr_by battery) → seal → verify passes, report fields
correct); registered-but-unevaluated trial excluded from scope but visible
on chain; second judge raises; seal without judge raises; post-seal
propose/evaluate raise; evaluation whose meta conflicts with run_config
(e.g. different label_expr) raises at `evaluate` AND a hand-crafted
conflicting attestation on the chain fails `verify` invariant 8; policy
declared after a verdict (hand-crafted file) fails invariant 4; smuggled
extra key inside the seal's `policy` payload copy fails invariant 5; raw
trailing garbage fails invariant 1; legacy (stripped-hash) file fails
invariant 2; manifest mismatch fails invariant 6; all three anchors pin +
verify round-trip (GitAnchor against `git init` tmp); `python -m
harness.verify` exit codes 0 and 1.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,demo]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_certified_run.py tests/test_harness_verify.py -v` → exit 0; ≥ 25 NEW tests including the three red-first bypass tests
3. `.venv/bin/python -m pytest` → exit 0 (qlib-dependent tests may skip; nothing else may fail; full suite ~30 min, run once at the end)
4. `.venv/bin/ruff check .` → exit 0 (verified satisfiable at this base by the commander)
5. Before your FIRST commit, record `BASE=$(git rev-parse HEAD)`. Then
   `git diff --stat $BASE..HEAD` touches ONLY the six files of hard
   constraint 7, and `git diff $BASE..HEAD -- examples/` is empty
6. TDD evidence in the receipt: at least one recorded pytest command with a
   non-zero exit code from the red phase, before the green run

## Out of scope

- Real qlib adapter wiring, E2E on market data (ticket 11); the killer demo
  (stays uncertified calculator use — do not touch it).
- Cryptographic signing, transparency logs, process separation (v0.3+;
  prereg-gate v3 §6). Cross-run sibling registries (§6, RP-1 territory).
- Periodic mini-anchors before seal (explicitly rejected in design — the
  pre-seal window is a disclosed boundary).
- `court/` changes of any kind.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and
   its real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-07: certified run — seal, anchors, verify (the pre-registration gate)"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced
   by the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.2-07`

## Operational notes

- Write files INCREMENTALLY (several smaller edits — max_tokens killed a
  v0.1 dispatch emitting one giant file).
- Full pytest ≈ 30 min — once, at the end; inner loop on your two new test
  files.
- The venv in AC-1 is the only environment change allowed; GitAnchor tests
  create their own tmp `git init` repos (never touch the worktree's git;
  commit with `git -c user.name=test -c user.email=t@t` — the tmp repo has
  no config; verification reads the anchored content, e.g.
  `git show <sha>:anchors/<head>.txt`).
- The fake evaluator's `meta` should mirror the real adapter's shape
  (top-level `label_expr`, `metric_params`, `price_field`,
  `cost_declaration`, plus `config{…}` — see `adapters/qlib_cn.py:487-506`)
  so ticket 11's real wiring drops in without test churn.
