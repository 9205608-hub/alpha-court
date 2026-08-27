# Quant workflow system — design & build order

*A personal, cross-project, self-growing operating system for quant research and
trading-tool development. Designed 2026-07-11 in a `/grilling` session, stress-tested
twice by a cross-model role-reversal review (grok). Status tags are honest:
**[LANDED]** = enforced artifact exists; **[DESIGNED]** = decided, not yet built;
**[DEFERRED]** = intentionally postponed with a trigger.*

One line: **the same discipline alpha-court applies to factors — don't believe it
until it survives adversarial out-of-sample — turned on the way I work.** A beautiful
design that isn't enforced is a backtest that never ran out of sample.

---

## Two cross-cutting laws (learned from grok's two reviews this session)

**RP-0 — Self-binding must be tamper-evident, recomputable, existence-checked.**
Every step where the commander self-executes must leave an artifact a script (or an
external model) can later verify. Intention to self-discipline is not evidence of it;
only mechanical traces count. This is the court iron law ("the evaluator is not in the
worker loop; the worker doesn't grade itself") applied to the commander — otherwise
the meta-layer forbids self-grading *only for the worker* and hands the commander the
most complete self-grading power of all. **[LANDED]** as: contract-freeze hard gate,
SIGPIPE trap, existence+shape `reflow-gate.sh`, `rework-lint.sh`, killed "survives your
reading" filter, tombstone inbox, frozen root-cause vocab, meta-review ledger.

**RP-1 — External adjudication is a heartbeat, not a ceremony.** The commander's read
of the commander's own work is structurally blind to its own disease (proven twice this
session). So a neutral cross-model reviewer is injected on a fixed cadence:
- **Mandatory triggers**: before freezing any contract/spec/design doc; before promoting
  any worker-binding rule; at every milestone close.
- **Heartbeat**: every ~3 foundational/contract decisions. The *first* heartbeat after a
  build verifies the teeth actually landed (content check), not just reads prose.
- **Un-gameable framing**: the review prompt is a fixed template (standing B-grade case +
  "find where I repeated the sins" + structured REFUTE schema). The commander chooses
  *when* to review, never *how it is framed*. **[DESIGNED]** (template to be codified);
  the two reviews this session used it ad hoc.

---

## D1 — The discriminator: skill vs hook vs memory  (question ①)

The sorting function every lesson passes through:

1. **Mechanizable as a deterministic predicate over a tool call / session event?** → eligible for hook.
2. **Hook three-gate** (all three, or it drops to skill): ① mechanizable; ② high forget/violation cost; ③ violation is a hard error with almost no legitimate exception.
3. Otherwise by shape: judgment-bearing multi-step procedure → **skill**; fact / decision / precedent → **memory**.

Sharp consequence: "it feels like an iron rule" does **not** qualify it as a hook. Most
hard-won rules stay skill text; only a small mechanizable, high-cost, exception-free
subset graduates to enforcement. Grok RP-1 corrected an over-reach here: an *existence*
hook must be paired with a **content contract**, or "the file exists" becomes compliance
theater (see the commander-rework content contract).

## D2 — Physical home: three layers  (question ④, home half)

| Layer | Location | Holds | Truth |
|---|---|---|---|
| **L1 meta-skills** | `~/.claude/skills`, `~/.claude/settings.json` | cross-project work discipline: worker-dispatch, adversarial-referee, reflow, generic hooks | **global** |
| **L2 project** | `alpha-court/.claude` | court-API-bound skills, meaningless outside the repo | repo |
| **L3 memory** | `~/.claude/.../memory` | preferences + jurisprudence | global |

worker-dispatch / adversarial-referee **promote to global** (live truth). The repo keeps
a **readable, desensitized exhibit** (not a mummy — grok RP-1: an invisible `~/.claude`
copy breaks the public evidence chain), pinned by a git tag for provenance. **[LANDED]**
this session: global live copies at `~/.claude/skills/` + provenance tag
`v0.1-skills-codified` on the codification commit.

## D3 — Reflow threshold: don't overfit your own process  (question ②)

A lesson promotes to a rule **iff**: **(a)** it recurs ≥2 times, or **(b)** a single
occurrence was expensive *and* systemic. Cheap one-offs do not promote (even if they feel
like rules); expensive-systemic single occurrences promote without waiting for recurrence.
Same anti-overfitting ruler alpha-court points at factors, pointed at the process.

Grok RP-1 hardening — the subjective escape hatches are closed with operational definitions:
- **"expensive"** is *auto-true* if the fault caused a worker rework / receipt loss / worktree pollution / attribution pollution.
- **recurrence** = same `root_cause_id` ≥2 — **[LANDED]** as a frozen vocabulary (`.scratch/reflow/root-cause-vocab.md`); splitting an id to launder a recurrence into a fresh n=1 requires an RP-1 review of the vocab change.
- Rules are **demotable** (reflow is bidirectional); demoting a worker-protective rule needs the same external check as promoting a worker-binding one.

## D4 — Asymmetric adjudication: whose screws, whose signature  (question ②)

The three-way attribution tag (worker / contract / referee-fault) is the **router**:

| A rule that… | Adjudicated by | Cadence |
|---|---|---|
| tightens the commander / fixes tooling | commander, immediately | Tier 1 |
| tightens the worker / exonerates the commander | must clear external REFUTE first | Tier 2 / persistent ledger |

Self-binding rules are free to adopt (no bias risk); worker-binding rules are where the
double-standard hides, so the worker's model must get to refute first. Grok RP-1 hardening
**[DESIGNED]**: attribution is a mandatory structured field the worker may dispute
(timeout → worker wins, on the record); worker-binding promotion needs a **persistent
ledger** (proposal + REFUTE verbatim + point-by-point rebuttal), not a transient call;
**no `--i-accept` escape valve** (a self-maintained VIP lane is just renamed post-hoc legislation).

## D5 — Capture: the lesson-inbox  (question ②)

Append-only inbox; Claude appends the moment a lesson surfaces (model captures, near-zero
human friction); human prunes at session close (the quality gate). **Deletion is tombstone,
not erase** — grok RP-1: human pruning is otherwise a selective-forgetting backdoor.
**[LANDED]** as `.scratch/reflow/lessons-inbox.md`.
**[DEFERRED]** (D5 walked back): the inbox is **in-repo**, not a global `~/.claude` file —
a global file has no git history, so its tombstones aren't tamper-evident. Promote to a
dedicated versioned reflow repo when project #2 appears (don't build cross-project
machinery before it exists — D3, applied to the tool itself).

---

## ③ Quant skill checklist — L1 discipline + L2 binding

Every quant skill splits into an **L1 discipline layer** (transferable — the case study's real
subject) and an **L2 binding layer** (qlib/court-specific — alpha-court is the reference
implementation). Composes with the installed `quant-mentor` judgment; does not duplicate it.

| Skill | L1 discipline | L2 binding | Form | Priority |
|---|---|---|---|---|
| **禁赢学 / honest validation** (pre-register → court battery → read verdict honestly → null archived = survivors → RP-1 refute survivors) | declare-before-test, no seed-fishing, null = survivor | court API, killer-demo pattern | skill(L1) + "pre-reg doc precedes results" existence hook | **P1-#1** |
| **因子研究流程 factor research flow** | net-of-cost / capacity / orthogonality lenses | adapter/court wiring | skill(L1) | P1-#2 |
| **数据管道卫生 data-pipeline hygiene** | PIT / no look-ahead / versioning | qlib-cn / investment_data | skill(L2) | P2 |
| **回测复用护栏 backtest-reuse guard** | don't rebuild; reuse oracle | court decoupling smoke test | **hook** (exists) + thin skill | P2 |
| worker-dispatch / adversarial-referee | cross-model mutual review | — | skill(L1) | promoted |

**Priority**: P0 reflow mechanization (this session) → P1 禁赢学 → factor flow → P2 data/backtest.
禁赢学 is **harvested from the existing `killer-demo.md`** (which is already a pre-registration),
so it does not delay the demo's mandatory E2E run (CLAUDE.md iron law). Grok RP-1 warning
adopted: the current threat is the reverse — the demo is dispatched while P0/P1 are unbuilt;
禁赢学-as-skill must not become a way to *avoid* running real alpha.

## ④ Public case study — "How it was built"

The system double-proves **design AND use**: *design* = the cross-model
adversarial + self-growing reflow layer; *use* = alpha-court built with it (24 dispatches /
8 reworks / 129 tests / killer demo). Positioning and audience context live in
`docs/private/` (never in public git).

- **Artifact**: a public "How it was built" case study in the alpha-court repo
  (the L1 live copy is invisible in `~/.claude`, so the repo carries the story + evidence).
  The repo exhibit (D2) must therefore stay **readable and current**, not a mummy.
- **Angle**: *epistemic honesty as engineering* leads — "I built a tool that doesn't let me
  fool myself (court), and a process that doesn't let me fool myself (reflow + external
  adjudication)." Throughput is *evidence it's real*, not the pitch. Every process claim is
  anchored to a concrete caught error (B-grade → rules; BY worker-wins; demo rejects fake
  alpha; this session's CR-06).
- **Guardrails**: public writeup, zero private strategy (`docs/private` never enters public
  git), zero prior-employer artifacts, methods cited from public literature. Grok RP-1
  additions: **pre-register the disclosure boundary before writing** (禁赢学 applied to the
  writeup itself); mind the process-astronaut misread for PnL-first readers — lead with
  caught errors, not ceremony.

---

## What landed this session (the acceptance gate)

Grok's second review judged the v0 framework an **empty-shelves prescription**. Rather than
ship a doc, the first act discharged the backlog and grew teeth:

- **[LANDED]** killed the `survives your reading` commander-filter (`adversarial-referee`).
- **[LANDED]** contract-freeze **hard gate** + SIGPIPE `trap` (`scripts/dispatch.sh`) — red-tested: dirty tree → `CONTRACT FROZEN`, exit 1.
- **[LANDED]** `.scratch/reflow/`: frozen vocab, content-contract template, **CR-01..CR-06** (v0.1 backlog + this session's own CR-06), inbox, `INDEX`, meta-review ledger + archived grok reviews.
- **[LANDED]** `scripts/reflow-gate.sh` — existence+**shape** gate (field presence + frozen id; substance is RP-1's job, per grok #3); green on the 6 entries, fails on a missing field or an unfrozen id (3 red-tests pass).
- **[LANDED]** `scripts/rework-lint.sh` — the post-dispatch half of CR-05 (bans "以我勘误为准 / worktree stale" in a rework note); red-tested to fail on 08d's historical note, pass on a clean one.
- **[LANDED]** global promotion (two skills → `~/.claude/skills/`, live truth) + provenance tag.
- **[DESIGNED]** (queued, honestly not done — grok #3): RP-1 fixed prompt template; worker-binding persistent ledger; wire `reflow-gate.sh`/`rework-lint.sh` as Stop hooks; receipt-schema attribution/dispute field; CR-03 `fixture_ref` schema; **commit + merge to main** (teeth live only on this branch — production path is toothless until merged); the P1 禁赢学 skill.

**The loop fired four times this session**: grok #1 turned D1–D5 from self-grading into
tamper-evident (RP-0); grok #2 caught the empty shelves → the teeth landed + CR-06; grok #3
verified the teeth by running them, caught CR-05's mislabelled tooth + the reflow-gate
over-claim → rework-lint built; grok #4 (triggered by the *user* asking "did you check with
grok?") caught the commander self-exempting the P1 skills from review — the B-grade
double-standard, recurring → CR-07 — plus CR-08 (gates red-tested on the happy path, not the
bypass; n≥3). Every criticism recorded and adjudicated in the meta-review ledger, not asserted.
The loop's most honest moment is that a human, not the machine, had to fire grok #4.

## Build order

1. **First batch (P0)** — [this session, mostly landed] reflow mechanization + backlog CRs + skill fixes + dispatch hardening. Remaining: global promotion + tag; codify the RP-1 fixed template; wire `reflow-gate.sh` as a Stop hook.
2. **P1-#1 — ✅ built (on branch), corrected by grok #4**: `honest-validation` (禁赢学) + `scripts/prereg-gate.sh`. Honest downgrade: prereg-gate enforces commit **ordering only**, not content freeze (backfilling looser thresholds after seeing results passes it) — the real content-hash tooth is queued below. Rule 6 (LLM refutation as belief gate) reframed to delayed OOS. The skill is mostly research-integrity baseline + `court` wiring, not novel judgment — now says so in-skill.
3. **P1-#2 — ✅ built (on branch), corrected by grok #4**: `factor-research-flow` (mechanism-first → net-of-cost / capacity / orthogonality → hand off to 禁赢学). Honest correction: the "no hook, it's all judgment" framing washed a gap into a virtue — parts of each lens (net-IC floor, residual-IC/R² cap, ADV floor) ARE mechanizable once params are frozen, are [DESIGNED] not built, and alpha-court v0.1 is a gross paper-series stack (no cost model) so net-of-cost is aspirational. Now says so in-skill.
4. **P2** — data-pipeline-hygiene; backtest-reuse guard skill over the existing decoupling hook.
5. **④** — the public case study, disclosure boundary pre-registered.
6. **[DESIGNED] real quant teeth + missing muscle (grok #4)** — the content-hash pre-registration tooth (seeds / thresholds / aggregation / cost-basis hashed into `run_config`, matched at judge time; amendment = new hash) — this is what makes prereg-gate real; mechanized pre-court gates once params are frozen (net-IC floor, residual-IC/R² cap, ADV floor — blocked on a v0.2 cost model + factor-neutralization code the gross-paper stack lacks); a "no skill merges to main without an archived `meta-reviews/*` review" gate — **✅ built: `scripts/skill-review-gate.sh`, bypass-red-tested against the real un-reviewed `1ce25a7` sin (it FAILS that range — would have blocked this session's double-standard); wiring it as a pre-merge / Stop hook is the one remaining step**; "write the bypass red-test first" for every new gate (CR-08 — applied to this gate itself). Missing desk muscle: multiple-testing budget / N_eff with stopping rules, IC half-life & rolling OOS, regime dependence, factor crowding, implementation shortfall, residual-IC neutralization pipeline, quantitative capacity screen, portfolio-layer marginal contribution. Many are genuinely v0.2+; named so they are not silently claimed done.

## Provenance

Two cross-model role-reversal reviews, archived: `scratchpad/grok-review*.json` (this
session). The B-grade v0.1 meta-review that seeded the two skills:
`.scratch/dispatch/meta-review-commander/`.
