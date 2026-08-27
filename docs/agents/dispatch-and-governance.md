# Dispatch generalization & referee governance — design ruling (v0.2 ticket 10)

Status: v1 (grilling-locked 2026-07-11).
Owner ticket: `.scratch/v0.2/issues/10-dispatch-gen-referee-gov.md`
Amends: `docs/agents/worker-bridge.md` (worker-generalization pointer).

This is the **process side** of v0.2 (parallel to the court-side tickets 01–09). It
does not touch the statistics kernel. Two parts: generalizing the dispatch bridge off
grok-only, and binding the referee-governance heartbeat (RP-1) to alpha-court.

## Part A — Worker generalization (Q1 = isolate the seam, no speculative 2nd worker)

`scripts/dispatch.sh` is grok-hardcoded in exactly **two seams**; everything else
(commander-side worktree isolation, the post-flight tripwire, the receipt schema) is
already worker-agnostic and battle-tested (v0.1: 24+ runs). The two seams:

1. **Invocation** — the `CMD=(grok --prompt-file … --cwd … --output-format json
   --json-schema … --reasoning-effort … --max-turns …)` array.
2. **Receipt extraction** — reading `envelope.structuredOutput` (grok's JSON envelope
   shape), with the `text`/`sessionId` fallbacks.

**Ruling:** refactor those two seams into two clearly-marked functions —
`worker_invoke(ticket, cwd, schema, opts) → raw_envelope` and
`worker_extract_receipt(raw_envelope) → receipt_json` — behind a **minimal worker
contract**:

> A worker is any headless CLI that (a) takes a self-contained ticket (prompt file),
> (b) works in a commander-created isolated worktree pinned via its own cwd flag, and
> (c) returns a receipt conforming to `scripts/receipt.schema.json`.

Only **grok** is wired. Adding a worker later = adding one `worker_invoke`/
`worker_extract_receipt` branch, **not** rewriting `dispatch.sh`. A config-driven
worker **registry** (per-CLI profiles) is deliberately deferred (YAGNI): there is no
second worker to run, and building the registry now would be speculative infrastructure
the three-don'ts reject. The seam being CLI-agnostic *is* the generalization; the
registry earns its place only when a real second worker appears.

**Audit revisions (2026-07-12, v0.2 design-layer audit):**

- Contract clause (c) had no enforcement: today schema conformance rides on grok's
  model-level `--json-schema`, and the extraction step checks only
  `isinstance(receipt, dict)` — for a second CLI the clause would be a wish. The
  two-seam refactor therefore **must add a commander-side jsonschema validation of
  every receipt against `receipt.schema.json` (validation failure = delivery
  rejected)**, independent of any worker's native schema support.
- Contract gains clause **(d): the worker must run fully non-interactively** (the
  grok wiring's `--permission-mode auto` was an implicit assumption inside seam 1).
- Disclosed accepted blind spot: the post-flight tripwire excludes
  `.scratch/dispatch/` wholesale (justified fix for concurrent-dispatch false
  trips, 2026-07-10) — an escaped worker rewriting **committed audit traces** under
  that path would not trip it. Accepted for v0.2, on the record.

**Deliverable (small, ready-for-agent):** the two-seam refactor of `dispatch.sh` + a
"Worker generalization" section in `worker-bridge.md`. No large implementation; the
isolation/tripwire/schema stay byte-for-byte.

## Part B — Referee-governance binding (Q2 = record the binding, connect to L1)

The referee-governance machinery mostly **already exists** and must **not** be rebuilt
here (respects the D2 three-layer ownership: meta-skills live globally at `~/.claude`;
the repo keeps a *readable exhibit*, not a mummy):

- **L1 (global, `~/.claude`)** — the governance *logic and gates*: the `worker-dispatch`
  and `adversarial-referee` skills (already promoted global), the RP-0/RP-1 principles,
  and the personal-workflow-system tooling (reflow-gate / prereg-gate / meta-review-ledger).
- **L2 (alpha-court, this repo)** — the *concrete substrate*: `scripts/dispatch.sh`,
  `docs/agents/worker-bridge.md`, and the committed meta-review archives. Plus this
  binding.

**The three RP-1 trigger points, bound to alpha-court:**

1. **Before freezing a design contract** — batch the open questions to an external model
   (grok) and fold the review before the contract is locked. *(This session, verbatim:
   every v0.2 design ticket 01/02/03/09-seam was batched to grok before freeze; the ICIR
   lock error and the tamper-proof-over-claim were caught exactly here.)*
2. **Before promoting a rule that blames the worker** — such a rule must pass an external
   REFUTE pass (the D4 asymmetric-adjudication router), not be self-adopted.
3. **At a milestone close** — the role-reversal meta-review (`adversarial-referee` skill
   §"Milestone meta-review"): the worker reviews the commander; every criticism is
   archived and converted to a rule. *(v0.1 precedent: graded the commander B, produced
   the rules now in the two skills.)*

**The mechanical trace (RP-0 "only mechanical traces count") is already honored:** each
consultation is committed verbatim under `.scratch/dispatch/` — the v0.1
`meta-review-commander/`, and this session's `v01-audit/`, `readme-review/`,
`v02-power-grill/`, `v02-03-grill/`, `v02-02-grill/`. *(Audit note, 2026-07-12:
this ruling itself froze without a trigger-1 archive of its own — the v0.2
design-layer audit `v02-design-audit/` is that archive, filed after the fact and
recorded here as the exception that proves the trigger is discipline, not
mechanism.)* The *trace* half of RP-1 is
mechanical (committed archives); the *trigger* half is discipline here, with full
enforcement gates (a hook that blocks a freeze without a logged review) owned by L1 /
a later wiring — **ticket 10 commits to the trace + the trigger checklist, not to
rebuilding the L1 gates.**

## Scope & non-goals

- 10 does **not** implement a second worker, a worker registry, or new governance gates.
- 10 does **not** touch `court/` or the statistics.
- If the two-seam refactor is dispatched, it is a small ready-for-agent task; 10 itself
  is a design ruling, resolved by this document.

## Deliverables

- This ruling; the `dispatch.sh` two-seam refactor + `worker-bridge.md` section
  (small task); the RP-1 trigger checklist recorded above as the alpha-court binding.
