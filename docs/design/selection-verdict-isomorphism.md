# Selection–verdict isomorphism — design ruling (v0.2 ticket 03)

Status: v2 (grilling-locked 2026-07-11; grok Q2 consult folded; **v0.2
design-layer audit folded 2026-07-12** — §3 argument rewritten, §2/§4 `less` and
mixed-direction rules pinned, role storage ruled; see §8).
Owner ticket: `.scratch/v0.2/issues/03-selection-verdict-isomorphism.md`
Implements into: `.scratch/v0.2/issues/08-selection-verdict-alignment.md`
Amends: `court-kernel-spec.md` (new applicability ruling), `killer-demo.md`
(aggregation narrative), `power-calibration.md` (§ directional PBO metric).

## 1. Purpose

The v0.1 audit found the battery's "unanimous 5-gate" story rests on gates that do
not match the selection rule. The naive selection is **`max|t|` with sign flips
allowed** — a *two-sided* search (effective 200 arms). But two gates test a
*one-sided / signed* question:

- **DSR** deflates a **signed** maximum Sharpe (Bailey–LdP 2014, Eq. 1–2). A
  flipped negative-t accused has a negative signed SR, so DSR rejects
  near-automatically — the deflation machinery "isn't what did the work"
  (`killer-demo.md` §5.4).
- **PBO** selects the per-combination IS best by the **signed** metric (sharpe /
  ICIR). The "best" it tests is not the `|t|`-selected accused.

FDR (two-sided p), pool-max (`abs_t_iid`), and individual noise (`|t|`) are
already selection-consistent. Presenting DSR/PBO as co-equal unanimous votes when
they test a different null is, in grok's words, "protocol fraud, not strict
multiple testing." This ruling makes the battery **direction-aware**.

## 2. Ruling (grilling Q1–Q3, 2026-07-11)

### Q1 — Applicability principle (generalizes spec ruling F2)

Spec F2 already makes the *noise* gates direction-aware: the court computes the
directed statistic the selection ranks on (`two-sided → |t|`, `greater → t`,
`less → −t`) and **never re-derives direction**. This ruling extends the same
principle to DSR and PBO:

> Each gate runs the form of its statistic **consistent with the trial's
> `declared.direction`**. If a sound, cheap direction-consistent form exists, the
> gate uses it and **remains discriminating** (counts in the survivor vote). If
> none exists, the gate **abstains**: it is still computed and recorded in the
> verdict, but is marked `informational` and does **not** enter the survivor
> boolean.

### Q2 — DSR abstains; PBO switches metric

| Gate | `two-sided` selection | `greater` | `less` (audit revision D5) | Why |
|---|---|---|---|---|
| **DSR** | **abstains** (`informational`) | **enabled** (signed, original DSR) | **enabled on the flipped series**: negate the series, recompute moments, original DSR — never feed a negative-SR accused to the signed hurdle | No clean literature two-sided DSR — see §3. Under `less`, flipping the pre-declared direction is a relabeling, not a search: N unchanged, 2012/2014 objects intact. |
| **PBO** | metric = **`|ICIR|` / `|sharpe|`** (discriminating) | metric = **signed** `sharpe`/`ICIR` | metric = **negated** (`-sharpe`/`-ICIR`, or equivalently the flipped series) — CSCV's IS-argmax takes the *largest* metric; feeding the raw signed metric under `less` would select the most-*positive* column and invert the isomorphism (audit D5) | CSCV is metric-agnostic; the metric must rank "best under the declared direction" — see §3. |
| FDR / pool-max / individual | unchanged (already `|t|`/two-sided consistent) | directed statistic per F2 | directed statistic per F2 (−t) | already isomorphic |

**Mixed-direction scope (audit revision D5):** every family-level gate (FDR /
pool-max / DSR / PBO) requires a direction-homogeneous scope. A judged scope whose
trials carry heterogeneous `declared.direction` **raises** (fail-closed, consistent
with court error semantics) — there is no principled single branch for a mixed
family, and silently picking one trial's direction would be an undeclared choice.

### Q3 — Aggregation over discriminating gates only

- Every verdict carries `role ∈ {discriminating, informational}`, derived from
  whether the gate's null-direction matches `declared.direction` (not stored input
  — derived at judgment time, like N).
- The **survivor / unanimous rule counts only `discriminating` verdicts.**
  `informational` verdicts are computed, appended to the ledger, and shown in the
  report, but never flip the survivor boolean.
- Consequence for the killer demo (§5): under `two-sided`, the discriminating
  gates are **FDR + PBO(`|ICIR|`) + pool-max + individual** (4); **DSR is
  `informational`.** The headline (survivors = 0/100, pool-max kills the accused)
  is unchanged; the narrative changes (§5).

## 3. Literature grounding (why PBO adapts and DSR does not)

**PBO metric-agnosticism — sound.** CSCV/PBO is agnostic to the performance
measure R: it only needs R computable on any IS/OOS sub-sample and inducing a total
order on columns (`pbo-cscv.md` §2.3; Bailey et al. 2017, Alg. 2.3). The
combinatorial symmetry comes from the equal-block partitions `C_S`, **not** from R
being signed. Switching to `|R|` leaves the symmetry, the logit `λ`, and
`φ = #{λ_c<0}/C(S,S/2)` unchanged; the null is still centered at φ≈0.5. What
changes is only **who "IS-best" is** — and for a `max|t|` selection, ranking by
`|R|` is the *correct* overfit question. (For a PnL strategy menu, two-sided `|SR|`
is economically odd — that case must pre-register as directional; §6, the 02/03
seam.)

**No clean two-sided DSR — abstain, don't fabricate.** DSR's object is the
**signed** extremum `E[max_i SR_i]` (Eq. 1) fed into a PSR on the signed selected
SR (Eq. 2). *(Argument rewritten by the 2026-07-12 audit — the v1 "three landmines"
framing overstated the case; two of the three did not survive numerical
re-derivation. The ruling itself is unchanged.)* The abstention rests on **two**
legs:

1. **The real landmine — flip-then-feed-original-DSR is anti-conservative.** Using
   `E[max SR]` over N as the hurdle for a flipped-positive SR sits systematically
   below the two-sided object `E[max|SR|]`: at N=100 the gap is
   E[max|Z|]=2.747 vs E[max Z]=2.508 ≈ **0.24 cross-trial SR standard deviations**
   (numerically integrated, audit-verified). A |t|-selected champion judged
   against the signed hurdle gets a systematically easy exam.
2. **The citation iron law.** A correct two-sided hurdle (`E[max_i |SR_i|]` +
   PSR conventions for it) has no Bailey-2012/2014 form to cite; the court does
   not invent uncited statistics, and pool-max already carries the two-sided
   selection load exactly (same directed statistic, empirical null).

Two v1 "landmines" are **retired as arguments** (kept here so the retirement is on
the record): *"N→2N is wrong"* — numerically, E[max of N |Z|] and E[max of 2N
signed Z] differ by ~0.0009 at N=100, 25× smaller than the EVT approximation error
DSR already tolerates (0.023); the 2N approximation is excellent, merely uncitable.
*"PSR's skew correction is sign-asymmetric"* — dissolved by the natural
implementation (flip the series, recompute moments on the flipped series, apply
the original 2012 PSR); the residual problem is only the hurdle's missing
citation, which is leg 2.

Abstaining (compute + report, don't vote) is honest; fabricating a "two-sided DSR"
would pollute the DSR name and break the iron law. Under directional hypotheses
(e.g. v0.2 power's β>0), the original signed DSR is exactly the right form.

## 4. Implementation notes (spec amendments for ticket 08)

- **`role` storage (audit revision D16, 2026-07-12).** `role` is derived at
  judgment time (Q3) and then **recorded on the `VerdictRecord` as a new optional
  field** `role: str | None = None` (mirroring the existing optional
  `engine_version`). Legacy ledgers replay fine (`role=None` = pre-v0.2 verdict);
  aggregation treats `None` as `discriminating` **only** for pre-v0.2 killer-demo
  artifacts until ticket 08 regenerates them, and the regenerated artifacts carry
  explicit roles. This is a (small, honest) court schema change owned by ticket 08
  — the "court unchanged" claim belongs to ticket 02's gate, not to this ruling.
- **Direction-aware metric registry (amends spec G5).** The v0.1 registry is
  `{"sharpe": sharpe_ratio}`. Add an absolute form (e.g. `{"abs_sharpe": ...}`) or
  have the judge wrap the callable by `declared.direction`. The verdict `params`
  **must record the actual R name used** (`abs_icir` vs `sharpe`) — never silently
  `abs()` the matrix while recording `metric: "sharpe"`, or the ledger is not
  auditable.
- **PBO consistency assertion (refines `killer-demo.md` §5.3 wording).** φ is a
  **process-level** quantity (each combination has its own IS-argmax); it does not
  pin a single defendant. The correct assertion is: full-sample `argmax_i |SR_i|`
  (or `|t_i|`) equals the naive accused. The narrative must say "PBO judged the
  overfit probability of the selection **process** isomorphic to the naive scan on
  this matrix," not "PBO judged this defendant's overfit."
- **φ threshold 0.2 unchanged.** Under `|R|`, noise still gives φ≈0.5, so 0.2
  remains a *rule* threshold (not a size guarantee — `killer-demo.md` §5.4 already
  says so). Do not post-hoc tune 0.2; changing it means changing the
  pre-registration first.
- **DSR's orthogonal diseases persist.** Abstention fixes polarity/isomorphism, not
  DSR's ρ̂ ill-conditioning (spec C8) at T=480, M=100 (N̂≈M, weak correlation
  correction). Even when DSR is enabled (directional), do **not** claim
  "multiple testing + correlation perfectly handled."

## 5. Killer-demo narrative revision (Q3 consequence; ticket 08 regenerates)

`killer-demo.md` §6 (aggregation) and §7.2 ("five gates ~5% correlated") are
**superseded**: the survivor rule is "**all discriminating gates** pass," which
under the demo's `two-sided` selection is the four gates FDR + PBO(`|ICIR|`) +
pool-max + individual; **DSR is `informational`** (shown with its z-path, marked
"abstains under two-sided — one-sided DSR does not match a `|t|` selection"). The
headline (survivors = 0/100, accused `volatility_lb150_v14`, |t|=2.6655, killed by
pool-max) is **unchanged**. The committed `examples/killer_demo/out/` artifacts
regenerate under ticket 08 (real-data run) with the new battery-table roles and the
`|ICIR|` PBO metric.

## 6. Cross-references

- **Power calibration (ticket 01).** Under directional `greater` (β>0), DSR is
  **enabled** and PBO uses the **signed** metric — **not** `|metric|`. This is a
  **runtime branch on `declared.direction`**, not a demo-special patch; a power
  harness that fed `|metric|` would distort directional φ and make the numbers
  incomparable to the two-sided demo. `power-calibration.md` is patched to state
  this (its §9 already relied on β>0 exercising signed DSR/PBO).
- **Pre-registration gate (ticket 02) — the 02/03 seam.** The two-sided `|R|`
  isomorphism is correct for **association / predictive-strength discovery**
  (IC-type factors, the killer demo's stage). For **PnL strategy optimization**,
  `two-sided |SR|` is economically wrong (nobody trades the most-negative-SR
  config as "best"), so the pre-registration must **declare a directional
  hypothesis** there. Ticket 02's gate is what enforces that a PnL menu pre-registers
  directional; ticket 03 must not hard-code "always `|metric|`."

## 7. Deliverables (ticket 08)

- Direction-aware judge: gate `role` derivation, `informational` verdicts recorded
  but out of the survivor vote, direction-aware PBO metric with the R name in
  `params`.
- Spec amendments (G5 registry, a new applicability ruling pointing here) and the
  `killer-demo.md` narrative revision.
- Regenerated killer-demo artifacts (real-data, ticket 08) with the new roles.
- Tests: a "weak/idling gate counted in the survivor vote" red test that this
  ruling turns green; the direction-branch (two-sided → DSR informational, PBO
  `|R|`; directional → DSR enabled, PBO signed) as an explicit invariant.

## 8. v0.2 design-layer audit — revisions folded (2026-07-12)

Five-way blind milestone audit (archive `.scratch/dispatch/v02-design-audit/`,
verdict `verdict.md`). Ruling outcomes of v1 are all **unchanged**; what changed:

1. **D4 (major)** — §3's "three landmines" argument did not survive numerical
   re-derivation (two of three retired on the record; the abstention now rests on
   the one real landmine + the citation iron law). Caught by an independent panel
   against the auditing model's own re-verification — the dispute was settled by
   the referee's numerical integration.
2. **D5 (major)** — the `less` branch as literally written in v1 would have
   inverted the isomorphism (CSCV argmax on a raw signed metric); Q2 now pins the
   negated-metric / flipped-series forms, and mixed-direction scopes fail closed.
3. **D16** — `role` storage pinned (§4): optional `VerdictRecord` field,
   legacy-replay compatible, owned by ticket 08.
