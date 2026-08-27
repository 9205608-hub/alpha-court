# CR-13 — resume path bypasses every bridge-isolation guarantee (recurrence of CR-01)

- **root_cause_id**: `bridge-isolation-failure`
- **attribution**: tooling (primary) + referee-fault (commander resumed without a
  worktree-existence preflight) + worker-secondary (continued delivering from the
  only writable tree it could find instead of stopping with an open_question —
  the v0.2 role-reversal review judged the original "adopted a foreign checkout"
  phrasing overly harsh; tag retained, tone corrected 2026-07-20, dispute recorded)
- **occurrences**: 2 (CR-01 = dispatch path, 2026-07-10; this = resume path,
  2026-07-19 ⇒ promoted by recurrence, D3(a))
- **evidence**: rework-02 raw receipt
  (`.scratch/dispatch/v0.2-05-power-harness/raw-rework-02.json`): worker states
  "Workspace moved… Found power_calibration in the peaceful-austin worktree.
  Working there", then commits `a51f66e4` directly on `claude/continuing-work-ca88e8`
  in the commander's worktree; `~/.alpha-court/dispatch-worktrees/` verified empty
  at referee time (original worker worktree deleted between rework-01 and rework-02).
  CR-01's tripwire lives in `scripts/dispatch.sh` — the raw `grok --resume` used for
  rework dispatch runs none of it.
- **fix**: this delivery was adjudicated with a full-diff ownership audit before
  acceptance (`git show --stat a51f66e4` = exactly the 5 owned files; nothing else
  touched — audit trail intact this time). Resume protocol amended on the record
  (05 issue Answer + this entry): raw `grok --resume` is no longer a permitted
  dispatch verb; rework resumes MUST run the preflight below first, and a missing
  worker worktree means re-dispatch fresh via `scripts/dispatch.sh` with the rework
  note as the ticket (never adopt a foreign checkout).
- **anti-recurrence**: re-runnable preflight (run before ANY resume):
  `test -d "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["worktree_path"])' <original-receipt.json>)" || { echo "worker worktree gone — re-dispatch fresh"; exit 2; }`
  — run against this incident's original receipt it FAILS today (worktree deleted),
  i.e. it detects exactly this class. **LANDED 2026-07-20**: `scripts/resume-worker.sh`
  (preflight fail-closed + post-flight tripwire), built red-first per CR-08 —
  23 bypass tests (16 enumerated + commander self-probe v11b + grok RP-1 additions
  v11c/d, v14b/c, v01b, v13c; RP-1 archive `.scratch/dispatch/rp1-resume-tooth/`).
  Raw `grok --resume` is retired; this script is the only resume verb.
- **polluted-rework**: rework-02 itself (delivery landed un-isolated on the
  production branch; content audited clean and accepted — see 05 issue Answer
  2026-07-19 addendum for the full referee record).
