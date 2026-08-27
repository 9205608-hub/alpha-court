# CR-16 — first cursor dispatch: worker never saw the receipt schema; a done delivery bounced at validation

- **root_cause_id**: `ticket-self-contradiction`
- **attribution**: contract-fault (commander)
- **occurrences**: **7** (CR-14 counted #6; this is the same class in a new
  carrier: the ticket's delivery protocol named only
  `branch/commit/worktree_path/ticket_id` while `receipt.schema.json` — the
  actual judging scale — enforces `summary` and more. The grok seam injects
  the schema via `--json-schema`; the freshly wired cursor seam (`7d7bb46a`)
  had no schema channel and the ticket didn't paste it: /worker-dispatch
  rule 1 half-applied — pointed at "the schema is enforced by the dispatch
  harness", never pasted.)
- **evidence**: `.scratch/dispatch/v0.3-00-blade-plumbing/raw-20260813-153647.json`
  (worker receipt `status: done`, real work on `dispatch/v0.3-00-blade-plumbing-
  20260813-153647` @ `f9297ebf`) vs dispatch exit 3
  `receipt invalid: summary is required but missing` (task log 2026-08-13).
- **fix**: `scripts/dispatch.sh` `worker_invoke_cursor` now appends the full
  receipt schema to the prompt under a `## RECEIPT SCHEMA (enforced
  commander-side…)` heading — the channel is mechanized in the bridge, so
  tickets stay worker-agnostic (this commit).
- **anti-recurrence**: `python3 -m pytest tests/test_dispatch_bridge.py` —
  fails if either worker seam loses its schema channel (cursor: prompt-append;
  grok: `--json-schema`).
- **polluted-rework**: none — the delivery itself was salvageable (receipt
  extracted commander-side from the envelope; work judged on the branch by the
  standard referee pass; no worker rework issued).

**Addendum (2026-08-13, same day)**: the class recurred through a THIRD
carrier — the MANUAL cursor resume for rework-01 bypassed dispatch.sh (whose
prompt-append fix only covers fresh dispatches) and the commander hand-typed
a receipt schema into the rework note that diverged from canonical
(`files` vs `files_changed`); the worker complied perfectly with the
schema-as-issued and the receipt failed canonical validation. Judged against
the contract-as-issued; delivery accepted on diff+re-runs. Standing rule
until mechanized: **any manual resume prompt must embed
`scripts/receipt.schema.json` verbatim via `$(cat …)`, never a hand-typed
schema.** Mechanization (a cursor resume path in scripts/) → v0.3 backlog.
