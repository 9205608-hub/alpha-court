# CR-01 — dispatch bridge let a worker escape into the commander checkout

- **root_cause_id**: `bridge-isolation-failure`
- **attribution**: tooling
- **occurrences**: 1 (expensive+systemic, D3(b): a worker writing into the dispatching checkout corrupts the audit trail every time)
- **evidence**: `docs/agents/worker-bridge.md` incident #1; TIMELINE 2026-07-10 "v0.1 开工" (grok `--worktree` headless silently no-op'd; 02 ran in the commander checkout)
- **fix**: commander-side isolation — `git worktree add -b <branch> <path> HEAD` + `--cwd`, grok's own `--worktree` abandoned (`scripts/dispatch.sh:60-90`); live proof in `scripts/BRIDGE-SELFTEST.md`
- **anti-recurrence**: `scripts/dispatch.sh:114` post-flight tripwire `exit 2` on any working-tree change outside dispatch artifacts — re-runnable: a worker that writes into the checkout hard-fails the dispatch
- **polluted-rework**: none (caught before any worker delivery was judged)
