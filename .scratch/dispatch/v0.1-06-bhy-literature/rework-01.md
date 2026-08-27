# Rework: v0.1-06 — referee findings on docs/research/bhy.md

Your delivery was reviewed by an adversarial referee panel (numeric recompute
+ formula/citation verification against the published PDFs + ticket-acceptance
check). The numeric content all recomputed correctly. The delivery is REJECTED
pending the fixes below. Modify ONLY `docs/research/bhy.md`, commit with
message `v0.1-06: address referee findings`, and end with ONLY the JSON
receipt (ticket_id `v0.1-06`, fresh commit hash).

## BLOCKER (hard-constraint violation)

1. §6.6 "Minimal machine-check payload" contains a fenced block of executable
   Python (`c10 = sum(1/i for i in range(1, 11))`, a `p_raw = {...}` dict
   literal). The ticket's hard constraint is "NO code — markdown document
   only", and the doc's own header declares "No code in this note". Fix:
   delete the block (the same numbers already appear in §6.3–6.5) or restate
   it as a markdown table / plain-text list. No fenced code of any language
   may remain.

## MAJOR (systematic citation mismatch)

2. Every Harvey-Liu-Zhu pinpoint uses the NBER working-paper numbering, but
   the bibliography cites the published RFS edition (RFS 29(1), 2016,
   doi:10.1093/rfs/hhv059). The referee verified against the published PDF.
   Convert ALL HLZ pinpoints to the published numbering:
   - FDP/FDR definitions: §3.3.2 "False discovery rate" (journal p.14) — NOT §4.1
   - Bonferroni / Holm / BHY adjustments: §3.4.1 / §3.4.2 / §3.4.3
     (BHY heading "Benjamini, Hochberg, and Yekutieli's adjustment", journal
     p.20) — NOT §4.4.1–4.4.3
   - Two-sided t-test quote: footnote 26 in §3.5 ("We usually calculate
     p-values based on two-sided t-tests") — NOT "note 31" in §4.5
   - BY-proof footnote: footnote 24 ("See Benjamini and Yekutieli (2001) for
     the proof") — NOT "notes 28–29"
   - Hidden tests / M>R discussion: §3.7.2
   You may add one sentence noting that the RFS typesetting itself retains
   some working-paper cross-references (it prints "Example 4.4.1" etc. inside
   the 3.x-numbered sections), so text-searching either numbering finds the
   material — but our pinpoints follow the published headings.

## MINOR

3. §3.1 presents as a direct quote: "the procedure works under arbitrary
   dependence structure among the p-values". The published text reads "allows
   the procedure to work under arbitrary dependency among the test statistics"
   (§3.4.3, journal pp.20–21). Quote verbatim or drop the quotation marks.
4. §2.2 anchors "step-up (not step-down)" terminology to BH 1995 §3.1–3.3,
   but BH 1995 itself (p.294) calls its procedure a "step-down" procedure —
   pre-2001 terminology, opposite of the modern convention. Re-anchor the
   terminology claim to BY 2001 (which uses "step-up" throughout, e.g.
   "general step-up procedures", p.1169) or HLZ footnote 23; keep the
   operational description (it is correct).
5. §6.5 "The gap is exactly the harmonic penalty c(10) ≈ 2.929": wrong
   object. What equals c(10) exactly is the ratio of BH to BY critical
   thresholds τ_BH,i / τ_BY,i for every i; the rejection-count gap (9 vs 3,
   ratio 3.0) is not "exactly" c(10). Reword.
6. §7.3 "(N/i)·p_(i) ... can overflow to +∞ for tiny p and large N": wrong —
   with p ≤ 1 these products cannot overflow float64 for any realistic N. The
   real tiny-p hazards are underflow/subnormal precision loss, and clipping
   adjusted values at 1. Reword.
7. §6.1 cumulative column claims float64-match but mixes exact-rational
   roundings with float64 reprs (rows 4–8). Either state the convention as
   "exact rational rounded to 16 digits" or print the float64 ascending-sum
   reprs consistently (2.4499999999999997, 2.5928571428571425,
   2.7178571428571425; H4 float64 repr 2.083333333333333). The final
   c(10)=2.9289682539682538 is correct either way.

## Delivery protocol

Same as the original ticket: work only in your worktree; run
`git status --porcelain` (must be empty after commit) and
`git log --oneline -1`; final output = ONLY the JSON receipt.
