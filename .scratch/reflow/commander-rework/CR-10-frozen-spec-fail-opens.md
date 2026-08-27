# CR-10 — two fail-opens were latent in the ticket-07 frozen spec: reopen-revives-brick + anchor-disabled-by-manifest-deletion

- **root_cause_id**: `ticket-self-contradiction`
- **attribution**: contract-fault (commander)
- **occurrences**: 1 for this specific shape (a *frozen, adversarially-linted* spec
  still shipped two MAJOR fail-opens in the flagship security ticket). Related but
  distinct from CR-09 (`ticket-self-contradiction` there = AC unsatisfiable at base);
  this is the spec's *security semantics* being self-defeating, not its ACs.
  **Vocab note:** neither hole is a clean `ticket-self-contradiction` — F-1 is two
  pinned rulings (M-1 open-recovery × M-4 brick-forever) interacting to open a hole;
  Finding A is invariant-9 wording trusting an attacker-writable sidecar. Mapped to
  the nearest frozen id rather than minting a new one unilaterally (the vocab is
  append-only behind an RP-1 gate). Flag for a possible future
  `spec-trusts-attacker-controllable-input` id if the class recurs.
- **evidence**: probes panel Finding A + fidelity panel F-1, both **independently
  re-reproduced by the referee** (`.scratch/dispatch/v0.2-07-certified-run/
  referee-repro.py` + `referee-repro-output.txt`): F-1 = judge bricks in-memory →
  `CertifiedRun.open()` → `seal()` succeeds → `verify` PASS (n_verdicts=1);
  Finding A = honest sealed run, `rm run_manifest.json`, `verify(path, anchor=real)`
  → still PASS (anchor never consulted).
- **fix**: prereg-gate.md → v4 §4.2 (both) + issue 07 amendment + ticket-07 rework-01:
  (1) an on-chain `judgment` event appended only on `court.judge` success, carrying
  the battery + verdict_ids; seal requires it, open recovers judged-state from it,
  verify asserts it covers every verdict (brick is now durable across reopen, and the
  battery is auditable on-chain); (2) `verify(anchor=backend)` queries the backend with
  verify's own **recomputed final_head** and is **fail-closed** when a supplied anchor
  does not attest it — the attacker-writable manifest `anchor_ref` is downgraded to
  advisory. Plus verify asserts exactly-one policy declaration (Finding B).
- **anti-recurrence** (binds the commander; strengthens `/worker-dispatch` rule 3 lint):
  the pre-dispatch adversarial lint of any **gate/verify-style ticket** must include a
  "trusted-input provenance" pass — for every security decision the gate makes, name the
  input it reads and prove that input is **inside or outside the attacker's rewrite
  surface**; an input inside the surface (unsigned sidecar, manifest, non-chained file)
  used for a fail-open/fail-closed branch is a CR-10 recurrence. Re-runnable assertion:
  the two referee-repro scenarios must FAIL verify (raise `CertificationError`) after
  the rework — added to `tests/test_harness_verify.py`.
- **round 2 (2026-07-16)**: probe panel on rework-01 found a THIRD contract-fault of
  the same class — `judgment.battery` on-chain but never cross-checked (the "auditable
  battery" claim was false; referee-reproduced `referee-repro-battery.py`). Folded into
  rework-02 (verify inv 7.5 battery↔verdict-statistics cross-check + judgment position
  pin + CLI `--anchor`). Also logged a small **referee-fault**: rework-01 note's Finding A
  scenarios (a)/(b) wrongly said an honestly-anchored run with a deleted manifest should
  fail — the worker correctly refused and disclosed; deleting a human-convenience
  manifest must not fail a genuinely-anchored run. Attribution: (a)/(b) spec error =
  referee-fault (commander); the battery half-fix = contract-fault (commander).
- **polluted-rework**: none — the worker (grok) delivered the frozen v3 contract
  verbatim and wins both findings (zero worker-fault; changing the pinned wording would
  have violated contract freeze). The rework is issued as a NEW ruling attributed
  contract-fault, not as post-hoc legislation against the worker.
