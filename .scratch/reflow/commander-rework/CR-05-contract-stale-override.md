# CR-05 — rework notes overrode contracts stale in the worker's worktree

- **root_cause_id**: `contract-stale-override`
- **attribution**: contract-fault
- **occurrences**: **≥2** (recurrence, D3(a)) — 08b / 08c / 08d / 10a rework notes carried "the spec in YOUR worktree is stale; the amended text below overrides"
- **evidence**: `.scratch/dispatch/v0.1-08d-tstats-fdr/rework-01.md` ("bhy.md and the spec in YOUR worktree are stale"); meta-review `top_criticisms[0]` 事后立法; both grok reviews flagged it as the #1 sin
- **fix**: contract freeze is now a **hard gate**, not an honor-system line — `scripts/dispatch.sh:70` exits 1 if any tracked file is modified/staged (worker worktree is built from HEAD and cannot see a dirty tree); `/worker-dispatch` Pre-flight rewritten to say so; no silent `--override`
- **anti-recurrence**: two halves, both re-runnable — because the crime has two halves and grok #3 caught that the freeze gate alone was the *wrong tooth*. **(pre-dispatch)** with a dirty tracked tree, `dispatch.sh <ticket>` prints `CONTRACT FROZEN` and exits 1 before `git worktree add` — a stale contract cannot reach a worker. **(post-dispatch, the actual v0.1 sin)** `scripts/rework-lint.sh <note>` exits 1 on "worktree stale / 以我勘误为准 / erratum overrides" phrasing in a rework note; red-tested to FAIL on 08d's historical rework note and PASS on a clean one. The dirty-tree gate never covered post-dispatch override; rework-lint does.
- **polluted-rework**: `.scratch/dispatch/v0.1-08b/`, `v0.1-08c`, `v0.1-08d`, `v0.1-10a` rework-01 notes (the reworks whose attribution was muddied by post-hoc contract edits)
