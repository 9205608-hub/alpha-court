# CR-14 — rework-02 ownership list contradicted its own FIX-B (ticket-self-contradiction, #6)

- **root_cause_id**: `ticket-self-contradiction`
- **attribution**: contract-fault
- **occurrences**: 6 (CR-09 was #2 noted, CR-11 counted #5; this is #6 — chronic)
- **evidence**: `rework-02.md` ownership section lists `config.py / calibrate.py /
  beta_t.py / figure.py (+ whichever module defines solve_matched_beta) …
  Nothing else.` — but FIX-B as specified (raise instead of clamp when the target
  lies outside the observed ICIR range) requires touching the PCHIP solver in
  `stats_util.py`, which the parenthetical does not reach (solve_matched_beta is
  defined in beta_t.py; the clamp lives in stats_util.pchip_beta_for_icir). The
  worker had to deviate, self-reported it, and won the adjudication (05 Answer
  2026-07-19 late). Named by the v0.2 role-reversal meta-review (weakness #4).
- **fix**: the deviation was adjudicated worker-WINS on the record (no worker
  charge); this entry books the fault on the commander ledger where it belongs.
- **anti-recurrence**: existing dispatch-lint rule 3 (execute env-class ACs at
  base) does not catch ownership/reachability contradictions. Addition to the
  pre-dispatch lint (recorded here, applies to every future ticket): for each FIX,
  trace the named change to the defining module (`grep -n "def <symbol>"`) and
  assert the module is in the ownership list — a 1-minute mechanical step that
  fails on exactly this class. Mechanizing into `rework-lint.sh` is [DESIGNED].
- **polluted-rework**: none (worker deviated correctly and won; zero rework cost),
  but only because the worker chose deviation-with-report over refusal.
