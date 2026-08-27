# CR-02 — concurrent-dispatch tripwire false-tripped on sibling artifacts

- **root_cause_id**: `bridge-tripwire-falsetrip`
- **attribution**: tooling
- **occurrences**: 1 (expensive+systemic, D3(b): any parallel dispatch would false-trip, and parallelism is the bridge's main throughput lever)
- **evidence**: `docs/agents/worker-bridge.md` incident #2; TIMELINE 2026-07-10 "四张 AFK 票并行派单" (sibling raw/receipt files misread as isolation leak)
- **fix**: tripwire pathspec excludes the whole `.scratch/dispatch` convention dir plus OUT_DIR, not just this run's dir (`scripts/dispatch.sh:75-87`); HEAD-move downgraded to a warning
- **anti-recurrence**: `scripts/dispatch.sh:81` `STATUS_PATHSPEC` carries `:(exclude).scratch/dispatch` — re-runnable: `grep -q 'exclude).scratch/dispatch' scripts/dispatch.sh`; two concurrent dispatches no longer see each other's artifacts
- **polluted-rework**: none
