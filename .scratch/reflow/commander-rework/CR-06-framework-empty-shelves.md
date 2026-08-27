# CR-06 — the workflow framework was designed as an empty-shelves prescription

The reflow system's own first firing. This is not backlog — it is this session:
the v0 framework (D1–D5, RP-0/RP-1) was ratified as *design*, and grok's second
role-reversal review (RP-1 heartbeat) caught that a design of an anti-self-deception
system had been mistaken for its enforcement — zero landed artifacts, yet the
killer-demo ticket already dispatched.

- **root_cause_id**: `framework-design-without-enforcement`
- **attribution**: framework-fault
- **occurrences**: 1 (expensive+systemic, D3(b): shipping the constitution before the enforcement is the exact second sin from the B-grade meta-review, and would recur on every future framework)
- **evidence**: `.scratch/reflow/meta-reviews/grok-review-2.json` (`cure_worked`: "处方写得很漂亮、药房货架空着"; `biggest new self-deception`: "有 hook 设计 = 已不骗自己"); verified true this session — zero `commander-rework` files existed, `dispatch.sh` only WARN'd, `adversarial-referee:73` still carried the "survives your reading" filter
- **fix**: landed the teeth this session — killed the "survives your reading" filter (`adversarial-referee` skill), hard contract-freeze gate + SIGPIPE trap (`dispatch.sh`), this whole `.scratch/reflow/` (vocab + template + CR-01..06 + inbox + `scripts/reflow-gate.sh`), and made backlog-discharge the framework's acceptance gate
- **anti-recurrence**: re-runnable — `scripts/reflow-gate.sh` exits non-zero if any commander-rework entry is missing a content-contract field or cites an unfrozen id; the framework is not "done" until this gate is green AND an RP-1 external review confirms the content isn't theater
- **polluted-rework**: none directly, but honesty (grok #3): the acceptance gate ("framework's first act = discharge backlog before new heavyweight dispatch") was **already violated** — killer-demo v0.1-11a was dispatched in a prior session, before any teeth existed. It is grandfathered (allowed to complete), not retro-blocked; the hard gate binds new dispatches going forward. The RP-1 heartbeat catching the empty shelves is the loop working; the demo having jumped the gate is a real ordering fault, not a triumph.
