# Rework: v0.1-08b — referee findings on court/sharpe.py + court/dsr.py

Your delivery passed adversarial review with NO blockers — all document hand
vectors reproduce to 1e-9 and 200-case fuzzing against an independent
reference found no mismatches. The items below are two majors and three
minors. Modify ONLY your four owned files (court/sharpe.py, court/dsr.py,
tests/test_sharpe.py, tests/test_dsr.py), commit with message
`v0.1-08b: address referee findings`, and end with ONLY the JSON receipt
(ticket_id `v0.1-08b`, fresh commit hash).

NOTE: the spec in YOUR worktree is stale on two points; the amended ruling
text is quoted verbatim below and overrides your local copy.

## MAJOR

1. `court/dsr.py` (expected_max_sr, ~lines 178-180): you build right-tail
   quantiles as `norm.ppf(1.0 - 1.0/n)` and `norm.ppf(1.0 - 1.0/(n*e))` — the
   exact low-precision construction dsr.md §5.5 says to avoid, while the
   inline comment CLAIMS the complementary-tail mitigation is applied. Swap to
   `scipy.stats.norm.isf(1.0/n)` and `norm.isf(1.0/(n*np.e))` and fix the
   comment. Referee-measured evidence: at N=1e9, ppf(1-1/N)=5.997807019601637
   vs isf(1/N)=5.9978070150076865 (diff ~4.6e-9); from N≈4e15 the ppf form
   returns +inf. Add a regression test at large N (e.g. isf-based value finite
   and matches norm.isf to 1e-12 at N=1e9; expected_max_sr finite at N=1e16).
2. Non-finite scalar arguments slip past every guard and propagate NaN
   silently: psr(0.5, 0.0, 24, nan, 3.0) → nan; sr_standard_error(...,
   nan) → nan; dsr(1.0, 24, nan, ...) → DsrResult(dsr=nan, ...);
   expected_max_sr(0.0, nan, 10.0) → nan. Comparisons like `vf <= 0`,
   `std < 0`, `n < 1` are False for NaN. New spec ruling (verbatim, now in
   spec §6): "every scalar float parameter of every public function must be
   finite; a non-finite scalar (NaN/±inf) raises ValueError at entry. Range
   guards written as plain comparisons are False for NaN and therefore do NOT
   satisfy this rule on their own." Add explicit finiteness checks on all
   public-function scalar params in both modules + one raising test per
   function (parametrized is fine).

## MINOR

3. tests/test_sharpe.py (~lines 37, 62, 81): the documents pin EXACT equality
   for rational variance-factor anchors (dsr.md §4.1 writes
   `sr_var_factor == 1.125`; spec §7 pins `== 1.125`, `== 1.4375`, and the
   Normal identity). Your tests weaken these to pytest.approx(abs=1e-9).
   Referee verified exact equality actually holds — tighten those specific
   assertions to `==` (keep approx for the non-pinned z/psr/dsr values).
4. `court/dsr.py` (~lines 216-217): DsrResult.z is re-derived locally while
   dsr comes from a separate psr() call that re-derives z internally — two
   copies of the same computation that can desynchronize. Refactor so both
   reported values come from one shared computation.
5. Docstring/comment sweep: make sure no comment claims a mitigation or
   convention the code does not implement (the line-178 comment was the one
   confirmed offender).

## Delivery protocol

Run your full suite + ruff; record real exit codes; `git status --porcelain`
must be empty after the commit; final output = ONLY the JSON receipt.
