# Rework: v0.1-05 — referee findings on docs/research/pbo-cscv.md

Your delivery passed adversarial review with NO blockers and NO majors — the
S=4 test vector and all λ computations recomputed correctly, and your catch of
the paper's binom(16,8) typo was verified. The items below are minor precision
fixes that matter because the implementation ticket will treat this note as
ground truth. Modify ONLY `docs/research/pbo-cscv.md`, commit with message
`v0.1-05: address referee findings`, and end with ONLY the JSON receipt
(ticket_id `v0.1-05`, fresh commit hash).

## Fixes (all minor)

1. §3.5 "Boundary λ_c = 0" (and the §3.1 parenthetical "sitting exactly at
   the median is not counted"): your claim that the strict λ_c < 0 rule
   "matches both the strict definition and the discrete fraction formula"
   overstates the equivalence. Since ω̄ = r̄/(N+1), λ_c < 0 ⟺ r̄_{n*} < (N+1)/2,
   while the paper's Def./Eq. (2.2) literally prints the threshold r̄_n < N/2.
   These diverge for even N at r̄ = N/2 (e.g. N=4, r̄=2: λ = ln(2/3) < 0 counts
   as overfitting under the λ rule, but 2 < 2 is false under a literal
   Eq. (2.2)). This is the paper's own internal inconsistency (the true median
   of ranks {1..N} is (N+1)/2, the value implied by Alg. 2.3(f)'s N+1
   denominator). Keep your operational rule (count λ_c < 0 only — correct for
   the estimator φ = ∫_{−∞}^0 f(λ)dλ) but state the N/2 vs (N+1)/2 mismatch
   explicitly instead of saying the conventions "match", and stop calling N/2
   "the median" in §3.1.
2. §3.4(c) / §3.7 pseudocode: you silently corrected a typo in the paper —
   Alg. 2.3 step c) literally reads "the performance associated with the nth
   column of J (the testing set)" although J is defined in step a) as the
   training set (and the same sentence says "IS ranking"). Your rendering
   (R^c on J = IS/training) is the correct intent, but flag this paper typo
   explicitly, exactly like you flagged the binom(16,8)=12,780 typo —
   otherwise a line-by-line checker reading the paper's step (c) literally
   will think the note swapped IS and OOS.
3. §1 Sources edition note: it says equation numbers follow "Eq. (2.2)–(2.4)"
   of the Feb 2015 PDF, but the doc also cites Eq. (2.1) (Def. 2.1) in §3.1
   and Appendix A. Widen the stated range.

## Delivery protocol

Same as the original ticket: work only in your worktree; run
`git status --porcelain` (must be empty after commit) and
`git log --oneline -1`; final output = ONLY the JSON receipt.
