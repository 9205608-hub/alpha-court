# Trial Ledger — Contract (v0.1)

**Provenance:** decided 2026-07-10 in ticket `.scratch/v0.1/issues/03-trial-ledger-contract.md`
(HITL grilling; all four rulings confirmed by the project owner).
**Consumers:** the court kernel spec (ticket 08) must cite this document; the DSR / PBO-CSCV /
BHY / noise-control implementations take their ledger-facing interface from here.
**Scope:** data schema + API contract only. No implementation in this document.
**Vocabulary:** canonical terms (Trial, Hypothesis, Verdict, Declared protocol, Effective
trial count, Ledger, Scope) are defined in the repo-root [`CONTEXT.md`](../../CONTEXT.md);
this document uses them without redefinition.

---

## 1. Purpose

The trial ledger is the court's single source of evidence: an append-only audit log of
every hypothesis declared, every trial evaluated, and every verdict rendered. Its contract
answers the deepest interface question in the project: **what is one trial, and where does
each statistic's multiplicity input (N) come from?** Everything downstream — DSR's
expected-max hurdle, BHY's correction strength, PBO's selection pool — inherits its
semantics from this document.

## 2. The four rulings

1. **Atom & counting.** One trial = one evaluation of one factor configuration
   (construction × parameter set × evaluation window) producing one performance series.
   A parameter sweep of k settings is k trials. Two-level family structure:
   hypothesis → trials. **N is never stored** — each statistic derives its own effective
   count from the ledger at judgment time (§4).
2. **Records.** Three record types (Hypothesis / Trial / Verdict), all immutable and
   append-only. Series are stored **by value** inline. Derived statistics are never
   authoritative fields on a trial; they are computed at judgment time and logged inside
   the verdict. Trial status is derived from which records exist, with no `abandoned`
   escape hatch (§5).
3. **Storage.** A single-file append-only JSONL event log (`ledger.jsonl`), replayed into
   an in-memory index on open. Physical line order guarantees registration-before-evaluation
   auditability. Crash recovery: discard a trailing unparseable line (§6).
4. **API.** Three layers: `Ledger` is pure bookkeeping and understands no statistics;
   the statistics are pure functions over arrays and do not know the ledger exists;
   a thin `judge` orchestrator is the only component that knows both (§7).

Rationale for ruling 1, in one sentence: coarse granularity destroys information
irreversibly (PBO loses its selection pool, DSR loses the series needed for ρ̂), while
fine granularity costs only a derivation step at read time — all the irreversibility
lives on the coarse side.

## 3. Non-negotiable constraints inherited from the constitution

- **Decoupling:** `court/` never interprets market-specific content. `spec`, `params`,
  and series index labels are opaque to the court (§9). Calendars, trading halts, and
  universe definitions live in `adapters/`.
- **Honesty:** null-archived trials receive the same record treatment as survivors.
  The ledger has no verb that removes or hides a trial.
- **Literature fidelity:** every statistic consuming this contract implements the cited
  public formulas; the sufficiency matrix in §8 maps ledger outputs to the inputs those
  formulas require, with citations into `docs/research/`.

## 4. Trial definition and multiplicity accounting

### 4.1 The atom

A **trial** is one evaluation of one factor configuration against data, yielding exactly
one performance series (period returns or period IC, per the declared protocol). Sweeping
momentum lookbacks {5, 10, 20, 60} under one hypothesis produces four trial records under
one hypothesis record. The ledger records facts at this finest grain and **never collapses
at write time**.

### 4.2 Effective N is a per-statistic query, not a field

| Consumer | Effective N it derives | What it reads from the ledger | Source |
|---|---|---|---|
| **DSR** | N̂ = 1 + (M−1)(1−ρ̂), the implied independent count from raw trial count M and average pairwise correlation ρ̂; cross-trial SR variance V[{SR}] from the trial SR vector | all series in scope (to compute per-trial SRs and ρ̂); the selected trial's series (moments, T) | `docs/research/dsr.md` §2.c, §5.3–5.4; Bailey & López de Prado (2014) Eq. (1), (2), App. A.3 Eq. (9) |
| **PBO (CSCV)** | N = number of columns in the selection pool — every configuration compared, one column each | the T×N synchronous matrix over the scope (§7.2 `matrix`) | `docs/research/pbo-cscv.md` §2; Bailey et al. (2017) Alg. 2.3 |
| **BHY** | N = number of hypothesis tests in the FDR family. **v0.1 policy: one trial = one hypothesis test**, full scope enters the family, nulls included | one p-value per trial, computed at judgment time from the series under the trial's declared protocol (direction, SE convention) | `docs/research/bhy.md` §4.4, §7.5; Harvey, Liu & Zhu (2016) §3.7.2 |
| **Noise control** (design: ticket 07) | consumes the same read surface: counts, series, family structure | scope listing + series + hypothesis grouping | ticket 07 (pending); no additional ledger capability anticipated |

Notes:

- Family structure is **not** used to shrink any N at write time. For DSR, within-family
  dependence is absorbed automatically by ρ̂; for BHY, correlated per-configuration
  p-values are legitimate family members because BY's harmonic correction holds under
  arbitrary dependence (Benjamini & Yekutieli 2001, Thm 1.3).
- The alternative BHY policy — one representative test per hypothesis with an
  in-family selection-adjusted p-value — is **deliberately deferred** to a v0.2 policy
  switch. Feeding the best-of-family p-value without selection adjustment is exactly the
  hidden-tests failure HLZ warn about and is forbidden.
- In the v0.1 killer demo (100 noise factors × 1 configuration each) the two BHY policies
  coincide: 100 trials = 100 hypotheses.

## 5. Record schemas

Field names are contractual at the semantic level; exact serialization casing is fixed by
ticket 08. Types below use JSON vocabulary. All timestamps are ISO-8601 UTC. All IDs are
opaque strings assigned by the ledger, unique within one ledger.

### 5.1 HypothesisRecord

| Field | Type | Semantics |
|---|---|---|
| `hypothesis_id` | string | Ledger-assigned. |
| `statement` | string | The economic claim, in plain language. |
| `created_at` | timestamp | When the hypothesis was declared. |

### 5.2 TrialRecord

Assembled from two events (§6): a **registration** event and at most one **evaluation**
event. The registration part is complete before any performance data exists.

Registration part:

| Field | Type | Semantics |
|---|---|---|
| `trial_id` | string | Ledger-assigned. |
| `hypothesis_id` | string | Must reference an existing HypothesisRecord (fail-closed otherwise). |
| `spec` | object | Factor construction description. **Opaque to the court** — provenance for humans and adapters. |
| `params` | object | This trial's parameter setting. Opaque to the court. |
| `registered_at` | timestamp | Pre-registration timestamp. Stamped by the ledger, not the caller. Reserved seat for the v0.2 pre-registration gate. |
| `declared` | object | The declared protocol, locked before evaluation (below). |
| `source_ref` | string, optional | Pure provenance pointer (e.g. adapter run id). The court never dereferences it. |

`declared` protocol object:

| Field | Type | Semantics |
|---|---|---|
| `metric` | `"returns"` \| `"ic"` | Semantics of the series values. |
| `direction` | `"two-sided"` \| `"greater"` \| `"less"` | Test sidedness. Default `"two-sided"`; a one-sided declaration is only legitimate at registration time (`docs/research/bhy.md` §4.2). |
| `window` | `{start, end}` | Declared evaluation window (opaque labels; court compares, never interprets). |
| `periods_per_year` | number | Display-only annualization factor. The kernel computes everything at native frequency (`docs/research/dsr.md` §5.1). |
| `se` | `{kind: "iid" \| "newey_west", lags?: int}` | Standard-error convention for the trial's t/p computation, declared so the court can reproduce p (`docs/research/bhy.md` §4.3). Default choice is fixed by tickets 08/11, not here. |

Evaluation part (appended by `record`, at most once):

| Field | Type | Semantics |
|---|---|---|
| `series` | `{index: [label...], values: [number...]}` | The performance series. Equal-length arrays; labels opaque, equality-comparable only. Stored **by value**. |
| `evaluated_at` | timestamp | Stamped by the ledger. |

**No derived statistics on the trial record.** SR, t, p, moments are computed at judgment
time from `series` and logged in the verdict — the series is the single source of truth,
so stale derived fields cannot exist.

**Status is derived, never stored:** `registered` (registration event only) →
`evaluated` (evaluation event present) → `judged` (appears in ≥1 verdict's decisions).
There is deliberately **no `abandoned` state**: a registered-but-never-evaluated trial is
a standing, auditable file-drawer datum (HLZ hidden tests), and an explicit abandon verb
would be a legal channel for moving bodies out of the family.

### 5.3 VerdictRecord

One record per application of one statistic to one scope.

| Field | Type | Semantics |
|---|---|---|
| `verdict_id` | string | Ledger-assigned. |
| `statistic` | string | e.g. `"dsr"`, `"pbo_cscv"`, `"fdr_by"`, `"fdr_bh"`, `"noise_control"`. Use explicit `fdr_by`/`fdr_bh`, never the ambiguous name "BHY" in code (`docs/research/bhy.md` §7.5). |
| `scope` | [trial_id...] | The explicit trial set used as evidence (pool / family). No implicit "everything". |
| `params` | object | Statistic inputs: q, confidence level, S, SE convention actually applied, etc. |
| `computed` | object | Intermediate values sufficient for line-by-line audit against the research notes (e.g. SR*, V[{SR}], N̂, ρ̂ for DSR; φ and logit counts for PBO; k*, thresholds, per-trial p for FDR). |
| `decisions` | `{trial_id: "pass" \| "reject"}` | Per-trial rulings. May cover a subset of scope (DSR judges only the selected trial; FDR covers the family). |
| `judged_at` | timestamp | Stamped by the ledger. |
| `engine_version` | string, optional | Code identity for reproducibility. |

Verdicts never mutate trial records. Aggregating multiple statistics into a trial's final
survival call is **judge configuration** (ticket 11's design), not ledger contract.

## 6. Storage: single-file JSONL event log

One ledger = one file, `ledger.jsonl`, UTF-8, one JSON object per line, append-only.
The path is supplied by the caller; the court hardcodes no location.

**Event envelope:** every line carries `{"type": <event>, "at": <timestamp>, ...payload}`
with `type` ∈:

| Event | Payload | Produces |
|---|---|---|
| `hypothesis` | HypothesisRecord fields | a hypothesis |
| `trial` | TrialRecord registration part | a registered trial |
| `evaluation` | `trial_id` + evaluation part | trial becomes evaluated |
| `verdict` | VerdictRecord fields | a verdict |

**Invariants**

1. Append-only: no line is ever rewritten or deleted.
2. Referential order: an event referencing an id must appear after the event that created
   it. In particular, a trial's `evaluation` line physically follows its `trial` line —
   the registration-before-evaluation property is guaranteed by file order, not just
   timestamps.
3. At most one `evaluation` event per `trial_id` (replay fails closed on a duplicate).
4. Crash recovery: if the final line fails to parse as JSON, it is discarded as a torn
   write — the corresponding operation is deemed never to have happened. A parse failure
   anywhere else is corruption: fail closed, do not silently skip.
5. Single writer per ledger file is assumed in v0.1 (one court process). Concurrent
   writers are out of scope and unguarded.

On open, the ledger replays the file into an in-memory index. Replay cost is linear and
comfortable to ~10⁵ lines; the v0.1 demo is four orders of magnitude below that.

## 7. API surface

Signatures are contractual in shape (verbs, inputs, outputs, failure semantics); exact
Python typing is fixed by ticket 08. General failure rule: **fail closed** — raise on any
violated precondition; never repair, coerce, or silently drop.

### 7.1 Bookkeeping verbs (write side)

```
Ledger.open(path) -> Ledger
    Create the file if absent; otherwise replay and index it.

ledger.register_hypothesis(statement) -> hypothesis_id
    Declare an economic claim. Deliberately a separate verb: the claim precedes
    any of its trials (pre-registration discipline).

ledger.register(hypothesis_id, spec, params, declared) -> trial_id
    Register one trial. Stamps registered_at (ledger clock, not caller-supplied).
    Returns only after the line is durably appended (flushed) — the pre-registration
    timestamp is credible because it is on disk before any evaluation can be recorded.
    Fails: unknown hypothesis_id; malformed declared protocol.

ledger.record(trial_id, series) -> None
    Attach the performance series; stamps evaluated_at.
    Fails: unknown trial_id; trial already evaluated (immutability);
    index/values length mismatch; non-finite values policy per ticket 08.

ledger.append_verdict(verdict) -> verdict_id
    Write-side entry reserved for the judge layer.
    Fails: any scope/decision trial_id unknown.
```

### 7.2 Read side (the four statistics' data surface)

```
ledger.trials(scope=None) -> list[TrialRecord]
    scope = explicit trial_id collection; default = the whole ledger.

ledger.series(trial_id) -> Series

ledger.matrix(trial_ids) -> (index, values[T×N])
    The synchronous performance matrix (PBO's M; also the ρ̂ feed for DSR).
    Fail-closed alignment: every trial's index must be label-for-label identical,
    otherwise raise — never outer-join, resample, or silently align
    (docs/research/pbo-cscv.md §6.1).

ledger.verdicts(trial_id=None) -> list[VerdictRecord]

ledger.status(trial_id) -> "registered" | "evaluated" | "judged"
    Derived from record existence (§5.2); not a stored field.
```

### 7.3 Statistics layer — pure functions

`psr`, `dsr`, `expected_max_sr`, `pbo_cscv`, `fdr_by`, `fdr_bh`, … take arrays and
scalars, return values and intermediates, and hold no reference to any ledger. This makes
the hand-worked test vectors in `docs/research/{dsr,pbo-cscv,bhy}.md` directly executable
as pytest cases with zero glue. Exact signatures follow each note's §3 code-mapping table
and are assembled by ticket 08.

### 7.4 Judge — thin orchestrator

```
judge(ledger, scope, config) -> Judgment
```

The only component that knows both sides: reads evidence via §7.2, computes p-values and
statistics via §7.3 under each trial's declared protocol, appends one VerdictRecord per
statistic application via `append_verdict`, and returns a summary. Battery composition
and survival aggregation policy live in `config` (ticket 11), not in this contract.

## 8. Sufficiency check (ticket acceptance criterion)

The contract must let all four statistics obtain N and series from the ledger alone:

| Requirement | Satisfied by |
|---|---|
| DSR: raw M, trial SR vector, ρ̂, selected trial's series & T | `trials(scope)` count; per-trial `series`; `matrix` for pairwise ρ̂; `series(selected)` |
| PBO: T×N synchronous matrix over the selection pool | `matrix(trial_ids)` with fail-closed alignment |
| BHY: one p per family member incl. nulls, sidedness & SE reproducible | full-scope `trials()` (nothing can be hidden or removed); `declared.direction` + `declared.se` + series → p at judgment time |
| Noise control: counts, series, family grouping | `trials`, `series`, `hypothesis_id` grouping |

## 9. Decoupling guarantees

The court **never interprets**: `spec`, `params`, `source_ref`, series index labels
(equality-comparable opaque tokens; no calendar arithmetic), or `window` label content.
Anything that knows what a trading day, a ticker, or a limit-up rule is belongs in
`adapters/`. This is the API-level form of the constitution's decoupling iron law, and it
is what keeps `court/` importable with numpy/pandas/scipy alone.

## 10. Reserved seats for v0.2 (pre-registration gate)

Already present in v0.1 so the gate needs no schema migration: `registered_at` (ledger-
stamped, durable-before-return), the full `declared` protocol (metric, direction, window,
frequency, SE), and the physical registration-before-evaluation line ordering. The v0.2
gate adds **enforcement** (fail-closed hooks around agent behavior), not fields.

## 11. Out of scope for this contract

- Statistic function signatures and numeric guards (ticket 08, from the research notes).
- Battery composition, survival aggregation, and demo presentation (ticket 11).
- The in-family representative policy for BHY (v0.2 policy switch, §4.2).
- Concurrent multi-writer ledgers; storage backends beyond JSONL.
- Any enforcement/governance behavior (v0.2 harness).

## References

- `docs/research/dsr.md` — Bailey & López de Prado (2012, 2014): PSR, E[max SR], DSR, N̂.
- `docs/research/pbo-cscv.md` — Bailey, Borwein, López de Prado & Zhu (2017): CSCV/PBO.
- `docs/research/bhy.md` — Benjamini & Hochberg (1995); Benjamini & Yekutieli (2001);
  Harvey, Liu & Zhu (2016): FDR control, family accounting.
- `CONTEXT.md` — canonical vocabulary.
- `.scratch/v0.1/issues/03-trial-ledger-contract.md` — the deciding ticket.
