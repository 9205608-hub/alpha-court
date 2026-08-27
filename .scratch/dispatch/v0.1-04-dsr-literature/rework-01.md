# Rework: v0.1-04 — referee findings on docs/research/dsr.md

Your delivery passed adversarial review with NO blockers and NO majors — every
numeric test vector recomputed correctly. The items below are minor precision
fixes that matter because implementation tickets will treat this note as
ground truth. Modify ONLY `docs/research/dsr.md`, commit with message
`v0.1-04: address referee findings`, and end with ONLY the JSON receipt
(ticket_id `v0.1-04`, fresh commit hash).

## Fixes (all minor)

1. §2.a / PSR-DSR denominators: you present the Mertens variance as
   `1 − γ₃SR + (γ₄−1)/4·SR²` attributed to 2012 Eq. (8). The printed Eq. (8)
   is the expanded form `1 + ½SR² − γ₃SR + (γ₄−3)/4·SR²`; the collapsed form
   first appears in the paper's §2.5 σ̂_SR and Eq. (11). They are algebraically
   identical (½ + (γ₄−3)/4 = (γ₄−1)/4) — state this collapse explicitly with
   both citations so a line-by-line reviewer isn't surprised.
2. §2.c and §2.d: the 2014 paper writes Eq. (1) with `≈` conditioned on
   `N ≫ 1` ("after N ≫ 1 independent trials can be approximated as"); your
   display uses `=` and never states the approximation condition. Add the ≈
   and an explicit note that this is an EVT approximation whose small-N error
   the paper only addresses via App. A.2 Monte Carlo — important since your
   own test vector uses N=10 and §5.5 contemplates N as low as 2.
3. §2.c/§2.d benchmark symbol: the 2014 paper names the DSR benchmark SR̂₀
   (Eq. (2): "DSR ≡ PSR(SR₀)"); you renamed it SR̂* (the 2012 paper's PSR
   benchmark symbol) without declaring it. Add one line declaring the
   renaming (or switch to SR̂₀).
4. §5.3 third bullet: you write "when M > T the correlation matrix is
   ill-conditioned". The paper (App. A.3) gives the ill-conditioning
   condition as T < ½M(M−1) — strictly weaker, can hold even when T > M.
   Restate with the paper's condition (your claim is a special case).
5. §3 code-mapping tables: several "runtime source" cells contain
   Python-syntax expressions (e.g. `norm.cdf((sr_hat - sr_star) * ...)`).
   Rephrase these cells as math/prose (e.g. "Φ((SR̂ − SR̂₀)·√(T−1)/σ̂_SR)") to
   stay clearly on the no-code side of the ticket's constraint.
6. §2.b second displayed equation ("Equivalently, with the standard-error
   form..."): give this display its own bracketed citation (2012 Eq. (11) /
   §2.5) instead of relying on the preceding prose.

## Delivery protocol

Same as the original ticket: work only in your worktree; run
`git status --porcelain` (must be empty after commit) and
`git log --oneline -1`; final output = ONLY the JSON receipt.
