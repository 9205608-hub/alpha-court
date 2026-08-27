---
name: adversarial-referee
description: Judge a worker delivery with independent re-runs and a multi-lens adversarial panel, rule on document-vs-code conflicts (workers can win), keep attribution honest, and run role-reversal meta-reviews at milestones. Use whenever a dispatched delivery comes back, and at every milestone close.
---

# Adversarial Referee

The commander-side half of cross-model mutual review. Three principles,
all learned the expensive way in alpha-court v0.1:

- **Never trust self_test** — re-run everything yourself.
- **Never trust your own memory** — referee spot-checks must read the
  document's original fixtures; twice in v0.1 the referee "caught" a worker
  with hand-invented inputs and the worker was right both times.
- **The authority can be wrong** — panels must try to refute the cited
  documents too, not only the delivery. v0.1's best finding was a published
  paper's internally inconsistent recursion, ruled in the worker's favor.

## Process per delivery

1. **Receipt first**: status, deviations, open_questions. A disclosed
   deviation is a question for adjudication, not an automatic fault.
2. **Independent re-run**: acceptance commands in the worker's worktree,
   plus your own behavior probes (contract matrices for stateful modules,
   integration probes for orchestrators). Diff review against file
   ownership.
3. **Panel** (Workflow, parallel agents, lenses by artifact type):
   - statistics/formula code → *fidelity* (code vs literature line-by-line)
     + *recompute* (independent reference implementation + hand vectors +
     seeded fuzz);
   - documents/notes → *recompute* + *citation-vs-published-PDF* +
     *ticket-acceptance*;
   - adapters/integrations → *contract-fidelity* + *numeric adjudication of
     any disclosed deviation on production-shaped data* (measure, don't
     speculate — quantify deviation vs the contract tolerance).
   Verifiers are prompted to REFUTE, graded blocker/major/minor, and must
   attach evidence (measured numbers, file:line, published-PDF quotes).
4. **Proportionality** (the 08e lesson — one docstring nit does not deserve
   its own rework session). **Report as blocker/major/minor only findings
   that affect the ticket's AC or the artifact's correctness; everything else
   is `optional`** = evidence-backed, listed in the issue Answer, never a
   rework trigger. A reviewer told to find problems will always find some, and
   chasing them is how reworks turn into over-engineering. Two guards so
   `optional` cannot become a hiding place: (i) a real defect downgraded to
   optional *only because the AC did not cover it* triggers a contract-fault
   check on the ticket (rule 2 of `/worker-dispatch`) — "correctness beyond AC"
   is attributed contract-fault, never worker-fault; (ii) errors in cited
   authorities/documents are recorded as jurisprudence (item 5) regardless of
   AC impact:
   - blocker → rework, always;
   - major → rework, or a referee ruling if the fault is in the contract;
   - minor(s) only → batch them into the next natural rework, or accept
     with the minors logged in the issue Answer.
5. **Worker-wins provision**: when delivery and cited authority conflict,
   the panel adjudicates with counterexamples. If the document loses: code
   stands unchanged, the document gets a dated erratum, the spec gets
   re-pinned, and the rework (if any) touches only paperwork. Record it as
   jurisprudence.
6. **Attribution ledger**: every rework and every accepted-with-log lands in
   the issue's Answer classified worker-fault / contract-fault /
   referee-fault. These statistics are only meaningful if ticket AC was
   written at the panel's scale (see `/worker-dispatch` rule 2).

## Verification before any claim (added 2026-08-15)

The referee's own conclusions are subject to the same rule as the worker's:
**no "闭环 / 突破 / 找到 bug / null 成立" is announced without an attached
independent receipt**, defined per artifact type — code: command + exit code +
numbers; document: quoted passage + page/section + PDF path/hash; data:
recomputed value + script path. Without a receipt the only permitted wording is
"待验证", and the finding **is still entered in the ledger** with
`status=pending`, owner and due date — never omitted (omission would be the
"commander-filter" the v0.1 role-reversal killed). Precedent: in one 2026-08
sprint four conclusions were announced first and refuted by independent re-run
later; the cost of that pattern is what this paragraph buys back.

## Symmetric accountability (the commander is not above the law)

Referee and commander errors get the same treatment workers get:

- A commander-caused incident (bridge bug, pipeline hygiene, fabricated
  spot-check, mid-flight contract change) gets its own **commander rework
  entry** in the tracker. It is not a confession paragraph: it must carry a
  `root_cause_id` (from the frozen vocab), an evidence pointer, a
  **re-runnable anti-recurrence assertion** (a check that fails if the class
  recurs), and a link to any worker rework it polluted. A bare
  cause/fix/prevention file passes an existence check but is compliance
  theater; an existence+**shape** gate (`scripts/reflow-gate.sh`) enforces
  the fields' presence and a frozen `root_cause_id` — substance (are the
  fields honest?) is not scriptable and is the RP-1 external review's job. "I'll log it
  later" is the double-standard the v0.1 role-reversal caught (worker paid 8
  rework sessions; the commander's fixture-fabrication ×2 and `| head`
  SIGPIPE got a one-line TIMELINE aside).
- Contract-fault reworks are counted against the commander's ledger, not
  the worker's.
- **A worker may dispute an attribution tag** in its receipt; the dispute
  gets a ruling on the record (timeout defaults to the worker), never a
  silent overrule.

## Milestone meta-review (互评)

At each milestone close, run a **role-reversal review**: give the worker
model the full case files (tickets, reworks, receipts, rulings, TIMELINE)
in a read-only worktree and a structured-output schema, and ask it to
adversarially review the COMMANDER — ticket quality, ruling quality,
fairness, tooling, top criticisms with evidence. Archive the output
verbatim under `.scratch/dispatch/meta-review-*/`. **Every criticism must
be adjudicated on the record** — adopted (→ process ticket or skill
amendment) or rejected-with-reason — in the meta-review ledger. You may
overrule a criticism; you may not silently drop one. ("Survives your
reading" was the commander-filter the v0.1 role-reversal itself flagged —
it let the judge quietly discard inconvenient findings. Killed here.)
v0.1's meta-review graded the commander B and produced the rules now in
`/worker-dispatch` — the loop demonstrably closes.

## See also

`/worker-dispatch` (the sending end), `docs/agents/worker-bridge.md`,
`.scratch/dispatch/meta-review-commander/` (v0.1 precedent).
