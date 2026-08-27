# Rework: v0.1-08d — referee rulings on court/tstats.py + court/fdr.py

Adversarial review outcome, and it is an unusual one: your BY adjusted-p base
case `min(1, c(N)·P_(N))` was flagged as deviating from bhy.md §3.2's printed
recurrence — and the referee panel then PROVED the printed recurrence (a
faithful transcription of the HLZ 2016 §3.4.3 display) is internally
inconsistent, while your convention is the unique self-consistent one and
matches R `p.adjust("BY")` / statsmodels. k*, rejection sets, and c_factor
showed 0 mismatches in 480 fuzz runs. **Your implementation's behavior
stands.** bhy.md §3.2 now carries a referee erratum and spec ruling E6 has
been amended to pin YOUR base case. What must change is the paperwork plus
four minors. Modify ONLY your four owned files (court/tstats.py, court/fdr.py,
tests/test_tstats.py, tests/test_fdr.py), commit with message
`v0.1-08d: address referee findings`, and end with ONLY the JSON receipt
(ticket_id `v0.1-08d`, fresh commit hash).

NOTE: bhy.md and the spec in YOUR worktree are stale; the amended text quoted
below is authoritative and overrides your local copies.

## Required changes

1. `court/fdr.py` (~lines 166-176): the inline comment mis-cites bhy.md
   §2.4/§3.2 as supporting your base case — as of your worktree's copy they
   did NOT (they printed the HLZ init `p_(m) = P_(m)`). Rewrite the comment to
   cite the new ruling, e.g.: "BY base case = min(1, c(N)·P_(N)) per the
   referee erratum in bhy.md §3.2 and amended spec ruling E6 (2026-07-10):
   the HLZ-printed init P_(N) violates the identity adjusted_p ≤ q ⟺ reject
   (counterexample p=(0.04,0.04), q=0.05, c(2)=1.5: k*=0 but doc-literal
   adjusted values claim two rejections); this convention = R p.adjust('BY') /
   statsmodels fdr_by."
2. `court/tstats.py` line ~10 (module docstring): pinpoints are wrong — §3.4.3
   is the BY adjustment (an fdr.py concern). Cite HLZ §3.4 opening / §3.5
   footnote 26 and bhy.md §4.1–§4.3 instead.
3. `court/fdr.py` (~lines 194-195, `_as_p_vector`): a 0-d scalar input is
   silently reshaped to a 1-element vector (`fdr_bh(0.03, 0.05)` runs as
   N=1). Spec §3.5 forbids coercion — raise ValueError on ndim == 0 instead,
   with a raising test.
4. tests/test_fdr.py (~line 106): the monotonicity assertion carries a 1e-15
   slack although the backward-min recurrence guarantees exact non-decreasing
   order in IEEE-754. Drop the slack (strict `>=`).
5. `court/fdr.py` (~line 130) + FdrResult docstring: empty BY input returns
   c_factor=1.0, which a caller could misread as a BH result. Keep the value
   but DOCUMENT the N=0 sentinel explicitly in the fdr_by docstring and the
   FdrResult field comment.
6. tests/test_tstats.py: the iid hand-vector pin has been re-pinned by referee
   ruling (spec §5.4): the original spec pinned se = 0.5773502691896258 AND
   t = 3.4641016151377544 simultaneously, which is unsatisfiable by exactly
   1 ulp. The authoritative pin is now the float64 PIPELINE value:
   t == 3.464101615137754 (i.e. 2.0/0.5773502691896258). Assert it with
   exact `==` (your implementation already produces exactly this value).

## Delivery protocol

Run your full suite + ruff; record real exit codes; `git status --porcelain`
must be empty after the commit; final output = ONLY the JSON receipt.
