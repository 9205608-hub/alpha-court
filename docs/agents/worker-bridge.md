# Commander→Worker Bridge (M0)

How work gets dispatched from the commander session (Claude Code) to headless
worker agents (grok CLI), and how deliveries come back. Established by ticket
[01 M0 指挥→工人桥](../../.scratch/v0.1/issues/01-m0-commander-worker-bridge.md).

## Roles

- **Commander / referee** (Claude Code session): writes tickets, dispatches,
  reviews deliveries. The evaluator stays out of the worker loop — workers
  never grade their own output.
- **Worker** (grok CLI, headless): reads the ticket file verbatim, works in an
  isolated git worktree, commits, and emits a schema-constrained JSON receipt.

## The three contract pieces

1. **Ticket format** — `scripts/ticket-template.md`. Tickets are
   self-contained: context, iron laws, task, acceptance criteria (as
   re-runnable commands), out-of-scope, delivery protocol. Workers read the
   original ticket text, never a paraphrase; quoted contracts are pasted
   inline, not linked.
2. **Receipt contract** — `scripts/receipt.schema.json`. Grok still receives
   the schema via `--json-schema` (model-level nudge), but **commander-side
   validation** in `scripts/dispatch_receipt.py` is the hard gate — a
   non-conforming or missing receipt fails the dispatch. Receipts carry facts
   (branch, commit, files, commands + real exit codes, deviations, open
   questions) — not self-evaluation.
3. **Dispatch script** — `scripts/dispatch.sh <ticket.md>`. Isolation is
   enforced on the **commander side**: the script runs `git worktree add -b
   dispatch/<name>-<stamp>` under `~/.alpha-court/dispatch-worktrees/` (override
   with `DISPATCH_WORKTREE_ROOT`) and pins the worker into it via `grok --cwd`.
   Do NOT rely on grok's own `--worktree` flag — in headless mode it silently
   ran the worker in the dispatching checkout (incident #1, 2026-07-10). A
   post-flight tripwire exits 2 if the dispatching checkout's working tree
   changed (excluding `.scratch/dispatch/`, where concurrent dispatches drop
   their own artifacts — excluding only the current ticket dir false-tripped
   parallel runs, incident #2, 2026-07-10) and prints a loud warning listing
   new commits if HEAD moved (commander commits during long runs are
   legitimate; worker commits are a breach — referee eyeballs the list). The receipt is read from the envelope's
   `structuredOutput` field (`text` is a concatenation of per-turn objects;
   only a fallback). Writes `raw-<stamp>.json` (full envelope, incl. sessionId
   for `grok --resume`) and `receipt-<stamp>.json` next to the ticket.
   Options: `-n` best-of-n, `-m` model, `-t` max turns, `-w` worktree name,
   `-e` reasoning effort (default `high` — grok-4.5's top menu tier, pinned
   explicitly so CLI default changes can't silently lower worker effort).
   After merging a delivery: `git worktree remove <path> && git branch -d
   dispatch/<name>-<stamp>`.

## Conventions

- Worker tickets live at `.scratch/dispatch/<ticket-id>/ticket.md`;
  raw envelopes and receipts land in the same directory (committed — they are
  part of the audit trail).
- Ticket ids: `<map>-<issue>` (e.g. `v0.1-02` = issue 02 of the v0.1 map),
  suffixed `-a`, `-b`… if an issue splits into several worker tickets.
- Workers must commit their work in their worktree; the receipt's
  `branch`/`commit`/`worktree_path` fields tell the referee where to look.
- Dispatch from a committed state: the worker's worktree is based on the
  current HEAD of the checkout you dispatch from.

## Resuming an interrupted worker

If a run dies mid-ticket (envelope `stopReason: Cancelled`, receipt is a
mid-run progress object with empty `commit`), do NOT re-dispatch from scratch:
the worker's worktree state (venv, partial work) survives. Resume headless
with the envelope's sessionId:

```sh
grok --resume <sessionId> \
  --prompt-file <ABSOLUTE path to rework/resume instructions> \
  --cwd <worktree_path> --output-format json \
  --json-schema "$(cat scripts/receipt.schema.json)" \
  --permission-mode auto --reasoning-effort high \
  --max-turns 120 > <ticket-dir>/raw-resume.json
```

For long blocking steps (large downloads), tell the worker to run them
detached (`nohup ... > log 2>&1 &`) and poll — single long commands risk the
in-session tool timeout that caused the cancellation.

## Referee checklist (before merging a delivery)

1. Read the receipt: status, deviations, open_questions first.
2. `git -C <worktree_path> diff <base>..HEAD` — review the actual diff, file
   by file, against the ticket's acceptance criteria and the iron laws
   (especially: no market-specific imports inside `court/`).
3. Re-run the acceptance commands **independently** in the worker worktree —
   never trust `self_test` exit codes.
4. Merge the worker branch (or cherry-pick) into the commander branch on pass;
   on fail, write a follow-up ticket quoting the receipt and the rejection
   reasons. Either way, note the outcome in the wayfinder issue.

## Worker generalization

Ruling source: `docs/agents/dispatch-and-governance.md` Part A (incl. the
2026-07-12 audit revisions).

`scripts/dispatch.sh` has exactly **two worker-specific seams**; everything
else (worktree isolation, post-flight tripwire, SIGPIPE trap, branch
mechanics) is worker-agnostic and stays byte-for-byte:

1. **`worker_invoke`** — builds the CLI command array and runs it into
   `raw-<stamp>.json`. Only **grok** is wired (flags: `--prompt-file`,
   `--cwd`, `--output-format json`, `--json-schema`, `--permission-mode auto`,
   `--reasoning-effort`, `--max-turns`, optional `--best-of-n` / `--model`).
   A second worker later = a second branch inside this function, not a
   rewrite of the bridge.
2. **`worker_extract_receipt`** — calls
   `python3 scripts/dispatch_receipt.py <raw> <schema> <receipt_out>`. That
   script extracts `envelope.structuredOutput` (with the `text`
   concat-decode fallback) and **validates the receipt against
   `scripts/receipt.schema.json` on the commander side**.

### Minimal worker contract (a–d)

A worker is any headless CLI that:

- **(a)** takes a self-contained prompt file (ticket),
- **(b)** works in a commander-created isolated worktree pinned by a cwd flag,
- **(c)** returns a receipt conforming to `scripts/receipt.schema.json`,
- **(d)** runs fully non-interactively (no human prompts; grok's
  `--permission-mode auto` is the current wiring of this clause).

### Commander-side validation (why)

Schema conformance used to ride only on grok's model-level `--json-schema`.
That is not enough for clause (c): a second CLI may lack native schema
support, and even grok can emit a dict that is not a valid receipt. The
bridge therefore **always** validates the extracted receipt against
`receipt.schema.json` with a **dependency-free** stdlib structural checker
(`scripts/dispatch_receipt.py` — no `jsonschema` pip dep). Validation
failure = delivery rejected (exit 3); missing receipt = exit 4. The check
is independent of any worker's native schema support.

Only **grok** is wired. A config-driven worker **registry** is deferred
(YAGNI): there is no second worker to run.

Referee governance (RP-1) is bound in
`docs/agents/dispatch-and-governance.md` Part B, pointing at the global
`adversarial-referee` / `worker-dispatch` skills rather than rebuilding them.

## Scope guard

M0 is "can dispatch, can receive" only. Pre-registration gates, adversarial
referee review, multi-CLI generalization belong to `harness/` (v0.2) — do not
grow them here. The two-seam refactor above is the v0.2 generalization
deliverable; a registry waits for a real second worker.
