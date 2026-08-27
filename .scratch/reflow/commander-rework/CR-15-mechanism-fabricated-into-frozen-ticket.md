# CR-15 — unreproduced crash mechanism written into a frozen ticket as fact (recurrence of CR-03's class)

- **root_cause_id**: `referee-fabricated-spotcheck`
- **attribution**: referee-fault
- **occurrences**: 3 (×2 v0.1 spot-checks = CR-03; this = the same fabrication
  family one layer up, at contract-freeze time. The 2026-07-20 RP-1 explicitly
  REJECTED minting a new id `diagnosis-asserted-not-reproduced` as recurrence
  laundering — "layer-split is exactly the move the freeze rule forbids" — and
  ruled occurrences += 1 on this id instead.)
- **evidence**: `rework-02.md` FIX-C asserted "β=0 NaN row fed into errorbar"
  as the crash mechanism and its AC required "today raises ValueError" — neither
  reproduced before freezing. Referee real-input probe (05 Answer 2026-07-19
  late): the NaN row does NOT trip this matplotlib; the true trigger was
  float-noise negative yerr (−2.2e-17 at strength 1.5). Worker's deviation
  report adjudicated TRUE.
- **fix**: probe ran before acceptance; misdiagnosis self-charged in the 05
  Answer + lessons-inbox 2026-07-19; this entry books the recurrence under the
  ruled id. No worker harm only because the same ticket mandated clip-at-0,
  which covered the true mechanism by luck.
- **anti-recurrence**: cannot be fully mechanized (a ticket's causal prose is
  free text). Standing process rule, on the record here: **a causal mechanism
  may enter a frozen ticket only with attached repro evidence (command + output),
  otherwise it must be labeled `HYPOTHESIS`** — and the referee's independent
  re-run must include reproducing any mechanism the ticket states as fact.
  Pre-dispatch lint gains this as a checklist line (with CR-14's symbol-trace).
- **polluted-rework**: rework-02 FIX-C's red test was aimed at the wrong
  mechanism (vacuous red on the real matplotlib) — caught and superseded by the
  referee probe; no rework cycle wasted.
