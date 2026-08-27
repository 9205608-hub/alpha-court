# Ticket: <TICKET-ID> — <title>

<!--
Worker ticket template (M0 commander→worker bridge).
Fill every section. The ticket must be SELF-CONTAINED: the worker reads this
file and nothing else — no conversation history, no other repo docs assumed.
Dispatch with: scripts/dispatch.sh <path-to-this-file>
-->

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

<!-- COMMANDER PRE-FLIGHT (required since 2026-08-15) — NOT part of this file. The whole ticket
rides the worker prompt verbatim, so owner/commander bookkeeping (ETA, ¥ cost, design + failure
modes, "AC commands executed at base: yes/no + date") goes in the sidecar
`.scratch/dispatch/<TICKET-ID>/preflight.md`, never here. -->

## Checkpoints and status (worker-actionable)

<!-- dsh has no resume: an interrupted ticket is re-dispatched into a FRESH worktree from HEAD.
Only what is committed on the previous dispatch branch (and merged/cherry-picked by the commander)
or pasted into this ticket survives. Name the checkpoints. -->
- Checkpoint 1: after <…> — commit `<TICKET-ID>: checkpoint 1 — <…>`
- Checkpoint 2: after <…> — commit `<TICKET-ID>: checkpoint 2 — <…>`
- After every checkpoint update `.scratch/dispatch/<TICKET-ID>/STATUS.md` (3-6 lines: done / in
  progress / blocked / next). It is audit trail, not deliverable: the referee excludes it from
  the diff review. The commander polls it manually (`tail`) — no harness poller exists.

## Context

<!-- Why this work exists. Enough background that the worker never needs to
guess intent. Quote relevant contracts/specs INLINE (workers read the original
text, not a paraphrase — paste, don't point). -->

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality (the project reuses qlib; the court
   kernel only consumes return/IC series).
2. Do NOT build idea/factor generation logic (generation side is a stub).
3. Statistical implementations must be written fresh from public literature,
   with the citation and formula reference in the docstring.
4. `court/` must not import any market-specific code or library (no qlib, no
   exchange calendars, no universe definitions). Market specifics live in
   `adapters/` only.
5. Code, docstrings, comments: English.
<!-- Keep the laws that apply; add ticket-specific constraints below. -->

## Task

<!-- The actual work, as a numbered list of concrete deliverables. -->

## Acceptance criteria

<!-- Objectively checkable, each one a command or an inspectable fact.
The referee will re-run these independently — write them as commands. -->

## Out of scope

<!-- Explicit non-goals so the worker doesn't gold-plate. -->

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit at every checkpoint named above (`git add -A && git commit -m "<TICKET-ID>: checkpoint N — …"`);
   the final commit message is `<TICKET-ID>: <summary>` and `receipt.commit` = final HEAD.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
