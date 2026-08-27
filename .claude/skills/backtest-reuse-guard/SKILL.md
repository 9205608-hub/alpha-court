---
name: backtest-reuse-guard
description: The engineering-reuse station (工位三) — reuse the existing oracle, don't NIH-rebuild it. Use before writing ANY numeric line in factor/research code — a Sharpe, an IC, a DSR/PBO/BHY/empirical-null, a PnL loop, a trading calendar, a PIT mask — and whenever you're tempted to hand-roll a statistic instead of calling the audited one. qlib gives returns/IC, vectorbt/openalgo gives the backtest loop, court gives the validation statistics (DSR/PBO/BHY/empirical-null); you write only the factor + the orchestration, and court/ never imports market code. L2 engineering discipline; alpha-court's `court` + qlib-cn adapter + the decoupling smoke test are the reference.
---

# Backtest-reuse guard (回测复用护栏 · 工位三)

**Reuse the oracle; don't rebuild it.** Almost every number in a factor pipeline —
the Sharpe, the IC, the deflation, the overfitting probability, the PnL curve, the
trading calendar — is a *solved* problem with an audited implementation already in
reach. The only two things a research task legitimately adds are **the factor score
function** and **the orchestration glue** that wires existing parts together. This
station is the engineering discipline that keeps you inside that thin waist: it is
the research pipeline's **anti-NIH gate**. It sits beside `data-pipeline-hygiene`
(工位一, the bytes) and `research-session-protocol` (工位二, the search) as the third
pre-court station — the one that guards your *code*.

It is useful **even if you never run alpha-court**: the moment you reach for
`np.corrcoef` to "just quickly" compute an IC, or write a `for day in dates:` equity
loop, this station is the thing that stops you. The court is only the most demanding
consumer of the discipline.

Its ethos is 禁赢学 pushed into the codebase: **a hand-rolled statistic is a
validation bypass.** A private Sharpe that forgets the skew/kurtosis standard-error
correction, an IC that uses Pearson where the contract says Spearman, a DSR with the
wrong number-of-trials — each is a *divergent duplicate* that hands you a friendlier,
unreviewed number than the audited oracle would. NIH here is not wasted effort; it is
self-deception with an off-by-one.

## 0. The thin waist — what is actually yours to write

Before writing numeric code, know the split. Everything on the left already exists;
you write only the right (`adapter-interface.md` §1: the orchestrator "knows both
sides — registers trials, calls the adapter, records series into the ledger, invokes
the judge"):

- **Reuse (never re-implement):** every statistic on a return/IC series, every
  factor→forward-return evaluation, the PnL loop, the calendar, the universe mask,
  the data loaders. §2 is the register.
- **Write (the waist):** (a) the **factor score** — the panel of scores you believe
  predicts returns; (b) the **orchestration** — register the trial, call the
  adapter, record the series into the ledger, invoke `court.judge`. That is the whole
  job. If your diff grows a second Sharpe or a second IC, you left the waist.

## 1. The reuse-vs-build decision (判据) — run it before the first numeric line

For any number you are about to compute, walk this in order and stop at the first hit:

1. **Is it a statistic on a return/IC/PnL series** (Sharpe, PSR, DSR, PBO, FDR,
   empirical-null, t, p, deflation, moments)? → it is in `court`. **Reuse.** If it is
   *genuinely* new **and** market-agnostic, it goes **into `court`** as a pure
   numpy/pandas/scipy function tested against a published reference — **never** inline
   in factor code, **never** with a market import.
2. **Is it a factor-vs-forward-return evaluation** (RankIC, quantile long-short)? →
   adapter `evaluate` / `evaluate_shifted`, which wrap qlib's `eva.alpha`. **Reuse.**
   A new *market rule* (calendar, membership mask, label, tradability) goes **into
   `adapters/`**, never into `court`.
3. **Is it a full PnL backtest** (positions → equity → drawdown → turnover)? →
   **vectorbt / openalgo** (the user's engine). Do **not** hand-roll a day-loop.
   And note the court needs no backtest at all: it eats the *series*, and the adapter
   is contractually **forbidden** to invoke qlib's backtest stack (`adapter-interface.md`
   §4.5).
4. **Is it data loading / calendar / universe** (K-line, fundamentals, membership)? →
   `qlib.data.D` or **baostock**, through the adapter. **Reuse** — never synthesize a
   calendar or freeze a universe by hand (that is also 工位一's T1/T8).
5. **Only what survives all four** — the factor score and the glue — is yours.

The load-bearing corollary is **where a new thing goes**, which is the decoupling law
(§3): a new *statistic* → `court` (no market import, ever); a new *market rule* →
`adapters/`; *both-sides* glue → the orchestrator (`examples/`). Putting a market
assumption into `court` is the one architectural mistake this station exists to stop.

## 2. 别重造这些 — the do-not-rebuild register

Each row is a capability people re-implement "just this once," and the exact thing to
call instead. In-repo targets are `[LANDED]` code; external targets are the user's
real stack.

| Capability (do NOT hand-roll) | Reuse this | Where |
|---|---|---|
| Sharpe, annualized SR, PSR, **SR standard error (skew/kurtosis-adjusted)**, moments | `court.sharpe`: `sharpe_ratio`, `annualized_sr`, `psr`, `sr_standard_error`, `sr_var_factor`, `series_moments` | in-repo [LANDED] |
| **Deflated Sharpe** + expected-max-SR + implied independent trials + avg pairwise ρ | `court.dsr`: `dsr`, `expected_max_sr`, `implied_independent_trials`, `avg_pairwise_correlation` | in-repo [LANDED] (Bailey & López de Prado) |
| **PBO** (probability of backtest overfitting) via CSCV | `court.pbo`: `pbo_cscv` | in-repo [LANDED] (Bailey, Borwein, LdP, Zhu) |
| **Multiple-testing / FDR** family correction | `court.fdr`: `fdr_by` (Benjamini–Yekutieli 2001; the project's "BHY" notes), `fdr_bh` (BH), `harmonic_number` | in-repo [LANDED] |
| **Empirical null** p̂ (Phipson–Smyth add-one; pool-max ≈ White Reality Check *semantics*) | `court.noise`: `empirical_null_p` | in-repo [LANDED] |
| t-statistic, p-from-t | `court.tstats`: `t_stat`, `p_from_t` | in-repo [LANDED] |
| **RankIC** (Spearman) and **quantile long-short** return | `QlibCNFactorEvaluator(...).evaluate(scores, "ic")` / `.evaluate(scores, "returns")` — a *method*, not a free function — wrapping qlib `calc_ic` (`ric`) / `calc_long_short_return` | in-repo adapter [LANDED]; qlib is the semantic oracle |
| **Forward-return label** + t+1/t+2 execution alignment | adapter `DEFAULT_LABEL_EXPR = "Ref($close, -2)/Ref($close, -1) - 1"` (qlib Alpha158/360 convention) | in-repo [LANDED] |
| **Trading calendar** + evaluation-date set | qlib `D.calendar()` via adapter `_evaluation_dates_from_calendar`; baostock trading days | qlib/adapter [LANDED]; baostock external |
| **PIT universe membership mask** | adapter `_build_pit_mask` (qlib interval filtering) | in-repo [LANDED] |
| **Full PnL backtest loop** (positions→equity→drawdown) | **vectorbt / openalgo** | external (user's engine); the adapter is forbidden to build one (§4.5) |
| Data loading (K-line, fundamentals, membership) | `qlib.data.D` / **baostock** | external, via the adapter |

Rule of thumb: if the thing you're about to write reduces a *series of returns or ICs*
to a scalar or a verdict, it is already in `court`; stop and import it.

**The table above is the *in-repo oracle map* — L2 binding to this stack, not portable
muscle.** The run-anywhere tooth is the §1 decision ladder, the §4 thesis, and these
**greppable anti-patterns** — each is a hand-rolled duplicate of something audited, and each
survives without alpha-court:

- a re-implemented **Sharpe** (`def …sharpe…`, or inline `.std(` / `np.std(` with a 244/250/252
  annualization) — missing the skew/kurtosis SE. Call the audited one.
- a **correlation used as an IC** (`corrcoef`, `.corr(` / `.corrwith(`, `spearmanr` / `pearsonr`)
  — Pearson/aliased where the metric should be the adapter's Spearman.
- a hand-rolled **equity/PnL curve** (`for … in …dates:`, or `equity = (1+ret).cumprod()`) — use
  vectorbt / openalgo.
- a re-implemented **court statistic** (`def …pbo…` / `…deflat…` / `…t_stat…`) beside the kernel.

These are mechanized as a **[LANDED, high-recall] cheap-knife gate** — `harness/anti_pattern_gate.py`
(`python -m harness.anti_pattern_gate <factor-dir>`, exit 1 on a hit). It **anchors** to a `def` /
inline formula / named correlation — *not* bare tokens — so it does **not** bark on the audited
`court` source, a legitimate court *call*, a comment, or a config string; it excludes the audited
dirs by path **component** (this repo lives under `alpha-court/`, where a substring exclusion would
skip everything); and it **reports** rather than silently skips `.ipynb` notebooks. Honest limits it
structurally cannot catch (pinned in `tests/test_anti_pattern_gate.py`): hand-*expanded* arithmetic
— a DIY Pearson, or the worst duplicate, a Sharpe SE that drops the skew/kurtosis correction — plus
aliased/renamed defs, multi-line splits, and notebooks. It surfaces candidates for you to reuse-away
or justify; advisory and manual (CI wiring stays [DESIGNED]). Its bypass set was enumerated by a
4-lens adversarial workflow — a one-mind bypass list misses half.

## 3. The decoupling law — court/ never imports market code (the tooth)

The iron law (CLAUDE.md #2, `adapter-interface.md` §1): `court/` knows arrays and
statistics and **never imports adapters, qlib, baostock, or any market module**; all
market knowledge — calendars, 涨跌停, universe definitions — lives in `adapters/`. This
is not style: a market import inside `court` lets a market assumption leak into the
"market-agnostic" judge, so the same statistics can no longer be trusted on another
desk's data, and the portability the whole kernel promises quietly dies.

**The tooth [LANDED]:** `tests/test_smoke.py::test_court_market_agnostic` spawns a
fresh subprocess, `import court`, and asserts that **no** `qlib*` or `adapters*` module
landed in `sys.modules` — a runtime proof that importing the judge pulls in zero market
code. `court/__init__.py`'s runtime deps are numpy/pandas/scipy only; `pyproject.toml`
keeps `pyqlib` in an *optional* extra.

**Honest limit of the tooth.** The smoke test catches **import-time** coupling only —
a top-level `import qlib` in any court module. A *lazy* `import baostock` buried inside
a court function body would pass the smoke test and still violate the iron law. And the
test only runs when you run `pytest`: it is **not** wired into any `scripts/` gate or
pre-commit/CI hook today (grep confirms no gate references it). So the guarantee is
"the import path is clean," not "no market symbol can ever appear in `court/`" — that
stricter, static check is `[DESIGNED]` (§ Honest form).

## 4. Why a divergent duplicate is worse than a duplicate

Plain duplication wastes time. A *divergent* duplicate corrupts a verdict, because the
copy is always the friendlier one:

- your private Sharpe drops the skew/kurtosis SE term (`court.sr_standard_error`) → an
  inflated t → a factor that "passes";
- your quick IC is Pearson, not the contract's Spearman `ric` → a different, unreviewed
  number, often outlier-inflated in *either* direction on fat-tailed cross-sections;
- your DSR uses `n_trials = 1` because you forgot the search you ran → no deflation at all.
  (The audited path avoids this *structurally*: the `judge` counts multiplicity from the
  trials in the ledger scope — 工位二's honest N — so you cannot under-report it by passing a
  number; you under-report only by failing to register the trials you ran.)

None of these is caught by a test, because there is no second implementation to
disagree with — that is the whole point of not writing one. The audited oracle is
audited *once*; every hand-roll is an un-reviewed fork of the exact arithmetic the
court exists to get right. Reuse is not tidiness here; it is keeping the number you
believe identical to the number that was verified.

## A worked example

You have a candidate factor and want "the Sharpe and whether it survives." The NIH
path: `ret.mean()/ret.std()*sqrt(252)`, eyeball it against a threshold, ship. Three
silent errors — no skew/kurtosis SE, no deflation for the 20 variants you tried, no
overfitting check — and the number is optimistic in a way you cannot see. The
reuse path is the thin waist: build the score panel (yours), `evaluate(scores, "ic")`
for the series (adapter), record it to the `Ledger` (glue), then call
`court.judge(ledger, scope, [Application("dsr", {...}), Application("pbo_cscv", {...}),
Application("fdr_by", {...}), Application("noise_control", {...})])`. Note the exact API,
because getting it wrong is itself the anti-pattern: `Application` is a
`NamedTuple(statistic, params)` built **positionally** (`court/judge.py`), and the
statistic name for the empirical null is **`"noise_control"`**, not `empirical_null_p`.
You wrote a factor and a few lines of orchestration; every statistic came from the audited
kernel, and — because you registered *every* trial you ran into the ledger scope, not just
the winner — the judge derives DSR's multiplicity from that scope size (工位二's honest N, made
structural: you can't under-report it by passing a number, because a judge-path `n_trials`
param is silently ignored — the count *is* the ledger). The only new code is the idea.

## What this is NOT — boundary

- **vs `court` (the validator itself).** `court` *is* the oracle you reuse; this
  station is the discipline of **reusing it instead of forking it**. The court computes
  the Sharpe/DSR/PBO; this skill is the reason you never write a second one. `court` is
  a library; this is a rule about how you consume it (and where new statistics are
  allowed to live).
- **vs `data-pipeline-hygiene` (工位一, the bytes).** 工位一 audits the *data* for
  look-ahead / survivorship / PIT contamination — a *correctness-of-input* gate. This
  audits your *code* for re-implementation and coupling — a *don't-rebuild / stay-decoupled*
  gate. A pipeline can be byte-clean (工位一 passes) and still carry a hand-rolled,
  divergent Sharpe (工位三 fails), and vice-versa.
- **vs `research-session-protocol` (工位二, the search).** 工位二 counts *how many
  variants you tried* (the honest N). This governs *how much code you wrote to try
  them*. They meet at one seam — 工位二's honest N must show up as the trials you **register
  into the ledger scope** (the `judge` derives DSR's `n_eff` from scope size; only a *direct*
  `court.dsr` call takes `n_trials` as a param) — but 工位二 is about search multiplicity, this
  is about code reuse.
- **vs `factor-research-flow` / `honest-validation`.** Those are *research* discipline —
  is the idea economically real, is the *result* believable. This is *engineering*
  discipline — is this line of code something that already exists. Orthogonal axes; a
  well-reasoned factor can still be shipped on top of three re-implemented statistics.
- **vs `quant-mentor` / `quant-analyst` / `vectorbt-expert` / `risk-manager`.** Those
  teach you how to *build* signals, backtests, and risk models. This station is the
  restraint that says **don't build the parts that already exist** — it points you *at*
  `vectorbt-expert`/openalgo for the PnL loop and at `court` for the statistics, rather
  than reproducing either. It adds no how-to-backtest knowledge; it removes duplication.
- **Not a generic DRY / NIH lecture.** The teeth are specific and checkable: the exact
  `court` + adapter + qlib/vectorbt/baostock symbols you must not re-implement (§2), the
  court↔market decoupling law with a **landed** dynamic smoke test (§3), and the routing
  rule for where a genuinely-new statistic vs market-rule is allowed to live (§1 tail / §3). A
  generic "don't repeat yourself" tool knows none of these.

## Honest form (D1) — what's built vs designed

This station is a **skill** (an L2 engineering discipline: a decision procedure + a
reuse register + the decoupling law), **not** a new hook and **not** a memory. Its
deliverable is §1's judgment, §2's register, and §3's law.

- **[LANDED]** — the reuse *targets* are all real code: the full `court` statistical
  library (`sharpe`/`dsr`/`pbo`/`fdr`/`noise`/`tstats`) + `judge` + `ledger`; the
  qlib-cn adapter (`evaluate`/`evaluate_shifted`, `_build_pit_mask`,
  `_evaluation_dates_from_calendar`, `DEFAULT_LABEL_EXPR`, the fail-closed guard); and
  the **decoupling smoke test** `tests/test_smoke.py` (`test_court_market_agnostic` +
  `test_packages_importable`), which runs under `pytest`. vectorbt/openalgo/baostock are
  LANDED *in the user's stack*, not in this repo.
- **[LANDED, advisory]** — a **reuse lint**, `harness/anti_pattern_gate.py` (10 tests). It
  scans factor/research `.py` and flags candidate re-implementations: a `def sharpe`, an IC
  from `corrcoef`/`.corr(`/`spearmanr`/`pearsonr`, a `cumprod` equity curve, a
  `def dsr/pbo/fdr/…`. **High-recall, not precise** — it also barks on a legitimate `.corr(`,
  a vol `std*sqrt`, or a diagnostic `cumprod` (a human justifies or reuses-away), and it
  cannot see hand-*expanded* arithmetic (a DIY Pearson; the worst duplicate, a Sharpe SE that
  drops the skew/kurtosis correction), aliased/renamed defs, multi-line splits, or `.ipynb`
  (reported-skipped, never silent). Advisory + manual.
- **[DESIGNED, not built]** — (1) **wiring** the reuse lint + the decoupling smoke test into a
  **pre-commit / CI gate** (today both only run if invoked; no `scripts/` gate fires them);
  (2) a **static (AST)** import-boundary check for `court/` — the smoke test is dynamic and
  import-time-only, so a lazy in-function market import slips past it; an AST reuse-lint would
  also close the hand-expanded-arithmetic and aliasing holes the grep cannot.
- **[discipline only]** — the reuse-vs-build *decision* (§1) and "is this genuinely new"
  are judgment; no predicate decides them. The muscle isn't wired yet, and we say so.

## See also

`court` public API (`judge`, `dsr`, `pbo_cscv`, `fdr_by`, `empirical_null_p`,
`sharpe_ratio`, `psr`, `Application`, `Ledger`), `adapters/qlib_cn.py`
(`evaluate`/`evaluate_shifted`, `_build_pit_mask`), `docs/design/adapter-interface.md`
§1 (decoupling law), §4.1 (qlib `eva.alpha` oracle), §4.5 (no backtest engine), §5
(market-specific handling), `tests/test_smoke.py` (the landed decoupling tooth),
`data-pipeline-hygiene` (工位一, the bytes), `research-session-protocol` (工位二, the
honest N — registered as ledger scope, from which the judge derives DSR multiplicity), the installed `vectorbt-expert` / `setup` /
`backtest` / `baostock` skills (the external engine + data stack this routes you to).