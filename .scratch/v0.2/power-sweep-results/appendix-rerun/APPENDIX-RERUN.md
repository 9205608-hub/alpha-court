# β_t appendix re-run (quarantine lift) — 2026-07-19 20:53 → 2026-07-20 18:20

Re-run of the FULL appendix (2 targets × 4 arms × R=40 = 320 arms, 21.5h, head
`8a1aff08`) after rework-02 (`a51f66e4`) closed the three quarantined defects.
The original run's appendix (see `../report.md` §Appendix and the quarantine
record in the 05 issue) remains committed as history; **its numbers are
superseded by this directory**. The hero main sweep was never affected.

## Why the original appendix was quarantined

1. t3.0 had no frozen β* key → silent fallback β=0.15 → realized ICIR 39 (target
   3): row uninformative. 2. `solve_matched_beta` grid floor 0.05 clamped the
   matched arms (realized 5.63/5.73 vs constant 3.79): "matched" wasn't matched.

## Re-run health (all acceptance checks pass)

- Fail-closed validation active: both targets resolve from the re-frozen
  calibration (14 original keys bit-identical; new 3.0 → β*=0.014609).
- Matched solutions strictly interior: β = 0.0338 / 0.0340 (ref 4.0),
  0.0271 / 0.0261 (ref 3.0) — no boundary values.
- Matched quality: realized full-sample ICIR within 0.4–3.7% of the constant
  arm's realized (tolerance 20%).
- t3.0 constant row informative again: unanimous TPR 0.405 — consistent with the
  hero curve's A at strengths 2.9 (0.421) / 3.2 (0.500), an independent
  cross-check between appendix and main sweep.

## Result (the one number the appendix answers)

| ref ICIR | unan const | unan matched | unan drop | pbo const | pbo matched | pbo drop |
|---:|---:|---:|---:|---:|---:|---:|
| 4.00 | 0.800 | 0.850 | **−0.050** | 0.875 | 0.900 | **−0.025** |
| 3.00 | 0.405 | 0.436 | **−0.030** | 0.649 | 0.616 | **+0.032** |

All |drop| ≤ 0.05 = ≤2 seeds at R=40, inside binomial noise (Wilson half-width
at these rates ≈ 0.12–0.14). **No unanimous/PBO TPR drop was detected at R=40
under matched full-sample ICIR on half-window episodic (β_t) signals.** Stated
at the honest resolution: this is *non-detection at R=40*, not proof of absence —
a true drop smaller than ~0.12 would be invisible here (wording tightened
2026-07-20 on the role-reversal review's objection). The secondary same-nominal arms (unan 0.111 / 0.000) show the
labeled confound (less total signal), which is exactly why matched is primary.

Scope honesty: same claim scope as the main sweep (constructed oracle,
discrimination not discovery, no costs/capacity/regime realism); random-block
sensitivity remains a declared real-data hook, not run here.
