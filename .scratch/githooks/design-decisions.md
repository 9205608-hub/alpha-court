# Candidate B — git pre-commit hook enforcement: pinned decisions (2026-07-13)

Turning two *manual* gates into *auto-firing* pre-commit checks. Not "unbypassable
enforcement" — an honest tripwire (see honesty ceiling below).

## Scope (user /grilling)

- **Only the two commit-shaped gates are hooked** (user: "只挂两个 commit-形状的门"):
  - `anti_pattern_gate.py` → pre-commit, scans STAGED `.py`.
  - `skill-review-gate.sh` → pre-commit, when staged changes touch `.claude/skills/`.
- `confirm_gate.py` and `trial_counter.py` stay **research-session ritual gates** — they are
  CONFIRM-time / manual-reconcile, NOT commit-time. Forcing them into git hooks would be the
  D3 overfit ("凑'四门'这个数硬塞"). Explicitly left out.

## anti_pattern in the hook (user /grilling: "硬拦 + 内联 acknowledge")

- HARD-BLOCK the commit on any finding, BUT honor an inline `# reuse-ok: <reason>` on the SAME
  physical line as the flagged token (like `# noqa`), reason must be non-empty/non-whitespace.
- A blanket / file-level / wrong-line / empty-reason acknowledge must NOT exempt.
- This acknowledge mechanism is NEW code added to `anti_pattern_gate.py` (+ its own bypass
  red-tests). Honest limit (CR-08): the gate cannot judge whether the reason is *substantive* —
  that stays a human's/RP-1's job; it raises the bar from "silently hand-roll" to "at least
  name a reason on the line".

## skill-review in the hook (commander-decided; may revise after enum)

- The gate takes two refs and does `git diff base head`. At pre-commit the staged state is not
  a ref, so the hook builds a throwaway commit from the index
  (`TREE=$(git write-tree); TMP=$(git commit-tree $TREE -p HEAD -m _precommit)`) and runs
  `skill-review-gate <merge-base main HEAD> $TMP`.
- **The FF-merge gap (grok #5 territory):** main is local-only, updated by `git merge --ff-only`.
  An FF merge creates NO commit, so `pre-merge-commit` never fires. pre-commit on the branch tip
  is therefore the guard for "before this FF-lands on main". Open tension the enum must resolve:
  committing skill in commit 1 and the review in commit 2 would false-block commit 1 (range
  mergebase..commit1 has the skill, not-yet the review). Candidate resolutions:
  (a) accept it — stage skill+review together; (b) only enforce when committing directly ON main
  (catches the original v0.1 sin) + a manual/CI guard for the FF-merge; (c) --no-ff merges so
  pre-merge-commit fires (changes the clean-history workflow). **Decide after the enum.**

## Honesty ceiling (禁赢学 — do NOT repeat grok #5's "friction not enforcement" over-claim)

Local git hooks are bypassable BY DESIGN. These are **declared holes**, labelled, not pretended
closed:
- `git commit --no-verify` / `-n`; `git -c core.hooksPath=/dev/null commit`.
- A fresh clone has no hooks until `install-hooks.sh` runs; `core.hooksPath` can be unset.
- Non-commit paths (merge/rebase/cherry-pick/commit-tree) skip pre-commit.

The honest label: **auto-fire tripwire that closes the "forgot to run it" failure mode; NOT
unbypassable enforcement.** True enforcement = server-side CI / branch protection, `[DESIGNED]`
for when the public mirror has GitHub Actions. Red-tests for the declared-hole class assert the
hook fires in the NORMAL path and DOCUMENT the hole — they do not pretend to prevent `--no-verify`.

## Install mechanism

- `scripts/install-hooks.sh` sets `git config core.hooksPath .githooks` (a TRACKED dir), so the
  hook is version-controlled and one command enables it. Must be idempotent; must fail-closed if
  the gate errors (python missing / import fails / bash error → BLOCK the commit, never fail-open).
- Worktree caveat: `core.hooksPath` is per-repo config shared across worktrees of the same repo —
  verify it resolves correctly from a linked worktree (this repo uses worktrees).

## Methodology (must complete all three — memory)

enum-first (4-lens workflow) → bypass red-tests FIRST (CR-08) → implement → fresh grok RP-1.
