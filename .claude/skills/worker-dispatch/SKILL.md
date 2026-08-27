---
name: worker-dispatch
description: Dispatch a well-specified implementation ticket to the headless worker (DeepSeek Harness `dsh`, via dispatch.sh) — ticket authoring rules, required ticket fields (ETA/failure modes/checkpoints), contract freeze, dispatch mechanics, rework protocol without resume. Use when an issue is ready-for-agent and the deliverable is code or a document a worker can build unsupervised.
---

# Worker Dispatch

Cross-model division of labor: the commander (this session) writes the ticket,
a headless worker CLI builds it in an isolated worktree, the delivery comes
back as a JSON receipt that is schema-validated commander-side (for ds the
schema rides the prompt and the last JSON object of the final message is
validated), and `/adversarial-referee` judges it. The evaluator never lives in the worker loop; the worker never grades
itself. Grown in alpha-court v0.1 (24 worker runs, 14 tickets, 8 reworks);
the ticket-authoring rules below encode the worker-side critique from the
2026-07-11 meta-review — read them as paid-for lessons, not style advice.

## Current worker (2026-08-15 ruling: "改用 ds，全线")

- **Builder = DeepSeek Harness**: `npx @deepseek-ai/dsh@0.1.0-rc.6 --profile headless`
  (version pinned; developer preview drifts). Default model `deepseek-v4-flash`;
  heavy tickets `-m deepseek-v4-pro`. **Reviewer + referee = Claude** (cross-vendor
  iron law holds). grok CLI (retired 2026-08-13) and Cursor (retired 2026-08-15,
  subscription lapsed) remain as dormant seams: `-k grok|cursor` revives them.
- **Key must be sourced first** (not in shell profile):
  `set -a; . ~/Desktop/智能投研助手/run_research.local.sh; set +a`
- **Pay-per-use.** flash ticket ≈ ¥0.2 measured. Balance is a variable — check
  `curl -s https://api.deepseek.com/user/balance -H "Authorization: Bearer $DEEPSEEK_API_KEY"`
  before long runs; an empty balance fails silently.
- **No headless resume.** dsh has no `--resume` → an interrupted ticket is
  RE-DISPATCHED. **Every dispatch builds a FRESH worktree from HEAD** (`-w` is
  only a name prefix; a new timestamp = new path + new `dispatch/<name>-<stamp>`
  branch). Prior work is carried forward only by (a) merging/cherry-picking the
  previous dispatch branch into the base before re-dispatching, or (b) pasting
  STATUS.md and the prior diff summary into the ticket. `resume-worker.sh` refuses
  ds/cursor envelopes and tells you to re-dispatch; do not bypass it. This is why
  checkpoints (below) are mandatory.
- ⚠ Every ds mechanic on this page (`-k`, ds default, key guard, `--patch` model
  overlay, resume guard) lives in `dispatch.sh` on branch
  `claude/project-progress-opensource-58d4be` (worktree
  `.claude/worktrees/project-progress-check-9334db`); **main's `dispatch.sh` is still
  grok-only** and rejects `-k` until that branch is fast-forwarded.
- Channel table with verification dates lives in the owner's global Claude config
  (private; not part of this repo).

## Pre-flight: contract freeze

Before dispatching, every authoritative document the ticket names must be
**committed and final**. `dispatch.sh` **hard-fails (exit 1) if any tracked
file is modified or staged** — the worker worktree is built from `HEAD` and
cannot see a dirty tree. No `--override`; commit (or stash) first. If a
contract changes while a worker is in flight, do NOT patch it into the rework
note — either wait for the delivery and issue the change as a new ruling
attributed "contract-fault, not worker-fault", or kill and re-dispatch against
the amended base. A worker may only ever be judged against the contract that
was in its worktree.

## Ticket authoring rules (violations invalidate the rework statistics)

1. **Self-contained means paste, then point.** Critical constraints, formulas
   and conventions are pasted inline; a named repo document may carry the
   rest ONLY if it is committed in the worker's base and the ticket names the
   exact sections. Never point at anything uncommitted. **Facts that live in
   the commander's memory files are invisible to the worker — paste them.**
2. **Acceptance criteria at the referee's scale.** Write the AC at the same
   severity the panel will actually judge. If you can't write the scale down,
   you haven't decided it — decide it first.
3. **Lint the ticket adversarially before dispatch.** Hunt internal
   contradictions; for heavyweight tickets spend one verifier agent on
   ticket-lint. The lint must **EXECUTE every environment-class AC command at
   the dispatch base** (ruff, pytest collection, venv install) — reading an AC
   is not validating it (CR-09, recurrence #2 of `ticket-self-contradiction`).
4. **Operational notes are part of the ticket**: incremental file writes,
   detach-and-poll for any command over ~2 minutes, venv/data-cache isolation
   exceptions named explicitly.
5. **Iron laws excerpted in every ticket**, plus file-ownership boundaries
   (disjoint ownership is what lets parallel tickets merge with zero conflicts).
6. **Receipt is an instance, not a copy of the schema**: the receipt prompt
   suffix (`receipt_prompt_suffix()`) tells the worker not to echo `$schema`/
   `title` keys. Never "fix" a rejected receipt by editing it — the receipt is
   the worker's own statement of fact.

## Required pre-flight fields (added 2026-08-15; **NOT enforced by any script and not yet tracked** — honour system until a lint exists)

The whole ticket file rides the worker prompt verbatim, so **commander/owner
bookkeeping never goes in the ticket**. It goes in the sidecar
`.scratch/dispatch/<TICKET-ID>/preflight.md`; only worker-actionable lines
(checkpoints, STATUS.md contract) go in the ticket body (see `scripts/ticket-template.md`).

| Field | Where | Why |
|---|---|---|
| ETA / cost estimate | preflight.md | Owner's rule: no run without "what/why/ETA" first; ds is pay-per-use. Never shown to the worker (an implicit budget invites self-truncation) |
| Design + failure modes | preflight.md | What will be built and 2-3 ways it can fail silently, and which AC catches each (owner go/no-go input) |
| AC commands executed at base (yes/no + date) | preflight.md | Rule 3 |
| Checkpoints | ticket body | dsh cannot resume → name stage commits; worker updates `.scratch/dispatch/<TICKET-ID>/STATUS.md` after each stage (audit trail, referee excludes it from diff review) |
| Progress reporting | ticket body + commander | STATUS.md per stage; the commander polls it manually (`tail`) and reports upward — no harness poller exists; `caffeinate -dims` is a manual commander duty |

## Mechanics

- `scripts/dispatch.sh <ticket.md> [-k ds|cursor|grok] [-m flash|pro] [-w NAME]`
  (`-n N` / `-t TURNS` / `-e EFFORT` are grok-only; ds rejects them loudly, exit 1)
  — commander-side worktree isolation, post-flight tripwire, commander-side
  receipt validation. ds has no effort dial: use `-m deepseek-v4-pro` for heavy
  tickets. dsh headless has no `--cwd`/`--json-schema`/`--model`: dispatch.sh
  handles cwd (subshell `cd`), schema (rides the prompt via
  `receipt_prompt_suffix()`) and model (generated `--patch` overlay); `--max-turns`
  is simply not available on ds. Do not hand-roll these.
- Receipts are facts, not grades: status / branch / commit / files /
  commands-with-real-exit-codes / deviations / open_questions. An honest
  `partial` outranks a dishonest `done`.
- Receipts persist to files, not stdout; `dispatch.sh` traps SIGPIPE.
- Parallel dispatches: stagger launches ~5s; artifacts land under
  `.scratch/dispatch/<ticket-id>/` and are committed as the audit trail.
- Long dispatches: run under `caffeinate -dims`; launch must be confirmed
  landed (STATUS/process visible) — a queued job on a sleeping Mac is not a launch.

## Rework protocol (no-resume edition)

Rework notes quote the referee evidence verbatim, enumerate fixes by
severity, restate the delivery protocol, and are **merged into the original
ticket, which is re-dispatched into a FRESH worktree from HEAD**. The worker
does NOT see its prior worktree: before re-dispatching, either merge/cherry-pick
the previous `dispatch/<name>-<stamp>` branch into the base (committed) or paste
STATUS.md + the prior diff summary into the ticket. Every rework is attributed in
the issue's Answer: worker-fault / contract-fault / referee-fault.

## See also

`docs/agents/worker-bridge.md` (bridge contract + incident log),
`scripts/ticket-template.md`, `/adversarial-referee` (the receiving end).
