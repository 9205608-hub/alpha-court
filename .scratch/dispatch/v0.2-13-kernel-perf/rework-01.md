# Rework 01 — v0.2-13 kernel vectorization: the hot path on real data is the SLOW path

Your fast-path vectorization is **correct and accepted** — `_masked_row_pearson`
is bit-equivalent (referee reproduced: 0.0 diff on a dense battery), the frozen
reference test is right, and it is a genuine 3.7× on all-fast-path panels. **This
is a contract-fault on the commander's side, not yours: the original ticket scoped
the wrong branch.** Here is the finding and the (verified) re-scope.

## The finding (referee-reproduced on real csi300)

On the real csi300 panel (T=480, N=336), **0 of 480 dates hit the fast path — every
date hits the SLOW path** (`_ranks_within_joint` re-rank). Reason: each date's PIT
membership is ~300 of the 336-instrument union, so ~36 finite score/label cells are
excluded from the joint every date → the fast-path condition
(`not np.any(score_finite[s] & ~joint)`) is false on 480/480 dates. Measured:
```
fast-path dates: 0/480 (0.0%)     slow-path dates: 480/480 (100.0%)
mean PIT members/date: 300.0 of 336
current kernel evaluate_shifted(ic, 199 offsets): ~31s   (your fast-path vec unchanged here)
```
So your fast-path vectorization, while correct, does **nothing** for the
power-calibration sweep (or any real PIT-churned universe). The bottleneck is the
per-date re-rank-within-joint + Pearson loop.

## The re-scope: vectorize the SLOW path (masked rank-within-joint)

Extend the SAME approach to the branch that actually runs on csi300: a **vectorized
masked average-rank within the joint**, then your existing `_masked_row_pearson`.
Keep it a single vectorized path per offset (loop only over the ~199 offsets, never
over the 480 dates). The commander prototyped this on real csi300 — **it is
bit-identical to the current kernel (max abs & rel diff = 0.0) and 7.6× faster
(31.3s → 4.1s)**. Pasted construction (verbatim from the verified prototype):

```python
def _masked_avg_ranks(X, M):
    """Average ranks (1..m) of X within row-mask M; matches _ranks_within_joint.
    Vectorized across rows. Non-joint positions get arbitrary values (ignored by
    the masked Pearson). Ties → average rank."""
    R, N = X.shape
    Xf = np.where(M, X, np.inf)                       # masked sort to the end
    order = np.argsort(Xf, axis=1, kind="stable")     # STABLE (mergesort) — tie order fixed
    Xs = np.take_along_axis(Xf, order, axis=1)
    pos = np.broadcast_to(np.arange(N), (R, N))
    same = np.zeros((R, N), bool); same[:, 1:] = Xs[:, 1:] == Xs[:, :-1]
    grp_start = np.maximum.accumulate(np.where(~same, pos, -1), axis=1)
    is_end = np.zeros((R, N), bool); is_end[:, :-1] = Xs[:, 1:] != Xs[:, :-1]; is_end[:, -1] = True
    grp_end = np.minimum.accumulate(np.where(is_end, pos, N)[:, ::-1], axis=1)[:, ::-1]
    ranks_sorted = 0.5 * (grp_start + grp_end) + 1.0  # 1-indexed average ordinal
    ranks = np.empty((R, N)); np.put_along_axis(ranks, order, ranks_sorted, axis=1)
    return ranks

# per offset delta (src = (arange(T) - delta) % T):
#   sc = scores[src]; joint = pit_mask & label_finite & isfinite(sc)
#   rx = _masked_avg_ranks(sc, joint);  ry = _masked_avg_ranks(labels, joint)
#   ic[delta] = _masked_row_pearson(rx, ry, joint)     # your existing helper
#   then min_cross_section check (joint.sum(1) per date) + non-finite→raise, SAME cells/messages
```

Why bit-identical (not just rtol=1e-12): the joint ranks feed the SAME
`_ranks_within_joint` numbers (stable-sort tie order is identical), and the masked
Pearson on the full finite support has no zero-padding reorder in the churn case
(all joint cells are real), so the commander measured 0.0 diff. Keep the
`kind="stable"` (== mergesort tie semantics of `_rankdata_1d`/`_ranks_within_joint`)
— that is load-bearing for tie equivalence.

## Fixes required

1. **[MAJOR, contract-re-scope] Vectorize the slow path** per the construction
   above so `evaluate_shifted(ic, 199 offsets)` on a **PIT-churned** (480, 336)
   panel drops from ~31s to ≤ ~5s. Keep the fast-path vectorization you already
   built (it is free and helps all-dense panels); route each date to whichever, OR
   (simpler and proven) use the unified masked-rank path for ALL dates (the prototype
   used one path for everything and is bit-identical + fast — a single path is
   cleaner and removes the fast/slow branch entirely). Your call; the equivalence +
   perf tests decide.
2. **[MAJOR] The perf test must use a PIT-CHURN panel**, not only the all-dense one.
   Add `test_evaluate_shifted_ic_churn_panel_under_5s`: a (480, 336) synthetic panel
   with a per-date PIT mask that excludes ~10–15% of instruments (mirroring csi300),
   asserting `evaluate_shifted(ic, range(199))` completes in **< 5.0 s** (the
   current kernel is ~31s on such a panel; ≥6× headroom over the expected ~4s). The
   existing all-dense perf test stays.
3. **[required] The equivalence battery must include a PIT-churn panel** (a
   per-date `pit_mask` excluding finite cells) so the frozen-reference test proves
   the slow-path vectorization is bit-identical (`atol=0, rtol=1e-12`) — your current
   battery is fast-path-only and would have passed a broken slow path.
4. **[optional, if free] dense-score speedup**: when `score_finite` is all-True the
   joint is offset-independent (`pit & label_finite`), so `ry` (label ranks) can be
   computed ONCE and reused across all offsets — the power factors are dense, so this
   roughly halves the argsorts. Only if it stays bit-identical and simple.

## Unchanged constraints (from the original ticket, still binding)

- Numeric result frozen: oracle test (`rtol=1e-12`), equivalence invariant
  `evaluate_shifted(S,m,[0]) == evaluate`, determinism — all still pass.
- `kind="stable"`/mergesort tie order preserved (tie equivalence).
- File ownership: ONLY `adapters/qlib_cn.py`, `tests/test_adapter_qlib_cn.py`,
  `tests/test_adapter_kernel_perf.py`. Not court/harness/examples/docs/pyproject.
- `returns` branch: leave as-is (IC is the sweep bottleneck) unless a free win.
- TDD: a red run FIRST for the new churn equivalence + churn perf tests (record the
  non-zero exit in the receipt), then green.
- Act early, write incrementally, keep responses short (a prior dispatch died of
  max_tokens on a long turn-1 block).

## Delivery protocol

Resume in your existing worktree (your fast-path commit `25f6d508` stays; build the
slow-path vectorization on top). Re-run the AC — reduced adapter+perf tests without
qlib, full `python3 -m pytest`, `ruff check .`, and record the measured
`evaluate_shifted(199)` on BOTH the dense and the churn panel. Note the full-suite
matplotlib failures are the pre-existing `[demo]`-extra gap (not yours) — run
`pip install -e ".[dev,demo]"` if you want them green, or `--ignore=tests/test_killer_demo.py`
and say so. Final output = ONLY the JSON receipt.
