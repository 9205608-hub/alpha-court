# Ticket: v0.1-01-probe — Bridge self-test marker

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court dispatches work from a commander session to headless worker agents
through a bridge (ticket file in → isolated git worktree → JSON receipt out).
This ticket is the bridge's end-to-end self-test: a deliberately tiny but real
task that proves the isolation, commit, and receipt chain works. Your working
directory should be a fresh, dedicated git worktree created by the dispatcher —
part of your job is to report exactly where you actually ran.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Touch ONLY the single file named in the Task. Do not create, modify, or
   delete anything else.
2. Do not modify: `CLAUDE.md`, `README.md`, `TIMELINE.md`, anything under
   `docs/`, `.scratch/`, `.claude/`, or `.gitignore`.
3. File content in English.

## Task

1. Create `scripts/BRIDGE-SELFTEST.md` with exactly this content (fill in the
   two placeholders with real values from your environment):

   ```markdown
   # Bridge self-test

   This file was created by a headless worker agent through the alpha-court
   commander→worker bridge, as the end-to-end proof for ticket v0.1-01.

   - Working directory: <output of `pwd`>
   - Branch: <output of `git branch --show-current`>
   ```

## Acceptance criteria

1. `cat scripts/BRIDGE-SELFTEST.md` shows the content above with real values → exit 0
2. `git status --porcelain` after your final commit → empty
3. `git log --oneline -1` shows your commit with message `v0.1-01-probe: bridge self-test`

## Out of scope

Everything else. No other files, no dependencies, no tests.

## Delivery protocol

1. Work only in your current working directory (a fresh git worktree).
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt.
3. Commit: `git add scripts/BRIDGE-SELFTEST.md && git commit -m "v0.1-01-probe: bridge self-test"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-01-probe`
