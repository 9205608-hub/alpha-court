---
name: research-session-protocol
description: 研究 session 协议 — the discipline for running one research *session* (a search over many factor/signal variants) without p-hacking yourself. Use when opening an exploratory session; when you catch yourself on "just one more tweak"; when a horizon/universe/winsor sweep is quietly inflating your effective N; before you tell the court a factor was "found". It sits UPSTREAM of the court and AROUND factor-research-flow, making the N you hand downstream the *true* count of what you tried. L1 discipline (any desk); alpha-court's adapter (`evaluate`/`evaluate_shifted`) + court consume the honest N it produces.
---

# Research-session protocol (研究 session 协议 · 工位二)

**A research session is a *search*, and every search over noise finds a winner.** The
only question that keeps you honest is *how many things you tried to find it* — because
that count is the multiplicity you owe the court, and it is the one number that stays
invisible unless you log it as you go. This station governs the live search loop:
`factor-research-flow` grades **one idea's** quality; `honest-validation` (禁赢学) judges
**one finished result**; this governs the messy stretch **between** them, where you try
variant after variant and, unlogged, your true N silently inflates until every downstream
correction (DSR number-of-trials, FDR family size, best-of-N selection) is computed on a lie.

It is useful **even if you never run alpha-court**: the protocol + log are how you keep a
Jupyter search over baostock/qlib honest. The court is just the most demanding consumer of
the honest N it produces.

## 0. Declare the mode — EXPLORE or CONFIRM (never both at once)

A session is one or the other, and you write which in the log header.
- **EXPLORE**: you are searching; you do **not** yet have the candidate. Legitimate and
  necessary — but its only outputs are a *hypothesis* and an *honest N*, never a verdict.
- **CONFIRM**: you have a frozen candidate; you pre-register and hand to 禁赢学. No new
  variants may be tried here.

You cannot pre-register while exploring (you don't yet know what to freeze); you cannot try
variants under a CONFIRM banner (that is **HARKing** — writing the mechanism to fit the
winner you already saw). The **stopping rule (§2) is the one-way door** from EXPLORE to
CONFIRM. This mode split is exactly why 禁赢学's "pre-register before you touch the data"
does not cover this station: pre-registration is a confirmatory act, and a session's job is
to survive the *exploratory* phase that precedes it — and to emit the thing you register.

## 1. Before the first data pull — hypothesis + the kill-test

- **Mechanism sentence**: carry `factor-research-flow` §1's mechanism sentence in
  *unchanged* — flow owns whether the idea is any good. The session's *only* new obligation
  is that this sentence is **frozen as the search target before the first pull**, so the data
  can't retro-fit a mechanism onto the winner you happen to see (that is HARKing, §0).
- **The kill-test** (quant-mentor #1/#3 *falsify-before-you-optimize*, made session-scoped):
  the single cheapest cut whose *failure ends the session* — "this idea is **dead** if ___"
  (RankIC sign flips against the mechanism; no monotonicity across quantiles; the whole edge
  is one month or one name). The session-specific rule the mentor doesn't give you: **the
  kill-test is the first draw against budget K, and its failure is a *legal stop*, not a
  wasted session** (禁赢学: null = survivor). Run it before any tuning.

## 2. Set the search budget BEFORE searching — the stopping rule (the core)

Write a number down: **"I will evaluate at most K variants, then stop and either declare
one candidate or kill the hypothesis."**

- **What counts as a trial (a fork).** *Every* analyst choice made after seeing data is a
  test: horizon {1,5,10d}, universe {csi300, csi500}, winsorize on/off, neutralize on/off,
  decay half-life, quantile cut, `adjustflag` {1,2,3}. Sign-flips are two arms (禁赢学 rule 5).
  But the raw grid product is only an **upper bound** on N. It cuts two ways:
  - *down* — adjacent forks are **correlated** (5d vs 10d horizon on the same names move
    together), so the multiplicity you truly owe is an **effective** N_eff < grid product;
    discount for it only with an argument you write in the log, never by feel;
  - *up* — an **adaptive** search (each fork chosen after seeing the last result) is a garden
    of forking paths whose real multiplicity includes the branches you *would* have taken
    (Gelman & Loken), not just the rows you ran; optional-stopping inflates N beyond the count.
- **Derive K from the haircut you'll pay — don't pick a mood.** Not "keep it small (~10–20)":
  that is a number dressed as a threshold, the exact move this project condemns. Under a
  **family-wise** bar (Bonferroni/Šidák — controls *any* false positive) at level α, your
  single best finding must clear ≈ α/K, so the budget cap is **K ≲ α / p\*(target |t|)** — the
  weaker the edge you expect, the *less* you are allowed to search:

  | target \|t\| | two-sided p\* | max K at α=0.05 (Bonferroni/FWER) |
  |---|---|---|
  | 2.0 | 0.045  | **≈ 1** |
  | 2.5 | 0.012  | **≈ 4** |
  | 3.0 | 0.0027 | **≈ 18** |
  | 3.5 | 0.0005 | **≈ 108** |

  Pick the family by what you're doing, and **don't blur FWER and FDR into one "Šidák/BHY"**:
  Bonferroni/Šidák control FWER; BH/BHY control FDR (BHY is *stricter* than Bonferroni by the
  Hₖ factor; BH at rank-1 ≈ Bonferroni). **"Best of the sweep" — the max over your N variants
  — is a FWER / White Reality-Check problem, not BHY.** The budget is a *consequence* of the
  correction, not a vibe: a |t|≈2.5 idea you searched 40 ways for is dead on arrival.
- **Stop at:** the budget K, OR the first kill-test failure, OR a pre-declared "good enough"
  (§3). **No "one more tweak."** Hitting K empty and quietly raising it is the search-layer
  version of seed-fishing. Raising the budget is legal **only** as a dated log entry written
  *before* the extra runs — and the **new K is the N you owe the court**.

## 3. Freeze the go/no-go before you look

- **Decision numbers up front**: what RankIC / ICIR / |t| / quantile-monotonicity makes a
  variant a *candidate*, what makes it *dead*, and — critically — **on which slice you read
  it**. Written before running, so the data cannot move the goalposts.
- **Pin label + universe first; then anything you *un*-pin is a counted fork.**
  `factor-research-flow` §0 says fix the label and universe before you start — do that. The
  reconciliation with §2: those pins are your *defaults*, not forbidden knobs. The moment you
  sweep horizon or swap csi300→csi500 to chase IC, each alternative becomes a fork that
  spends budget K. Pinning is the honest default; un-pinning is legal but *costs N*.
- **Carve the OOS slice at session start; spend it once, at CONFIRM.** Split the evaluation
  `window` into an *explore* span and a *reserved* span now (禁赢学 rule 6, timed to
  session-start). A **legal OOS read** happens exactly once and decides one thing: does the
  candidate's reserved-span IC land inside the noise band its explore-span IC predicts? If
  yes → confirm; if it collapses → the explore result *was* the search overfitting, and the
  honest close is *no signal*. Peeking mid-search burns it — there is no second one.

## 4. The session log — the honest-N artifact (second deliverable)

**Append-only, one row per trial, written the moment you run** — never reconstructed at the
end (reconstruction silently drops the failures; that *is* the file-drawer). Template:

```
# Research session — <factor / hypothesis name>
mode:            EXPLORE
opened:          <ISO datetime>
hypothesis:      <one line>
mechanism:       <one line: whose mistake / why it persists>
kill-test:       dead if <the single falsifying cut>
budget K:        <max variants, e.g. 15>
decision (GO):   candidate if <RankIC/ICIR/|t|/monotonicity + which slice>
decision (KILL): dead if <numeric>
window split:    explore=[start..cut], reserved-OOS=[cut..end]   (reserved untouched)
data tag:        <declared_data_tag>   # replay id = (data_tag + fork coords); seed col only if construction is stochastic

## Trials  (append-only; realized values as they come out — no rounding)
| # | time | fork coords (horizon/universe/winsor/adjustflag/…) | seed | metric | decision | note |
|---|------|----------------------------------------------------|------|--------|----------|------|
| 1 | …    | 5d / csi300 / winsor=on / adj=1                     | …    | IC=…   | continue | kill-test ran first |
| … |      |                                                    |      |        |          |      |

## Close
trials run (honest N): <count, incl. sign-flip arms>   # ← the N you hand downstream
winner:          <exact fork coordinates, or NONE>
abandoned branches (null = survivor — equal weight):
  - <coord> : <realized metric> : <why killed>
budget amendments: <none | dated entries>
```

The **honest N** is the row count (sign-flip arms doubled), not the survivor count. Every
abandoned branch is listed with the same weight as the winner — the morgue is documentation,
not a file-drawer (禁赢学 rule 4 / flow §3).

## 5. Hand-off — the honest N is a contract with the court

The session's trial count is not bookkeeping; it is the **effective multiplicity you owe to
*whatever* haircut you apply next** — a Bonferroni/BHY family size, a Deflated-Sharpe trials
count, a best-of-N / White-Reality-Check selection correction, or even the discount you take
in your head
before believing a number. Under-reporting it — quietly dropping the branches you abandoned
— makes every one of those too lenient, and you "pass" by hiding your search. Concretely:
*tried 40 horizon×universe×winsor combos, kept 1 → the count you carry forward is 40, not 1.*
If alpha-court is your validator, fold the log **header** (hypothesis / mechanism / frozen
criteria / data tag / reserved window) into the pre-registration and run 禁赢学; if it isn't,
the same honest N still governs whatever correction you do run. **This station produces the
honest N and the frozen criteria; the downstream validator consumes them.**

## A worked micro-example (illustrative)

You hypothesise *5-day reversal in CSI500 small-caps* (mechanism: retail overreaction to
week-moves, slow to correct) — a mechanism you rate strong, so **you expect |t|≈3 if it's
real**. **Kill-test:** if full-window RankIC carries the *momentum* sign, dead. **Budget:**
a family-wise bar at α=0.05 caps K at ≈ 0.05 / p\*(|t|=3) ≈ **18**, so you set **K = 16**. You
sweep horizon {3,5,10d} × winsor {on,off} × neutralize {on,off} = 12 rows (reading both signs
on the finalist could reach 24, so you stop the grid at 12 and reserve the sign-read). The
finalist (5d / winsor on / neut on) reaches **|t| = 3.1** on the explore span, monotone
quintiles: a candidate — and 3.1 clears the Bonferroni bar for K=12 (which needs |t| ≳ 2.9).
**Honest N handed forward = 12** (every abandoned row logged, equal weight), *not* 1. Reserved
OOS (last 6 months, untouched all session) read once: the |t| holds inside its explore-span
confidence band → confirm, hand to 禁赢学 with N = 12. Had you quietly raised K to 60, the bar
climbs to |t| ≳ 3.34 (0.05/60) — your 3.1 finding now *dies*, and 60 is the N you'd owe
anyway. The budget forces the discipline; it isn't a mood. *(Numbers are two-sided normal
approximations, for the shape of the argument — a real read needs T, mean IC and IC vol to
turn RankIC into a t.)*

## What this is NOT — boundary

- **vs `court` (the validator):** court is a thing you *run on a finished result*
  (`judge` / `dsr` / `pbo_cscv` / `empirical_null_p`). This station lives entirely
  **upstream**, during the search, before any verdict exists. It computes no statistic; it
  makes the *inputs* (N, seeds, criteria) to court's statistics honest.
- **vs `quant-mentor` (the judgment):** mentor *names* the moves ("falsify before you
  optimize," "overfitting is the null," "number-of-trials"). This is the **concrete session
  procedure** that executes them: a live trial counter, a written budget, a stopping rule, a
  log template. Mentor is the mindset; this is the checklist that leaves a trace.
- **vs `honest-validation` (禁赢学):** 禁赢学 pre-registers **one confirmatory study** and
  reads **one verdict** honestly. This governs the **exploratory search that precedes having
  a candidate to register** — the budget, the stopping rule, and the live N-count that 禁赢学
  assumes but does not itself track. 禁赢学 says "N is what you tried"; this is *how you
  actually count it, as you go.*
- **vs `factor-research-flow`:** flow grades **one idea** through three quality lenses
  (net-of-cost / capacity / orthogonality). This governs the **process of searching over
  many ideas** (budget / N / log). You run flow *on the candidate you emerge with*; you run
  this *around the whole search*, deciding whether you're even allowed to emerge with one —
  and counting how many you tried.
- **Not generic engineering hygiene.** Determinism and versioning matter here only insofar
  as they make a *trial* replayable (a seed per row). This is a research-integrity protocol,
  not a data-eng checklist.

## Form & what's mechanizable (D1 honesty)

By D1 this is a **skill (judgment-bearing multi-step procedure) plus a structured log
template** — most of it (choosing K, what counts as a fork, when the kill-test fires) is
judgment that cannot be a predicate. Two parts *are* mechanizable once params are frozen —
**one is now built**:
- **[LANDED, narrowly]** a **file-backed session counter + a manual reconcile helper** —
  `harness/trial_counter.py` (*not* an auto-firing gate). You `record_trial(session_dir, fork)`
  each evaluation; `reconcile(...)` — or `python -m harness.trial_counter reconcile <dir>
  --declared-k K --reported-n N` (exit 1 on a flag) — fails when the trials you ran exceed the
  declared K, when the N you report is smaller than what you ran, or when you claim N > 0
  against an **empty** ledger (it refuses to certify a phantom N). It writes a
  `<session_dir>/session-trial-count.jsonl` — **not** `court`'s trial `Ledger`
  (`docs/design/trial-ledger.md`); don't conflate the session count with the court ledger. It
  is **file-backed** so the count survives a kernel restart (the "where does the counter live"
  problem): the subprocess red-test in `tests/test_trial_counter.py` fails an in-memory draft
  (CR-08 — the bypass red-test was written *first* and shown to bite a naive counter before the
  real tooth passed it; grok RP-1 then caught the phantom-N and sharding bypasses the first
  pass missed, both now red-tested).
- Honest limits, red-tested where a test can pin them: the count is a **lower bound** (declare
  sign-flip arms via `arms=`); a **NIH** evaluation you never record is invisible (工位三's
  job); it reconciles **one** `session_dir` — sharding across dirs / a fresh empty dir / wiping
  the file all evade it (use one canonical dir); a corrupt line fails **loud**
  (`TrialCountError`). It stops you *forgetting*, not you *editing the count out*
  (tamper-evidence needs git — a self-honesty aid, same posture as `skill-review-gate`).
- **[LANDED — callable/CLI, not CI-wired]** a **budget gate** at CONFIRM —
  `harness/confirm_gate.py` (11 tests). Reads a prereg JSON (`{"reported_n", "session_dir"}`) and
  refuses to open it unless the N you declare covers the trials recorded *in that ledger* (blocks
  under-reporting + a phantom empty ledger; over-declaring is allowed). **Fail-closed on malformed
  input** — a bypass-enumeration workflow found `json` accepts `NaN`/`Infinity` (which defeat the
  reconcile against *any* ledger), so `reported_n` must be a finite `int ≥ 1` (rejecting
  NaN/Inf/float/bool/str/null/0/missing) and `session_dir` an **absolute** existing directory; a
  corrupt ledger REFUSES, never swallowed. **What it does NOT do** (inherited trial_counter
  limits, not "every degenerate"): it counts the ledger you *name* — it cannot check you named the
  *right* one (a decoy dir / symlink with an honest-looking small N passes), and it is a
  point-in-time check (append trials after it passes and it never re-fires).

The counter and the CONFIRM budget gate are both real (callable + CLI); neither auto-fires in
CI, and both only see the one session you honestly record into. Run them and read the output
*before* you tell any validator your N.

## L2 binding — the real tools

- **qlib-cn adapter** (`adapters/qlib_cn.py`): one `evaluator.evaluate(scores, metric)` (or
  one row of `evaluate_shifted`) **= one trial** — log it. Fork coordinates map to config:
  `window`, `quantile`, `min_cross_section`, `label_expr` (horizon), `universe`. The adapter
  holds **zero RNG** (contract §8), so a factor evaluation is **deterministic given
  `(declared_data_tag, fork coordinates)`** — *that tuple*, not a seed, is the load-bearing
  per-row identity that replays a trial. Keep a seed column **only** for the sub-case where
  factor *construction* is genuinely stochastic (a random projection, a sampled sub-universe).
  The `evaluate_shifted` offset jury (`B_OFFSETS = 199` circular shifts) is an **independent**
  null-resolution parameter — *not* fed by your session N. Don't conflate them: N is how many
  variants you tried; 199 is how finely the harness resolves one candidate's null.
- **baostock** (data pull): `adjustflag` {1=back,2=fore,3=raw}, `frequency`, and universe
  (`query_hs300_stocks` vs `query_zz500_stocks`) are **fork coordinates, not innocent
  defaults** — re-pulling with a different `adjustflag` until IC turns positive is a trial
  you must count. Log the exact pull params per row.
- **N → validator:** the session trial count (sign-flips doubled) is the **selection
  multiplicity** — it sets DSR's `n_trials`, the FDR family size, and the best-of-N /
  Reality-Check correction. It does **not** set the empirical-null jury size
  (`B_OFFSETS = 199`, independent). The log's Close block is the single source of truth for N.

## See also

`factor-research-flow` (idea-quality lenses; runs on the winner), `honest-validation`
(禁赢学; pre-registers + judges the CONFIRM phase), `quant-mentor` (the judgment this
proceduralizes), `docs/design/killer-demo.md` §7 (a worked pre-registration; master-seed
tree §9), `docs/design/adapter-interface.md` §7.3 (`evaluate_shifted` offset jury = the
empirical null your N feeds), `docs/design/quant-workflow-system.md` (D1 form; the station map).