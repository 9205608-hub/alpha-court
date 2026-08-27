---
name: honest-validation
description: 禁赢学 — the discipline for deciding whether a factor / signal / strategy result is real rather than overfit. Use before believing ANY backtest, factor IC, or strategy PnL; when pre-registering a study; when reading DSR/PBO/FDR/empirical-null verdicts; whenever tempted to re-run with a nicer seed or a looser threshold. L1 discipline (transferable to any shop); alpha-court's `court` is the reference validator.
---

# Honest validation (禁赢学)

**The backtest tells you how good the idea *looked*; honest validation tells you
whether to *believe* it.** Every result is overfit until it survives a test it
could have failed. This is the L1 discipline — transferable to any desk or tool;
alpha-court's `court` kernel is its reference implementation. It **composes with
`quant-mentor`** (economic mechanism, capacity, orthogonality — the judgment) and
is the *operational protocol* that makes that judgment enforceable.

Worked example to read first: `docs/design/killer-demo.md` §7 is a real
pre-registration; the demo ran it and the court rejected **100/100** pure-noise
"discoveries" (survivors = 0/100). That is this skill, executed.

**Honest scope (grok #4 RP-1 correction).** Most of the prose rules below —
pre-register, don't cherry-pick tests, don't seed-fish — are research-integrity
baseline (Bailey & López de Prado), not a differentiator for a serious desk. The
real increment over `quant-mentor` is narrow and concrete: the executable
`court.judge` battery binding, null-archived-with-equal-weight, and the (currently
weak) prereg-gate. Read this as **operational wiring for `court`**, not novel judgment.

## 1. Pre-register before you touch the data  (the load-bearing rule)

Freeze, in a **committed** doc, BEFORE the first real run: the hypothesis + its
economic mechanism, the seeds, the decision thresholds, the aggregation rule, and
the **expected magnitudes** (killer-demo §7.2 writes "max |t| median ≈ 2.70" down
*before* running). The doc's commit must **precede** the results commit —
`scripts/prereg-gate.sh <prereg-doc> <results-path>` fails if results were
committed first. Amendments require a dated changelog entry, written *before*
re-running. No pre-registration, no belief.

**Honest limit of the tooth (grok #4).** `prereg-gate.sh` enforces commit
**ordering only**, not content freeze: it cannot stop you committing a stub
pre-registration, seeing results, then backfilling looser thresholds (the file's
first-add time is unchanged, so it still passes). The real tooth — the
pre-registration's seeds / thresholds / aggregation / cost-basis **hashed into
`run_config` and matched at judge time**, amendment = new version + new hash — is
**DESIGNED, not built**. Until then, prereg-gate guards against gross inversion, not
against dishonesty; that guarantee is yours, and the seed-sweep (rule 4) is its
empirical check.

## 2. Run the declared battery — never cherry-pick the test that passes

Complementary tests catch different lies, and you commit to all of them up front:
- `fdr_by` — multiplicity (you tested many things);
- `dsr` — deflated Sharpe (you tried many configs);
- `pbo_cscv` — backtest overfitting (IS-best falls below OOS median);
- `empirical_null_p` — pool-max (White 2000 Reality Check) + per-candidate.

L2 binding: one `court.judge(ledger, scope, [Application(...), ...])` call; the
Application list and order are in `killer-demo.md` §5.2 / `examples/killer_demo/battery.py`.
Running only the gate that clears your factor is seed-fishing by another name.

## 3. Aggregation is pre-committed and strict

**Unanimous — one rejection kills; headline = survivors / N.** You do not invent a
lenient aggregation after seeing results. Polarity is a landmine: statistical
discovery ⟺ court `"pass"` (kernel ruling G2) — test the reversal in both directions.

## 4. Read the verdict honestly — the 禁赢学 core  (killer-demo §7.3)

- Results are reported **as they come out**.
- **Null = survivor**: an archived null gets the *same* documentation weight as a
  winner. No file-drawer; the morgue table and any survivor share one template.
- **No seed-fishing**: never re-roll to hit a rounder number. Report the
  pre-registered seed's realized value — "typically 2.5–3.2", not "3".
- **No post-hoc threshold tightening; never relabel a survivor as a bug.** A
  survivor is the *realization of your declared error rate* — not a triumph, not an
  embarrassment. (~5 individual passes at α=0.05 over 100 is calibration, not a leak.)
- Single-run luck → run the pre-registered **seed sweep**, report every seed, check
  per-gate pass frequencies sit near their declared α (killer-demo §7.4).

## 5. Prosecute the selection, not the statistic

The per-factor arithmetic is usually *fine* — under the null the daily-IC t is
≈ N(0,1). The inflation lives in **max-over-N** (garden of forking paths). Sign
flips count: a "great contrarian discovery" doubles the arms (two-sided ⇒ effective
2N). The court never disputes your t; it disputes your **inference**
(killer-demo §4.1 mechanism note).

## 6. Survivors are not believed until forward out-of-sample confirms them

Clearing the battery earns a factor a hearing, not belief. Belief comes from **delayed
out-of-sample** — a held-back forward window the factor has never touched, or paper
trading, watched live. The market is the out-of-sample, not a reviewer.

> grok #4 cut the earlier version of this rule, which made an LLM cross-model refutation
> the belief threshold. That conflated the workflow's *process* self-governance (RP-1,
> which reviews rules and skills) with a *factor* belief standard — process astronaut,
> not alpha. RP-1 keeps this skill honest; it does not certify a factor.

## Determinism

Seed tree from one master seed (no naked `default_rng()` anywhere); a run manifest
(seeds, thresholds, window, `data_version`, engine versions) makes the chain
factor → series → verdict replayable from the manifest alone (killer-demo §9).

## See also

`docs/design/killer-demo.md` §7 (禁赢学 operationalized, worked to 0/100),
`court` public API (`judge`, `dsr`, `pbo_cscv`, `fdr_by`, `empirical_null_p`,
`Application`), `quant-mentor` (the judgment layer this wires up), `factor-research-flow`
(the upstream that produces the pre-registration), `scripts/prereg-gate.sh` (the tooth —
commit-ordering only today; content-hash binding is DESIGNED).
