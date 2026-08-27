# Ticket: v0.2-12-RP1 — adversarial cross-model review of commit 610f9f82

You are a headless REVIEWER agent for the alpha-court project. This is a
READ-AND-PROBE audit, not a build ticket. Your job is to try to BREAK the
delivery, not to improve it. You are in a fresh git worktree whose HEAD
already contains the commit under review.

## Subject

Commit `610f9f82` ("v0.2-12: robustness nits batch"), built by the commander
(the usual worker was quota-blocked). Because builder and referee were the
same party, YOUR review is the independent-eyes step (RP-1) and it gates the
next snapshot publish. Do not defer to the commit message's claims — verify.

The frozen contract the work was built against is committed reading material:
`../v0.2-12-robustness-nits/ticket.md` relative to this file, absolute:
`[HOME]/Desktop/alpha-court/.scratch/dispatch/v0.2-12-robustness-nits/ticket.md`
Read it first; judge the diff `52566a27..610f9f82` against it.

## What to do (all inside your worktree)

1. `git show 610f9f82` and `git diff 52566a27..610f9f82` — read every hunk.
2. Independently re-establish the red evidence for at least slices A, B, C:
   check out or stash-revert the relevant hunk (e.g.
   `git checkout 52566a27 -- court/ledger.py` while keeping the new tests)
   and confirm the new tests actually FAIL on the old code — a test that
   passes on both sides is theater. Restore afterwards.
3. Attack construction (live, not by reading): for each of
   - slice A byte-exact recovery: craft at least one torn/encoding case the
     tests do NOT cover (e.g. torn line ending exactly at a span boundary,
     final line valid JSON but non-dict, \r\n contamination) and check
     recovery neither corrupts intact bytes nor accepts garbage;
   - slice B symmetry: hunt for any REMAINING write-validates-replay-trusts
     asymmetry in `court/ledger.py` (fields beyond metric/decisions/role —
     e.g. se.kind, direction, periods_per_year, series shape, scope empty);
   - slice C: any remaining consumer assuming statistic-keyed
     `Judgment.decisions` (grep the whole repo including examples/).
4. Run the full acceptance set yourself: `python3 -m pytest -q` (expect
   556 passed / 2 skipped), `ruff check .`, 
   `python3 -m harness.court_import_gate --court court`.
5. Verdict per slice: ACCEPT / ACCEPT-WITH-FINDINGS / REJECT, with evidence
   (commands + real exit codes / observed behavior). Findings ranked
   major/minor. An empty findings list must mean you genuinely tried and
   failed to break it, not that you did not try.

## Hard constraints

- Your final committed diff must be EMPTY (audit only — `git status` clean;
  scratch files under /tmp, not the worktree). Temporary reverts for red
  verification must be restored before you finish.
- Code/comments you quote stay in English; your findings prose may be
  English or Chinese.

## Delivery protocol

Final output: ONLY the JSON receipt (schema enforced by the harness):
`ticket_id`="v0.2-12-RP1", `status` ("done"|"partial"|"blocked"),
`summary` = one-paragraph verdict (overall ACCEPT/REVISE/REJECT + counts),
`branch`, `commit` (= HEAD you audited), `worktree_path`,
`files_changed`=[] (must be empty), `self_test` = every command you ran with
real exit codes, `deviations`, `open_questions` = your findings list
(each: severity, file:line, claim, evidence).
