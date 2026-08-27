# Noise Control — Design (v0.1)

**Provenance:** decided 2026-07-10 in ticket `.scratch/v0.1/issues/07-noise-control-design.md`
(HITL grilling; all four rulings confirmed by the project owner).
**Consumers:** the court kernel spec (ticket 08) takes the court-side function contract
from §4; the killer-demo design (ticket 11) takes the generation protocol from §3 and the
grid layout from §5.
**Depends on:** `docs/design/trial-ledger.md` (record schemas, read surface, decoupling);
`CONTEXT.md` vocabulary (Trial, Verdict, Scope, Null jury).
**Scope:** design contract only. No implementation in this document.

---

## 1. Purpose and role in the battery

The noise control is the court's empirical-null statistic: it asks *"would an equally
privileged jury of information-free factors have performed this well?"* It complements
the analytic deflation statistics — DSR's expected-max hurdle rests on EVT and
independence approximations (`docs/research/dsr.md` §2.c, N ≫ 1 caveat), whereas the
noise control is distribution-free and **procedure-faithful**: the null factors run
through the *identical* evaluation pipeline and, in pool mode, the *identical selection
procedure* as the accused.

How noise-control verdicts combine with DSR/PBO/FDR verdicts (chain, weighted battery,
veto) is **deliberately out of scope**: survival aggregation is judge configuration,
owned by ticket 11 (`docs/design/trial-ledger.md` §5.3, §7.4).

## 2. Architecture: the generation/judgment split

The constitution's decoupling law forces a clean split:

- **Generation protocol (adapter/demo side).** Building null factors requires the factor
  score panel and re-evaluation against market data — capabilities `court/` must not
  have. The harness (demo runner in v0.1) generates the jury per §3, evaluates it through
  the same adapter pipeline as the candidate, and hands the court plain arrays.
- **Court-side statistic (pure function).** `court/` receives the candidate's ranking
  statistic and the jury's statistics and computes an empirical p-value and a decision
  (§4). It never generates, shifts, or evaluates factors, consistent with
  `docs/design/trial-ledger.md` §4.2 ("no additional ledger capability anticipated")
  and §7.3 (statistics are pure functions over arrays).

## 3. Null generation protocol: circular time-shift (ruling 1)

### 3.1 Definition

Let S be the candidate factor's score panel over evaluation dates t = 0..T−1 (rows) and
instruments (columns), and let δ be an offset. The null panel is the circular shift

> S⁽δ⁾ (t, ·) = S((t − δ) mod T, ·)

evaluated against the **unshifted** return panel through the identical pipeline
(same universe, same metric, same declared protocol).

### 3.2 Why this jury is fair (what is matched by construction)

Because S⁽δ⁾ *is* the candidate's own panel, the null matches — exactly, with no
modeling — the properties that make performance comparisons honest:

- **Coverage:** the same names are scored on the same relative pattern of dates.
- **Cross-sectional marginals:** each row is a row of S; per-period score distributions
  are identical.
- **Score dynamics / turnover:** autocorrelation of scores, and hence portfolio
  turnover, are preserved (up to the single wrap-around seam).

The only thing destroyed is the *alignment between scores and subsequent returns* —
precisely the content on trial. This is the randomization-test logic of Fisher (1935),
in the practical form described by Davison & Hinkley (1997, Ch. 4: permutation and
randomization p-values); preserving serial structure by shifting rather than i.i.d.
shuffling follows the same motivation as block/stationary resampling (Politis & Romano
1994).

Rejected alternatives, for the record: per-period cross-sectional permutation destroys
score persistence (null turnover is maximal — unfair to low-turnover candidates); fresh
i.i.d. random scores match only coverage. Both remain legitimate juries for special
cases; circular shift is the v0.1 default and the demo's protocol.

### 3.3 Offset discipline

- δ is drawn uniformly from integers [δ_min, T − δ_min], with **δ_min = 60 trading
  days** by default — the offset must exceed the candidate's signal horizon and score
  autocorrelation length, or the "null" still carries live signal.
- **Seam honesty:** a circular shift has one seam where the score history wraps; its
  contamination is O(horizon/T) of the sample and is accepted and disclosed rather than
  patched (constitution: report facts as they are).

## 4. Court-side statistic (rulings 2, and the arithmetic)

### 4.1 One pure function, two modes

The kernel needs exactly one function (exact signature fixed by ticket 08):

> empirical_null_p(observed, nulls, alpha) → {p_hat, decision}

with the add-one permutation p-value of Phipson & Smyth (2010, Eq. (2)):

> p̂ = (1 + #{ j : null_j ≥ observed }) / (K + 1)

where K = number of jurors. The add-one form is exact for randomly sampled
permutations, can never return zero, and ties count against the candidate
(conservative). Decision: pass iff p̂ ≤ α; **default α = 0.05** (a verdict parameter,
not a constant).

The *ranking statistic* compared is the same directed statistic the selection procedure
ranks on — under a two-sided declared protocol, |t| of the series mean under the trial's
declared SE convention; under a one-sided protocol, the signed statistic. The statistic
name is recorded in the verdict's params; the court never re-derives direction on its
own (`docs/design/trial-ledger.md` §5.2 declared protocol).

### 4.2 Individual mode

Candidate i is compared against its own K jurors: observed = stat(candidate i),
nulls = {stat(S_i⁽δ_b⁾)} for b = 1..K. This is the reusable primitive — it applies to a
single factor submitted for judgment with no selection pool at all.

### 4.3 Pool-max mode (the demo's headline)

The accused is the *selection procedure's output*: observed = max over the real pool of
the ranking statistic; nulls = {max over the pool at common offset δ_b} for b = 1..B.
Same arithmetic, different inputs — this is the Reality Check logic of White (2000):
naive selection's t ≈ 3 must beat the distribution of the *best of an equally sized
noise pool*, not the single-factor bar.

## 5. The common-offset grid (ruling 4)

One evaluation grid serves both modes. Draw **B = 199** common offsets {δ_1..δ_199};
evaluate every candidate at every offset:

> G[i, b] = ranking statistic of candidate i's panel shifted by δ_b

- Column i (fixed candidate, all offsets) = candidate i's individual jury (K = 199,
  p̂ resolution 1/200 = 0.005).
- Row-wise max over i (fixed offset) = one pool-max null draw; the 199 row-maxes are
  the pool-mode null distribution.

Common offsets preserve the cross-candidate dependence structure within each null pool
replication — the faithful null for the max statistic (a pool of correlated factors has
a lower max distribution than an independent one; breaking that correlation would
misstate the hurdle). Cost: 100 × 199 ≈ 2·10⁴ vectorized series evaluations for the
demo — trivial on CPU.

Disclosed side effect: because offsets are shared, individual-mode p̂'s are correlated
*across* candidates. Each candidate's own p̂ remains a valid randomization p-value
(exchangeability holds within each column); cross-candidate correlation matters only to
procedures that aggregate the p̂'s — and per §1, aggregation is ticket 11's problem, to
be decided with this fact on the table.

## 6. Verdict recording (ruling 3): the jury lives in the verdict

Null jurors are **not** registered as trials. Two reasons, both contractual:

1. `docs/design/trial-ledger.md` §4.2 rules that the full trial scope enters BHY's FDR
   family. Jurors registered as trials would pollute the family N unless a scope-
   exclusion rule were invented — new complexity against a freshly closed contract.
2. File-drawer discipline (no `abandoned` state, hidden-tests audit) protects
   *candidates under accusation*. Synthetic jurors are evidence inside one verdict, not
   accused parties; they carry no file-drawer information.

One VerdictRecord per statistic application, per the ledger contract §5.3:

- `statistic`: `"noise_control"`.
- `params`: mode (`"individual"` | `"pool_max"`), alpha, K or B, recipe
  (`"circular_shift"`), delta_min, the master seed, **the drawn offsets verbatim**, and
  the ranking-statistic name.
- `computed`: the jury's K (or B) statistic values, p̂, and in pool mode the identity of
  the selected (accused) trial.
- `decisions`: individual mode — the judged candidate; pool mode — the selected trial.

Reproducibility chain: recipe + verbatim offsets + adapter data version +
`engine_version` regenerate every juror deterministically; storing the jury's statistic
values (199 floats) keeps the verdict auditable without re-running anything.

## 7. RNG discipline (ruling 4)

- One **master seed** per demo run, recorded in the run config and in every
  noise-control verdict's params.
- Derived streams via numpy `SeedSequence(master).spawn(...)` — one child for candidate
  generation (ticket 11's concern), one for the offset draw. No naked `default_rng()`
  anywhere.
- Offsets are drawn once and recorded verbatim (§6), so audit-time reproduction needs
  no RNG replay at all.
- Court-side functions are deterministic; all randomness lives with the generation
  protocol on the adapter/demo side.

## 8. Hand-worked test vectors (for ticket 08's pytest)

Using p̂ = (1 + #{null ≥ observed}) / (K + 1), α = 0.05:

1. observed = 2.0, nulls = (1.0, 2.5, 0.5, 3.0), K = 4:
   #{≥} = 2 → p̂ = 3/5 = 0.600000 → reject.
2. observed = 2.0, nulls = (1.9, 2.0, 0.5), K = 3 (tie counts against):
   #{≥} = 1 → p̂ = 2/4 = 0.500000 → reject.
3. observed = 4.0, nulls = 199 values all < 4.0, K = 199:
   #{≥} = 0 → p̂ = 1/200 = 0.005000 → pass at α = 0.05.
4. Minimum attainable p̂ at K = 199 is 1/200 = 0.005 — a jury of 199 can never certify
   below that resolution (Phipson & Smyth 2010; this is why K = 99 was declined as the
   default).

## 9. Known limitations (declared, not patched)

- **Seam artifact** (§3.3): one wrap-around discontinuity per juror; O(horizon/T).
- **No explicit style/industry matching:** the shift preserves the candidate's own
  exposure *dynamics* but not their alignment with contemporaneous style returns. A
  style-neutralized jury is a legitimate v0.2+ refinement; v0.1 declares this limit.
- **Cross-candidate p̂ correlation** from common offsets (§5) — declared to ticket 11.
- **Calendar-locked signals:** a score that is a pure function of calendar date changes
  meaning under shift; such factors are pathological for this jury and should be flagged
  by their spec (adapter concern, out of court scope).

## References

- Fisher, R. A. (1935), *The Design of Experiments* — randomization-test logic.
- Davison, A. C. & Hinkley, D. V. (1997), *Bootstrap Methods and their Application*,
  Cambridge UP, Ch. 4 — permutation/randomization p-values in practice.
- Phipson, B. & Smyth, G. K. (2010), "Permutation P-values Should Never Be Zero",
  *Statistical Applications in Genetics and Molecular Biology* 9(1), Article 39,
  Eq. (2) — the add-one estimator.
- Politis, D. N. & Romano, J. P. (1994), "The Stationary Bootstrap", *JASA* 89(428) —
  serial-structure-preserving resampling motivation.
- White, H. (2000), "A Reality Check for Data Snooping", *Econometrica* 68(5) — the
  max-of-pool null for selection procedures.
- `docs/design/trial-ledger.md` — record schemas, read surface, decoupling guarantees.
- `docs/research/dsr.md`, `docs/research/bhy.md` — the analytic statistics this control
  complements; declared-protocol SE conventions.
