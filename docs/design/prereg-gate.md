# Pre-registration gate — design contract (v0.2 ticket 02)

Status: v4 (grilling-locked 2026-07-11; batched grok review folded — §10; v0.2
design-layer audit folded 2026-07-12 — §11; **ticket-07 delivery audit folded
2026-07-16** — two fail-opens closed: the *judgment* on-chain event (mid-battery
brick can no longer be revived via reopen) and anchor query-by-recomputed-head
(a supplied anchor is fail-closed and never consulted via the attacker-writable
manifest); see §12).
Owner ticket: `.scratch/v0.2/issues/02-prereg-gate-model.md`
Implements into: `.scratch/v0.2/issues/06-ledger-provenance.md` (evidence layer),
`.scratch/v0.2/issues/07-prereg-gate-enforcement.md` (the gate),
`.scratch/v0.2/issues/09-aggregation-config.md` (aggregation on-chain).

## 1. Purpose & scope

The v0.1 audit's verdict: **the ledger has the seat but not the gate.**
`DeclaredProtocol` can carry a locked protocol and `register` precedes `record`, but
nothing *enforces* that the family the court judges is **the full search run through
the certified path** (audit revision D9, 2026-07-12: the v2 wording "the full
search the agent ran" over-claimed — off-path pre-screening is a disclosed boundary,
§6, not something this gate can see). The court derives multiplicity N from the
judged **scope**; if the agent controls scope, it controls N — the core
self-deception (under-register / shrink scope).

This gate makes the court's iron discipline **reflexive on the agent that uses it** —
the v0.2 embodiment of **RP-0**: a pre-registration leaves a **trace**, is
**re-computable**, and is **tamper-evident** — *only mechanical traces count, intent
does not*. Idea generation stays stubbed (three-don'ts); the gate is the choke point a
future idea-mining agent passes through so it cannot fool itself.

## 2. Decisions (grilling Q1–Q5 + batched grok review, 2026-07-11)

| # | Decision | Ruling |
|---|---|---|
| Q1 | Enforcement philosophy | **(A) impossible-by-construction *on the certified path*** (the harness owns the loop; the agent never passes scope and cannot evaluate outside the loop) **+ (B) tamper-evident seal** as the backstop. A direct `court` call is still *possible* — (A) is not a physical prohibition; (B) is what makes a bypass **detectable** (no valid seal). |
| Q2 | Placement | **court stays pure** (iron law #2). `harness/` is the **certified path**. Certification attaches to the **run seal**, not to any single `VerdictRecord`. A run is "pre-registration-certified" iff it carries a valid seal; a direct `court` call is a legitimate **uncertified calculator use**. |
| Q3 | Tamper-evidence | in-ledger **hash-chain** over event *content* (integrity: local edit/insert/delete/reorder is detected on replay) **+ an external anchor pinned ONCE at seal** (not per-trial). "tamper-**evident**", not tamper-proof: the anchor only defeats a full rewrite if it lives outside the rewrite surface (pushed remote / protected branch). Anchoring is a **pluggable backend** (git default, `FileAnchor`/`NoopAnchor` for tests) — no hard VCS import. |
| Q4 | Invariants | (1) declared-before-series (physical line order + chain); (2) judged scope = complete registered-evaluated set (harness derives); (3) **series↔declared conformance** — the adapter **attests** `metric`/`window`/`universe`/`*_version`/`n_evaluation_dates`; the harness checks `metric`/`window` against `DeclaredProtocol` and `universe`/`*_version`/adapter config against the **run-level `run_config` declaration event** (§3a — audit revision D7: the v2 "attested == declared" had no declared-side home for universe/versions, and nothing locked the adapter configuration per run) + **cheap structural checks**; (4) direction (and every declared field, incl. the run_config) immutable once a series exists. Adapter does **not** attest `direction`/`se` (not adapter semantics). |
| Q5 | Granularity & interface | **trial-level incremental** (per-trial protocol lock + no-hidden-trials, *not* fixed-N-up-front). `propose(hypothesis, declared, spec, params)` → harness registers into the chain → `evaluate` via the adapter (attesting) → `record` (check) → `judge` derives scope from the complete set → **seal**. **One `Run` = one multiplicity family = one `judge` = one seal**; a new experiment needs a new run. |

## 3. Architecture

- **`court/` — three changes, honestly listed** (audit revision, 2026-07-12: the v2
  "unchanged (except …)" parenthesis under-reported its own delta): ticket 06's
  (1) `source_ref` reachability + optional `record(..., attestation)` param,
  (2) the **hash-chain fields + canonical serialization** in `_append_event`
  (§4.1), and (3) two new **court-opaque event types** in the ledger vocabulary —
  `declaration` (payload uninterpreted by court; used by the harness for the
  `run_config` and the ticket-09 aggregation policy) and `seal` (§4.2). The court
  stores and replays these without interpreting them — no market semantics enter
  `court/`; it stays a pure calculator + append-only ledger; `judge` still accepts
  a caller scope for pure-function tests and the killer demo.
- **`harness/` — the certified path** (the package already hosts the unrelated
  session-governance modules `trial_counter`/`confirm_gate`/`anti_pattern_gate`;
  the certified path lives in its own submodule, e.g. `harness/run.py` — audit
  minor). A `Run` object holds the ledger + the running chain head:
  - **`run_config` declaration (at Run creation, before any trial — audit revision
    D7):** the first chain event locks the **full adapter configuration** —
    universe, provider_uri, label_expr, quantile, min_cross_section, declared data
    tag, and the version-pinning policy. This is the declared-side home for every
    attestation key that `DeclaredProtocol` (deliberately) does not carry; it also
    closes the deeper hole the audit found: without it, an agent could swap
    `label_expr` (the definition of ground truth) mid-run with every per-trial
    check green.
  - `propose(hypothesis, declared, spec, params)` → registers (appends a chain event);
  - `evaluate(handle)` → runs the sanctioned adapter, which returns the series **and an
    attestation** (`qlib_cn._meta` already yields metric/window/universe/data_version/
    adapter_version/qlib_version/n_evaluation_dates + `meta.config`); the harness
    checks conformance — `metric`/`window` vs declared, everything else vs the
    `run_config` event — and records both;
  - `judge()` → derives scope from the **complete** registered-evaluated set (the agent
    never passes a scope), runs `court.judge`, then writes a **seal** event.
- On the certified path the agent cannot evaluate outside the loop, cannot pass scope,
  cannot reorder declared-after-series, and cannot alter a recorded event without
  breaking the chain. Off the path (direct `court` use) it can — and the missing seal
  is what marks that output `uncertified`.

## 4. The seal & tamper-evidence

### 4.1 Hash-chain (content, not wall-clock)

Each event links by content hash, excluding the real-clock timestamp:

```
content       = event minus (at, prev_hash, event_hash)   # `type` IS in content (audit pin: flipping an event's type must break the chain; note the envelope has only `at` — "registered_at" etc. are replay-derived record fields, a v2 typo)
content_hash  = H(canonical_json(content))
event_hash    = H(prev_hash || content_hash)
stored line   = {type, at, ...content, prev_hash, event_hash}
```

- **Timestamps are audit-aux, not the security root.** The hard pre-registration
  evidence is **physical order** — the JSONL line order, with each `evaluation` event's
  `prev_hash` locking its `register`. `at` is not in the content hash: honest
  **re-execution** of an experiment stamps new wall-clock times and must reproduce
  the same content chain (audit wording fix — *replay* of a stored file reads the
  stored `at` and is unaffected; the v2 rationale conflated the two). Consequence,
  stated plainly (audit revision, was over-claimed as "back-dating" defense): the
  chain protects **relative order**, not absolute time — an editor who rewrites
  `at` values without touching content or order breaks nothing. Absolute time is
  attested only by the external anchor's own timestamp at seal. If time itself must
  be tamper-evident, that is a separate `clock_hash` sub-chain or the anchor —
  never bound to the content root.
- **Canonical serialization (07/06 must-add).** The hash path uses
  `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False,
  allow_nan=False)`. (Today `_append_event` has **no `sort_keys`** — verified; storage
  lines may stay insertion-order for readability, but the *hash* path must sort.) Floats
  enter the hash via a fixed encoding (`struct.pack('<d', x).hex()`), never the default
  json float repr. Implementation note (audit nit): `json.dumps` does not invoke
  `default=` for floats — the tree must be **recursively pre-transformed** (floats
  replaced by their hex encoding) before dumping; NaN/Inf are rejected before the
  hash path (the ledger's finiteness guards already run first).

### 4.2 The seal event (the certificate — authoritative)

The run's final event is `type: "seal"` carrying: `chain_head`, the complete
`scope` (all evaluated trials), `verdict_ids`, the `aggregation`/`selection` policy id
(ticket 09), and an optional `anchor_ref`. **This is the certificate** — verification
reads one file: replay the line order, recompute the chain from genesis, check it matches
`chain_head`.

**The `judgment` event (ticket-07 delivery audit, 2026-07-16 — closes a reopen
fail-open).** `court.judge` appends its verdicts **per-application**; if the battery
raises mid-way it leaves orphan verdicts on the chain. A `CertifiedRun.judge()` that
bricks in-memory must stay bricked **across a reopen** — otherwise an agent shrinks
the battery by making the N-th statistic throw, reopens the ledger (crash-recovery),
and seals a run that verify cannot distinguish from an honest N−1-gate run (the
reconstructed `verdict_ids` cover exactly the orphans). The fix: **on a successful
`court.judge`, and only then, append a court-opaque `judgment` declaration event**
`{"kind": "judgment", "battery": [<Application(statistic, params) list, verbatim,
in order>], "verdict_ids": [...]}` BEFORE the seal. Consequences:
- `seal()` requires a `judgment` event whose `verdict_ids` equal ALL verdict events
  on the chain; absent or mismatched → `ValueError`/`CertificationError`.
- `open()` recovers judged-state from the **`judgment` event**, not from raw verdict
  presence: verdicts-without-judgment (a brick or a crash) → `judge` is spent and
  `seal` is refused (the run is durably bricked).
- The battery is now **on-chain and auditable** and `verify` gains invariant 7.5:
  exactly one `judgment`, its `verdict_ids` == every chain verdict == the seal's
  `verdict_ids`, **and its `battery` statistics multiset == the covered verdicts'
  statistics** (rework-02 — without the cross-check the field could lie under a full
  reforge, referee-reproduced). The load-bearing protection against N-shrink is that a
  verdict cannot be hidden (verdict_ids covers all); the `battery` field is the
  human-readable summary the cross-check keeps honest. A copy of `chain_head` + `seal_event_hash` + env versions goes into a
human/CI `run_manifest.json` (aligned with the killer demo's `run_config.json`). Git (or
another `AnchorBackend`) may commit the manifest/anchor once — but a **git commit message
is never** the machine-verifiable root, and the `VerdictRecord` is **never** mutated to
hold the certificate (that would pollute the pure calculator).

**Anchor/manifest ordering (audit minor — the v2 text folded two artifacts into one
sentence):** the precise sequence is (1) seal event appended (chain head final);
(2) anchor pins **that chain head** externally (e.g. one git commit); (3) the
`anchor_ref` naming the pin is written to the `run_manifest.json` **copy** — the
seal event itself carries `anchor_ref` only when the backend can mint the reference
*before* the seal line is written (e.g. `FileAnchor`); with git-after-seal the seal's
`anchor_ref` is null and the manifest carries it. A seal may never reference an
artifact that does not yet exist.

**Pre-registration certifies the RUN, not a single statistic verdict.**

**Anchor verification is query-by-recomputed-head, fail-closed (ticket-07 delivery
audit, 2026-07-16 — closes an anchor-bypass fail-open).** The `run_manifest.json` is
a human/CI convenience copy that lives **inside the rewrite surface** — an attacker
who forges the whole chain simply deletes or blanks it. Therefore verification must
**never** decide whether-and-what to check against an anchor from the manifest's
`anchor_ref`. Binding rule for `verify(path, anchor=backend)`:
- when a `backend` is supplied, verify computes the honest `final_head` from the
  chain itself and asks the backend **"have you anchored THIS head?"** —
  `backend.verify(final_head) -> bool`, using the backend's own protected state (its
  anchor file / git repo), not any manifest-supplied reference;
- a supplied backend that returns False, errors, or has no record of `final_head` →
  **fail-closed `CertificationError`** ("anchor supplied but does not attest the
  recomputed head"). A supplied anchor is never silently skipped because a sidecar
  file is missing.
- The manifest `anchor_ref` is downgraded to advisory (reported, never trusted for
  the security decision). This makes the anchor a real defense against full-chain
  rewrite (the forger cannot make a protected backend attest a head it never pinned),
  which is the whole point of §6's "tamper-evident" claim.

### 4.3 Anchor timing & compatibility

- The external anchor is pinned **once, at seal** — never per-trial. (A literal
  "git commit before each series" over a trial-level incremental loop would be 100 commits
  per 100-trial run — grok's catch.) Incremental integrity rides on the chain alone.
  **What the anchor attests (audit revision D6 — the v2 §5 clause "an anchor that
  does not predate the series → seal invalid" contradicted this design and is
  deleted; it had copied the anchor-*before*-results semantics of the personal
  prereg-gate.sh precedent into an anchor-*after*-results design):** the anchor
  proves the sealed chain head existed **no later than** the anchor's own
  timestamp, and any post-anchor rewrite must move or orphan the pin. It does
  **not** prove declarations predate series — that is the chain's line order. A
  run-creation **pre-anchor** (pinning the `run_config` event before any trial) is
  a distinct, optional, separately-named object — not required in v0.2.
- The chain is compatible with the ledger's append-only + fsync + torn-write recovery:
  compute `event_hash` → write the single line (hashes included) → fsync; a torn last line
  truncates and the chain stops at the previous head; a mid-file corruption raises
  `LedgerCorruptionError` and fails verification. **Never** "write hashless then patch a
  hash in" (that fights append-only). Single-writer assumption unchanged.

## 5. Fail-closed semantics (extends court §6)

- a `record` whose trial has no prior `register` in the chain → raise;
- a certified `judge` scope smaller than the complete registered-evaluated set → raise;
- a certified run with **no `run_config` declaration event before the first trial**
  → raise (audit revision D7);
- an adapter attestation not equal to its declared home — `metric`/`window` vs
  `DeclaredProtocol`, `universe`/`*_version`/adapter config vs the `run_config`
  event — or failing a structural check (`len(series) != n_evaluation_dates`;
  missing required attestation key; a bare `record` with no attestation on the
  certified path) → raise;
- a second `declared` overwriting an existing one, or any declared field (incl.
  `run_config`) changed after a series exists → raise (append-only already forbids
  mutation; the gate forbids a shadow re-declaration);
- **no pre-registered aggregation/selection policy on the chain at seal time**, or
  a rule at seal not equal to that policy (ticket 09) → raise (audit minor: the v2
  list covered only the not-equal case, not the absent case);
- **the seal must be the final event**: any event after a seal, or a second seal →
  verify fails (audit revision D8 — this also closes post-seal suffix games);
- `propose`/`evaluate`/`record` called on a sealed `Run` → raise;
- a seal whose `verdict_ids` do not cover **every** verdict event on the chain →
  verify fails (a wild `court.judge` verdict smuggled onto a certified ledger is
  not silently absorbed);
- a broken hash-chain → seal invalid. *(The v2 clause "an anchor that does not
  predate the series → seal invalid" is deleted — see §4.3, audit revision D6: it
  was unsatisfiable under anchor-at-seal and belonged to a different anchor
  design.)*

## 6. Honest boundaries (禁赢学 — on the first screen)

The gate defends against a **researcher / agent fooling itself on the certified
path** — changing metric/direction after seeing data, shrinking scope, hiding
trials mid-run, reordering, post-hoc-picking the aggregation. ("Back-dating" is
deliberately absent from this list — the chain protects relative order, not
absolute time; §4.1.) It does **not**:

- **Verify the adapter computed correctly.** The harness *trusts the sanctioned adapter's
  attestation* (attested == declared + shape); it does not re-derive ground truth. Correct
  computation is the adapter's own oracle + golden fingerprint (`adapter-interface.md`).
  A **same-adapter sampling-recompute would catch nothing** (same source) and an
  independent recompute breaks the layering — so v0.2 does neither; it adds only the cheap
  structural checks of §5. Do not claim the gate "verifies the data."
- **Achieve cryptographic non-repudiation.** The seal is **tamper-evident**, not
  tamper-proof: a local `git --amend`/`reset`/history-rewrite can erase a local anchor.
  This is enough for RP-0 (rewriting an *anchored* history is deliberate and leaves a
  reflog — the reflog claim applies to git-anchor rewrites only, not to the forgery
  and truncation boundaries below, which leave no trace; audit revision D10 narrowed
  this sentence); it is not a third-party court of law. v0.2 does **not** add signing
  keys / transparency logs (v0.3+).
- **Protect the pre-seal window against suffix truncation (audit revision D8 —
  measured, not hypothetical: deleting the last evaluation line of a real ledger
  replays with zero warnings).** Before the seal there is no external pin; the
  chain proves only the **order-consistency of the surviving lines** (prefix
  integrity), and the torn-write recovery rule legitimizes a missing tail. An agent
  that evaluates, dislikes the result, and truncates the suffix produces a ledger
  byte-indistinguishable from an honest "registered but not yet evaluated" state.
  The seal-must-be-final rule (§5) closes this **after** sealing; the pre-seal
  window is an accepted, disclosed limit (periodic mini-anchors were considered and
  rejected with per-trial anchoring, §4.3).
- **See searches run off the certified path (audit revision D9).** Direct
  adapter/court use is *legitimate uncertified calculator use* (Q2) — an agent can
  scan 1000 variants off-path, then open a certified run for its 5 favorites and
  earn a perfectly valid seal with N=5. The seal certifies "the family = everything
  evaluated through **this** Run"; it cannot certify "…and nothing was tried
  elsewhere." This is the classic pre-registration limitation, and it is exactly
  where **RP-1** must ask: *what did you touch on this data window before this
  run?* (A fresh-window requirement is the real mechanization — v0.3+ material.)
- **Authenticate the provenance of series/attestations (audit revision D10).** The
  attestation is an unsigned in-process dict; an agent holding the ledger can
  hand-craft a conformant series+attestation and extend the chain validly — the
  resulting seal is *valid* and certifies protocol-consistency and order of what
  was recorded, **not** that the sanctioned adapter produced it. In-process
  unforgeability is impossible without process separation (v0.3+); ticket 07 must
  **not** fake it with in-process nonces/HMACs (security theater).
- **Bind sibling runs (audit revision D11).** §8 forbids stuffing two experiments
  into one run (N dilution); nothing binds the *opposite* — splitting one search
  into many small certified runs, or restart-until-lucky across runs, is invisible
  to any single seal. Governance rule (RP-1 checkpoint, not mechanized in v0.2):
  **presenting any sealed run entails presenting all sibling runs of the same
  claim.** A cross-run registry/anchor chain is deferred, by name.
- **Prevent fine-grained hypothesis pre-declaration.** An agent may pre-declare one claim
  as many narrow hypotheses to shrink each FDR family — the limitation real
  pre-registration has. The gate **locks the grouping before series and makes it visible in
  the chain**, so a reviewer can *see* it — but does not auto-prevent it, and 07 must
  **not** add a heuristic "merge similar hypotheses" (policy hell). This is exactly where
  **RP-1** (external adjudication as a heartbeat) is the backstop the gate cannot mechanize.

## 7. Cross-references

- **Ticket 06** — ledger evidence layer, and the **sole owner of every `court/`
  change** (audit revision D14 — the v2 ticket text omitted the chain entirely,
  which would have stranded ticket 07 with no chain to seal): `register(...,
  source_ref=)` reachable (`source_ref` stays a *pointer*, not a meta dump);
  `record(trial_id, series, attestation)` with the attestation stored on the
  evaluation event and a shallow `declared`-vs-attestation (metric/window)
  fail-closed check inside `court` (no market semantics); the **hash-chain fields +
  canonical serialization in `_append_event`** (storage-line serialization stays
  byte-identical to v0.1 — the hash path is separate; audit minor, keeps ticket 12's
  torn-write semantics intact); the two court-opaque event types `declaration` /
  `seal` (§3); a red test "tamper one mid-file line → replay verification fails".
- **Ticket 07** — the harness gate: the `Run` loop, scope derivation, the seal + anchor
  backend, all fail-closed checks. (07 acceptance must **not** assert "in-process cannot
  call court" — the guarantee is *uncertified*, not *impossible*.)
- **Ticket 09** — the aggregation/selection policy is a **pre-registration object**: it
  must be a declaration event on the chain **before the first verdict** (or locked at run
  creation), so "discriminating-only aggregation" (ticket 03) cannot be cherry-picked
  post-hoc. The 02/03/09 seam.
- **Ticket 03** — direction lock: the gate enforces `declared.direction` immutable and the
  selection rule ∈ the pre-registered policy; PnL menus must pre-register directional.
- **RP-0 / RP-1** (personal quant-workflow-system): this gate is RP-0 for alpha-court; the
  `prereg-gate.sh` "results not before the pre-registration commit" pattern is the
  anchor-timing precedent (a single pin, not per-trial).

## 8. Run boundary (grok pin)

A `CertifiedRun` is exactly **one multiplicity family**: `scope` = every trial evaluated
in the run (nulls and survivors equal). Registered-but-not-evaluated trials keep the v0.1
file-drawer semantics — not in the series-derived N, but still visible on the chain.
**Stuffing two unrelated experiments into one run and judging once is forbidden** (N would
be diluted): one `Run` → one `judge()` → one seal; a new experiment starts a new run.

## 9. Deliverables (tickets 06 / 07 / 09)

- `harness/` certified path: propose → evaluate(attest) → record(check) → judge(derive
  scope) → seal(chain_head + anchor).
- Ledger hash-chain with the §4.1 canonical serialization; a `harness verify` command
  (replay + recompute; no adapter re-run, no cross-machine head reproduction).
- Tests (red first): each §5 violation raises; a certified run verifies; a tampered
  mid-file ledger line / reordered events / scope-shrink / post-hoc aggregation / any
  event appended after seal fails (audit revision — "back-dated series fails" is
  withdrawn: the chain does not protect absolute time, §4.1/§6); an **honesty test**
  pins the disclosed §6 truncation boundary (pre-seal suffix deletion *passes*
  replay — asserted as passing, so the boundary stays on the record); killer-demo
  keeps asserting series/stats (not a cross-run identical `chain_head`).

## 10. Batched grok review — resolved (2026-07-11)

The §9 open items of DRAFT v1 went to grok (`.scratch/dispatch/v02-02-grill/`). Verdict:
Q1–Q5 philosophy holds (no power-level lock error), but three implementation/framing pins
were folded into this v2:

1. **"tamper-proof" was over-claimed** → tamper-**evident** + external-anchor-if-present;
   a local git anchor is not cryptographic (§4, §6).
2. **per-trial git clashes with Q5 incremental** → the anchor is pinned **once at seal**,
   pluggable (git default, not a hard dependency); incremental integrity is the chain
   alone (§4.3).
3. **canonical serialization** → hash covers content not wall-clock; **`sort_keys` +
   fixed float encoding** are a 06/07 must-add (verified: `_append_event` has no
   `sort_keys`); verify ≠ cross-run head reproduction (§4.1).
4. **certificate location** (v1's blurriest spot) → the ledger `seal` event is
   authoritative; manifest is a copy; git optional; commit-message forbidden;
   `VerdictRecord` untouched; certifies the **run** (§4.2).
5. **"by construction" framing** → certified-run vs uncertified-calculator-use; (A) is not
   a physical prohibition, (B) gives it teeth (§2, §6).
6. **conformance == declared is sufficient** for the stated threat model; no
   sampling-recompute; add cheap structural checks; adapter attests metric/window/versions
   but not direction/se (§4, §5).
7. **run boundary + 09-on-chain** pinned (§8, §7).

grok's freeze verdict: **freeze after folding the pins (done), then dispatch 06 (evidence
layer) before 07** — 07 without 06's attestation/`source_ref` would be a scope/direction
shell that can't wire E2E.

## 11. v0.2 design-layer audit — revisions folded (2026-07-12)

Five-way blind milestone audit (archive `.scratch/dispatch/v02-design-audit/`,
verdict `verdict.md`). The Q1–Q5 architecture held; what changed in this v3:

1. **D6 (blocker)** — the v2 anchor-timing clause ("anchor must predate the series")
   contradicted the anchor-at-seal design and was literally unimplementable; §4.3
   now states what the anchor attests, §5's clause is deleted, and a pre-anchor is
   named as a distinct optional object.
2. **D7 (blocker)** — "attested == declared" had no declared side for
   universe/versions, and nothing locked the adapter configuration per run
   (label_expr/provider_uri could change mid-run with every check green). A
   run-level **`run_config` declaration event** (§3) is now the first chain event
   and the conformance target for everything `DeclaredProtocol` does not carry.
3. **D8–D11 (majors, disclosure)** — §6 gained four honest boundaries: pre-seal
   suffix truncation (measured live against the real ledger), off-path
   pre-screening, in-process attestation forgery (valid seal ≠ provenance), and
   sibling-run splitting/shopping with the RP-1 presentation rule. §5 gained
   seal-must-be-final / second-seal / absent-policy / wild-verdict / post-seal-call
   clauses.
4. **Minors** — `type` pinned into the content hash; `at`-exclusion rationale
   rewritten (re-execution vs replay); "back-dating" claims narrowed to reorder
   protection; anchor/manifest ordering pinned; float-encoding pre-transform note;
   court-side delta honestly listed as three changes (§3); `harness/` package
   coexistence note; ticket-06 ownership of the chain (§7).

## 12. Ticket-07 delivery audit — two fail-opens folded (2026-07-16)

The certified-run delivery (dispatch `v0.2-07`) passed both收货 panels on the frozen
v3 contract, but the panels — and referee re-reproduction — found **two MAJOR
fail-opens that were latent in the v3 spec itself** (contract-fault, worker-innocent:
the worker implemented the pinned wording verbatim, and changing it would have
violated contract freeze). Both are folded into this v4:

1. **Reopen-revives-brick (fidelity F-1 / probes misc-9a; referee-reproduced).** v3's
   pinned "mid-battery court.judge failure bricks the run forever" rested on "orphan
   verdicts fail verify invariant 7" — false across a reopen, where the reconstructed
   `verdict_ids` cover exactly the orphans. Closed by the **on-chain `judgment` event**
   (§4.2): success-only marker carrying the battery + verdict_ids; seal requires it;
   open recovers judged-state from it (not from raw verdict presence); verify asserts
   it covers every verdict. Bonus: the battery is now auditable on-chain.
2. **Anchor silently disabled by deleting the manifest (probes Finding A;
   referee-reproduced: forge chain + `rm run_manifest.json` + `verify(anchor=real)` →
   PASS).** v3's invariant-9 wording "*if the manifest carries an anchor_ref* and a
   backend is supplied …" trusted an attacker-writable sidecar to decide whether the
   anchor is checked. Closed by **query-by-recomputed-head, fail-closed** (§4.2): a
   supplied backend is asked about verify's own recomputed `final_head` and must
   attest it, else `CertificationError`; the manifest ref is advisory only.

Also folded (minor, same delivery): `verify` asserts **exactly one** aggregation-policy
declaration (probes Finding B — v3 checked only the first, inconsistent with
`read_declared_policy`'s "corrupt if >1"). Implemented by ticket 07 rework-01;
attribution = commander contract-fault (CR-10).
