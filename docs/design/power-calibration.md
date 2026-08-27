# Power calibration — design contract & pre-registration book

Status: v3 (grilling-locked 2026-07-11; batched cross-model review folded in;
**v0.2 design-layer audit folded 2026-07-12** — see §13; grid **frozen** below).
Remaining open item is a scheduling decision, not a design one (§12).
Owner ticket: `.scratch/v0.2/issues/01-power-calibration-protocol.md`
Implements into: `.scratch/v0.2/issues/05-power-calibration-harness.md`

## 1. Purpose & scope

The v0.1 milestone audit found the court's single largest gap: the killer demo
proves only **size** — the court *rejects* constructed pure noise (0/100). It has
never been shown to have **power** — to *pass* a genuine signal. As the README
states, "an always-reject stub would score the identical 0/100." This document
pre-registers the experiment that measures the court's power.

**What this proves:** the court's true-positive rate (TPR) as a function of a
genuine, known-strength signal — its operating characteristic. This distinguishes
the court from a reject-everything machine.

**What this does NOT prove** (honest boundary, reported on the first screen of
every power artifact): the signal is a **constructed oracle** (it peeks at the
forward return by construction — an intentional calibration mechanism), *not* a
discoverable, deployable alpha. This measures **discrimination**, not
**discovery**. The claim scope is "TPR for approximately-stationary mean-IC
signals," never "TPR for arbitrary real-world alpha." No costs, no capacity, no
regime realism — those are later milestones.

## 2. Relationship to the killer demo (`killer-demo.md`)

Power is the **symmetric mirror** of size. Everything is held identical to the
size experiment except a single injected mean-IC:

| Dimension | size (killer demo) | power (this doc) |
|---|---|---|
| Returns | real csi300 forward returns | **same** |
| Adapter / window (T=480) / universe / seed tree | as `killer-demo.md` §4.2 | **same** |
| The 99 noise candidates | pure-RNG AR(1) shells | **same** |
| The injected candidate | — (all noise) | β·oracle + √(1−β²)·noise |
| Injected mean-IC | ≈ 0 | ≈ g(β) > 0 |
| Daily IC serial correlation | ≈ 0 | ≈ 0 (non-overlapping label preserved) |

| declared protocol | `direction="two-sided"` | **`direction="greater"` (all 100 trials)** |

On the **data side** only the mean-IC changes. On the **battery side** the
directional declaration changes every gate's form per the ticket-03 runtime branch
(DSR informational→discriminating, PBO `|ICIR|`→signed, pool-max jury `|t|`→t, FDR
p two-sided→one-sided) — the power experiment is a **self-contained greater-battery
experiment**, disclosed as such, *not* the killer demo with a knob turned. The
killer demo's two-sided 0/100 is cited as the operating point of a *different
battery form*, never as this experiment's β=0 point. Size and power share one axis
but are reported in **separate panels** (§6). *(Audit revision D1, 2026-07-12 —
the v2 claim "only the mean-IC changes; the attribution channel is therefore
clean" overstated the mirror.)*

## 3. Decisions (grilling 2026-07-11, Q1–Q7; batched grok review folded)

| # | Decision | Ruling |
|---|---|---|
| Q1 | Objective | **A primary** = the court's ROC (does it pass a genuine signal). **B derived** = natural selection rate `P(win)`. |
| Q1b | Conditioning | Primary A conditions on the injected signal **naturally winning the directed scan `argmax t`** (§5; audit revision D1 — the v2 `max|t|`+flip-guard patch judged a two-sided selection with a one-sided battery, violating the ticket-03 isomorphism). Forcing a non-winner is a **separate "submission power" table** (a non-champion judged with the champion's DSR hurdle is over-strict). |
| Q2 | Signal construction | **(b)** future-return-mixed factor on **real** returns (§4). β is an internal, pre-registered knob; the reported strength axis is **realized annualized ICIR** (which absorbs the β↑ ⇒ mean↑ & IC-vol↓ variance channel). |
| Q3 | Pool | **1 genuine + 99 noise** (N=100, data-side size mirror — battery form differs by direction, §2; audit sweep 2026-07-12). Multiple-genuine → appendix sensitivity only. |
| Q4 | Strength grid | **FROZEN targets in annualized ICIR** (§4.3). A is dense in the **2.0–5.0** transition; **0–1.5 serves mainly B / submission** (low-band A is reported at whatever n_won lands — see §4.3; the v2 "structurally empty" claim was an audit-corrected error); β=0 is the size anchor; a 6.0 upper anchor pins the interpretable "industry ICIR≈0.4 (daily)" point. |
| Q5 | Replication / compute | **Shared-noise-pool reuse** within a seed (cross-seed reuse forbidden). R₀=40, adaptive re-seed in the transition to n_won≥20 (cap R=120); Wilson CIs; under-won strengths flagged, never extrapolated. |
| Q6 | Reporting | Hero = a **power curve**. Per-gate TPR curves are a **default output** (not an appendix toggle) alongside unanimous. Submission-power separate table. Size (β=0) same-axis, separate panel. B=P(win) plotted beside A. |
| Q7 | Directional / interactions | Inject **β > 0 only**; pool-max consistency assertion branch-handled; DSR-conservative footnote; **power's big run scheduled around tickets 03+08** (§12; audit D13 — the schema-changing step is 08). |

## 4. Data-generating process — signal construction (Q2 = (b))

### 4.1 The injected factor

For the single injected candidate, on each signal day *t* and instrument *i*:

```
oracle_i,t  = Φ⁻¹( rank_xs( forward_return_i,t ) )      # van der Waerden score of the day-t forward return
noise_i,t   = Φ⁻¹( rank_xs( AR1_i,t(φ) ) )              # same transform of the killer-demo AR(1) shell
factor_i,t  = β · oracle_i,t  +  √(1−β²) · noise_i,t
```

- Both terms are cross-sectionally rank-then-normal-quantile transformed via the
  **Hazen / rankit plotting position** `Φ⁻¹((r − 0.5) / m)` (m = finite
  cross-section that day; loosely called "van der Waerden normal scores" — the
  canonical van der Waerden position is `r/(m+1)`, but the Hazen position is the
  one implemented and calibrated against). Each term is therefore
  **approximately** unit-variance cross-sectionally (exact only as m→∞: var ≈ 0.77
  at m=5, 0.96 at m=30, 0.99 at m=100), and since oracle and noise share the
  identical per-row transform, **β is a well-defined mixing weight** (factor
  variance ≈ constant in β; the finite-m variance shortfall is common to both
  terms and absorbed by calibrating β on realized ICIR). RankIC of `factor` vs the
  return is a monotone increasing function of β.
- `forward_return_i,t` is the **same** label the adapter evaluates against
  (`Ref($close,-2)/Ref($close,-1)-1`) — a deliberate, disclosed look-ahead, the
  mirror of the null's "constructed zero information."
- `AR1_i,t(φ)` is the killer-demo shell, **φ fixed to one median value** (a 2–3 φ
  appendix is optional). The mix preserves the null's serially-uncorrelated daily
  IC (non-overlapping label), so the iid-t stays calibrated and the *only* thing
  that moves vs the null is the IC **mean**.

### 4.2 β→ICIR calibration (frozen pre-run)

Strength targets are set in **realized annualized ICIR**, then β is solved to hit
them — do **not** hand-pick a uniform β grid (uniform β is highly non-uniform in
ICIR and would leave the transition empty).

Procedure (run once, before any power run, then frozen into `run_config`):

1. Same window / universe / label / φ as the real power run (T=480, csi300, RankIC,
   gross).
2. **Calibration seeds:** `SeedSequence(320260711).spawn(64)` — a fixed K=64 list,
   written to `run_config`; **must not** reuse the power run's noise realizations.
   *(Audit revision, 2026-07-12: the v2 root 20260711 collided with the killer-demo
   sweep reserve — `SeedSequence(20260711).spawn(2)` children are bit-identical to
   the calibration's first two children, verified. The root moves outside the
   20260710–20260730 reserve so the isolation promise is mechanically checkable.)*
   *(Ratification, 2026-07-17: the **power sweep's** master seed root is
   `POWER_SEED_ROOT = 420260711` — the noise-pool / offset / injected-shell trees
   descend from `SeedSequence(420260711)` per replication. It is distinct from the
   calibration root 320260711 and also outside the 20260710–20260730 reserve;
   0 first-draw collisions between the 64 calibration and 120 sweep realizations
   were verified. This root is pinned HERE before any sweep runs — the v3 book had
   pinned only the calibration root, so the sweep root was under-specified and is
   now frozen as a commander ruling, not a worker choice.)*
   Frozen with the seeds: the **candidate β grid** for calibration is
   `0.002, 0.004, …, 0.030` (15 points), β\* solved by **monotone PCHIP interpolation**
   of the 64-seed mean ICIR(β) curve (root-finding on the interpolant); the shell
   φ is **the median of the 100 killer-demo shell φ values** (its numeric value is
   recorded in `run_config` at calibration time). These were free knobs in v2
   (audit minor).
   *(Re-centering, 2026-07-17 — pre-registration amendment from the FIRST real
   csi300 calibration, made from the ICIR(β) curve BEFORE any power/sweep result, so
   it is honest calibration not p-hacking: the v3 grid `0.02, 0.04, …, 0.30`
   overshot. The oracle Φ⁻¹(rank(forward_return)) is a near-perfect predictor
   (RankIC≈1), and csi300's realized daily IC vol is only ≈0.058, so even the grid
   floor β=0.02 already yields **annualized ICIR ≈ 4.4** — the entire transition band
   (2.0–3.6, the "gate-opening" band) fell BELOW the floor and every transition β\*
   clamped to 0.02, leaving the science region unresolved. Evidence: 64-seed-mean
   ICIR at β=0.02 = 4.39, mean_ic ≈ 0.795·β, ICIR ≈ 218·β at low β. The grid is
   shifted DOWN ~10× (floor 0.02→0.002, ceiling 0.30→0.030) so the low/transition
   bands resolve to distinct β\*<0.02 — target 2.0 ↦ β≈0.009, 3.6 ↦ ≈0.017, 6.0 ↦
   ≈0.027. `CALIBRATION_BETA_GRID` in `config.py` carries the numeric grid.)*
3. Per candidate β: generate the injected factor, `evaluate` → daily RankIC series,
   record `mean(IC)`, `std(IC, ddof=1)`, and `annualized ICIR = mean/std·√252`.
4. Freeze the **mean over 64 seeds** (report the sample SE in an appendix line).
5. Root-find/interpolate β* for each ICIR target; store β* in the frozen table.
6. **Frozen:** the calibration table goes into `run_config` and this doc. The main
   experiment's realized ICIR is **never written back** onto the axis (that would
   let selection wash the axis).

Calibration cost is negligible (64 × ~14 β × one `evaluate`, seconds each — **no
battery, no 199-offset grid**): minutes.

### 4.3 Frozen strength grid (annualized ICIR targets)

Anchored to the project's own landmark: the N=100 noise `max|t|` champion sits at
**annualized ICIR ≈ 1.93** (report.md, |t|=2.6655); under the directed scan the
99-noise `max t` median is ≈ 2.46 (natural-win median ≈ ICIR 1.78). **P(win) must
be computed with the t statistic's own realization noise** (sd ≈ 1 at T=480 — larger
than the noise-max spread; audit revision D3, 2026-07-12: the v2 fixed-mean numbers
"≈1% at 1.5, A structurally empty below 1.5" were wrong by an order of magnitude —
the error entered from a prior consult and was folded unverified). MC under
`argmax t` (400k reps): P(win) ≈ **0.05 @ 0.5, 0.15 @ 1.0, 0.35 @ 1.5, 0.60 @ 2.0,
0.73 @ 2.3, 0.84 @ 2.6, 0.92 @ 2.9, 0.96 @ 3.2**. The A-dense band stays 2.0–5.0
because that is where the **gates open** (table below), not because lower strengths
cannot win.

| Band | Targets (annualized ICIR) | Role |
|---|---|---|
| Transition (A, dense) | `2.0, 2.3, 2.6, 2.9, 3.2, 3.6, 4.0, 4.5, 5.0` | the court ROC — where FDR/pool-max/DSR open in turn |
| Low (B + submission; A as it lands) | `0, 0.5, 1.0, 1.5` | natural-win rate & submission power; **A is reported at whatever n_won lands** (≈ 2–14 wins at R₀=40), with wide Wilson CIs, never extrapolated |
| Upper anchor | `6.0` (optional `8.0`) | interpretable ceiling; ≈ the industry "ICIR≈0.4 (daily)" point |

≈ 14 points including β=0. The low band is not scanned densely for A, but its free
conditioned samples are **reported, not discarded**.

**Mandatory unit footnote (both languages):** the axis is **project annualized
ICIR = ICIR_daily·√252 ≈ ICIR_daily×16**. Industry "ICIR ≈ 0.3–0.8" is usually the
*daily, non-annualized* ratio (or a monthly-IC ratio) → project annualized ≈ 5–13.
Without this the figure is read as "the court can't/can trivially pass ICIR 0.4,"
both wrong.

Approximate gate-opening thresholds, **one-sided (`greater`) convention throughout**
(audit revision D1 — the v2 table mixed two-sided FDR with near-signed pool-max):

| Gate | ≈ t needed | ≈ annualized ICIR | provenance |
|---|---:|---:|---|
| natural `argmax t` win (median) | 2.46 | 1.78 | Φ(x)^99 = 0.5, exact |
| pool-max (α=0.05, signed jury) | 3.28 | 2.38 | Φ(x)^99 = 0.95, exact iid |
| FDR-BY (single true discovery, one-sided p) | 3.73 | 2.70 | p ≤ q/(N·c(N)), c(100)=5.1874, exact |
| DSR (N̂≈100, harshest deflation) | ≈4.4+ | ≈3.2+ | MC incl. the signal's own lift of the cross-trial SR std; conservative band 3.2–3.6 |
| PBO (constant edge, signed metric) | modest | mid | qualitative; see §7 for the episodic corrector |

## 5. Experiment design

- **Pool:** 1 injected genuine + 99 pure-noise = N=100 (data-side size mirror). FDR
  family then has exactly 1 true positive / 99 true negatives. **All 100 trials
  declare `direction="greater"`** — the pool is direction-homogeneous, so every
  family-level gate branches on one unambiguous direction (audit revision D1; v2
  left the noise trials' declaration unstated).
- **"Won" definition (Q1b, audit revision D1):** the injected candidate counts as
  won in a run iff it is the **`argmax t`** (directed scan matching the declared
  `greater`; no flip guard needed — a negative-t champion cannot win a directed
  scan). The v2 rule `argmax|t| ∧ t>0` judged a two-sided search with a one-sided
  battery — the exact selection–verdict mismatch ticket 03 exists to kill.
- **Primary estimate A (court ROC):** over R seeds per strength, among the *won*
  runs, `P(unanimous pass | won)` with a Wilson CI. The injected candidate sits
  inside the full 99-noise pool so pool gates operate at N=100. Figure caption is
  **mandatory**: "A is the court ROC *given the signal already won naive
  selection*; B = P(win) is plotted beside it" — A alone is optimistic (conditions
  on stronger realizations).
- **Submission power (secondary table):** `P(unanimous pass | injected forced as
  the judged candidate)`, labeled "submission power (researcher-designated)",
  footnoted that DSR is conservative off-champion; **never** overlaid on A.
- **Derived note B:** natural selection rate `P(argmax t = injected | strength)` (audit sweep — the v2 two-sided form contradicted the §5 directed scan).
- **Replication (Q5):** baseline **R₀ = 40** per strength; in the transition band
  (2.0–3.6) **adaptively re-seed** (pre-registered algorithmic seed sequence) until
  n_won ≥ 20, capped at **R = 120**. Wilson n=20@p=0.5 → half-width ≈0.20; report
  it honestly, never fake precision. Adding samples means adding **seeds** only —
  never resampling the noise pool (that changes N and breaks the size mirror).
- **Compute (Q5):** the ~26.8 s/candidate cost is the **199-offset
  `evaluate_shifted` grid**, not the battery. Per seed, evaluate the 99 noise
  **once** (~44 min) and cache their IC series, t, the 199-column jury **directed
  t** (per spec F2 under `greater` — *not* |t|; audit revision D1 fixed this v2
  remnant), and the per-offset (signed) max-of-99; each β then costs only the
  injected factor's `evaluate` + `evaluate_shifted` (~27 s) plus a **cheap** battery
  re-run (pool-max updates the cached max, PBO/DSR swap one column, FDR swaps one
  p). **Cross-β reuse within a seed only; cross-seed reuse is forbidden** (it
  fabricates samples and narrows CIs falsely). Serial wall-clock ≈ 1.5–2 days
  (R₀=40, ~14 β); worst case at the R=120 cap ≈ 4.2 days serial (ticket 05 plans
  for this, audit nit); parallelizable by seed.
- **B's estimator (audit minor):** B = P(win) is estimated **from the first R₀=40
  fixed seeds only** at every strength. The adaptive re-seed continues sampling the
  *conditional* leg (A is unbiased under the stopping rule — it stops on n_won, not
  on passes), but a stopped-on-win count would bias B upward (~+4% relative at
  p_win=0.25, simulated); freezing B's denominator removes the bias.

## 6. Reporting

- **Hero figure — the power curve:** `P(unanimous pass | won)` vs realized
  annualized ICIR, with the β=0 size anchor marked, **B = P(win)** plotted beside
  it, and the five **per-gate TPR curves as a default panel** (not an appendix
  toggle — unanimous alone is silently PBO-hijackable).
- **Size same-axis, separate panel — "directional size" (audit revision D1):** the
  β=0 anchor is a **re-run of this same greater-battery** at zero signal, labeled
  "directional size". It is *not* the killer demo's two-sided size (different
  battery form: DSR votes here, PBO is signed, p one-sided) and the two are never
  presented as the same number. The assertion at β=0 is `P(pass) ≈ nominal α` **for
  the size-type gates** (FDR / pool-max / individual — per-gate); PBO's φ≤0.2 is a
  rule threshold, not a size guarantee (`killer-demo.md` §5.4), and is excluded
  from the assertion (audit nit). The killer demo's 0/100 is cross-referenced as
  the two-sided battery's operating point.
  - **Estimator (ruling, 2026-07-17 — resolves the hero-anchor/size-panel
    conflation):** the size-panel per-gate `P(pass) ≈ α` is the **accused
    champion's** per-gate pass rate over **all R₀ seeds — UNCONDITIONAL on which
    trial is the champion**. At β=0 the injected is pure noise and wins argmax t
    only ≈1/N of the time, so a `P(pass | injected won)` estimator (the hero
    curve's leftmost point) has ≈0.4 expected wins at N=100/R₀=40 → NaN. The size
    panel must instead judge whatever champion the directed scan selects each seed
    (one champion always exists) and report its per-gate pass rate → ~R₀ samples
    and a measurable ≈α. The hero curve's β=0 point stays `P(unanimous | won)`
    (informational, wide CI); the **size-panel numbers are the unconditional
    champion rate** and are the ones bearing the `≈α` assertion. Reporting both is
    fine; they are labeled as different estimands and never conflated.
- **First-screen honesty:** the §1 claim scope + the §4.3 unit footnote.
- **Under-powered strengths** are shown with wide CIs and flagged, never smoothed
  or extrapolated.

## 7. Appendices

- **β_t regime-switch (in v0.2 scope) — the PBO-optimism corrector.** A constant
  daily edge is friendlier to PBO than episodic real alpha, so unanimous power is
  optimistic. **Main appendix = half-window**, both polarities to defend against a
  directional coincidence:
  - Forward-off: t=1..240 β=s, t=241..480 β=0.
  - Backward-off: t=1..240 β=0, t=241..480 β=s.
  - **Primary contrast (audit revision D2, 2026-07-12): matched realized ICIR.**
    The half-window arm's β is solved so the **full-sample** realized ICIR equals
    the constant-β reference (targets ≈ 4.0 and a waist ≈ 3.0). This isolates
    *episodicity* — the mechanism the appendix exists to measure. The v2 design
    compared at the **same nominal β=s**, where the full-sample ICIR halves; CSCV
    simulation shows that comparison is ~dominated by the strength drop (const
    ICIR-4 P(φ≤0.2)≈0.97 → half-window nominal-4 ≈0.17, of which strength-matching
    alone explains ≈0.13 and episodicity ≈0.90→0.97's gap of only a few points) —
    it would have pre-registered a mis-attribution.
  - **Secondary display: same-nominal-β arm** — kept as the "what a researcher who
    designed for ICIR 4 but got an episodic factor actually experiences" view,
    explicitly labeled as confounding strength with episodicity.
  - **Secondary (sensitivity): random block** — 30-evaluation-day blocks (= T/S,
    aligned to PBO's split so it introduces no new partition), 50% duty (8 of 16
    blocks ON via a pre-registered seed), β=s on / 0 off. **Not** daily Bernoulli
    (indistinguishable from a weaker constant β at daily granularity — not faithful
    to "episodic"; audit nit corrected the v2 rationale). Note (audit minor): under
    the iid daily-IC model, random-block aligned to PBO's partition is
    distribution-identical to half-window for every full-sample gate and for CSCV —
    this arm only detects **real-data regime/calendar coincidences**, and is kept
    for exactly that.
  - The appendix answers one number: **how many points unanimous/PBO-TPR drops from
    constant edge to matched-ICIR episodic edge.** If it drops from e.g. 0.9 to
    0.6, the hero figure must cite that — otherwise the hero is victory theater.
- **Multiple-genuine (optional):** K genuine among (100−K) noise; steadier
  FDR-power statistics but departs from the size mirror. Appendix only.
- **2–3 φ values (optional):** show φ-insensitivity.
- **Calibration decomposition:** small plots of `E[IC](β)` and `ICvol(β)` proving
  the variance channel is real and absorbed by the ICIR axis (audit / 禁赢学).

## 8. Pre-registration & no-victory-theater

This is the power experiment's pre-registration book, on the same footing as
`killer-demo.md`:

- The **frozen ICIR grid (§4.3), the β→ICIR calibration (§4.2), seed budget & the
  adaptive re-seed algorithm, decision lines, and aggregation** are fixed **before
  any power run**.
- If the transition falls outside the frozen grid, report it honestly and note a
  follow-up grid — **never** silently re-tune the grid for a prettier curve.
- **Size is reported beside power, always.** A flattering power curve without its
  size panel is a禁赢学 violation.
- No re-rolling seeds, no post-hoc threshold moves, no relabeling.

## 9. Traps & subtleties (grilling + grok, 2026-07-11)

- **Directional β>0 exercises DSR properly, and fixes PBO's metric.** The size
  demo's accused was a flipped negative-t factor, so one-sided DSR did no real work.
  A β>0 genuine signal has positive SR — the case DSR *can* pass — so DSR is
  genuinely load-bearing here (visible in its per-gate TPR). Per the ticket-03
  ruling (`selection-verdict-isomorphism.md`), gate forms branch on
  `declared.direction` at runtime: the power run declares `greater`, so **DSR is
  enabled and PBO uses the signed metric** (`sharpe`/`ICIR`) — **not** the `|ICIR|`
  form the two-sided killer demo uses. A power harness that fed `|metric|` would
  break the isomorphism with the declared `greater` hypothesis (audit nit: it
  would in fact *match* the two-sided demo's convention — the sin is against the
  declared direction, not against demo comparability); the branch is a runtime
  rule, not a per-experiment patch.
- **pool-max consistency assertion is branch-dependent.** Natural-win branch: it
  holds. Submission (forced) branch: the injected may not be the max, so the
  harness must disable/rewrite the assertion there (ticket 05 note).
- **DSR is a conservative lower bound here.** The independent noise pool has ρ̂≈0,
  so N̂≈M and DSR deflates hardest; a real correlated library passes DSR more
  easily. `rho_ill_conditioned=True` at T=480, M=100 is by design — do **not**
  shrink M to manufacture power. Footnote only.
- **A conditions on stronger realizations** (Q1b) → slightly optimistic vs an
  "average true factor"; B=P(win) beside it and the mandatory caption keep this
  honest.
- **FDR family with one true positive** behaves as expected (mid strength: the one
  signal enters the discovery set; weak: empty rejection). BY's c(N) power cost at
  N=100 matches size — do not move q post-hoc.

## 10. Entry point & deliverables (ticket 05)

- A one-command power sweep (mirroring `python -m examples.killer_demo`) producing:
  the hero power curve (with B and per-gate TPR panels), the size panel, the
  submission-power table, and the β_t appendix.
- Determinism on a fixed machine + locked deps, as the killer demo.
- Results reported however they land, including an unflattering power curve.

## 11. Batched cross-model review — resolved (2026-07-11)

The §11 open items of DRAFT v1 were put to grok in one batch
(`.scratch/dispatch/v02-power-grill/`). Outcome, folded above:

1. **ICIR band was a lock error** (v1's 0.1–1.5 anchor would plot A on an empty
   set — the noise champion already sits at annualized ICIR≈1.93). Corrected to the
   frozen §4.3 grid (A dense 2.0–5.0). **This is the review's headline catch.**
2. β→ICIR calibration procedure fixed at K=64 frozen seeds, axis = realized
   annualized ICIR, decomposition disclosed (§4.2, §7).
3. Compute model confirmed (26.8 s = the shift grid, not the battery); R₀=40 +
   adaptive re-seed to n_won≥20 (§5); ~1.5–2 days serial.
4. β_t appendix = half-window (main) + random block (secondary) (§7).
5. Added the "won ⇒ t>0" flip guard (§5) and made per-gate TPR a default output
   (§6). Flagged the ticket-03 scheduling risk (§12).

## 12. Scheduling — the one remaining decision

Ticket 03 (selection–verdict isomorphism) may change the battery (e.g. gate DSR
only under directional hypotheses). If it does **after** a full power run, that run
is invalidated and must be re-done (~1.5–2 days). The grid and calibration can be
frozen now regardless; the question is only *when* the big power run executes:

- **Option 1 (recommended):** ticket 05 (power run) is **Blocked by 03** as well as
  01 — freeze/calibrate now, run after 03 settles. Zero wasted compute.
- **Option 2:** run power now on the current battery, accept a possible re-run if 03
  changes a gate. Faster to a first curve, risks ~1.5–2 days of rework.

**Decided 2026-07-11: Option 1; amended 2026-07-12 (audit D13).** Ticket 05 is
`Blocked by: 01, 03, 08` — the audit found Option 1 protected against the wrong
object: the schema-changing step is **08** (verdict `role` field, direction-aware
registry), not 03's text. Running power before 08 would mint artifacts one field
behind the court — the exact debt ticket 08 exists to clear. Honesty note (audit
D13): what is frozen **now** is the ICIR target grid and the calibration
*procedure*; the β\* table itself does not exist yet — producing and freezing it is
**step one of ticket 05**, before any power run. Two further rulings (audit D13):

- **Certified path:** the power harness runs as **uncertified calculator use**
  (direct `court`), disclosed on the first screen of every power artifact. Power
  is an instrument-calibration experiment — the certified path (tickets 06/07)
  governs *discovery* workflows, where self-deception is the threat; calibrating
  the court is not a discovery. An optional post-07 sealed re-run of one strength
  is ticket-11 material, not a 05 requirement.
- **Aggregation source:** the power harness reuses the ticket-08
  discriminating-only aggregation helper — **no second aggregation code path**.

## 13. v0.2 design-layer audit — revisions folded (2026-07-12)

Five-way blind milestone audit (grok + three independent Claude panels + the
commander's pre-committed seam list; archive
`.scratch/dispatch/v02-design-audit/`, verdict `verdict.md`). Verdict on v2:
**revise before build.** Folded into this v3:

1. **D1 (blocker)** — selection–verdict isomorphism: selection is now the directed
   `argmax t`, all 100 trials declare `greater`, the jury statistic is the directed
   t, the gate table is one-sided throughout, the size anchor is a same-battery
   "directional size" (§2, §3 Q1b, §4.3, §5, §6). The v2 `max|t|`+flip-guard design
   judged a two-sided search with a one-sided battery.
2. **D2 (blocker)** — the β_t appendix's primary contrast is now **matched realized
   ICIR** (§7); the v2 same-nominal-β contrast confounded strength halving with
   episodicity (CSCV-simulated: the drop was ~dominated by strength).
3. **D3 (major)** — P(win) recomputed **with the t statistic's realization noise**
   (§4.3): 1.5 → ≈0.35 under the directed scan (v2 claimed ≈1% and "structurally
   empty" — a fixed-mean-approximation error that entered from a prior consult and
   was folded unverified; the number is corrected and low-band A is now reported as
   it lands).
4. **Minors** — calibration seed root moved off the sweep reserve (§4.2, collision
   verified); calibration β grid / interpolation / φ pinned (§4.2); B estimated
   from the first R₀ fixed seeds (§5); R=120 worst case ≈4.2 days (§5);
   random-block arm honestly scoped (§7); gate-table provenance column (§4.3);
   §9/§6 wording nits.
5. **D13 (blocker, scheduling)** — ticket 05 is additionally blocked by **08**;
   power runs uncertified (disclosed); aggregation reuses the 08 helper (§12).
