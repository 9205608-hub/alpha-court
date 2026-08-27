# Rework: v0.1-10a — referee findings on adapters/qlib_cn.py

Adversarial review verdict: one BLOCKER, two majors, four minors. Much passed
cleanly (equivalence invariant array_equal incl. correct roll direction;
oracle on dense panels 2.8e-17; L-S path; §5.3 guard from both entry points;
zero RNG; kernels=1; SH600519 spot-check on the real pack) — the rework is
surgical. Modify ONLY your owned files (adapters/qlib_cn.py,
adapters/__init__.py, tests/test_adapter_qlib_cn.py), commit with message
`v0.1-10a: address referee findings`, and end with ONLY the JSON receipt
(ticket_id `v0.1-10a`, fresh commit hash).

NOTE: the contract in YOUR worktree is stale on two points; the amended text
below is authoritative.

## BLOCKER

1. IC ranking convention (`_rank_panel` + `_shared_kernel` IC path): ranks are
   precomputed on each series' own finite support and Pearson-correlated on
   the joint (PIT ∧ score-finite ∧ label-finite) subset. The contract's
   semantic oracle (qlib `calc_ic` ric, §4.1; pairwise exclusion §5.3) ranks
   WITHIN the joint subset. Referee measurements: single-date probe deviation
   up to 2.3e-2; realistic panels (dense scores × NaN labels) max 8.6e-4 to
   4.7e-3 with 71–100% of dates beyond the 1e-12 oracle tolerance; the
   PIT-membership mask alone makes it fire on 100% of dates even with dense
   labels — so on the real demo window essentially every IC value deviates
   from the declared RankIC. The disclosure ("sparse-NaN") did not cover the
   PIT-mask effect, and the shipped oracle tests are dense-only, so CI is
   green while production semantics are wrong.
   FIX: re-rank within the per-date joint mask wherever that mask excludes
   any finite-scored cell; dense/no-exclusion dates may keep the precomputed
   fast path (bit-for-bit unchanged there). Note the per-date label/PIT mask
   is offset-INDEPENDENT (labels and PIT never shift), so masked re-ranking
   remains vectorizable across offsets; the grid budget (seconds-to-minutes
   per candidate, §7.3 note) still stands — re-measure and report the
   benchmark in your receipt.
   TESTS: extend the oracle battery with NaN-bearing labels AND PIT churn
   (both must match calc_ic ric to rtol ≤ 1e-12 per §7.5.1); keep the dense
   cases.

## MAJOR

2. Meta completeness — contract §7.1 has been clarified (2026-07-11),
   verbatim: config fields are "ALL of them recorded verbatim into
   EvalResult.meta ... a meta.config sub-object carrying every constructor
   field including provider_uri, min_cross_section, and quantile regardless
   of metric, in addition to the named §7.4 keys". Today provider_uri and
   min_cross_section are never recorded and quantile is dropped for
   metric="ic". Add meta.config; extend the meta test to assert every
   constructor field round-trips.
3. Missing §8 layer-2 determinism test (golden fingerprint): a fixed
   synthetic factor over the demo window against the pinned tag, asserting
   stored first/last-five RankIC values at full float64 repr plus a
   whole-series hash, `pytest.mark.skipif` when the pack is absent. The
   §6 tag-bump procedure depends on this test existing. (Data is present on
   this machine — generate the golden values, run it live once, and paste the
   values into the test.)

## MINOR

4. `_normalize_config` coercions violate the no-repair rule (also now
   explicit in §7.1): `min_cross_section=49.9` silently truncates to 49;
   string quantile accepted; int universe str()'d. Replace with strict type
   validation that raises. Add raising tests.
5. `_validate_offsets`: contract erratum (2026-07-11) now reads "validates
   0 ≤ δ < T ... an empty offsets list raises". Your δ=0 choice is thereby
   ratified — update the comment to cite the erratum; make empty list raise;
   delete the dead `if not offsets and offsets != []` branch.
6. Lines ~311–328: the comment claims an end-time extension the code does not
   perform — fix the comment (the code is right; §5.2 guarantees t+2 ≤ end);
   collapse the two identical if/else branches.
7. `_align_scores` silently ignores score rows outside the evaluation-date
   set — this is the contract's definition (only missing rows raise) but must
   be DOCUMENTED in the evaluate docstring, not silent.

## Delivery protocol

Full suite + ruff; real exit codes in receipt; `git status --porcelain`
empty after commit; write files incrementally (max_tokens discipline);
final output = ONLY the JSON receipt.
