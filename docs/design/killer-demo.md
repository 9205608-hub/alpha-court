# Killer Demo — Design (v0.1)

**Provenance:** decided 2026-07-10 in ticket `.scratch/v0.1/issues/11-killer-demo-design.md`
(HITL grilling; all twelve rulings confirmed by the project owner).
**Consumers:** the demo implementation ticket takes the full script from this document;
the adapter implementation ticket cross-checks the grid feed (§5.3) against
`docs/design/adapter-interface.md` §7.3; the README endgame takes the figure (§8) and the
headline (§6) from here.
**Depends on:** `docs/design/trial-ledger.md` (records, judge seam);
`docs/design/noise-control.md` (generation protocol §3, offset grid §5, RNG §7);
`docs/design/adapter-interface.md` (evaluation conventions, `evaluate`/`evaluate_shifted`);
`docs/design/court-kernel-spec.md` (signatures, judge applications §5.8, decision polarity);
`CONTEXT.md` (canonical vocabulary, used without redefinition).
**Scope:** design contract for `examples/killer_demo`. No implementation in this document.

**Pre-registration status:** this document is the demo's own pre-registration. Every
parameter below — seeds, thresholds, window, aggregation rule — is fixed **before the
first real run** and may not be tuned after results are seen. Amendments require an
explicit changelog entry in this file, made before re-running.

---

## 1. Purpose

The demo is the project's reason-to-exist in one figure: **100 pure-noise factors → naive
selection "discovers" a fake alpha with |t| ≈ 3 → the court rejects it** (expected: all
100 rejected). It exercises the full chain end to end — data pack, adapter, ledger, all
four court statistics, judge, verdict records — and its output is a complete audit log,
not a performance claim.

Honesty clause (constitution, binding): results are reported as they come out. If the
court does **not** reject everything, that outcome goes on the headline with the
pre-written interpretation of §7.3. Null archives receive the same documentation
treatment as survivors.

## 2. The twelve rulings

| # | Ruling | Section |
|---|---|---|
| 1 | Candidates = pure-RNG AR(1) persistent score panels; the "family shell" is spec metadata plus a family-specific persistence φ. Zero information by construction — scores are generated from an RNG, statistically independent of all return data | §4.1 |
| 2 | Shell menu = 5 families × 20 variants, φ spanning the full turnover spectrum | §4.2 |
| 3 | Ledger mapping = 100 hypotheses × 1 trial each; family membership lives only in `spec.family` | §4.3 |
| 4 | Seed tree: `SeedSequence(20260710)` → `spawn(2)` → child 0 candidates (→ `spawn(100)`, one grandchild per factor), child 1 offset draw | §4.4 |
| 5 | Naive selection statistic = max \|t\| with sign flips allowed; every trial declares `two-sided`, `iid` SE | §5.1 |
| 6 | Naive window discipline = none: full-window in-sample selection, no holdout | §5.1 |
| 7 | Battery = `fdr_by` → `dsr` → `pbo_cscv` → `noise_control` pool-max → `noise_control` individual × 100 (104 verdicts in one `judge` call) | §5.2 |
| 8 | Decision lines: q = 0.05, DSR confidence = 0.95, noise α = 0.05 (both modes), PBO φ ≤ 0.2; window pinned to T = 480 evaluation dates, S = 16 | §5.4 |
| 9 | Survival aggregation = unanimous: a trial survives iff **every** verdict that decides it is `"pass"`; headline = survivor count out of 100 | §6 |
| 10 | Honesty protocol: single pre-registered master run (seed 20260710), pre-written interpretation for survivors, plus a 20-seed sweep appendix (seeds 20260711–20260730, all reported) | §7 |
| 11 | The figure = one panel: pool-max null histogram + accused's \|t\| line + naive significance bar | §8 |
| 12 | Entry point `python -m examples.killer_demo`; outputs = `ledger.jsonl`, figure, `report.md` (headline / morgue table / specimen autopsy / calibration appendix), `run_config.json` | §9, §10 |

Defaults pinned without objection during grilling: score panels are dense over PIT
members (no NaN injection); no per-day cross-sectional standardization (RankIC and
quantile membership are rank-invariant to it — pure decoration, dropped); offsets drawn
without replacement; annualized ICIR is dual-reported at the presentation layer (it is a
monotone transform of t, never a second ranking); per-trial pass counts appear in the
report as information, never as an aggregation rule.

## 3. Cast and stage

- **Stage:** csi300, dynamic PIT membership, RankIC metric (`declared.metric = "ic"`),
  label `Ref($close,-2)/Ref($close,-1)-1`, data pack `chenditc/investment_data` tag
  `2026-07-05` — all per `docs/design/adapter-interface.md`. Gross paper series; the §4.4
  cost-declaration string must appear in the figure caption.
- **Window:** the most recent **T = 480** evaluation dates available in the pinned pack
  (calendar through 2026-07-03). The declared window's `{start, end}` are the concrete ISO
  dates computed from the qlib calendar before registration such that the adapter's
  evaluation-date rule (`adapter-interface.md` §5.2) yields exactly those 480 dates.
  Deterministic given the pack; recorded in every trial's declared protocol.
  Why exactly 480: PBO requires `T % S == 0` fail-closed and the judge feeds
  `matrix(scope)` straight into `pbo_cscv` — the window, not the statistic, must absorb
  the constraint. 480 = 16 × 30 (S = 16, block length 30 trading days, C(16,8) = 12870
  combinations).
- **The accused:** whichever trial naive selection picks (§5.1). The demo asserts that the
  judge's pool-max `computed.selected_trial_id` equals the naive pick — same statistic,
  same series, same arithmetic (§5.3); a mismatch is a bug, fail loudly.

## 4. The generation stub (100 noise candidates)

### 4.1 Mechanism: pure-RNG AR(1) persistent panels

Factor i's score panel over the 480 evaluation dates × PIT instruments is generated
per instrument as a stationary AR(1):

> s(0) ~ N(0,1),  s(t) = φᵢ · s(t−1) + √(1−φᵢ²) · ε(t),  ε(t) ~ N(0,1) i.i.d.

- **Zero information is a constructive fact:** scores come from an RNG stream that never
  touches return data. No scramble-completeness argument to audit (the rejected
  alternative — real formulas on shuffled data — makes "no information" a property of the
  shuffling protocol, and collides with the jury's own time-shift trick, muddying who is
  judging whom).
- **φ is the only operative disguise.** It sets score autocorrelation and hence portfolio
  turnover (daily AR(1): half-life = ln 2 / ln(1/φ); φ = 0.98 ≈ 34 trading days,
  φ = 0.3 ≈ 0.6 days). Momentum shells turn over slowly, reversal shells fast — the
  naive world's menu looks real where it matters.
- Panels are dense over instruments that are PIT members at any point in the window; the
  adapter's per-day PIT + pairwise-NaN rule handles membership. No NaN injection.
- No cross-sectional standardization: RankIC and quantile membership depend only on
  within-day ranks; standardization would be decoration.

**Mechanism note (corrected during grilling, load-bearing for the narrative):** under the
null, the daily RankIC series is approximately **serially uncorrelated regardless of φ** —
the noise in IC_t comes from each day's fresh, non-overlapping forward returns, so
persistent scores do not produce persistent IC. Consequently each factor's iid t-statistic
is approximately N(0,1): the naive researcher's per-factor arithmetic is *fine*. The
entire inflation lives in the **selection** (max over 100), which is exactly what the
court prosecutes. The court never disputes the t; it disputes the inference.

### 4.2 The shell menu: 5 families × 20 variants

| Family | φ range (linear across 20 variants) | Pseudo-lookback (cosmetic) | Turnover flavor |
|---|---|---|---|
| momentum | 0.90 – 0.97 | 5, 10, …, 100 d | slow |
| reversal | 0.20 – 0.60 | 1, 2, …, 20 d | fast |
| volatility | 0.95 – 0.99 | 10, 20, …, 200 d | slow |
| liquidity | 0.97 – 0.995 | 10, 20, …, 200 d | very slow |
| value/quality | 0.995 – 0.999 | 20 named ratio proxies | near-static |

- Pseudo-lookbacks are **cosmetic metadata** — φ is the only parameter that reaches the
  generator. This is disclosed, not hidden: the disguise targets the selection procedure,
  not the auditor.
- The spec of every trial carries the full recipe:
  `spec = {family, name, pseudo_params: {lookback}, generator: {kind: "ar1_noise", phi,
  master_seed, seed_path}}` — the ledger itself knows these are noise; the naive procedure
  simply doesn't care. Reproducibility chain: spec alone regenerates the panel.

### 4.3 Ledger mapping: 100 hypotheses × 1 trial

Each factor registers its own hypothesis (statement = the shell's fake claim, e.g.
*"20-day price momentum predicts csi300 returns"*), one trial under it. Family membership
lives only in `spec.family`. Rationale: N = 100 then runs through every statistic and
every sentence of the story (FDR family = 100, DSR M = 100, PBO columns = 100, pool
size = 100); it matches the descriptive remark already in `trial-ledger.md` §4.2; and the
v0.2 per-hypothesis representative policy switch cannot change the demo's numbers. The
5 × 20 alternative is statistically identical in v0.1 (one trial = one test either way)
and was declined on narrative grounds.

Event order is part of the theater: the demo registers **all 100 hypotheses and trials
first**, then evaluates and records series, then judges — the physical line order of
`ledger.jsonl` exhibits pre-registration discipline (ledger contract §6, invariant 2).

### 4.4 Seed tree

```
SeedSequence(master)                     # master default: 20260710 (design date)
├── spawn child 0: candidate generation
│   └── spawn(100): grandchild i → factor i's panel   (independently reproducible)
└── spawn child 1: offset draw (199 offsets, without replacement)
```

Master seed is a CLI flag (`--seed`, default 20260710), recorded in `run_config.json` and
in every noise-control verdict's params (noise-control §7). No naked `default_rng()`
anywhere. Factor i is reproducible from `(master, seed_path=[0, i])` alone.

## 5. The two arms

### 5.1 The naive arm ("a day in the world without a court")

1. Evaluate all 100 panels over the full window (adapter `evaluate`, metric `"ic"`).
2. For each factor compute t = `court.tstats.t_stat(series, se_kind="iid")` — the **same
   function the judge uses**, so "the court doesn't dispute your t" is literal.
3. Pick the accused: **argmax \|t\|**. Sign flips allowed — a significantly negative IC
   factor is flipped and reported as a great "contrarian" discovery. This is the everyday
   garden-of-forking-paths move, and it makes the selection two-sided (effective 200
   arms). Ties (measure zero): smallest trial index.
4. Report: factor name, direction, \|t\|, naive p = 2(1−Φ(\|t\|)), annualized ICIR
   (= t/√T × √252, dual-reported, same ranking).

No holdout, no correction — full-window in-sample selection. The declared protocol of
every trial: `metric="ic"`, `direction="two-sided"`, `se={kind:"iid"}`,
`periods_per_year=252`, the §3 window. This matches kernel defaults (spec ruling B10) and
makes the court's recomputed p equal the naive p per factor.

### 5.2 The court arm: battery configuration

One `judge(ledger, scope=all_100, config)` call; config (order = ledger narrative order):

```
1.      Application("fdr_by",        {"q": 0.05})
2.      Application("dsr",           {"selected_trial_id": accused, "confidence": 0.95})
3.      Application("pbo_cscv",      {"selected_trial_id": accused, "n_splits": 16,
                                      "phi_threshold": 0.2, "metric": "sharpe"})
4.      Application("noise_control", {"mode": "pool_max", "alpha": 0.05,
                                      "null_stats": [199 row-maxes], ...provenance})
5–104.  Application("noise_control", {"mode": "individual", "alpha": 0.05,
                                      "judged_trial_id": trial_i,
                                      "null_stats": [trial_i's 199 juror stats],
                                      ...provenance})     # one per trial
```

104 VerdictRecords. Scopes: `fdr_by` decides all 100 (one trial = one hypothesis test);
`dsr`/`pbo_cscv`/pool-max read the full 100-column matrix/pool and decide the accused
only; each individual noise application decides its own trial. Provenance keys on every
noise application (recorded verbatim, noise-control §6): `recipe="circular_shift"`,
`delta_min=60`, `seed` (master), `offsets` (199 ints verbatim), `ranking_stat="abs_t_iid"`,
plus the adapter `data_version` triple.

Why individual mode for all 100: the grid columns are free, and ~5 expected individual
passes at α = 0.05 are **calibration evidence, not an accident** — the single-factor test
works exactly as advertised and still cannot stop a selection over 100. Multiplicity is
the killer; this row teaches it.

### 5.3 The offset grid feed

Per `noise-control.md` §5 and `adapter-interface.md` §7.3:

- Draw B = 199 offsets uniformly **without replacement** from integers [60, 420]
  (δ_min = 60, T − δ_min = 420; 361 candidates), under seed child 1; record verbatim.
- For each candidate i: `evaluate_shifted(scores_i, "ic", offsets)` → 199 juror series;
  reduce each with the same `court.tstats.t_stat` (iid) → G[i, b] = \|t\| of candidate i
  at offset δ_b. Reduction uses court pure functions on the demo side (noise-control §2).
- Individual jury for trial i = {G[i, b] : b = 1..199} (p̂ resolution 1/200 = 0.005).
- Pool-max null distribution = {max_i G[i, b] : b = 1..199} — common offsets preserve
  cross-candidate dependence (White 2000 Reality Check logic).
- Consistency assertion (§3): the judge's pool-max argmax must equal the naive accused.

Cost: 100 × 199 vectorized evaluations, seconds on CPU (rank-precomputation trick,
`adapter-interface.md` §7.3 performance note).

### 5.4 Decision lines and two disclosed subtleties

| Gate | Pass rule | Line | Rationale |
|---|---|---|---|
| `fdr_by` | trial in rejection set (discovery) | q = 0.05 | size-type parameter, uniform 5% |
| `dsr` | DSR ≥ 0.95 | confidence = 0.95 | size-type (1−confidence = 5%); paper's example value |
| `pbo_cscv` | φ ≤ 0.2 | 0.2 | φ is **not** a size — it is the share of CSCV combinations where the IS-best falls below the OOS median (noise ⇒ φ ≈ 0.5, strong true signal ⇒ φ → 0). 0.2 keeps a wide safety margin against the noise center 0.5 while not guillotining moderate true factors in v0.2+ |
| `noise_control` (both modes) | p̂ ≤ 0.05 | α = 0.05 | size-type, uniform 5% |

Disclosed subtleties (reported, not patched):

- **DSR is one-sided by construction.** E[max SR] deflates a signed maximum; if the
  accused is a flipped negative-t factor (probability ≈ ½), its signed SR is negative and
  DSR rejects immediately — correct verdict, but the deflation machinery isn't what did
  the work. The flip-faithful hurdle is the pool-max noise control, whose \|t\| ranking
  matches the naive procedure exactly (kernel ruling F2). The seed-sweep appendix (§7.4)
  shows both sign cases. Footnoted in the report.
- **PBO's metric form is direction-aware (superseded 2026-07-13 per ticket 03 v2):**
  under this demo's `two-sided` selection PBO ranks by the **absolute** metric
  (`abs_sharpe` on the IC series, i.e. \|ICIR\|), matching the \|t\| scan — the v0.1
  signed-metric mismatch this bullet used to disclose is what ticket 08 fixed. PBO
  judges the overfit probability of the selection **process** isomorphic to the naive
  scan on this matrix (03 §4); under the global null φ ≈ 0.5 either way. Footnoted.
- **DSR's ρ̂ is ill-conditioned by design here:** T = 480 < ½·M·(M−1) = 4950, so
  `rho_ill_conditioned = True` goes into the verdict (kernel ruling C8) and must be
  surfaced in the report — the disclosure machinery on display, not an error.
- **PBO metric on IC series:** `"sharpe"` via the judge registry computes mean/std of
  daily RankIC = ICIR; likewise DSR reads as ICIR deflation (documented isomorphism,
  `adapter-interface.md` §9).

## 6. Survival aggregation (the judge config ruling 03/08 delegated here)

> **v0.2 revision (ticket 03 — `selection-verdict-isomorphism.md`):** the unanimous
> rule counts only **discriminating** verdicts. Under this demo's `two-sided`
> selection, DSR abstains (`role="informational"`: one-sided DSR does not match a
> `|t|` selection) and PBO ranks by `|ICIR|`, so the accused's discriminating gates
> are **FDR + PBO(`|ICIR|`) + pool-max + individual** (four, not five). The headline
> (survivors = 0/100, pool-max kills the accused) is unchanged; §7.2's "five
> correlated gates" framing is superseded. Ticket 08 regenerates the artifacts.

**Unanimous rule:** a trial survives iff every **discriminating** verdict that
decides it is `"pass"` (v0.2 revision above; the pre-revision text below is kept
consistent with it — 2026-07-12 audit removed the stale five-gate double-write).
One rejection kills. Applied at the demo orchestration layer over the 104 verdicts
(the judge itself never aggregates — kernel ruling G1).

- Non-accused trials are decided by `fdr_by` + their individual noise verdict (both must
  pass for survival; expected: neither does… and an individual pass alone cannot save a
  trial the FDR rejected-nothing family screen already failed).
- The accused is decided by its **four discriminating** gates (FDR, PBO(`|ICIR|`),
  pool-max, individual); its DSR verdict is computed and shown `informational`.
- **Headline = survivor count / 100.** Expected 0. Per-trial pass counts (e.g. "1/2",
  "0/5" pre-v0.2; the accused faces 4 discriminating gates after the ticket-03
  revision, so "x/4" + an informational DSR row) appear in the morgue table as
  information only.

Polarity reminder (kernel ruling G2): statistical discovery ⟺ court `"pass"`; under the
global null the expected FDR rejection set is empty, i.e. all 100 get `"reject"`.

## 7. Honesty protocol (禁赢学 operationalized)

### 7.1 Pre-registration

This document pins, before any real run: master seed 20260710; sweep seeds
20260711–20260730; all §5.4 lines; T = 480; S = 16; B = 199; δ_min = 60; the aggregation
rule; the figure form. After results are seen, none of these move without a dated
amendment note in this file.

### 7.2 Expected magnitudes (written down before running)

| Quantity | Expectation under the null |
|---|---|
| single-factor t | ≈ N(0,1) (§4.1 mechanism note) |
| max \|t\| over ~100 ≈ independent factors | median ≈ 2.70; P(max ≥ 3) ≈ 24%; P(max ≥ 1.96) ≈ 99% |
| factors with \|t\| > 1.96 | ≈ 5 (Binomial(100, 0.05)) |
| `fdr_by` any discovery | ≤ 5% (FDR = FWER under the global null) |
| individual noise passes | ≈ 5 of 100 (cross-candidate correlated via common offsets — variance above binomial, disclosed) |
| pool-max p̂ of the accused | ≈ Uniform on the 1/200 grid; P(pass) ≈ 5% |
| PBO φ | ≈ 0.5; P(φ ≤ 0.2) small |
| DSR of the accused | rejects (≈ 0 if flipped-negative; deflated below 0.95 with ≈ 95% if positive) |
| unanimous survival of the accused | ≪ 5% (five correlated ~5% gates, all required) |

The headline "\|t\| ≈ 3" therefore honestly means **"typically 2.5–3.2"**; the demo
reports the realized value, never re-rolls the seed to hit 3.

### 7.3 Pre-written interpretation if not everything is rejected

A survivor is **the realization of the court's declared error rate** — the court never
claims zero false passes; it claims to write its error rates into the verdicts. The
report's headline then reads "N/100 survived (court's declared per-gate false-pass rate:
5%)", the survivor gets the same full autopsy as the accused, and the seed-sweep appendix
turns the single-run outcome into an empirical calibration check. What is *never* done:
re-rolling seeds, tightening thresholds post hoc, or relabeling a survivor as a bug.
(~5 individual-noise passes are not this case — they are §5.2 calibration evidence.)

### 7.4 Seed-sweep appendix

20 additional full runs, seeds 20260711–20260730 (pre-registered list, all reported).
Per seed: accused's identity/sign/\|t\|, five per-gate verdicts for the accused, survivor
count. Sweep runs write to `out/sweep/seed-<seed>/` (own ledger each); no figures, one
appendix table. Purpose: single-run luck → empirical calibration evidence (per-gate pass
frequencies should sit near their declared 5%).

## 8. The figure (one panel)

Histogram of the 199 pool-max null values {max_i G[i, b]} with two reference marks:

- **The accused:** vertical line at its \|t\|, annotated with factor name, \|t\|, naive
  p = 2(1−Φ(\|t\|)), and the court's pool-max p̂ = (1 + #{null ≥ obs})/200; the tail
  region null ≥ observed is shaded with its count.
- **The naive significance bar:** dashed line at \|t\| = 1.96 ("single-test 5% bar"),
  expected far left of the null distribution's mass.

One glance reads: the number naive selection finds astonishing is unremarkable among
best-of-noise-pool outcomes — the illusion and the verdict share one axis. A verdict
stamp ("REJECTED — 0/100 survived", or the realized outcome) sits in the annotation box.

Caption (mandatory items): the cost-declaration string *"gross paper series — no
transaction costs, no market impact"* (`adapter-interface.md` §4.4), metric (RankIC),
universe (csi300, PIT), T = 480 window dates, master seed, data tag `2026-07-05`,
`engine_version`. Files: `figure.png` (300 dpi) + `figure.svg`, same content.

The battery table and everything else live in `report.md` (§10) — the poster stays a
poster, not a dashboard.

## 9. Entry point and reproducibility

### 9.1 One command

```
python -m examples.killer_demo
```

runs the whole chain: idempotent data download (pinned tag, checked by presence +
measured-calendar fingerprint; ~813 MB on first run) → generation → evaluation +
registration/recording → judgment → aggregation → figure + report. Flags:
`--seed` (default 20260710), `--sweep` (run the §7.4 appendix), `--skip-download`,
`--data-dir`, `--out` (default `examples/killer_demo/out/`). Runtime: minutes on a
laptop CPU (grid is the bulk; seconds per candidate, vectorized).

Demo code lives in `examples/killer_demo/` (constitution layering); it imports `court`
and `adapters` — it is the orchestrator that knows both sides
(`adapter-interface.md` §1). No console-script entry point: the demo is an example, not
package API.

### 9.2 Full-chain recording

`out/run_config.json` (the run manifest): master seed, sweep seeds, all §5.4 thresholds,
n_candidates = 100, B = 199, δ_min = 60, declared window dates, T, S, universe, metric,
`data_version` triple (declared tag + measured calendar end + measured instrument count),
`court.__version__` (also stamped into every verdict by the judge, kernel ruling G4),
adapter version, qlib/numpy/scipy/pandas/python versions, platform string. Together with
`ledger.jsonl` (trial specs carry generator recipes; noise verdicts carry offsets
verbatim) the chain factor → series → verdict → figure is replayable from the manifest
alone.

### 9.3 Clean-machine checklist (goes into the demo README)

1. Clone the repo at the release commit; install locked dependencies (the lock mechanism
   is the engineering-scaffold ticket's; the requirement here is *locked*, not floating).
2. `python -m examples.killer_demo` (network needed once for the 813 MB pack).
3. Verify: `run_config.json` matches the published one; headline numbers match.
   Determinism promise inherited from `adapter-interface.md` §8: same platform + locked
   deps + same tag ⇒ bit-identical series and statistics; across platforms, decisions and
   headline are expected stable but float identity is **not** promised (last-ulp drift,
   declared).

## 10. Corpse presentation (`report.md` — the v0.3 null-museum seed)

`ledger.jsonl` is the only authoritative archive (104 verdicts with computed
intermediates, 199 juror statistics and verbatim offsets in every noise verdict); the
report is a human tour of it, generated by the run. Four parts:

1. **Headline:** survivor count / 100, the figure, and the accused's battery table —
   five rows (gate, key computed values, line, verdict): `fdr_by` (adjusted p vs q),
   `dsr` (DSR, SR*, N̂, ρ̂, `rho_ill_conditioned` flag), `pbo_cscv` (φ vs 0.2),
   pool-max (p̂, observed vs 199 null max), individual (p̂).
2. **Morgue table:** 100 rows × (name, family, φ, \|t\|, naive p, FDR-adjusted p,
   individual-noise p̂, gates passed / gates faced, final status), each row keyed by
   `trial_id` into `ledger.jsonl`. Null archives and any survivor share this table —
   equal treatment is structural.
3. **Specimen autopsy:** the accused's full evidence chain walked end to end —
   registration event (timestamp, spec recipe, declared protocol) → series provenance →
   each of its five verdicts with `computed` unpacked against the literature conventions
   (citations to `docs/research/`). One specimen, full depth; the other 99 corpses have
   two verdicts each and are served by the table (a 100-section report would bury the
   template's value). The v0.3 museum extends exactly this template.
4. **Calibration appendix:** the ~5 individual-noise passes by name (expected, not
   embarrassing), and the §7.4 seed-sweep table when `--sweep` ran.

## 11. Implementation ticket shape (cutting happens after this document)

One demo implementation ticket, blocked by the adapter implementation ticket and kernel
ticket 18 (public API). Owns `examples/killer_demo/` (generation stub, orchestration,
figure, report, sweep) + `tests/test_killer_demo.py`. Test obligations: seed determinism
(two runs, identical ledger series values and identical figure numbers); the §5.3
consistency assertion; window arithmetic (exactly 480 evaluation dates, divisible by 16);
aggregation unit tests on hand-built verdict sets (unanimous rule, both polarities);
report smoke (all four sections render, caption carries the §8 mandatory items).
E2E acceptance = the §9.1 command on the real pack.

## 12. Known limitations (declared, not patched)

- **Cross-factor correlation is unrealistically low:** independent RNG panels give
  ρ̂ ≈ 0 across candidates, so DSR's N̂ ≈ M = 100 — the *hardest* deflation hurdle;
  conservative direction, but real factor menus are more correlated.
- **Pseudo-lookbacks are cosmetic** (§4.2); disclosed in every spec.
- **Wrap-around seam** in jurors: inherited and disclosed (`noise-control.md` §3.3, §9).
- **Individual p̂'s are correlated across candidates** (common offsets): the count of
  individual passes has above-binomial variance (`noise-control.md` §5).
- **DSR one-sidedness / PBO signed selection** vs the two-sided naive procedure: §5.4.
- **Gross paper series**, no costs/tradability (`adapter-interface.md` §4.4, §5.4).
- **One market, one window, one seed on the headline** — the sweep appendix and the
  pre-registered design are the honesty devices, not a claim of generality.

## References

- `docs/design/trial-ledger.md` — records, event ordering, judge seam, N accounting.
- `docs/design/noise-control.md` — circular shift, offset grid, Phipson & Smyth p̂,
  White (2000) pool-max, RNG discipline.
- `docs/design/adapter-interface.md` — RankIC conventions, window/evaluation dates,
  `evaluate_shifted`, data pinning, determinism tiers.
- `docs/design/court-kernel-spec.md` — signatures, judge applications, decision polarity,
  rulings B10/C8/F2/G1/G2/G4/G5 cited above.
- `docs/research/dsr.md`, `docs/research/pbo-cscv.md`, `docs/research/bhy.md` — the
  statistics' literature anchors.
- `CONTEXT.md` — canonical vocabulary (Trial, Hypothesis, Verdict, Scope, Null jury).
- `.scratch/v0.1/issues/11-killer-demo-design.md` — the deciding ticket.
