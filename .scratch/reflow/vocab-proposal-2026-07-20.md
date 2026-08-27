# Vocab proposal 2026-07-20 — three additions (PENDING RP-1; vocab is frozen until cleared)

Per the frozen-vocab rule, additions must clear an RP-1 external review before
landing in `root-cause-vocab.md` — because splitting one id into two is exactly
how a commander launders a recurrence back into an n=1. The reviewer is asked to
check each entry for exactly that: is this genuinely a NEW class, or a respelling
of an existing id that would reset a recurrence counter?

| proposed root_cause_id | class | one-line | closest existing id & why it is NOT the same |
|---|---|---|---|
| `diagnosis-asserted-not-reproduced` | referee-fault | an unreproduced causal mechanism written into a frozen ticket/contract as fact; workers implement against a false "why" | `referee-fabricated-spotcheck` is invented *inputs* at spot-check time; this is an invented *mechanism* at contract-freeze time — same fabrication family, different layer and blast radius (a frozen ticket binds the worker; a spot-check binds one judgment). If the reviewer rules it the SAME class, the honest outcome is occurrences(referee-fabricated-spotcheck) += 1, not a new id. |
| `acceptance-preflight-missing` | contract-fault | a multi-hour real-data burn launched without asserting the invariants it depends on (config targets ⊆ frozen artifacts; solver domains valid at the frozen scale) — prose "secondary" where a re-runnable guard belonged | `ticket-self-contradiction` is a defect *inside a ticket's text*; this is a missing *commander-side check between freeze and burn* — no ticket involved (the sweep is commander-run). CR-11's "asserted-statistic-unmeasurable-at-frozen-scale" is the nearest cousin but concerns a claim in the contract, not the launch procedure. |
| `publish-rules-blind-to-new-carriers` | framework-fault | every new artifact CLASS entering the tree (receipts quoting VCS metadata, path-mangled logs) is a sensitive-data carrier the publish rules have never seen; audit PASS while the byte-grep backstop catches it | `gate-tests-happy-path-not-bypass` is about a gate's *test coverage*; this is about a rule-driven gate's *rule set aging* against a moving input distribution — the gate works exactly as specified and is still blind. Evidence: 2026-07-20 pre-flight (qq-email in receipt-quoted `git show`; flattened `-Users-…` paths). |

Supporting evidence pointers: lessons-inbox 2026-07-19/20 entries; 05 issue Answer
addenda; meta-review-commander-v02 verdict (top-criticisms #1/#2); publish-rules
2026-07-20 entries.
