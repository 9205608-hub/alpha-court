# Adapter Interface & Factor Evaluation Conventions — Contract (v0.1)

**Provenance:** decided 2026-07-10 in ticket `.scratch/v0.1/issues/10-adapter-interface.md`
(HITL grilling; all six rulings confirmed by the project owner).
**Consumers:** the killer-demo design (ticket 11) takes the evaluation conventions and the
shifted-grid surface from here; adapter implementation tickets take the API contract (§7);
the court kernel spec (ticket 08) cross-checks the series shape (§3) against
`docs/design/trial-ledger.md` §5.2/§7.2.
**Depends on:** `docs/design/trial-ledger.md` (series contract, fail-closed alignment);
`docs/design/noise-control.md` (circular-shift generation protocol §3, common-offset grid §5);
`docs/research/qlib-cn-data.md` (measured data facts, ticket 09).
**qlib version:** every API citation refers to **pyqlib 0.9.7** (paths as laid out in the
0.9.7 wheel). Version bumps must re-verify the cited signatures.
**Scope:** interface and conventions contract only. No implementation in this document.

---

## 1. Purpose and position

`adapters/qlib_cn` is the **only gate between the court and the market**. The constitution's
decoupling law fixes the layering:

- `adapters/` knows qlib, pandas, trading calendars, universes, and every market-specific
  rule. It produces performance series as plain labeled arrays.
- `court/` knows arrays and statistics. It never imports adapters and never interprets
  series index labels (`docs/design/trial-ledger.md` §9).
- `examples/` (the demo runner) is the orchestrator that knows both sides: it registers
  trials, calls the adapter, records series into the ledger, and invokes the judge.

Two corollaries that are contractual, not stylistic:

1. **The adapter never touches the ledger.** Registering hypotheses/trials and recording
   series are the orchestrator's verbs. The adapter is a pure evaluation service.
2. **The adapter never computes court statistics.** Ranking statistics (t, |t|), p-values,
   and decisions are court pure functions (`docs/design/noise-control.md` §2). The adapter
   returns series; reduction happens on the court side.

## 2. The six rulings

1. **Metrics (§3, §4):** both evaluation paths are implemented — daily cross-sectional
   RankIC and quantile long-short returns. `declared.metric` values `"ic"` and `"returns"`
   are both real. The killer demo's primary metric is **RankIC**; the long-short view is a
   companion (whether it appears in the demo figure is ticket 11's call).
2. **Forward return & costs (§4.2, §4.4):** the label is qlib's official convention
   `Ref($close, -2)/Ref($close, -1) - 1`. Transaction costs, market impact, and turnover
   penalties are **not modeled** in v0.1 — both series are gross paper series, declared as
   such in adapter metadata, this contract, and the demo figure caption.
3. **Data conventions (§4.3, §6):** prices come from `$close` (the qlib-adjusted series);
   `$adjclose` is declared unused. The data pack is pinned to a fixed release tag of
   `chenditc/investment_data` (currently **`2026-07-05`**), with a documented bump procedure.
4. **Market-specific minimal handling (§5):** universe is csi300 with **dynamic
   point-in-time membership** (qlib interval filtering). Suspensions/missing data are
   handled by per-day pairwise NaN exclusion plus a fail-closed minimum cross-section
   guard. ST filtering, limit-up/down tradability, and suspension-at-execution are
   declared not handled.
5. **API (§7):** two entry points, `evaluate` and `evaluate_shifted`, routed through one
   shared kernel; qlib's `eva.alpha` functions are the semantic oracle in tests.
   Series index labels are ISO date strings of the signal date t.
6. **Determinism (§8):** bit-for-bit reproducibility is promised at the pinned-environment
   level (same machine, locked dependencies, same data tag), enforced by `kernels=1`,
   canonical sorting, zero adapter-side RNG, and a two-layer test battery. Cross-platform
   bit identity is explicitly **not** promised.

## 3. Series contract — what the court eats

The adapter's output plugs directly into `ledger.record(trial_id, series)`
(`docs/design/trial-ledger.md` §5.2, §7.1):

```
series = {index: [label, ...], values: [number, ...]}
```

- **`metric = "ic"`** — one value per evaluation date: the cross-sectional **Spearman rank
  correlation** between the day's factor scores and the day's forward returns (RankIC).
  This is the `ric` output of `qlib.contrib.eva.alpha.calc_ic` (§4.1).
- **`metric = "returns"`** — one value per evaluation date: the equal-weighted quantile
  long-short paper return `(r_long − r_short) / 2`, the first output of
  `qlib.contrib.eva.alpha.calc_long_short_return` (§4.1). The `/2` halving is qlib's
  convention and is kept as-is; court statistics built on t-ratios are scale-invariant,
  so the halving does not affect any verdict.
- **Index labels:** ISO `"YYYY-MM-DD"` strings of the **signal date t**, generated from the
  qlib trading calendar. Opaque to the court (equality comparison only), human-auditable in
  `ledger.jsonl`. The evaluation date set is defined in §5.2; it is a pure function of
  (calendar, declared window), so every trial evaluated under the same window shares an
  identical index and `ledger.matrix()`'s fail-closed label-for-label alignment passes by
  construction.
- **Finiteness:** every value in `values` is a finite float. The adapter **raises instead
  of emitting** any NaN/inf (see §5.3 guard) — aligned with `ledger.record`'s fail-closed
  non-finite policy. A day whose cross-section degenerates (below the guard, or zero score
  variance) is an error, never a silent NaN.

Annualization: series are native daily frequency; `declared.periods_per_year = 252` is
display-only metadata composed by the orchestrator (`docs/design/trial-ledger.md` §5.2).

## 4. Evaluation paths — qlib citations and conventions

### 4.1 Semantic reference functions (pyqlib 0.9.7)

Both live in `qlib/contrib/eva/alpha.py`:

- `calc_ic(pred, label, date_col="datetime", dropna=False) -> (ic, ric)` — per-date
  cross-sectional Pearson (`ic`) and Spearman (`ric`) correlations via pandas groupby.
  The adapter's `"ic"` metric is defined as **`ric`** (Spearman). Pearson IC is not part
  of this contract.
- `calc_long_short_return(pred, label, date_col="datetime", quantile=0.2, dropna=False)
  -> (long_short_r, long_avg_r)` — per-date equal-weight means of the top/bottom
  `int(n × quantile)` names by score (`nlargest`/`nsmallest`), long-short defined as
  `(r_long − r_short) / 2`. The adapter's `"returns"` metric is defined as
  **`long_short_r`** with default `quantile = 0.2` (a declared parameter, recorded in
  metadata; docstring requires `label` to be raw per-period stock returns, which §4.2
  satisfies).

Tie handling note: `nlargest`/`nsmallest` break score ties by position, i.e. by input row
order. Combined with §8's canonical instrument sort this is deterministic; ties have
measure zero for the demo's continuous scores, and the oracle tests (§7.5) use tie-free
synthetic panels.

### 4.2 Forward return (label)

```
label(t) = Ref($close, -2) / Ref($close, -1) - 1
```

evaluated per instrument on signal date t: score observed at t's close, position entered
at t+1's close, held to t+2's close. This is qlib's own benchmark convention — Alpha158
and Alpha360 both ship exactly this label (`qlib/contrib/data/handler.py`, lines 90 and
152 in 0.9.7). Rationale: the one-day execution gap avoids the implicit "trade at the same
close the signal was computed from" lookahead and is honest about A-share T+1 reality.
The naive `Ref($close, -1)/$close - 1` variant is rejected for v0.1.

### 4.3 Price field

Returns are computed from **`$close`**, the qlib-adjusted price series used by the entire
qlib ecosystem (the Alpha158 label above uses it verbatim). `$factor` (zero NaN in the
measured pack) recovers the cash price as `$close / $factor` when a market-rule check ever
needs it. **`$adjclose` is declared unused**: it is a community-pack-specific second price
series with unreconciled scale (`docs/research/qlib-cn-data.md` §3.3, §3.5); depending on
it would couple the adapter to one pack's private field.

### 4.4 Costs and turnover — not modeled, declared

Both series are **gross paper series**: no commissions, no slippage, no market impact, no
turnover penalty. Reasons of record: the court judges statistical validity, not
tradability; a cost model imports a pile of market-specific free parameters; and the
noise-control jury preserves turnover by construction (`docs/design/noise-control.md`
§3.2), so the cost exemption applies equally to candidates and jurors — fairness of the
trial is unaffected. Cost modeling would only make a fake alpha look worse; rejection
conclusions are conservative without it. The declaration string
`"gross paper series — no transaction costs, no market impact"` appears in every
`EvalResult.meta` (§7.4) and must appear in the demo figure caption (ticket 11).

### 4.5 No backtest engine

The adapter must **not** invoke qlib's backtest stack (executor / exchange /
`backtest_daily` / strategy classes). This is the constitution's "no backtest system"
rule applied at the API level, and it is also forced by arithmetic: the 100×199 noise grid
(§7.3) cannot afford seconds-to-minutes per cell. The adapter's whole market surface is
data loading (`qlib.data.D`) plus the §4.1 evaluation semantics.

## 5. Market-specific minimal handling set

Everything in this section is invisible to the court — it happens before series leave the
adapter.

### 5.1 Universe: csi300, dynamic point-in-time

`D.instruments("csi300")` with qlib's interval filtering: each stock enters the daily
cross-section only during its recorded index-membership span. This is qlib-native (zero
custom code), free of survivorship bias, and matches the measured pack (939 historical
members; 336 with data in the 2024-07→2026-07 window). Cross-section width floating with
index rebalances is normal and declared. A fixed start-of-window snapshot and the
all-market universe were rejected for v0.1.

### 5.2 Calendar and evaluation dates

The qlib trading calendar (`D.calendar`) is the only calendar. For a declared window
`[start, end]`:

```
evaluation dates = { t ∈ calendar ∩ [start, end] : t+1 and t+2 exist in calendar and t+2 ≤ end }
```

i.e. signal dates whose full label horizon fits inside the window. The last two trading
days of a window carry no forward return and drop out for every candidate identically.

### 5.3 Suspensions & missing data: pairwise exclusion + fail-closed guard

The measured pack shows two missing-data shapes (`docs/research/qlib-cn-data.md` §3.4):
missing rows against the calendar and NaN OHLCV rows (`$factor` stays filled). Policy:

- A cell (date, instrument) enters the day's cross-section **iff** the instrument is a PIT
  member that day **and** both its score and its label are finite. No forward-filling, no
  imputation — a suspended stock simply leaves the cross-section for the affected dates.
- **Minimum cross-section guard:** if any evaluation date's usable cross-section falls
  below `min_cross_section` (default **50** for csi300), the adapter raises — fail-closed,
  never a NaN leaked into a series. At quantile 0.2 the guard also keeps ≥10 names per
  long-short leg.
- Score panels may legitimately have NaN cells (factor undefined for late listings);
  the same pairwise rule covers them.

### 5.4 Declared not handled (v0.1 honesty list)

- **ST/\*ST filtering:** none. CSI 300 index rules already exclude ST names; residual
  exposure in the PIT window is negligible and accepted.
- **Limit-up/down tradability:** the paper convention assumes entry at t+1's close even
  when a limit move would have made the fill impossible. Same nature as the cost
  exemption (§4.4); jurors share it symmetrically.
- **Suspension at execution:** a stock suspended at t+1/t+2 has NaN label and silently
  leaves that day's cross-section — the paper series does not model the stuck position a
  real portfolio would carry.
- **Data provenance:** the community pack is multi-source and not exchange-grade
  (`docs/research/qlib-cn-data.md` §5); fine for statistical-method demos, never for
  production PnL claims.

## 6. Data version pinning

- **Source of record:** `chenditc/investment_data` GitHub release, **pinned tag
  `2026-07-05`** (calendar through 2026-07-03). Download URL shape:
  `https://github.com/chenditc/investment_data/releases/download/<tag>/qlib_bin.tar.gz`
  — never `latest` in docs, scripts, or CI.
- **Bump procedure:** update the tag in one place (adapter config default + the demo's
  reproduce script), re-run the golden fingerprint test (§8), re-run the demo E2E, update
  `docs/research/qlib-cn-data.md`'s measured facts if they shift. A freshness bump is a
  deliberate act scheduled for the README endgame, not an ambient drift.
- **`data_version` exposure:** every `EvalResult.meta` carries
  `{declared_tag, calendar_end (measured), n_instruments (measured)}`. The declared tag is
  config input (the pack does not self-identify); the measured fields let an auditor
  detect a tag/pack mismatch. This satisfies the noise-control reproducibility chain,
  which requires "adapter data version" in every noise-control verdict
  (`docs/design/noise-control.md` §6).

## 7. API surface

Shapes are contractual (verbs, inputs, outputs, failure semantics); exact Python typing
belongs to the implementation ticket. General failure rule, inherited from the ledger
contract: **fail closed** — raise on violated preconditions; never repair, coerce, or
silently drop.

### 7.1 Construction

```
QlibCNFactorEvaluator(config) -> evaluator
```

`config` fields — ALL of them recorded verbatim into `EvalResult.meta` (clarification
2026-07-11: a `meta.config` sub-object carrying every constructor field including
`provider_uri`, `min_cross_section`, and `quantile` regardless of metric, in addition to
the named §7.4 keys; an auditor must be able to reconstruct every guard threshold and
the data location from a verdict alone). Config values are validated strictly at
construction — wrong types raise; no `str()`/`float()`/`int()` coercion (the §7 no-repair
rule applies at the config boundary too):

| Field | Default | Semantics |
|---|---|---|
| `provider_uri` | `~/.qlib/qlib_data/cn_data` | qlib data pack location. |
| `universe` | `"csi300"` | qlib instrument set name; PIT interval filtering (§5.1). |
| `window` | required | `{start, end}` calendar dates; defines evaluation dates (§5.2). |
| `label_expr` | `"Ref($close, -2)/Ref($close, -1) - 1"` | Forward-return expression (§4.2). |
| `quantile` | `0.2` | Long-short quantile for `metric="returns"` (§4.1). |
| `min_cross_section` | `50` | Fail-closed guard (§5.3). |
| `declared_data_tag` | required | The pinned release tag (§6). |

Construction initializes qlib with `qlib.init(provider_uri=..., region=REG_CN,
kernels=1)` — `kernels=1` is **mandatory**, both for macOS multiprocessing stability
(`docs/research/qlib-cn-data.md` §2.3) and for determinism (§8). The label panel and PIT
membership are loaded once at construction; evaluations are pure pandas/numpy thereafter.

### 7.2 Single-panel evaluation

```
evaluator.evaluate(scores, metric) -> EvalResult
```

- `scores`: a date × instrument panel (pandas DataFrame, DatetimeIndex rows, instrument
  columns) of factor scores on signal dates. Must contain a row for **every** evaluation
  date (missing rows: raise). NaN cells are legal (§5.3). Columns outside the day's PIT
  membership are ignored by the universe rule (definition, not repair).
- `metric`: `"ic"` or `"returns"` — must equal the trial's `declared.metric`.
- Returns one `EvalResult` (§7.4) whose `{index, values}` is the trial's series.

### 7.3 Shifted-grid evaluation (the noise-control feed)

```
evaluator.evaluate_shifted(scores, metric, offsets) -> EvalGrid
```

- Implements the circular time-shift of `docs/design/noise-control.md` §3.1: with T
  evaluation dates, offset δ maps the score row of date index `(t − δ) mod T` onto date
  t; the label panel is **never** shifted. Shifting is defined on the evaluation-date row
  index after §5.2 restriction.
- `offsets`: an explicit non-empty list of integers, supplied verbatim by the caller
  (the demo draws them under its master seed, `docs/design/noise-control.md` §7). The
  adapter draws nothing, validates `0 ≤ δ < T` (erratum 2026-07-11: the original
  `0 < δ < T` contradicted this section's own equivalence invariant, which requires
  `evaluate_shifted(S, m, [0])` to succeed; δ = 0 is legal, δ_min discipline stays with
  the caller, and an empty offsets list raises — fail-closed, no unspecified grids).
- Returns `EvalGrid = {index: [label...], offsets: [int...], values: float[n_offsets][T],
  meta}` — row b is the juror series at `offsets[b]`, sharing the single `index`.
- The demo's 100-candidate loop stays on the demo side: 100 calls, each vectorized over
  199 offsets internally.

**Equivalence invariant (contractual, pytest-enforced):** for any δ,
`evaluate_shifted(S, m, [δ]).values[0]` equals — `array_equal`, bit-for-bit — 
`evaluate(circshift(S, δ), m).values`, where `circshift` is a reference row-roll done in
the test. Likewise `evaluate_shifted(S, m, [0])` reproduces `evaluate(S, m)` exactly.
Both entry points must route through **one shared kernel** so this holds by construction.

**Performance note (non-contractual guidance):** per-row ranks are invariant under row
shifts, so the kernel may precompute per-date score ranks once and evaluate all offsets
as vectorized row-wise correlations — sub-second per candidate, seconds for the full
100×199 grid, versus ~half an hour for 19,900 naive groupby passes. Quantile membership
depends only on ranks, so the same trick covers `metric="returns"`.

### 7.4 EvalResult / EvalGrid metadata

`meta` (identical schema for both result types) carries at minimum: `metric`,
`metric_params` (`quantile` for returns), `label_expr`, `price_field: "$close"`,
`universe`, `window`, `n_evaluation_dates`, `cost_declaration` (§4.4 string),
`data_version` (§6 triple), `qlib_version`, `adapter_version`. The orchestrator copies
what it needs into the trial's `spec` / `source_ref`; the court reads none of it.

### 7.5 Testing obligations (adapter implementation ticket must ship these)

1. **Oracle tests:** on tie-free synthetic panels, the kernel's `"ic"` output matches
   `qlib.contrib.eva.alpha.calc_ic`'s `ric` and its `"returns"` output matches
   `calc_long_short_return`'s `long_short_r`, within `rtol ≤ 1e-12` (tolerance exists
   only for floating-point summation-order slack; qlib defines the semantics).
2. **Equivalence invariant** of §7.3, asserted with `array_equal` (no tolerance).
3. **Determinism tests** of §8.
4. **Convention spot-check:** label and adjusted-price handling validated against a known
   name (e.g. SH600519) per `docs/research/qlib-cn-data.md` §3.3/§5.

## 8. Determinism

**Promise:** same machine + locked dependency versions + same `declared_data_tag` ⇒
byte-identical `EvalResult`/`EvalGrid` values across runs. **Explicitly not promised:**
bit identity across platforms, BLAS builds, or dependency versions — last-ulp drift is a
floating-point fact, and pretending otherwise would violate the honesty clause.

Implementation mandates:

- `kernels=1` in `qlib.init` (no parallel row-order nondeterminism).
- Canonical ordering everywhere: instruments sorted lexicographically, dates ascending,
  before any reduction. No iteration over unordered containers.
- **Zero RNG in the adapter.** All randomness (candidate generation, offset draws) lives
  with the orchestrator under its master seed (`docs/design/noise-control.md` §7);
  offsets arrive verbatim.

Two-layer test battery:

1. **Synthetic double-run (always-on CI):** build the evaluator twice on a synthetic
   in-memory panel fixture, evaluate identical inputs, assert `array_equal` — exercises
   the promise without the 813M pack.
2. **Golden fingerprint (integration, skipped when data absent):** against the pinned tag,
   evaluate a fixed deterministic synthetic factor over the demo window and compare a
   small stored fingerprint (e.g. first/last five RankIC values at full float64 repr plus
   a whole-series hash). Fails loudly on silent data or dependency drift; re-baselined
   only by the §6 bump procedure.

## 9. Known limitations (declared, not patched)

- **Paper-series gap to money:** no costs, no tradability constraints (§4.4, §5.4) — the
  court certifies statistical validity, not implementable PnL.
- **RankIC as headline metric** measures information, not portfolio capacity; the
  long-short companion view narrows but does not close that gap.
- **DSR on IC series:** the Sharpe-ratio literature (`docs/research/dsr.md`) is written
  for return series; applying PSR/DSR to an IC series reads mean/std as ICIR — a
  documented isomorphic generalization to be stated where ticket 08 fixes the statistic
  signatures.
- **Wrap-around seam** in shifted evaluations belongs to the generation protocol and is
  disclosed there (`docs/design/noise-control.md` §3.3, §9).
- **Community data pack** provenance and availability risks per
  `docs/research/qlib-cn-data.md` §5.

## 10. Out of scope for this contract

- US / crypto adapters (constitution: qlib-cn first; this document's §3 series contract
  and §7 API shape are the template they must satisfy).
- Tradability masks, cost models, turnover diagnostics (candidate v0.3 `gates/` blades).
- Style/industry-neutralized juries (v0.2+ refinement, `docs/design/noise-control.md` §9).
- Pearson IC, alternative labels, alternative universes as declared options.
- Battery composition and demo presentation (ticket 11).

## References

- pyqlib **0.9.7**: `qlib.contrib.eva.alpha.calc_ic`, `calc_long_short_return`
  (`qlib/contrib/eva/alpha.py`); Alpha158/Alpha360 label convention
  (`qlib/contrib/data/handler.py:90,152`); `qlib.data.D.calendar/instruments/features`;
  `qlib.init(..., region=REG_CN, kernels=1)`.
- `chenditc/investment_data`, GitHub release tag `2026-07-05` — the pinned data pack.
- `docs/research/qlib-cn-data.md` — measured data facts (ticket 09).
- `docs/design/trial-ledger.md` — series schema §5.2, read surface & fail-closed
  alignment §7.2, decoupling §9.
- `docs/design/noise-control.md` — circular shift §3, common-offset grid §5, RNG
  discipline §7.
- `CONTEXT.md` — canonical vocabulary.
- `.scratch/v0.1/issues/10-adapter-interface.md` — the deciding ticket.
