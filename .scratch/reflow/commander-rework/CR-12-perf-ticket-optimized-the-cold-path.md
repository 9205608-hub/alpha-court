# CR-12 — the v0.2-13 perf ticket vectorized the FAST path, but real csi300 hits the SLOW path on 100% of dates → the optimization was a no-op for its own purpose

- **root_cause_id**: `ticket-self-contradiction`
- **attribution**: contract-fault (commander)
- **occurrences**: 6th of `ticket-self-contradiction`; **direct sibling of CR-11**
  (same meta-cause: the pre-dispatch lint did not measure the relevant quantity at
  REAL-data scale). CR-11 = an asserted honesty statistic was NaN at the frozen
  N/R; CR-12 = a perf ticket optimized a code branch that the target data never
  takes. Same class, distinct ticket (13, not 05), so a distinct entry with the
  shared id (not laundered into a fresh n=1).
- **evidence**: the ticket scoped "vectorize the full-support FAST path" of
  `_shared_kernel` on the premise that csi300 is mostly fast-path. Referee measured
  on the real evaluator: **0/480 dates are fast-path — 100% hit the slow
  (`_ranks_within_joint`) branch** because each date's PIT membership (~300) is a
  strict subset of the 336-instrument union, excluding ~36 finite cells every date.
  The worker's fast-path vectorization is correct + bit-equivalent + tested (3.7× on
  an all-dense synthetic panel) but is a **no-op on real csi300** (evaluate_shifted
  still ~31s). The worker's own perf test used a synthetic ALL-DENSE panel, which
  masked the gap (it can't hit the slow path). Commander pre-dispatch: verified the
  equivalence *construction* on a synthetic dense panel and profiled the 32s total,
  but never checked the **fast/slow split on real csi300** — the exact CR-11 gap.
- **fix**: ticket-13 rework-01 (`.scratch/dispatch/v0.2-13-kernel-perf/rework-01.md`)
  re-scopes to the SLOW path: a vectorized masked-average-rank-within-joint
  (`_masked_avg_ranks`, stable-sort tie order) + the worker's existing
  `_masked_row_pearson`. Commander prototyped it on real csi300 first:
  **bit-identical (max abs & rel diff = 0.0) and 7.6× (31.3s → 4.1s)** — so the
  rework target is verified before dispatch. Rework adds a mandatory PIT-CHURN
  equivalence panel and a PIT-churn perf gate (< 5s) so a fast-path-only fix can no
  longer pass. Worker WINS the original delivery (zero worker-fault; correct build
  of a mis-scoped ticket).
- **anti-recurrence** (strengthens `/worker-dispatch` rule-3 lint, extends CR-11):
  a **performance** ticket's pre-dispatch lint must PROFILE THE HOT PATH ON
  REAL-SHAPED DATA (not a synthetic best case) and prove the branch being optimized
  is the one actually taken — "what fraction of the work goes through the code I'm
  speeding up, on the real target?" A synthetic all-dense benchmark that cannot
  exercise the slow branch is not a valid pre-dispatch perf check. Re-runnable
  assertion: `test_evaluate_shifted_ic_churn_panel_under_5s` in
  `tests/test_adapter_kernel_perf.py` — a PIT-churn (480×336) panel must finish in
  < 5s; it FAILS if the slow (churn) path was left as the Python loop, which is
  exactly the class that recurred here. Added in rework-01.
- **polluted-rework**: ticket-13 rework-01 (one worker rework, contract-fault). The
  worker's fast-path delivery `25f6d508` is accepted-and-extended, not discarded.
