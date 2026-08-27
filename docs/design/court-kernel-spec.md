# Court Kernel — Implementation Spec (v0.1)

**Provenance:** assembled 2026-07-10 in ticket `.scratch/v0.1/issues/08-court-kernel-spec.md`
(commander-side compilation; every delegated decision from the five source documents is
closed in §4 with its rationale).
**Consumers:** implementation tickets v0.1-08a…08f (`.scratch/dispatch/v0.1-08*/ticket.md`);
the referee re-checks deliveries against this document; ticket 11 (killer demo) takes the
kernel API from here.
**Depends on:** `docs/design/trial-ledger.md` (the ledger contract — this spec implements
it and never overrides it); `docs/design/noise-control.md` (§4 court-side function);
`docs/research/dsr.md`, `docs/research/pbo-cscv.md`, `docs/research/bhy.md` (formulas,
code-mapping tables, hand-worked test vectors); `CONTEXT.md` (canonical vocabulary, used
without redefinition).
**Scope:** module layout, exact function signatures, formula↔code correspondence, numeric
guards, error semantics, and the pytest plan for `court/`. No implementation in this
document.

---

## 1. Purpose and layering

This spec turns the closed contracts and literature notes into a construction contract
precise enough that (a) each worker ticket is self-contained, (b) the referee can put
paper, note, and code side by side, and (c) the hand-worked test vectors run as pytest
cases with zero glue.

The three-layer rule of `docs/design/trial-ledger.md` §7 is binding:

1. **`Ledger`** (`court/ledger.py`) — pure bookkeeping; understands no statistics.
2. **Statistics** (`court/sharpe.py`, `court/dsr.py`, `court/pbo.py`, `court/tstats.py`,
   `court/fdr.py`, `court/noise.py`) — pure functions over arrays and scalars; hold no
   reference to any ledger.
3. **`judge`** (`court/judge.py`) — the only component that knows both sides.

## 2. Module and file layout

```
court/
├── __init__.py     # public API re-exports + __version__ (ONLY ticket 08f touches this)
├── ledger.py       # 08a — records, JSONL event log, read surface
├── sharpe.py       # 08b — SR estimator, moments, SR standard error, PSR
├── dsr.py          # 08b — E[max SR], implied independent N, ρ̂, DSR
├── pbo.py          # 08c — CSCV / PBO
├── tstats.py       # 08d — t statistic (iid / Newey-West SE), p from t
├── fdr.py          # 08d — harmonic number, fdr_bh, fdr_by
├── noise.py        # 08e — empirical_null_p
└── judge.py        # 08f — thin orchestrator, verdict assembly

tests/
├── test_smoke.py   # exists (ticket 02) — decoupling assertion, do not modify
├── test_ledger.py  # 08a
├── test_sharpe.py  # 08b
├── test_dsr.py     # 08b
├── test_pbo.py     # 08c
├── test_tstats.py  # 08d
├── test_fdr.py     # 08d
├── test_noise.py   # 08e
└── test_judge.py   # 08f
```

**Why flat modules (no `court/stats/` subpackage):** tickets 08a–08e are dispatched to
parallel workers in separate worktrees. A shared `stats/__init__.py` would be created or
edited by five branches at once and conflict on merge. With flat modules, each ticket owns
disjoint files; `court/__init__.py` (which already exists from ticket 02 with a docstring
only) is modified by no ticket except 08f.

**Cross-module imports within `court/`:** `dsr.py` may import `sharpe.py` (same ticket).
`judge.py` imports everything (it is the last ticket). No other cross-imports — in
particular `pbo.py` does NOT import `sharpe.py`; its metric is a required parameter (§4,
ruling D1).

## 3. Global conventions and error semantics

### 3.1 Dependency whitelist

`court/` imports only: the Python standard library, `numpy`, `pandas`, `scipy`.
(`pandas` is a ceiling, not a floor — this spec happens to need only numpy + scipy +
stdlib.) Zero market-specific imports; `tests/test_smoke.py::test_court_market_agnostic`
is the executable assertion (fresh subprocess, `import court`, asserts no `qlib*` and no
`adapters*` module in `sys.modules`).

### 3.2 Naming

- FDR procedures are `fdr_bh` and `fdr_by`. The name "BHY" **never appears in code**
  (`docs/research/bhy.md` §7.5: HLZ's "BHY" is the BY harmonic procedure; the collision is
  a known trap). Verdict `statistic` strings: `"dsr"`, `"pbo_cscv"`, `"fdr_by"`,
  `"fdr_bh"`, `"noise_control"` (ledger contract §5.3).
- Python names follow the code-mapping tables of the research notes (`dsr.md` §3,
  `bhy.md` cross-walk, `pbo-cscv.md` App. B) wherever those tables name a symbol.

### 3.3 Result types

Multi-valued pure functions return `typing.NamedTuple` instances (immutable, zero-dep,
fields unpack directly into `VerdictRecord.computed`). Ledger records are
`@dataclass(frozen=True)`.

### 3.4 Numeric conventions

- All arithmetic in float64. Normal CDF/quantile: `scipy.stats.norm.cdf` / `.ppf`.
- `EULER_MASCHERONI = 0.5772156649015329` (float64-nearest; the notes' 10-digit value
  differs by ~1.5e-11, absorbed by test tolerance).
- Everything is computed at the **native frequency** of the series; annualization is
  display-only (`dsr.md` §5.1).
- Docstring of every statistic function cites: paper + equation number, and the research
  note section (project iron law).

### 3.5 Error semantics: fail-closed, everywhere

Any violated precondition **raises** — never repair, coerce, clamp, or silently drop
(ledger contract §7). Pure functions raise `ValueError` with a message naming the violated
precondition. `court/ledger.py` additionally defines
`class LedgerCorruptionError(RuntimeError)` for replay-time corruption (caller error vs
corrupt evidence are different failures). Statistical *caveats* (e.g. ill-conditioned ρ̂)
are not errors: they are computed, disclosed in the verdict, and never block (§5.2).

## 4. Rulings made by this spec

Decisions the source documents explicitly delegated to ticket 08, closed here.
"→" = where it lands in §5.

| # | Ruling | Rationale / source |
|---|---|---|
| A1 | Flat module layout, one file per ticket; `court/__init__.py` touched only by 08f | Parallel worker branches must merge without conflicts (§2) |
| A2 | Result types = NamedTuples; records = frozen dataclasses | §3.3 |
| B1 | Serialization casing = exact snake_case field names of ledger contract §5 tables | Contract delegated casing to 08; the tables are already snake_case |
| B2 | Non-finite series values rejected at `record()` (raise) | Contract §7.1 delegated the policy; NaN/Inf silently poisons every downstream moment — fail-closed |
| B3 | IDs: zero-padded sequential per type — `h-000001`, `t-000001`, `v-000001`, assigned in event order | Deterministic replay, human-auditable, unique within one ledger (contract §5) |
| B4 | Every append is flush + fsync before return | Contract requires durable-before-return for `register`; generalizing to all events is simpler and costs nothing at demo scale |
| B5 | Series labels must be unique within one series (raise otherwise) | Duplicate labels make `matrix` label-for-label alignment ambiguous — fail-closed |
| B6 | Timestamps: `datetime.now(timezone.utc).isoformat()` (ISO-8601 UTC, explicit offset) | Contract §5 |
| B7 | Event envelope `at` **is** the record timestamp (`created_at`/`registered_at`/`evaluated_at`/`judged_at`); payload does not duplicate it | One clock, no skew between envelope and record |
| B8 | Torn trailing line: truncated from the file (fsync) on open, before indexing; mid-file parse or invariant failure on replay → `LedgerCorruptionError` | Contract §6 invariant 4; appending after a torn line would corrupt the JSONL |
| B9 | `spec`/`params` opaque dicts are validated JSON-serializable at write time via `json.dumps(..., allow_nan=False)` | Fail-closed at the write boundary; NaN is not valid JSON |
| B10 | `DeclaredProtocol` defaults: `direction="two-sided"` (contract §5.2 says default), `se=SeConvention("iid")` (this spec's ruling E2) | — |
| C1 | Moment conventions: σ̂ with Bessel (n−1) [2012 §2.5]; skewness/kurtosis as population (biased) estimators; kurtosis **raw** (Normal → 3.0): `scipy.stats.skew(x, bias=True)`, `scipy.stats.kurtosis(x, fisher=False, bias=True)` | Papers pin Bessel for σ̂ and raw kurtosis (`dsr.md` §2.a); they do not bias-correct higher moments — scipy's population default, documented |
| C2 | Variance factor ≤ 0 → raise (no clamping) | `dsr.md` §5.6 offered clamp-or-fail; fail-closed wins |
| C3 | σ̂ = 0 → raise (`sharpe_ratio` undefined) | `dsr.md` §5.6 |
| C4 | `expected_max_sr` at N=1 returns `sr_trials_mean` exactly (max of one draw); N<1 → raise; **hurdle clamped so `max_z ≥ 0`, i.e. the result is never below `sr_trials_mean`** (E[max] of N≥1 draws ≥ the single-draw mean); docstring **must** state Eq. (1) is an EVT approximation valid for N≫1 | `dsr.md` §2.c approximation condition + §5.5 guard; N=1 needs no EVT. **Amended 2026-07-11 (v0.1 audit):** the original ruling special-cased only N==1, but N̂ is real-valued (C5) and Eq. (1) dips **below** the mean for N ∈ (1, ~1.29) — leaving that band unclamped made DSR anti-conservative (certifying near-zero-skill strategies when a few trials are highly correlated). §5.5 already contemplated "N as low as 2"; the clamp extends the guard to the full (1, 2) float band. Attribution: contract-fault (ruling narrowed §5.5), not worker. |
| C5 | `n_trials` is float (N̂ = 1+(M−1)(1−ρ̂) is real-valued); any real N ≥ 1 accepted | 2014 Eq. (9) output feeds Eq. (1) |
| C6 | ρ̂ = mean of upper-triangle pairwise Pearson correlations of the T×M **series** matrix | `ledger.matrix` is the ρ̂ feed (ledger contract §7.2); `dsr.md` §3.c |
| C7 | ρ̂ accepted on (−1, 1]; ρ̂ < 0 extrapolates Eq. (9) to N̂ > M — a **harsher** hurdle, erring against the candidate; documented in the docstring. Outside (−1, 1] → raise | Paper interpolates on [0,1]; small negative sample ρ̂ is routine for noise pools and must not kill the run; the extrapolation direction is conservative |
| C8 | Ill-conditioning T < ½M(M−1) is a disclosed caveat, not an error: predicate `rho_is_ill_conditioned`, recorded in `VerdictRecord.computed` | `dsr.md` §5.3 (2014 App. A.3); honesty by disclosure |
| C9 | Cross-trial SR variance V[{SR}] uses sample variance with ddof=1 | "Sample variance of the vector of trial SRs" (`dsr.md` §3.c) |
| C10 | `dsr()` computes SR* internally under the null E[{SR}]=0 | 2014 Eq. (2) defines DSR at the null benchmark |
| D1 | `pbo_cscv` metric is a **required** callable parameter (no default) | Metric-agnostic per the paper (`pbo-cscv.md` §2.3); avoids `pbo.py`→`sharpe.py` coupling across parallel tickets; the judge wires `sharpe_ratio`; the hand vector uses the mean |
| D2 | Metric ties → midranks (`scipy.stats.rankdata(..., method="average")`); IS-best tie → smallest column index (`np.argmax` first occurrence) | `pbo-cscv.md` §3.6 required a documented v0.1 choice |
| D3 | Non-finite metric value on any half → raise the whole run (never drop columns per-combination) | `pbo-cscv.md` §6.3; per-combination dropping reintroduces selection bias — fail-closed |
| D4 | φ counts **strict** λ<0 only; λ=0 does not count. Operational identity: λ<0 ⟺ r̄ < (N+1)/2. Eq. (2.2)'s literal N/2 is NOT implemented | `pbo-cscv.md` §3.5 v0.1 ground truth (paper-internal mismatch documented there) |
| D5 | Structural guards: S even and ≥2; T % S == 0; **T ≥ 2S** (each block ≥ 2 rows; also excludes T = 0 and T = S — an empty matrix must never yield the candidate-favorable φ = 0.0 silently); N ≥ 2 (N=1 is vacuous → raise) | `pbo-cscv.md` §6.4 (amended by referee ruling 2026-07-10: original D5 under-transcribed §6.4's T < 2S rejection) |
| D6 | Combination enumeration order pinned to `itertools.combinations(range(S), S//2)` | Makes the note's §5.4 logit sequence a positional pytest fixture |
| E1 | p-values from t via **standard normal** asymptotics (not Student-t) | HLZ convention (`bhy.md` §4.1–4.2, §3.5 fn 26) |
| E2 | Default SE convention = `{"kind": "iid"}`; `newey_west` requires an **explicit** `lags` (no automatic lag rule in v0.1) | Ledger contract §5.2 delegated the default to 08/11; an auto lag rule would be an undeclared researcher degree of freedom |
| E3 | Newey-West conventions: γ̂ℓ with 1/T normalization; Bartlett weights 1−ℓ/(L+1); se = √(LRV/T). iid: se = σ̂(Bessel)/√T | `bhy.md` §4.3 (Newey & West 1987); mixed normalization (Bessel iid vs 1/T HAC) is literature-standard and documented |
| E4 | `q` is a **required** argument of `fdr_bh`/`fdr_by` (no default) | The court never silently defaults a significance level; q is a verdict parameter |
| E5 | Empty p-vector → k*=0, empty rejection set, empty adjusted list (returns, not raises) | `bhy.md` §7.4 defines the N=0 behavior explicitly |
| E6 | Adjusted p-values always computed: backward min recurrence on the sorted list, clipped to [0,1], mapped back to input order via the stable sort permutation. **BY base case = min(1, c(N)·P₍N₎)** — the self-consistent convention (= R `p.adjust("BY")` / statsmodels), NOT the HLZ-printed init P₍N₎, which violates §7's identity `adjusted_p[i] ≤ q ⟺ reject[i]` (referee ruling 2026-07-10; erratum in `bhy.md` §3.2) | `bhy.md` §2.4/§3.2 (incl. erratum)/§7.2 |
| E7 | Sorting is stable (`np.argsort(..., kind="stable")`); rejection **sets** are tie-order invariant | `bhy.md` §6.4 |
| E8 | `harmonic_number` = ascending float64 sum Σ 1/i; `harmonic_number(10) == 2.9289682539682538` exactly | `bhy.md` §6.1 pins the summation convention |
| F1 | `empirical_null_p(observed, nulls, alpha=0.05)`; ties count against the candidate (`>=`); decision `"pass"` iff p̂ ≤ α | `noise-control.md` §4.1 (Phipson & Smyth 2010 Eq. (2); default α=0.05 pinned there as a parameter default) |
| F2 | Noise ranking statistic (computed by the judge from the series under the trial's declared protocol): two-sided → \|t\|; greater → t; less → −t (larger = more extreme in the declared direction) | `noise-control.md` §4.1: same directed statistic the selection ranks on; court never re-derives direction |
| G1 | `judge(ledger, scope, config)`; config = ordered sequence of `Application(statistic, params)`; one VerdictRecord per application; **no aggregation** (ticket 11) | Ledger contract §7.4; noise-control §1 |
| G2 | Decision polarity is pinned in one table (§5.8): statistical *discovery* (H0 rejected / hurdle cleared) ⟺ court `"pass"` | The FDR "rejection set" naming inversion is a classic bug source |
| G3 | Every trial in scope must be `evaluated`, else raise. Exclusion of unevaluated trials is the caller's explicit act, visible because scope is recorded verbatim in the verdict | Fail-closed; a p-value cannot exist without a series; hidden shrinkage of the family is impossible because the scope is on the record |
| G4 | `court.__version__ = "0.1.0.dev0"` (sync with pyproject); the judge stamps it into `VerdictRecord.engine_version` automatically | Contract §5.3 reproducibility |
| G5 | Judge's PBO metric registry (v0.1): `{"sharpe": sharpe_ratio}`; the params record the metric *name* | Minimal; pure-function tests use the callable directly |

**Amendment (v0.2 ticket 03 — `docs/design/selection-verdict-isomorphism.md`):** gate
forms become direction-aware, generalizing F2 to DSR and PBO. Under
`declared.direction="two-sided"` (the killer-demo selection), **DSR abstains**
(computed and recorded but `role="informational"`, out of the survivor vote) and
**PBO uses an absolute metric** (`|ICIR|`/`|sharpe|`, added to the G5 registry, with
the actual R name in `params`); under directional (`greater`/`less`) DSR is enabled
and PBO uses the signed metric. Every verdict carries `role ∈
{discriminating, informational}`; aggregation (v0.1 ticket 11 — the demo layer; in
v0.2 the aggregation policy is ticket 09's on-chain object) counts only
`discriminating`. `role` is stored as a new **optional** `VerdictRecord` field
(`role: str | None = None`, legacy replay compatible — 2026-07-12 audit ruling
D16). Implemented by ticket 08.

## 5. Module contracts

Every signature below is contractual: name, parameters, defaults, return type, raise
conditions. Type hints are the exact intended annotations.

### 5.1 `court/sharpe.py` (ticket 08b)

```python
class SeriesMoments(NamedTuple):
    n_obs: int
    mu_hat: float
    sigma_hat: float     # Bessel (n-1)
    sr_hat: float        # mu_hat / sigma_hat, native frequency
    skew_hat: float      # population estimator
    kurt_hat: float      # RAW kurtosis, population estimator (Normal -> 3.0)

def series_moments(values) -> SeriesMoments
def sharpe_ratio(values) -> float
def sr_var_factor(sr_hat: float, skew_hat: float, kurt_hat: float) -> float
def sr_standard_error(sr_hat: float, n_obs: int, skew_hat: float, kurt_hat: float) -> float
def psr(sr_hat: float, sr_benchmark: float, n_obs: int,
        skew_hat: float, kurt_hat: float) -> float
def annualized_sr(sr_hat: float, periods_per_year: float) -> float
```

`values` is a 1-D `numpy.ndarray` or sequence of floats (this convention holds for every
`values` parameter in this spec).

Formula correspondence (`docs/research/dsr.md` anchors):

| Function | Formula | Citation |
|---|---|---|
| `sharpe_ratio`, `series_moments` | SR̂ = μ̂/σ̂, σ̂ Bessel | BLdP 2012 §2, Eqs. (4)–(11) context; note §2.a |
| `sr_var_factor` | 1 − γ̂₃·SR̂ + (γ̂₄−1)/4·SR̂² (collapsed form; expanded Eq. (8) form is algebraically identical) | BLdP 2012 Eq. (8) + §2.5; note §2.a |
| `sr_standard_error` | √(var_factor/(n−1)) | BLdP 2012 §2.5; note §2.a |
| `psr` | Φ((SR̂−SR*)·√(n−1)/√var_factor) | BLdP 2012 Eq. (11); note §2.b |
| `annualized_sr` | √q·SR̂, **display only** | BLdP 2012 Eq. (5); note §5.1 |

Guards (raise `ValueError`): `n_obs < 2`; any non-finite value; `sigma_hat == 0`;
`var_factor <= 0` (rulings C1–C3); `periods_per_year <= 0`.

### 5.2 `court/dsr.py` (ticket 08b)

```python
EULER_MASCHERONI: float = 0.5772156649015329

class DsrResult(NamedTuple):
    dsr: float          # PSR at the expected-max benchmark
    sr_star: float      # SR̂* = E[max SR] under the null E[{SR}] = 0
    z: float            # the standardized statistic inside Phi
    var_factor: float

def implied_independent_trials(n_trials_raw: int, avg_corr: float) -> float
def avg_pairwise_correlation(values: np.ndarray) -> float
def rho_is_ill_conditioned(n_obs: int, n_trials_raw: int) -> bool
def expected_max_sr(sr_trials_mean: float, sr_trials_std: float, n_trials: float) -> float
def dsr(sr_hat: float, n_obs: int, skew_hat: float, kurt_hat: float,
        sr_trials_std: float, n_trials: float) -> DsrResult
```

| Function | Formula | Citation |
|---|---|---|
| `implied_independent_trials` | N̂ = 1 + (M−1)(1−ρ̂) | BLdP 2014 App. A.3 Eq. (9); note §2.c |
| `avg_pairwise_correlation` | mean of upper-triangle Pearson correlations of the T×M matrix | note §3.c (`avg_trial_corr`) |
| `rho_is_ill_conditioned` | True ⟺ T < ½M(M−1) | BLdP 2014 App. A.3 caveat; note §5.3 |
| `expected_max_sr` | E + √V·[(1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−1/(Ne))] — **EVT approximation, N≫1; docstring must say so** | BLdP 2014 Eq. (1), App. A.1 Eqs. (5)–(6); note §2.c |
| `dsr` | DSR = PSR(SR̂*) with SR̂* = `expected_max_sr(0.0, sr_trials_std, n_trials)`; calls `psr` from `court.sharpe` | BLdP 2014 Eq. (2); note §2.d |

Guards: `expected_max_sr` — `n_trials < 1` raises; `n_trials == 1` returns
`sr_trials_mean` exactly; `sr_trials_std < 0` raises; `sr_trials_std == 0` returns
`sr_trials_mean` (degenerate, exact). `implied_independent_trials` — `n_trials_raw < 1`
raises; `avg_corr` outside (−1, 1] raises; negative `avg_corr` allowed and documented as a
conservative extrapolation (ruling C7). `avg_pairwise_correlation` — matrix not 2-D,
M < 2, T < 2, non-finite entries, or any constant column raises.

### 5.3 `court/pbo.py` (ticket 08c)

```python
class PboResult(NamedTuple):
    phi: float                    # CSCV estimate of PBO
    logits: tuple[float, ...]     # one lambda_c per combination, combination order pinned
    n_combinations: int           # C(S, S/2)
    n_lambda_negative: int        # strict lambda_c < 0 count

def pbo_cscv(values: np.ndarray, n_splits: int,
             metric: Callable[[np.ndarray], float]) -> PboResult
```

`values` is the T×N performance matrix (rows time-ordered, columns = trials, i.e. the
output of `ledger.matrix`). `n_splits` is the paper's S. `metric` maps a 1-D array (one
column restricted to one half) to a float; **required, no default** (ruling D1).

Algorithm exactly as `docs/research/pbo-cscv.md` §3.2–§3.5 / pseudocode §3.7, with the
step-(c) train/test label erratum corrected as documented there:

| Step | Formula | Citation |
|---|---|---|
| Partition | S contiguous row-blocks of length T/S, time order preserved | Alg. 2.3 step 2; note §3.2 |
| Combinations | all C(S, S/2) IS-halves, `itertools.combinations` order | Alg. 2.3 step 3, Eq. (2.3); ruling D6 |
| Ranks | higher = better, best = N; midranks on ties | §2.1; ruling D2 |
| IS-best | n* = argmax of IS metric, first index on ties | Alg. 2.3(e); ruling D2 |
| Relative rank | ω̄c = r̄_{n*}/(N+1) | Alg. 2.3(f) |
| Logit | λc = ln(ω̄c/(1−ω̄c)) | Alg. 2.3(g) |
| PBO | φ = #{λc < 0}/C(S,S/2), **strict**; λc<0 ⟺ r̄_{n*} < (N+1)/2; Eq. (2.2)'s literal N/2 is not the implemented rule | §3.1; note §3.5; ruling D4 |

Guards: `values` not 2-D or containing non-finite entries; `N < 2`; `n_splits` odd or
< 2; `T % n_splits != 0`; non-finite metric output on any half (raise the whole run,
ruling D3).

### 5.4 `court/tstats.py` (ticket 08d)

```python
class TStatResult(NamedTuple):
    t: float
    mean: float
    se: float
    n_obs: int

def t_stat(values, se_kind: str = "iid", lags: int | None = None) -> TStatResult
def p_from_t(t: float, direction: str) -> float
```

| Item | Formula | Citation |
|---|---|---|
| `se_kind="iid"` | se = σ̂(Bessel)/√T | `bhy.md` §4.1 |
| `se_kind="newey_west"` | LRV = γ̂₀ + 2·Σ_{ℓ=1..L} (1−ℓ/(L+1))·γ̂ℓ, γ̂ℓ = (1/T)Σ_{t=1..T−ℓ}(x_t−x̄)(x_{t+ℓ}−x̄); se = √(LRV/T) | Newey & West 1987; `bhy.md` §4.3; ruling E3 |
| `direction="two-sided"` | p = 2(1−Φ(\|t\|)) | `bhy.md` §4.2; HLZ §3.5 fn 26 |
| `direction="greater"` | p = 1−Φ(t) | `bhy.md` §4.2 |
| `direction="less"` | p = Φ(t) | `bhy.md` §4.2 |

Normal asymptotics throughout (ruling E1). Guards: `n_obs < 2`; non-finite values;
`se == 0` (σ̂=0 or LRV=0); `se_kind` not in {"iid","newey_west"}; `newey_west` with
`lags` None, negative, non-integer, or ≥ T; `lags` supplied with `se_kind="iid"`
(contradictory declaration — raise); `direction` not one of the three literals;
non-finite `t`.

Hand-worked vectors for this module (derived for this spec; the worker re-derives in the
test docstring):

- `values = [1.0, 2.0, 3.0]`: x̄ = 2, Bessel σ̂ = 1 ⇒ se_iid = 1/√3 = 0.5773502691896258,
  **t_iid = 2√3 ≈ 3.464101615137754** — pin the float64 *pipeline* value
  (`2.0 / 0.5773502691896258 = 3.464101615137754`). Note `float(2*sqrt(3)) =
  3.4641016151377544` is exactly 1 ulp higher; the original double pin (se AND
  closed-form t simultaneously, bitwise) was unsatisfiable. Referee re-pin
  2026-07-10: tests assert the pipeline value.
- Same series, `newey_west, lags=1`: deviations (−1, 0, 1); γ̂₀ = 2/3; γ̂₁ = 0;
  LRV = 2/3; se = √(2/9) = 0.4714045207910317; **t_nw = 3√2 = 4.242640687119285**.
- `p_from_t(1.959963984540054, "two-sided") = 0.05000000` (z at Φ=0.975);
  `p_from_t(1.6448536269514722, "greater") = 0.05000000`;
  `p_from_t(-1.6448536269514722, "less") = 0.05000000`.

### 5.5 `court/fdr.py` (ticket 08d)

```python
class FdrResult(NamedTuple):
    k_star: int
    reject: tuple[bool, ...]       # input order; True = H0 rejected (discovery)
    adjusted_p: tuple[float, ...]  # input order; monotone in sorted order, clipped to [0,1]
    c_factor: float                # 1.0 for BH; harmonic_number(N) for BY

def harmonic_number(n: int) -> float
def fdr_bh(p_values, q: float) -> FdrResult
def fdr_by(p_values, q: float) -> FdrResult
```

| Item | Formula | Citation |
|---|---|---|
| `harmonic_number` | c(N) = Σ_{i=1..N} 1/i, ascending float64 sum | BY 2001 Thm 1.3; `bhy.md` §3.1, §6.1 |
| `fdr_bh` | k* = max{i : p₍ᵢ₎ ≤ (i/N)·q}, reject ranks 1..k* (step-up, `≤`) | BH 1995 §3.1 expr. (1); `bhy.md` §2.2 |
| `fdr_by` | k* = max{i : p₍ᵢ₎ ≤ i·q/(N·c(N))} | BY 2001 Thm 1.3; HLZ §3.4.3; `bhy.md` §3.2 |
| adjusted p | backward min recurrence, clip to [0,1], stable-sort permutation maps back to input order | `bhy.md` §2.4, §3.2, §7.2; ruling E6 |

Guards: any p outside [0,1] or non-finite → raise; `q` not in (0,1) → raise; empty input
→ `k_star=0`, empty tuples (returns, ruling E5). Step-up semantics per `bhy.md` §7.1: the
whole initial segment 1..k* is rejected, including ranks that fail their own line;
boundary `p₍ᵢ₎ == τᵢ` counts as pass (`≤`).

### 5.6 `court/noise.py` (ticket 08e)

```python
class NoiseResult(NamedTuple):
    p_hat: float
    decision: str       # "pass" | "reject"  (VerdictRecord decision vocabulary)
    n_nulls: int        # K
    n_at_least: int     # #{ null_j >= observed }  — ties count against the candidate

def empirical_null_p(observed: float, nulls, alpha: float = 0.05) -> NoiseResult
```

| Item | Formula | Citation |
|---|---|---|
| p̂ | (1 + #{null_j ≥ observed}) / (K + 1) | Phipson & Smyth 2010 Eq. (2); `noise-control.md` §4.1 |
| decision | `"pass"` iff p̂ ≤ α | `noise-control.md` §4.1 |

The same arithmetic serves both modes (individual jury / pool-max, White 2000); mode is
an input-selection concern of the caller (`noise-control.md` §4.2–4.3). Guards: `nulls`
empty, non-1-D, or non-finite; `observed` non-finite; `alpha` not in (0,1).

### 5.7 `court/ledger.py` (ticket 08a)

Record types (field names are the serialization names — ruling B1):

```python
@dataclass(frozen=True)
class SeConvention:
    kind: str                      # "iid" | "newey_west"
    lags: int | None = None        # required iff kind == "newey_west"

@dataclass(frozen=True)
class Window:
    start: str                     # opaque label; the court compares, never interprets
    end: str

@dataclass(frozen=True)
class DeclaredProtocol:
    metric: str                    # "returns" | "ic"
    window: Window
    periods_per_year: float        # display-only annualization factor
    direction: str = "two-sided"   # "two-sided" | "greater" | "less"
    se: SeConvention = SeConvention(kind="iid")

@dataclass(frozen=True)
class Series:
    index: tuple[str, ...]         # opaque labels, unique within the series
    values: tuple[float, ...]      # finite floats, same length as index

@dataclass(frozen=True)
class HypothesisRecord:
    hypothesis_id: str
    statement: str
    created_at: str                # ISO-8601 UTC

@dataclass(frozen=True)
class TrialRecord:
    trial_id: str
    hypothesis_id: str
    spec: dict                     # opaque to the court
    params: dict                   # opaque to the court
    registered_at: str
    declared: DeclaredProtocol
    source_ref: str | None = None
    series: Series | None = None       # None until evaluated
    evaluated_at: str | None = None    # None until evaluated

@dataclass(frozen=True)
class VerdictRecord:
    verdict_id: str
    statistic: str
    scope: tuple[str, ...]
    params: dict
    computed: dict
    decisions: dict[str, str]      # trial_id -> "pass" | "reject"
    judged_at: str
    engine_version: str | None = None
```

API (verbs and failure semantics from ledger contract §7; exact typing fixed here):

```python
class LedgerCorruptionError(RuntimeError): ...

class Ledger:
    @classmethod
    def open(cls, path: str | Path) -> "Ledger"
    def register_hypothesis(self, statement: str) -> str
    def register(self, hypothesis_id: str, spec: dict, params: dict,
                 declared: DeclaredProtocol) -> str
    def record(self, trial_id: str, series: Series) -> None
    def append_verdict(self, statistic: str, scope: Sequence[str], params: dict,
                       computed: dict, decisions: dict[str, str],
                       engine_version: str | None = None) -> str
    def trials(self, scope: Sequence[str] | None = None) -> list[TrialRecord]
    def series(self, trial_id: str) -> Series
    def matrix(self, trial_ids: Sequence[str]) -> tuple[tuple[str, ...], np.ndarray]
    def verdicts(self, trial_id: str | None = None) -> list[VerdictRecord]
    def status(self, trial_id: str) -> str   # "registered" | "evaluated" | "judged"
```

Storage: single-file append-only JSONL exactly per ledger contract §6. Event envelope
`{"type": ..., "at": ..., ...payload}` with `type` ∈ {`hypothesis`, `trial`,
`evaluation`, `verdict`}; the envelope `at` is the record timestamp (ruling B7). Every
append: `json.dumps(..., allow_nan=False)` + newline + flush + fsync (rulings B4/B9).
IDs per ruling B3. Replay on open builds the in-memory index; the immutability of
`TrialRecord` is preserved by replacing the instance (`dataclasses.replace`) when the
evaluation event arrives — records are values, the index is the only mutable state.

Fail-closed conditions (raise `ValueError` unless noted):

| Operation | Raises when |
|---|---|
| `register` | unknown `hypothesis_id`; malformed declared protocol (bad literals; `newey_west` without int `lags ≥ 0`; `lags` with `iid`; `periods_per_year ≤ 0`); `spec`/`params` not JSON-serializable |
| `record` | unknown `trial_id`; trial already evaluated; `len(index) != len(values)`; empty series; duplicate index labels; any non-finite value |
| `append_verdict` | any scope or decisions id unknown; decisions values outside {"pass","reject"}; empty statistic string; scope empty; params/computed not JSON-serializable |
| `series`, `status` | unknown `trial_id`; `series` also on a not-yet-evaluated trial |
| `matrix` | any id unknown or unevaluated; index labels not identical label-for-label across all trials (**never** outer-join, resample, or reorder) |
| `open` (replay) | mid-file unparseable line; event referencing an unknown id; duplicate `evaluation` for one trial → `LedgerCorruptionError`. Torn final line: truncate + fsync, then proceed (ruling B8) |

`matrix(trial_ids)` returns `(index, values)` where `values` is a float64 T×N ndarray
with columns in `trial_ids` order — PBO's M and the ρ̂ feed for DSR (contract §7.2).

### 5.8 `court/judge.py` (ticket 08f)

```python
class Application(NamedTuple):
    statistic: str    # "dsr" | "pbo_cscv" | "fdr_by" | "fdr_bh" | "noise_control"
    params: dict

class Judgment(NamedTuple):
    verdict_ids: tuple[str, ...]
    decisions: dict[str, dict[str, str]]   # verdict_id -> {trial_id: "pass"|"reject"} (v0.2-12 C)

def judge(ledger: Ledger, scope: Sequence[str],
          config: Sequence[Application]) -> Judgment
```

The judge: reads evidence via the §5.7 read surface, computes statistics via §5.1–5.6
under each trial's declared protocol, appends **one VerdictRecord per application**, and
returns the summary. No aggregation, no battery policy (ticket 11).

Global preconditions (raise): empty scope; empty config; unknown statistic name; any
trial in scope not `evaluated` (ruling G3); missing required params.

**Decision polarity (ruling G2)** — statistical discovery ⟺ court `"pass"`:

| statistic | court `"pass"` for a trial iff | decided trials |
|---|---|---|
| `fdr_by` / `fdr_bh` | the trial is **in** the FDR rejection set (H0 rejected) | every trial in scope |
| `dsr` | DSR ≥ `confidence` | `selected_trial_id` only |
| `pbo_cscv` | φ ≤ `phi_threshold` | `selected_trial_id` only |
| `noise_control` | p̂ ≤ `alpha` | judged/selected trial only |

Per-application contract:

- **`fdr_by` / `fdr_bh`** — params: `{"q": float}`. For each trial in scope:
  `t_stat(series.values, se_kind=declared.se.kind, lags=declared.se.lags)` →
  `p_from_t(t, declared.direction)`; then `fdr_by`/`fdr_bh` over the scope-ordered
  p-vector. v0.1 family policy: one trial = one hypothesis test, full scope enters
  (ledger contract §4.2). `computed`: `k_star`, `c_factor`, `q`, and per-trial parallel
  lists (`trial_ids`, `p`, `t`, `direction`, `se_kind`) for line-by-line audit.
- **`dsr`** — params: `{"selected_trial_id": str, "confidence": float}` (both required;
  the paper's example uses 0.95). Pipeline (note §3 pipeline order): `matrix(scope)` →
  per-column `sharpe_ratio` → V[{SR}] (ddof=1) and `avg_pairwise_correlation` → N̂ =
  `implied_independent_trials(M, ρ̂)` → selected trial's `series_moments` →
  `dsr(...)`. `computed`: `sr_selected`, `sr_star`, `z`, `var_factor`, `sr_trials_std`,
  `rho_hat`, `n_trials_raw`, `n_trials_effective`, `rho_ill_conditioned`
  (`rho_is_ill_conditioned(T, M)`, ruling C8), `n_obs`.
- **`pbo_cscv`** — params: `{"selected_trial_id": str, "n_splits": int,
  "phi_threshold": float, "metric": "sharpe"}`. Metric name resolved via the registry
  (ruling G5). `computed`: `phi`, `n_combinations`, `n_lambda_negative` (the logit vector
  itself is not persisted — contract §5.3 asks for "φ and logit counts").
- **`noise_control`** — params: `{"mode": "individual" | "pool_max", "alpha": float,
  "null_stats": list[float], "judged_trial_id": str (individual mode only)}` plus
  opaque provenance keys recorded verbatim into verdict params: `recipe`, `delta_min`,
  `seed`, `offsets`, `ranking_stat` (noise-control §6; the court never interprets them).
  The judge computes the ranking statistic from the series under the declared protocol
  (ruling F2): individual mode — observed = stat(judged trial); pool_max — observed =
  max over scope, argmax trial recorded as `computed.selected_trial_id` and judged.
  Then `empirical_null_p(observed, null_stats, alpha)`. `computed`: `observed`, `p_hat`,
  `n_at_least`, `n_nulls`, `null_stats` (the jury's values live in the verdict —
  noise-control §6), and in pool mode `selected_trial_id`.

`engine_version` is stamped from `court.__version__` (ruling G4). Ticket 08f also
finalizes `court/__init__.py`: `__version__` plus re-exports of `Ledger`, the record
types, all §5.1–5.6 public functions, `Application`, `Judgment`, `judge`.

## 6. Numeric guards summary

Collapsed from the notes' pitfalls sections; each guard must have a dedicated raising
test (§7).

**Global rule (referee ruling 2026-07-10, closing a §3.5 gap):** every scalar
float parameter of every public function must be finite; a non-finite scalar
(NaN/±inf) raises ValueError at entry. Range guards written as plain
comparisons (`vf <= 0`, `std < 0`, `n < 1`) are False for NaN and therefore do
NOT satisfy this rule on their own — NaN must never slip past a fence and
propagate silently (fail-closed everywhere, §3.5).

| Guard | Where | Source |
|---|---|---|
| n_obs < 2, non-finite values | sharpe, tstats | dsr.md §5.6 |
| σ̂ = 0 → raise | sharpe, tstats | dsr.md §5.6 |
| var_factor ≤ 0 → raise | sharpe (psr), dsr | dsr.md §5.6; ruling C2 |
| raw-vs-excess kurtosis: Normal case recovers 1 + SR²/2 | sharpe test | dsr.md §5.6 |
| Bessel n−1 in σ̂ and √(n−1) in PSR | sharpe | 2012 §2.5 / Eq. (11) |
| N=1 → E[max]=mean; N<1 → raise; N real-valued | dsr | dsr.md §5.5; rulings C4/C5 |
| ρ̂ ∉ (−1,1] → raise; ρ̂<0 documented extrapolation | dsr | ruling C7 |
| T < ½M(M−1) → disclosed flag, not an error | dsr/judge | dsr.md §5.3; ruling C8 |
| native frequency only; annualization display-only | all | dsr.md §5.1 |
| S even ≥2; T%S==0; N≥2; non-finite metric → raise run | pbo | pbo-cscv.md §6.3–6.4 |
| λ<0 strict; λ=0 not counted; (N+1)/2 midpoint | pbo | pbo-cscv.md §3.5 |
| step-up fills initial segment 1..k*; `≤` at boundaries | fdr | bhy.md §7.1, §6.5 |
| adjusted p monotone + clipped to [0,1] | fdr | bhy.md §7.2 |
| p ∉ [0,1] or NaN → raise; empty → k*=0 | fdr | bhy.md §7.3–7.4 |
| NW: explicit lags required; 0 ≤ lags < T | tstats | ruling E2/E3 |
| add-one p̂ never zero; ties count against; K≥1 | noise | Phipson & Smyth 2010; noise-control §4.1 |
| ledger fail-closed table | ledger | contract §6–7; §5.7 above |
| matrix label-for-label alignment, never repair | ledger | contract §7.2; pbo-cscv.md §6.1 |

## 7. Pytest plan — zero-glue vector mapping

Every hand-worked vector in the five documents becomes a pytest case calling the §5
functions **directly with the documented inputs** — no fixtures, no adapters, no glue.
Tolerance: `pytest.approx(abs=1e-9)` for derived floats (documents give ≥11 significant
digits; the γ 10-digit-vs-float64 difference is ~8e-12); exact equality (`==`) where the
spec pins a convention (`harmonic_number(10)`, rational fractions like φ = 0.5, λ = 0.0).

TDD order is contractual for every ticket: write the failing literature-vector tests
first, then implement to green (red → green → refactor).

| Test file | Case | Source | Anchors |
|---|---|---|---|
| test_sharpe.py | `psr` Normal returns | dsr.md §4.1 | var_factor == 1.125; z ≈ 2.26077666104; psr ≈ 0.98811345473 |
| test_sharpe.py | `psr` non-Normal | dsr.md §4.2 | var_factor == 1.4375; z ≈ 2.0; psr ≈ 0.97724986805 |
| test_sharpe.py | Normal-case factor identity | dsr.md §5.6 | `sr_var_factor(sr, 0.0, 3.0) == 1 + sr²/2` for sr ∈ {0.0, 0.5, 1.0} |
| test_sharpe.py | guards | dsr.md §5.6 | σ̂=0, n<2, non-finite, var_factor≤0 each raise |
| test_dsr.py | `expected_max_sr` | dsr.md §4.3 | max_z ≈ 1.57459830135; E[max] ≈ 0.78729915067 |
| test_dsr.py | `dsr` | dsr.md §4.4 | sr_star ≈ 0.78729915067; z ≈ 0.75509519676; dsr ≈ 0.77490406751 |
| test_dsr.py | paper cross-check | dsr.md §4.5 | N=100 → dsr ≈ 0.90039683445; N=46 → ≈ 0.95050170688; Normal (γ₃=0, γ₄=3) N=88 → ≈ 0.9505 (tolerance 5e-4 for the paper-rounded figure) |
| test_dsr.py | `implied_independent_trials` limits | dsr.md §2.c | ρ̂=0 → N̂=M; ρ̂=1 → N̂=1 |
| test_dsr.py | guards | dsr.md §5.5; rulings C4–C7 | N=1 → mean; N<1 raises; ρ̂ ∉ (−1,1] raises; constant column raises |
| test_pbo.py | S=4 fixture, metric = mean | pbo-cscv.md §5 | logits == (0, ln(1/3), 0, 0, ln(1/3), ln(1/3)) positionally (ln(1/3) ≈ −1.0986122886681098); phi == 0.5; n_combinations == 6 |
| test_pbo.py | guards | pbo-cscv.md §6.3–6.4 | N=1, odd S, T%S≠0, **T<2S (incl. T=0 and T=S)**, non-finite metric each raise |
| test_tstats.py | iid t | §5.4 vector | t == 3.464101615137754 (pipeline pin; see §5.4 re-pin note) |
| test_tstats.py | NW t, lags=1 | §5.4 vector | t == 3√2 ≈ 4.242640687119285 |
| test_tstats.py | `p_from_t` | §5.4 vector | three 0.05 anchors |
| test_tstats.py | guards | ruling E2/E3 | NW without lags; lags with iid; σ̂=0; bad direction each raise |
| test_fdr.py | `harmonic_number(10)` | bhy.md §6.1 | == 2.9289682539682538 (exact) |
| test_fdr.py | BH N=10 | bhy.md §6.3–6.6 | k*==9; rejection set == {H2,H9,H5,H7,H6,H3,H10,H1,H8} by input position; H4 (p=0.09) not rejected |
| test_fdr.py | BY N=10 | bhy.md §6.5–6.6 | k*==3; rejection set == {H2,H9,H5} |
| test_fdr.py | step-up inclusion | bhy.md §6.5 | rank-5 trial (p=0.026 > 0.025) IS rejected under BH |
| test_fdr.py | boundary equality | bhy.md §6.5 | p==τ at ranks 8, 9 counts as rejected (`≤`) |
| test_fdr.py | adjusted-p properties | bhy.md §7.2 | monotone in sorted order; clipped ≤ 1; `adjusted_p[i] ≤ q ⟺ reject[i]` |
| test_fdr.py | empty + guards | bhy.md §7.3–7.4 | empty → k*=0; p>1, p<0, NaN each raise |
| test_noise.py | vector 1 | noise-control.md §8.1 | p̂ == 3/5; decision "reject" |
| test_noise.py | vector 2 (tie) | noise-control.md §8.2 | p̂ == 2/4; tie counted against; "reject" |
| test_noise.py | vector 3 | noise-control.md §8.3 | K=199, none ≥ observed → p̂ == 1/200 == 0.005; "pass" at α=0.05 |
| test_noise.py | vector 4 (resolution) | noise-control.md §8.4 | min attainable p̂ at K=199 == 0.005; never 0.0 |
| test_ledger.py | behavioral contract | trial-ledger.md §5–7 | registration-before-evaluation line order; duplicate `record` raises; unknown ids raise; no-abandoned-state (status only ever registered/evaluated/judged); `status` derivation incl. judged after `append_verdict`; series stored by value; no derived stats fields on trial records |
| test_ledger.py | storage | trial-ledger.md §6 | reopen replays to identical records; torn final line discarded and next append valid; mid-file corruption → `LedgerCorruptionError`; at-most-one evaluation enforced on replay |
| test_ledger.py | matrix | trial-ledger.md §7.2 | label-for-label alignment; misaligned index raises; column order == trial_ids order |
| test_ledger.py | guards | §5.7 table | every row of the fail-closed table has a raising test |
| test_judge.py | fdr_by application E2E | contract §7.4; §5.8 | toy ledger (3 trials, hand-chosen series) → one VerdictRecord; scope verbatim; decisions polarity correct (discovery ⟺ "pass"); computed carries k_star + per-trial p |
| test_judge.py | noise_control application | noise-control §6; §5.8 | params carry provenance verbatim; computed carries null_stats + p_hat; decision correct |
| test_judge.py | polarity table | ruling G2 | one case per statistic exercising each pass/reject direction |
| test_judge.py | guards | ruling G3 | unevaluated trial in scope raises; unknown statistic raises; empty scope raises |
| test_smoke.py | decoupling (exists) | ticket 02 | stays green throughout |

## 8. Implementation ticket cut

Six tickets; 08a–08e are mutually independent (parallel-dispatchable); 08f integrates.

| Dispatch id | Issue | Delivers | Blocked by |
|---|---|---|---|
| v0.1-08a | 13 | `court/ledger.py` + `tests/test_ledger.py` | — (spec merged) |
| v0.1-08b | 14 | `court/sharpe.py`, `court/dsr.py` + tests | — |
| v0.1-08c | 15 | `court/pbo.py` + tests | — |
| v0.1-08d | 16 | `court/tstats.py`, `court/fdr.py` + tests | — |
| v0.1-08e | 17 | `court/noise.py` + tests | — |
| v0.1-08f | 18 | `court/judge.py`, `court/__init__.py` public API + tests | 13, 14, 15, 16, 17 |

Every ticket embeds: the TDD requirement (failing literature-vector tests first), the
acceptance commands (`pytest`, `ruff check .`, smoke test green, clean `git status`), and
the file-ownership boundary (§2) so parallel branches merge cleanly.

## 9. Out of scope

- Battery composition, survival aggregation, demo presentation, α/q/confidence values
  used by the demo → ticket 11.
- Null-jury generation (circular shift, offset grid, RNG) → adapter/demo side, tickets
  10/11 (`noise-control.md` §2–3, §7).
- BHY per-hypothesis representative policy → v0.2 switch (ledger contract §4.2).
- Pre-registration enforcement hooks → v0.2 harness (contract §10).
- Concurrent multi-writer ledgers; non-JSONL backends (contract §11).
- HAC/GMM SE variants beyond Newey-West; automatic NW lag selection (ruling E2).

## References

- `docs/design/trial-ledger.md` — the ledger contract (schema, API layers, N derivation).
- `docs/design/noise-control.md` — noise-control design (empirical_null_p contract, vectors).
- `docs/research/dsr.md` — Bailey & López de Prado (2012, 2014): PSR, E[max SR], DSR.
- `docs/research/pbo-cscv.md` — Bailey, Borwein, López de Prado & Zhu (2017): CSCV/PBO.
- `docs/research/bhy.md` — Benjamini & Hochberg (1995); Benjamini & Yekutieli (2001);
  Harvey, Liu & Zhu (2016); Newey & West (1987).
- `docs/design/noise-control.md` References — Phipson & Smyth (2010); White (2000).
- `CONTEXT.md` — canonical vocabulary (Trial, Hypothesis, Verdict, Declared protocol,
  Effective trial count, Ledger, Scope, Null jury).
- `.scratch/v0.1/issues/08-court-kernel-spec.md` — the assembling ticket.
