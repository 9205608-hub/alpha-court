# Power calibration — court ROC on a known signal

## First-screen honesty (mandatory)

UNCERTIFIED calibration experiment (direct court, not harness.run). Constructed oracle ≠ discoverable alpha: the injected factor peeks at the forward return by construction (power-calibration.md §1). This measures discrimination (TPR for approximately-stationary mean-IC signals), not discovery. No costs, no capacity, no regime realism.

Axis unit: project-annualized ICIR = ICIR_daily · √252 ≈ ICIR_daily × 16. Industry 'ICIR ≈ 0.3–0.8' is usually the daily non-annualized ratio → project annualized ≈ 5–13.

Cost declaration: gross paper series — no transaction costs, no market impact. Aggregation: unanimous-over-discriminating (`harness.aggregation_policy`, policy_id=unanimous-discriminating-v1).

Caption: **A** is the court ROC *given the signal already won naive directed selection* (`argmax t`); **B = P(win)** is plotted beside it. A alone is optimistic (conditions on stronger realizations).

## Hero: power curve data (A) and natural win rate (B)

| target ICIR | β* | n | n_won | A=P(pass|won) | Wilson A | B=P(win) R₀ | submission | underpowered |
|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 0.00 | 0.0000 | 40 | 0 | nan | [nan, nan] | 0.000 | 0.000 | no |
| 0.50 | 0.0047 | 40 | 2 | 0.000 | [0.000, 0.658] | 0.050 | 0.000 | yes |
| 1.00 | 0.0067 | 40 | 10 | 0.000 | [0.000, 0.278] | 0.250 | 0.000 | yes |
| 1.50 | 0.0087 | 40 | 14 | 0.000 | [0.000, 0.215] | 0.350 | 0.000 | yes |
| 2.00 | 0.0107 | 40 | 22 | 0.136 | [0.047, 0.333] | 0.550 | 0.075 | no |
| 2.30 | 0.0119 | 40 | 29 | 0.172 | [0.076, 0.345] | 0.725 | 0.125 | no |
| 2.60 | 0.0130 | 40 | 35 | 0.343 | [0.208, 0.508] | 0.875 | 0.300 | no |
| 2.90 | 0.0142 | 40 | 38 | 0.421 | [0.279, 0.578] | 0.950 | 0.400 | no |
| 3.20 | 0.0154 | 40 | 38 | 0.500 | [0.348, 0.652] | 0.950 | 0.475 | no |
| 3.60 | 0.0169 | 40 | 40 | 0.750 | [0.598, 0.858] | 1.000 | 0.750 | no |
| 4.00 | 0.0185 | 40 | 40 | 0.875 | [0.739, 0.945] | 1.000 | 0.875 | no |
| 4.50 | 0.0204 | 40 | 40 | 0.975 | [0.871, 0.996] | 1.000 | 0.975 | no |
| 5.00 | 0.0224 | 40 | 40 | 1.000 | [0.912, 1.000] | 1.000 | 1.000 | no |
| 6.00 | 0.0262 | 40 | 40 | 1.000 | [0.912, 1.000] | 1.000 | 1.000 | no |

Under-powered strengths (n_won small) show wide Wilson CIs and are flagged; never smoothed or extrapolated (power-calibration.md §6).

## Directional size (β=0, same greater-battery)

This is a re-run of **this** greater-battery at zero signal, labeled *directional size*. It is **not** the killer demo's two-sided size (different battery form: DSR votes here, PBO is signed, p one-sided).

Estimand: **unconditional champion** per-gate pass rate over all R₀ seeds (amended §6, 2026-07-17). One directed-scan champion exists every seed; size-type gates (FDR / pool-max / individual) should sit near nominal α on this estimand. PBO is excluded from the ≈α assertion (φ≤0.2 is a rule threshold, not a size guarantee). Hero-curve β=0 point stays `P(unanimous | won)` — a different estimand with wide CI when n_won is small; never conflated with the size panel.

size_panel_n_seeds=40 size_panel_champion_unanimous=0.000 Wilson [0.000, 0.088]
- n_seeds=40, n_won(injected)=0, n_champion_samples=40
- hero A (unanimous|won, informational at β=0)=nan Wilson [nan, nan]
- B (P(injected wins))=0.000
- champion_gate_tpr: {'dsr': 0.0, 'fdr_by': 0.0, 'noise_individual': 0.825, 'noise_pool_max': 0.05, 'pbo_cscv': 0.05}

## Per-gate TPR among won (default panel)

| target ICIR | dsr | fdr_by | noise_individual | noise_pool_max | pbo_cscv |
|---:|---:|---:|---:|---:|---:|
| 0.00 | — | — | — | — | — |
| 0.50 | 0.000 | 0.000 | 0.500 | 0.000 | 0.500 |
| 1.00 | 0.000 | 0.000 | 0.900 | 0.000 | 0.100 |
| 1.50 | 0.000 | 0.143 | 1.000 | 0.429 | 0.143 |
| 2.00 | 0.136 | 0.409 | 0.955 | 0.500 | 0.364 |
| 2.30 | 0.172 | 0.379 | 0.966 | 0.621 | 0.448 |
| 2.60 | 0.343 | 0.486 | 1.000 | 0.743 | 0.457 |
| 2.90 | 0.421 | 0.632 | 1.000 | 0.895 | 0.632 |
| 3.20 | 0.500 | 0.868 | 1.000 | 0.921 | 0.789 |
| 3.60 | 0.750 | 0.875 | 1.000 | 0.950 | 0.925 |
| 4.00 | 0.875 | 0.975 | 1.000 | 0.975 | 0.975 |
| 4.50 | 0.975 | 1.000 | 1.000 | 1.000 | 1.000 |
| 5.00 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 6.00 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Submission power (secondary; never overlaid on A)

P(unanimous pass | injected forced as the judged candidate). DSR is conservative off-champion (power-calibration.md §5 / §9). **Gate set (FIX 4):** fdr_by, dsr, pbo_cscv, noise_individual — pool_max is **excluded** from the submission unanimous denominator because pool_max has no force knob (it always judges the argmax champion; a forced non-champion never appears in its decisions).

| target ICIR | β* | P(pass) | Wilson |
|---:|---:|---:|---:|
| 0.00 | 0.0000 | 0.000 | [0.000, 0.088] |
| 0.50 | 0.0047 | 0.000 | [0.000, 0.088] |
| 1.00 | 0.0067 | 0.000 | [0.000, 0.088] |
| 1.50 | 0.0087 | 0.000 | [0.000, 0.088] |
| 2.00 | 0.0107 | 0.075 | [0.026, 0.199] |
| 2.30 | 0.0119 | 0.125 | [0.055, 0.261] |
| 2.60 | 0.0130 | 0.300 | [0.181, 0.454] |
| 2.90 | 0.0142 | 0.400 | [0.263, 0.554] |
| 3.20 | 0.0154 | 0.475 | [0.329, 0.625] |
| 3.60 | 0.0169 | 0.750 | [0.598, 0.858] |
| 4.00 | 0.0185 | 0.875 | [0.739, 0.945] |
| 4.50 | 0.0204 | 0.975 | [0.871, 0.996] |
| 5.00 | 0.0224 | 1.000 | [0.912, 1.000] |
| 6.00 | 0.0262 | 1.000 | [0.912, 1.000] |

## Calibration decomposition (§4.2 / §7)

Shell φ (median of 100 demo shells) = **0.970000**

Calibration seeds: SeedSequence(320260711).spawn(64)

| β | E[IC] | ICvol | mean annualized ICIR | SE(mean ICIR) |
|---:|---:|---:|---:|---:|
| 0.00 | 0.00012 | 0.05777 | 0.0370 | 0.0924 |
| 0.00 | 0.00124 | 0.05777 | 0.3471 | 0.0927 |
| 0.01 | 0.00296 | 0.05777 | 0.8186 | 0.0933 |
| 0.01 | 0.00476 | 0.05776 | 1.3156 | 0.0938 |
| 0.01 | 0.00660 | 0.05777 | 1.8205 | 0.0944 |
| 0.01 | 0.00845 | 0.05776 | 2.3312 | 0.0951 |
| 0.01 | 0.01031 | 0.05776 | 2.8438 | 0.0959 |
| 0.02 | 0.01218 | 0.05776 | 3.3572 | 0.0967 |
| 0.02 | 0.01404 | 0.05775 | 3.8717 | 0.0976 |
| 0.02 | 0.01591 | 0.05775 | 4.3865 | 0.0987 |
| 0.02 | 0.01779 | 0.05774 | 4.9028 | 0.0998 |
| 0.02 | 0.01966 | 0.05774 | 5.4188 | 0.1009 |
| 0.03 | 0.02153 | 0.05773 | 5.9359 | 0.1021 |
| 0.03 | 0.02340 | 0.05773 | 6.4509 | 0.1034 |
| 0.03 | 0.02528 | 0.05772 | 6.9686 | 0.1047 |

### Frozen β* table (axis = target ICIR; never overwritten by realized)

| target ICIR | β* |
|---:|---:|
| 0.00 | 0.000000 |
| 0.50 | 0.004714 |
| 1.00 | 0.006739 |
| 1.50 | 0.008734 |
| 2.00 | 0.010705 |
| 2.30 | 0.011878 |
| 2.60 | 0.013049 |
| 2.90 | 0.014219 |
| 3.20 | 0.015388 |
| 3.60 | 0.016944 |
| 4.00 | 0.018499 |
| 4.50 | 0.020440 |
| 5.00 | 0.022377 |
| 6.00 | 0.026249 |

## Appendix: β_t regime-switch (PBO-optimism corrector)

Primary contrast = **matched realized ICIR** half-window (forward-off / backward-off); secondary = same-nominal-β; sensitivity = random-block (honestly scoped). Answers: points unanimous/PBO-TPR drops constant → matched episodic (power-calibration.md §7). Greater battery via court.judge + harness.aggregation_policy (same path as the main sweep).

### TPR drops (constant → mean matched episodic)

| ref ICIR | unan_const | unan_matched | **unan_drop** | pbo_const | pbo_matched | **pbo_drop** |
|---:|---:|---:|---:|---:|---:|---:|
| 4.00 | 0.800 | 1.000 | **-0.200** | 0.875 | 1.000 | **-0.125** |
| 3.00 | 1.000 | 1.000 | **0.000** | 1.000 | 1.000 | **0.000** |

**Headline drop (ref ICIR=4.00):** unanimous TPR drops by -0.200 points; PBO TPR drops by -0.125 points (constant → matched episodic).

| arm | ref ICIR | β used | realized ICIR | n_seeds | unan_tpr | pbo_tpr | note |
|---|---:|---:|---:|---:|---:|---:|---|
| constant | 4.00 | 0.0185 | 3.7900 | 40 | 0.800 | 0.875 | constant daily edge; greater-battery TPR |
| forward_off_matched | 4.00 | 0.0500 | 5.6284 | 40 | 1.000 | 1.000 | primary: matched full-sample ICIR; greater-battery TPR |
| backward_off_matched | 4.00 | 0.0500 | 5.7257 | 40 | 1.000 | 1.000 | primary: matched full-sample ICIR; greater-battery TPR |
| same_nominal_forward | 4.00 | 0.0185 | 1.9799 | 40 | 0.111 | 0.259 | secondary: same-nominal-β (confounds strength with episodicity) |
| constant | 3.00 | 0.1500 | 39.0121 | 40 | 1.000 | 1.000 | constant daily edge; greater-battery TPR |
| forward_off_matched | 3.00 | 0.0500 | 5.6883 | 40 | 1.000 | 1.000 | primary: matched full-sample ICIR; greater-battery TPR |
| backward_off_matched | 3.00 | 0.0500 | 5.7257 | 40 | 1.000 | 1.000 | primary: matched full-sample ICIR; greater-battery TPR |
| same_nominal_forward | 3.00 | 0.1500 | 12.1009 | 40 | 1.000 | 1.000 | secondary: same-nominal-β (confounds strength with episodicity) |

battery_ran=True. Primary arms (`*_matched`) solve β so full-sample ICIR matches the constant-β reference; secondary `same_nominal_*` confounds strength with episodicity. Random-block sensitivity remains a real-data hook.

## Pre-registration & no-victory-theater (§8)

- Frozen ICIR grid, β→ICIR calibration, seed budget, adaptive re-seed algorithm, decision lines, and aggregation were fixed **before** results.
- Realized ICIR is **never** written back onto the strength axis.
- Size is reported beside power (when β=0 is on the grid).
- Power seed root=420260711; R₀=40; R_max=120.

