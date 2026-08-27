# Frozen root-cause vocabulary

Recurrence in the reflow system (D3(a): same cause ≥2 → promote) is detected by
`root_cause_id`, **not** by prose grep — otherwise the same failure written three
different ways ("fixture self-error" / "spot-check didn't read the doc" / "referee
memory fabrication") reads as three fresh n=1s and the recurrence bar is never met
(grok RP-1 review, 2026-07-11).

**This vocabulary is frozen.** Adding, renaming, splitting, or merging an entry is
itself a change that must clear an RP-1 external review before it lands — because
splitting one id into two is exactly how a commander would launder a recurrence
back into an n=1 (the D3 laziness shield). Append-only; changes go through the gate.

| root_cause_id | class | one-line |
|---|---|---|
| `bridge-isolation-failure` | tooling | grok `--worktree` headless silently no-op'd; worker ran in the dispatching checkout (worker-bridge incident #1) |
| `bridge-tripwire-falsetrip` | tooling | concurrent-dispatch tripwire excluded only its own dir → false-tripped on sibling raw artifacts (incident #2) |
| `referee-fabricated-spotcheck` | referee-fault | referee "caught" a worker using inputs invented from memory; worker was right (×2 in v0.1) |
| `pipeline-sigpipe-receipt-loss` | tooling | `dispatch.sh ... \| head` SIGPIPE killed the script before receipt persistence |
| `dispatch-maxtokens-truncation` | tooling | single giant emission hit max_tokens, left no session to resume; first 08a dispatch wasted |
| `contract-stale-override` | contract-fault | rework note overrode a contract stale in the worker's worktree ("my erratum overrides") = post-hoc legislation |
| `ticket-self-contradiction` | contract-fault | ticket internally inconsistent (δ=0 vs `0<δ<T`) or AC written below the panel's real judging scale |
| `framework-design-without-enforcement` | framework-fault | designed an anti-self-deception mechanism and treated the design as if it were the enforcement (empty-shelves prescription) |
| `commander-self-exempt-from-review` | framework-fault | commander shipped its own output (a skill, a ruling) without the external review it demands of worker-binding rules, and rationalized skipping it — the double-standard, recurring (added under grok #4 RP-1 sanction) |
| `gate-tests-happy-path-not-bypass` | framework-fault | a mechanical gate was red-tested only against easy/inverted inputs, never the actual adversarial bypass, so it green-lights while the real sin walks through (added under grok #4 RP-1 sanction) |
| `acceptance-preflight-missing` | contract-fault | a multi-hour real-data burn launched without asserting the launch-time invariants it depends on (config targets ⊆ frozen artifacts; solver domains valid at frozen scale) — prose "secondary" where a re-runnable guard belonged (added under RP-1 2026-07-20, grok ruling: genuinely new) |
| `publish-rules-blind-to-new-carriers` | framework-fault | a new artifact CLASS entering the tree carries sensitive data in a form the publish rules have never seen; the gate implements its rules exactly and is still blind — rule-set aging vs moving inputs (added under RP-1 2026-07-20, grok ruling: genuinely new) |
