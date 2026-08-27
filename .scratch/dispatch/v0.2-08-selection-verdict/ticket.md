# Ticket: v0.2-08 — Selection–verdict alignment: direction-aware battery, verdict `role`, discriminating-only aggregation

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court's court kernel judges factor trials with a five-gate battery
(FDR-BY, DSR, PBO/CSCV, noise pool-max, noise individual). The v0.1 audit
found the "unanimous 5-gate" story rests on gates that do not match the
selection rule: the naive selection is `max|t|` (two-sided), but DSR deflates
a **signed** max-Sharpe and PBO ranks by the **signed** metric — presenting
them as co-equal unanimous votes when they test a different null. Design
ticket 03 resolved this; you are implementing that ruling.

The authoritative design ruling is `docs/design/selection-verdict-isomorphism.md`
(v2, committed in your worktree) — read ALL of it; its Q2 table, Q3, §4
implementation notes and §5 demo revision are binding. Cross-references:
`docs/design/court-kernel-spec.md` (the F2 ruling and the "Amendment (v0.2
ticket 03)" block after §4's table — also binding), `docs/design/killer-demo.md`
§6 (the revised aggregation narrative). The issue file is
`.scratch/v0.2/issues/08-selection-verdict-alignment.md` (its 2026-07-12/13
audit-amendment section included). Where this ticket pins something more
precisely, this ticket wins.

**The binding ruling, pasted (03 v2 Q2/Q3):**

> Each gate runs the form of its statistic consistent with the trial's
> `declared.direction`. If a sound, cheap direction-consistent form exists,
> the gate uses it and remains **discriminating** (counts in the survivor
> vote). If none exists, the gate **abstains**: computed and recorded, but
> marked `informational` and never enters the survivor boolean.

| Gate | `two-sided` | `greater` | `less` |
|---|---|---|---|
| DSR | **abstains** (`informational`; computed as today, signed) | enabled (signed, original DSR) | enabled **on the negated series** (negate the series matrix and the selected series, recompute moments, original DSR — never feed a negative-SR accused to the signed hurdle) |
| PBO | metric = **absolute** form (`abs_*`) | metric = signed form | metric = **negated** form (`neg_*`) — CSCV's IS-argmax takes the largest metric; the raw signed metric under `less` would pick the most-*positive* column and invert the isomorphism |
| FDR / pool-max / individual | already isomorphic (two-sided p, `|t|`) | directed statistic per F2 (t; one-sided p) | directed statistic per F2 (−t; one-sided p) |

> **Mixed-direction scope:** every family-level gate requires a
> direction-homogeneous scope. A judged scope whose trials carry
> heterogeneous `declared.direction` **raises** `ValueError` (fail-closed) —
> there is no principled single branch for a mixed family.

> **Q3 — aggregation:** every verdict carries `role ∈ {discriminating,
> informational}`, derived at judgment time from whether the gate's
> null-direction matches `declared.direction`. The survivor/unanimous rule
> counts ONLY `discriminating` verdicts; `informational` verdicts are
> computed, appended to the ledger, and shown in the report, but never flip
> the survivor boolean.

> **`role` storage (audit ruling D16):** `role` is recorded on the
> `VerdictRecord` as a new optional field `role: str | None = None`
> (mirroring the existing optional `engine_version`). Legacy ledgers replay
> fine (`role=None` = pre-v0.2 verdict); aggregation treats `None` as
> `discriminating` (legacy artifacts only — new judge runs always stamp an
> explicit role).

> **G5 registry amendment:** the metric registry gains the absolute (and
> negated) forms; the verdict `params` **must record the actual R name used**
> (`abs_sharpe` vs `sharpe`) — never silently transform the matrix while
> recording the base name, or the ledger is not auditable.

Current code facts (verified at this base):
- `court/judge.py:34-36` — `_METRIC_REGISTRY = {"sharpe": sharpe_ratio}`.
- `court/judge.py:168-182` — `_ranking_statistic` already implements F2
  (two-sided → |t|, greater → t, less → −t).
- `court/judge.py:213` — FDR p-values already use per-trial
  `p_from_t(tr.t, rec.declared.direction)`.
- `court/judge.py:244` `_apply_dsr` (signed pipeline over `matrix(scope)`),
  `:312` `_apply_pbo` (`:327` registry lookup by params `metric` name).
- `court/ledger.py` — `VerdictRecord` has NO `role` field; `append_verdict`
  has no `role` param. The ledger carries a content hash-chain (ticket 06,
  merged): every append computes `prev_hash`/`event_hash`; **do not touch
  the chain, attestation, or declaration/seal code paths** — a new optional
  event key flows through the chain automatically.
- `examples/killer_demo/aggregate.py` — `trial_survives` = every deciding
  verdict "pass" (no role awareness yet). `battery.py:53` passes
  `"metric": "sharpe"`. `report.py` renders per-gate rows.
- The judge does NOT currently enforce direction homogeneity across a scope.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality.
2. Do NOT build idea/factor generation logic.
3. `court/` must not import any market-specific code (decoupling smoke test
   stays green). Statistical implementations carry their citation in the
   docstring — the direction-aware forms cite
   `docs/design/selection-verdict-isomorphism.md` §2–§3 (and keep the
   existing Bailey/CSCV citations intact).
4. Fail-closed: violated preconditions raise `ValueError`; never repair,
   coerce, or silently drop. Never compute one thing and record another
   name for it.
5. Code, docstrings, comments: English.
6. TDD is contractual: failing tests FIRST (red run recorded in the receipt
   `self_test` with its real exit code), then implement to green.
7. File ownership boundary — you may modify ONLY:
   `court/judge.py`; `court/ledger.py` (**only** the `VerdictRecord`
   dataclass, the `append_verdict` signature/validation/event dict, and the
   verdict-replay branch — nothing else in that file);
   `court/__init__.py` (exports only); `examples/killer_demo/aggregate.py`,
   `battery.py`, `report.py` (and `run.py` only if a call site must pass
   through); `tests/test_judge.py`, `tests/test_killer_demo.py`, and (new)
   `tests/test_judge_direction.py`. Do NOT touch `harness/`, `adapters/`,
   `docs/`, `tests/test_ledger*.py`, `examples/killer_demo/out/` (committed
   artifacts stay byte-identical in your delivery), or the demo's
   generation/data/grid modules.

## Task

### 1. `role` on the verdict record (court/ledger.py, surgical)

- `VerdictRecord` gains `role: str | None = None` (after `engine_version`).
- `append_verdict(..., role: str | None = None)`: validated
  `role in (None, "discriminating", "informational")` else `ValueError`;
  when not None, stored on the verdict event under key `"role"`; replay
  reads `event.get("role")` → legacy verdicts replay with `role=None`.

### 2. Direction-aware judge (court/judge.py)

- **Homogeneity guard:** derive the family direction from the scope's
  trials' `declared.direction`; heterogeneous → `ValueError` naming the
  directions found. (Global precondition, before any gate runs.)
- **Role derivation + forms** exactly per the pasted Q2/Q3 table:
  - `two-sided`: DSR computed exactly as today, verdict stamped
    `role="informational"`; PBO resolves the **absolute** metric form; FDR /
    pool-max / individual stamped `discriminating`.
  - `greater`: all five gates `discriminating`; DSR/PBO as today (signed).
  - `less`: all five `discriminating`; DSR runs on the **negated** matrix
    and negated selected series (pairwise correlations are negation-
    invariant, so ρ̂/N̂ are unchanged — say so in the docstring); PBO
    resolves the **negated** metric form.
- **Registry (G5):** `_METRIC_REGISTRY` gains `"abs_sharpe"` and
  `"neg_sharpe"` (wrapping `sharpe_ratio`). Callers keep passing the base
  name (`"metric": "sharpe"`); the judge resolves the direction-consistent
  form and the **verdict params record the resolved name** (e.g.
  `"metric": "abs_sharpe"`). An unknown base name still raises. A caller
  passing an `abs_*`/`neg_*` name directly → `ValueError` (the form is the
  judge's ruling, not the caller's choice).
- Every gate's verdict is appended with its derived `role`.
- Do NOT bump `court.__version__` (a test pins "0.1.0.dev0"; version
  semantics are a later commander decision).

### 3. Discriminating-only aggregation (examples/killer_demo/aggregate.py)

- `trial_survives`/`survivor_ids`/`gates_faced_passed` count only verdicts
  with `role != "informational"` (i.e. `None` counts as discriminating —
  legacy artifacts ruling, pasted above). Read role via
  `getattr(v, "role", None)` — verdict-like objects without the attribute
  count as discriminating (existing tests pass SimpleNamespace stubs). Docstrings updated to cite
  killer-demo.md §6 (v0.2 revision).
- An informational verdict must be UNABLE to flip the survivor boolean —
  this is the ruling's red test (03 §7): first write the failing test
  showing a DSR "reject" under two-sided kills a trial that passes all four
  discriminating gates, then make it green via role.

### 4. Demo narrative (examples/killer_demo/battery.py, report.py)

- The battery table / per-gate report rows gain the gate's `role`; the DSR
  row under two-sided is labeled `informational` with the footnote
  "abstains under two-sided — one-sided DSR does not match a `|t|`
  selection" (03 §5).
- Concretely: `report.py:148` docstring "Five-row battery table" → reflect
  the role split; the battery table gains a Role column. (There is no other
  literal "five gates" string — do not hunt for one.) The morgue table's
  faced-count becomes x/4 for the accused; `docs/design/killer-demo.md` §6's
  example was already updated commander-side to match.
- PBO row reports the resolved metric name (`abs_sharpe`).
- The report footnote (`report.py:219-224`) currently says "PBO's internal
  selection is signed … while naive selection is |t|-based" — after this
  ticket that sentence is FALSE. Replace the PBO half with the 03 §4
  process wording: "PBO (abs metric under two-sided) judged the overfit
  probability of the selection process isomorphic to the naive scan on
  this matrix." (`docs/design/killer-demo.md` §5.4/§6 were already updated
  commander-side to match — cite them as-is.)

### 5. Exports (court/__init__.py)

- Re-export `DeclarationRecord` and `SealRecord` (closing the recorded
  ticket-06 seam), and nothing else new (`VerdictRecord` is already
  exported; `role` rides on it).

### 6. Tests (red first; new file `tests/test_judge_direction.py` is
MANDATORY for the direction/role tests AND for the ledger `role`
round-trip tests — `tests/test_ledger*.py` stay frozen and no other new
test file is allowed; extend `test_judge.py` / `test_killer_demo.py` where
natural)

Cover at least:
- **Idle-gate red test (03 §7):** two-sided scope where the accused passes
  FDR+PBO(abs)+pool-max+individual but DSR says "reject" → survives under
  role-aware aggregation; assert the DSR verdict exists, has
  `role="informational"`, and its decision is recorded.
- **Three-branch invariant:** two-sided → DSR verdict `role="informational"`,
  PBO params `metric == "abs_sharpe"`; greater → all verdicts
  `role="discriminating"`, PBO params `metric == "sharpe"`; less → PBO
  params `metric == "neg_sharpe"`, and DSR(less on data X) equals
  DSR(greater on data −X) numerically (same z, sr_star magnitude).
- Mixed-direction scope → `ValueError`.
- `append_verdict(role=...)` round-trip across reopen; invalid role raises;
  legacy verdict event without `role` key replays to `None`.
- Aggregation: informational verdict cannot flip survival; `role=None`
  verdict still counts (legacy).
- Caller passing `abs_sharpe` directly to PBO params → raises.
- Existing tests must pass unmodified, with ONE pre-authorized exception
  (ticket-lint verified it is forced): `tests/test_judge.py::
  test_pbo_cscv_pass_and_reject` is built on two-sided fixtures with a
  signed-sharpe oracle — under the new abs form its φ flips 1/3 → 2/3 and
  its decision assertions break by construction. **Authorized fix: change
  that test's (or its `_aligned_three_trials` fixture's) declared protocol
  to `direction="greater"` and keep every assertion byte-identical** (the
  signed oracle is then the correct form; the fixture-sharing DSR tests are
  numerically unchanged under greater). Record it under `deviations`. The
  two-sided/abs PBO coverage lives in `tests/test_judge_direction.py`.
  Beyond this: narrative-string assertions MAY be updated to the new
  wording, decision/count assertions may NOT.

## Acceptance criteria (the referee re-runs these independently)

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,demo]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_judge.py tests/test_judge_direction.py -v` → exit 0; ≥ 14 NEW tests, including the idle-gate red-turned-green test and the three-branch invariant
3. `.venv/bin/python -m pytest` → exit 0 (qlib-dependent tests may skip; nothing else may fail — zero regressions; note: the full suite takes ~11 minutes, mostly the small-scale demo E2E)
4. `.venv/bin/ruff check .` → exit 0 (verified satisfiable at this base by the commander)
5. Before your FIRST commit, record `BASE=$(git rev-parse HEAD)`. Then
   `git diff --stat $BASE..HEAD` touches ONLY the files listed in hard
   constraint 7, and `git diff $BASE..HEAD -- examples/killer_demo/out/` is
   empty
6. TDD evidence in the receipt: at least one recorded pytest command with a
   non-zero exit code from the red phase, before the green run

## Out of scope

- **Regenerating `examples/killer_demo/out/` with real data** — the referee
  runs that (~1 h qlib job) at acceptance; you deliver code + tests only.
- `harness/` (tickets 07/09), `adapters/`, `docs/` (the spec/design
  amendments are already committed), the ledger chain/attestation code, the
  aggregation-policy-on-chain work (ticket 09).
- Any change to selection/scan logic in `examples/killer_demo/naive.py` —
  the demo stays a two-sided `max|t|` scan (that is its point).

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and
   its real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.2-08: direction-aware battery, verdict role, discriminating-only aggregation"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced
   by the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.2-08`

## Operational notes

- Write files INCREMENTALLY (several smaller edits, never one giant
  emission — a v0.1 dispatch died of max_tokens_truncation).
- The full pytest run takes ~11 minutes — run it once at the end; use the
  two judge test files for your inner loop.
- The venv in AC-1 is the only environment change allowed.
