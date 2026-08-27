# Commander-rework ledger

The symmetric-accountability half of the attribution ledger: the commander's own
faults get rework entries with the same content contract workers' reworks get
(`/adversarial-referee` → Symmetric accountability). Existence+shape is gated by
`scripts/reflow-gate.sh`; substance is gated by the RP-1 external review.

| id | root_cause_id | attribution | occ | anti-recurrence re-runnable? |
|---|---|---|---|---|
| CR-01 | bridge-isolation-failure | tooling | 1 | yes (tripwire exit 2) |
| CR-02 | bridge-tripwire-falsetrip | tooling | 1 | yes (grep pathspec) |
| CR-03 | referee-fabricated-spotcheck | referee-fault | **2** | no (process rule — declared) |
| CR-04 | pipeline-sigpipe-receipt-loss | tooling | 1 | yes (grep trap; pipe test) |
| CR-05 | contract-stale-override | contract-fault | **≥2** | **yes — red-test ran green this session** |
| CR-06 | framework-design-without-enforcement | framework-fault | 1 | yes (reflow-gate.sh) |
| CR-07 | commander-self-exempt-from-review | framework-fault | **2** | yes (skill-review-gate.sh — hardened 2026-07-12) |
| CR-08 | gate-tests-happy-path-not-bypass | framework-fault | **3** | yes (bypass-red-tests-first discipline; 4 teeth landed with it) |
| CR-09 | ticket-self-contradiction | contract-fault (commander) | **4** | yes — lint must EXECUTE env-class AC at base (/worker-dispatch rule 3 amended); assertion: `ruff check .` exits 0 at any dispatch base |
| CR-10 | ticket-self-contradiction | contract-fault (commander) | 1 | yes — gate/verify tickets need a trusted-input-provenance lint pass; assertion: the 2 referee-repro fail-opens must raise after rework |
| CR-11 | ticket-self-contradiction | contract-fault (commander) | **5** | yes — lint needs a measurability-at-frozen-scale pass; assertion: FIX-1 test asserts β=0 size per-gate numbers finite (non-NaN, ~R₀ samples) — fails if the won-conditioned estimator returns |
| CR-12 | ticket-self-contradiction | contract-fault (commander) | **6** | yes — perf-ticket lint must profile the hot path on REAL-shaped data; assertion: churn-panel perf test (<5s) fails if the slow/churn path is left as the Python loop |
| CR-16 | ticket-self-contradiction | contract-fault (commander) | **7** | yes — `python3 -m pytest tests/test_dispatch_bridge.py` fails if a worker seam loses its receipt-schema channel |

**Backlog discharged**: the five v0.1 faults grok named (bridge×2, fixture×2, SIGPIPE)
plus the post-hoc-legislation headline — all now carry re-runnable or declared
anti-recurrence checks, not confession paragraphs. CR-06 is the workflow session's own; CR-07/08 rows backfilled; CR-09 added 2026-07-13 (v0.2-06); CR-10 added 2026-07-16 (v0.2-07 delivery audit — two frozen-spec fail-opens, worker won both); CR-11 added 2026-07-17 (v0.2-05 delivery audit — the size P(pass)≈α assertion was NaN under the contract's own specified estimator; worker won pyproject + seed-root deviations).; CR-12 added 2026-07-17 (v0.2-13 perf ticket optimized the fast path but real csi300 is 100% slow-path — worker won, commander re-scoped after prototyping the slow-path vectorization at 7.6x bit-identical); CR-13 added 2026-07-19 (rework-02 dispatch: raw `grok --resume` bypassed every bridge-isolation guarantee after the worker worktree was deleted — worker landed `a51f66e4` directly on the production branch; diff audited clean, delivery accepted; **recurrence #2 of `bridge-isolation-failure` ⇒ promoted**, resume-preflight [DESIGNED]); CR-14 added 2026-07-20 (rework-02 ownership list contradicted its own FIX-B — stats_util unreachable from the list, worker deviated and WON; `ticket-self-contradiction` #6, named by the v0.2 role-reversal review; pre-dispatch lint gains the symbol-trace step, mechanization into rework-lint [DESIGNED]); CR-15 added 2026-07-20 (rework-02 FIX-C wrote an unreproduced crash mechanism into the frozen ticket as fact — RP-1 REJECTED the proposed new id as recurrence laundering, ruled `referee-fabricated-spotcheck` occurrences=3; standing rule: mechanism claims in tickets carry repro evidence or the label HYPOTHESIS); CR-16 added 2026-08-13 (first cursor dispatch, v0.3-00: the receipt schema never reached the worker — grok's `--json-schema` channel had no cursor equivalent and the ticket pointed instead of pasting; a `status: done` delivery bounced at validation exit 3. Schema now rides the cursor prompt in the bridge itself; anti-recurrence `tests/test_dispatch_bridge.py`).
