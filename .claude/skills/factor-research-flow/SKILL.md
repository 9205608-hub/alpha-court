---
name: factor-research-flow
description: The upstream discipline for taking a factor / signal idea from hypothesis to a court-ready candidate — mechanism-first, then the net-of-cost / capacity / orthogonality lenses — before honest-validation judges it. Use when starting factor research, constructing a signal, deciding whether an idea is even worth backtesting, or asking whether an IC is economically real (not just statistically present). L1 discipline; alpha-court's adapter + court are the reference tools.
---

# Factor research flow

The pipeline from "I have an idea" to "this is worth bringing to court." Where
`/honest-validation` (禁赢学) decides whether a *result* is real, this skill governs
how you get there without fooling yourself **upstream** — before a single verdict is
computed. L1 discipline; alpha-court's `adapters` (`evaluate` / `evaluate_shifted`)
and `court` are the reference tools. It **composes with `quant-mentor`**, which holds
the elite judgment (interrogate the objective, falsify before you optimize, demand a
mechanism, think in capacity and net-of-cost); this skill sequences that judgment
into a repeatable flow and hands off to 禁赢学.

## 0. Interrogate the objective before optimizing it

What are you actually predicting — forward return over what horizon, which universe,
which rebalance? An IC against the wrong label is a precise answer to the wrong
question. Pin the label and universe *first* (alpha-court: label
`Ref($close,-2)/Ref($close,-1)-1`, t+1 close; universe = PIT membership) so every
number afterward means what you think it means.

## 1. Mechanism first — no mechanism, no factor

Before data: write **one sentence** on why this predicts returns — who is on the
other side of the trade, why the edge persists, why it hasn't been arbitraged away.
That sentence is the seed of the pre-registration (禁赢学 rule 1). A great IC with no
mechanism is overfit until proven otherwise; the mechanism is the thing you will
spend the rest of the flow trying to falsify.

## 2. Construct the signal without look-ahead

Point-in-time everything: PIT universe membership, no future data in the score at
time t, label aligned to tradable execution (t+1 close). Rank-based metrics (RankIC)
are invariant to monotone transforms — don't "improve" a factor with standardization
that changes no ranks; that's decoration, and decoration is where self-deception
hides. (alpha-court adapter: `evaluate(scores, "ic")`; long-short path
`(r_long − r_short)/2`.)

## 3. The three lenses — screen BEFORE the court, not after

A raw **gross** IC is a hypothesis, not an edge. Put it through three lenses before
it earns a court date:

- **Net-of-cost**: gross ≠ tradable. Charge the factor its turnover × cost; a
  fast-turnover signal needs a far larger gross edge to survive. State the cost
  basis explicitly (alpha-court prints "gross paper series — no transaction costs"
  in every figure — that is honesty, not a pass). A factor that only works gross is
  not a factor.
- **Capacity**: at what AUM does the edge decay? If it lives in microcaps or needs
  positions too small to move real money, say so. Think in capacity, not just IC.
- **Orthogonality**: is this edge already inside known factors (momentum, value,
  size, vol)? Regress them out and look at the residual — that is your real alpha.
  A signal that is 90% momentum *is* momentum with extra steps.

A candidate that clears its mechanism **and** all three lenses earns a court date.
One that doesn't is archived with the same documentation weight as a winner
(禁赢学: null = survivor) — not buried.

## 4. Hand off to the court under pre-registration

Fold the mechanism, cost basis, capacity estimate, and orthogonality result into the
pre-registration doc, then run `/honest-validation`: freeze seeds / thresholds /
aggregation, run the declared battery (`court.judge`), read the verdicts honestly.
`scripts/prereg-gate.sh` enforces that the pre-registration precedes the results.
**This skill produces the pre-registration; 禁赢学 judges what comes back.**

## Hooks: what's mechanizable, and what alpha-court can't enforce yet (grok #4 correction)

An earlier draft claimed "no hook, because the three lenses are judgment." That washed a
gap into a virtue. The truth: once you **freeze** the cost model and the known-factor set,
parts of every lens become predicates that *should* be gates —

- net-of-cost → a `turnover × bps` net-IC / Sharpe floor (isomorphic to the DSR line);
- orthogonality → a residual-IC / R² cap after regressing out the frozen factor set;
- capacity → an ADV-participation / position floor.

None of these exist yet: alpha-court v0.1 is a **gross paper-series** stack (no cost model,
no factor-neutralization code), so net-of-cost and residual-IC here are **aspirational — a
declared v0.2 gap, not a discipline the current tooling can enforce**. What genuinely stays
skill is the judgment (*which* cost model? *which* factor set? capacity defined how?); the
frozen-param predicates above are **DESIGNED, not built**. The only thing enforced today is
downstream and weak: the pre-registration this flow produces is guarded by `prereg-gate.sh`
(commit-ordering only). Don't read "no hook" as "nothing to build" — read it as "the muscle
isn't here yet, and we say so."

## See also

`quant-mentor` (the judgment this operationalizes), `/honest-validation` (禁赢学, the
downstream judge), `docs/design/adapter-interface.md` (`evaluate` / `evaluate_shifted`,
RankIC and quantile long-short conventions, PIT membership), `docs/design/killer-demo.md`
(cost-basis honesty in practice).
