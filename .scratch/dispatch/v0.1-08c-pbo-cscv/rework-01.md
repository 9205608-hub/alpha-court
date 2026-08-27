# Rework: v0.1-08c — referee findings on court/pbo.py

Your delivery passed adversarial review with NO blockers — the recompute lens
(independent reference + fuzz) found zero numeric mismatches, including the
full S=4 fixture. One major (a guard gap that needed a ruling — now ruled) and
one minor. Modify ONLY court/pbo.py and tests/test_pbo.py, commit with message
`v0.1-08c: address referee findings`, and end with ONLY the JSON receipt
(ticket_id `v0.1-08c`, fresh commit hash).

NOTE: the spec in YOUR worktree is stale on this point; the amended ruling
text below is authoritative and overrides your local copy.

## MAJOR

1. Missing structural guard: ruling D5 has been amended (referee ruling
   2026-07-10) to read, verbatim: "Structural guards: S even and ≥2;
   T % S == 0; **T ≥ 2S** (each block ≥ 2 rows; also excludes T = 0 and
   T = S — an empty matrix must never yield the candidate-favorable φ = 0.0
   silently); N ≥ 2 (N=1 is vacuous → raise)". Your code follows the OLD
   narrower D5, so today `pbo_cscv(np.empty((0, 2)), 2, lambda c: 0.0)`
   returns φ=0.0 with no raise — zero rows of evidence producing the most
   candidate-favorable verdict — and T=S (block length 1) is likewise
   accepted. Add the `T >= 2*S` guard (raising ValueError) + raising tests
   for T=0, T=S, and T just under 2S.

## MINOR

2. tests/test_pbo.py (~lines 45-46): the fixture test asserts all six logits
   via pytest.approx(abs=1e-12), but three of them are the pinned rational
   anchor λ = 0.0 and φ = 0.5 is a pinned fraction — spec §7 reserves exact
   `==` for pinned conventions, and the referee verified bit-exact 0.0 and
   bit-exact math.log(1/3) are actually produced. Tighten the pinned
   positions to `==` (approx is fine for the unpinned log values only if you
   prefer, but they are exactly log(1/3)/log(3) — exact equality holds).

## Delivery protocol

Run your full suite + ruff; record real exit codes; `git status --porcelain`
must be empty after the commit; final output = ONLY the JSON receipt.
