---
name: data-pipeline-hygiene
description: The data-ingress station (工位一) — audit the data feeding your factors for quant-specific contamination (PIT membership & fundamentals, forward-return alignment, survivorship, feature look-ahead, universe/tradability, calendar, snapshot versioning) BEFORE any result exists. Use when wiring or refreshing a qlib-cn / baostock data source, building a factor's input panel, or whenever a backtest looks 'too clean.' L1 discipline: a run-once preflight checklist + per-trap 中招/自查; alpha-court's qlib-cn adapter is the reference for the checks it mechanizes.
---

# Data-pipeline hygiene (数据管道纪律 · 工位一)

**The court tells you whether a *result* is overfit; this station keeps a
contaminated *input* from ever producing one.** It is the research pipeline's
data-ingress gate — you run it **once when you wire up or refresh a data source**,
before a single factor score exists, and it protects every factor built on top. A
look-ahead leak or a survivorship-frozen universe produces a series that looks
clean and can *pass* the court; garbage-in is invisible to every downstream
statistic. This is the L1 discipline that makes the bytes honest. Your two real
sources are **qlib-cn** (`adapters/qlib_cn.py`, the reference implementation for
the checks it mechanizes) and **baostock** (a *live* API, hand-wired) — every trap
below is bound to both.

Its ethos is 禁赢学 pushed one layer upstream: **handle it, or *declare* you
don't** — in a string that travels with the result (`adapter-interface.md` §5.4
"declared not handled"). Never silently pretend.

## 0. The preflight — clear all eleven gates before the first factor; re-run on every snapshot refresh

A dataset is not "ready" because it loads. Each gate maps to a trap (§T*); emit the
**data manifest** (T9) only when all clear.

- [ ] **P1 Version frozen** — source pinned to a fixed tag/hash, or self-snapshotted if the source is live. (→T9)
- [ ] **P2 Universe is point-in-time** — membership resolved as-of each date, not one snapshot; width varies over the window. (→T1)
- [ ] **P3 Survivors aren't the only names** — delisted / merged names are present for the window. (→T4)
- [ ] **P4 One calendar, edges drop clean** — every t, t+1, t+2 is a real trading day; the window tail drops identically for every candidate. (→T8)
- [ ] **P5 Label is execution-honest** — score_t → enter t+1 → exit t+2; a one-day *extra* shift of the label collapses IC. (→T3)
- [ ] **P6 Fundamentals keyed to pubDate** — nothing enters the panel before its publication / as-of date. (→T2)
- [ ] **P7 No full-sample stats in features** — every normalization uses data ≤ t only. (→T5)
- [ ] **P8 One fixed universe def, signal == label** — ST / limit / suspension policy chosen once and applied to both sides identically. (→T6)
- [ ] **P9 Tradability modeled or declared** — suspension / limit-up-down either implemented or written into a declaration string. (→T7)
- [ ] **P10 Fail closed** — in a hand-wired (baostock) pipeline *you* must build the floor: raise on NaN/inf, enforce a min-cross-section, never silently impute. The qlib-cn adapter already does this (§T6); a raw source won't unless you add it. (→T6)
- [ ] **P11 Cross-source & field semantics clean** — instrument codes reconciled across sources; string/empty fields not silently coerced to NaN. (→T10)

## T1 · PIT universe membership

**中招 (bitten):** you call `bs.query_hs300_stocks(date="today")` once and apply
today's constituent list to all of history — you are now trading names *because*
they end up in CSI 300 (look-ahead + survivorship in one). Same trap with a
start-of-window snapshot, or qlib `D.instruments("csi300")` used without interval
filtering: membership frozen, cross-section width flat.

**自查 (self-check):** width must *change* across rebalances — a flat member count
over two years means you froze it. **qlib-cn [LANDED]:**
`D.list_instruments(D.instruments("csi300"), start, end, as_list=False)` returns
per-instrument membership **spans**; the adapter's `_build_pit_mask` admits a name
on date d only if `a <= d <= b` (`adapters/qlib_cn.py` `_build_pit_mask`;
`adapter-interface.md` §5.1, 939 historical members / 336 with data in a 2-yr
window). **baostock [discipline]:** loop `query_hs300_stocks(date=d)` per rebalance
date and build the membership calendar yourself — a single-date call is PIT *only*
at that date. Subtlety even the per-date loop misses: `query_hs300_stocks(date=d)`
returns *effective-date* membership, knowable only **after** the index committee's
announcement — for strict PIT, lag membership to the **announce** date, not the
effective date.

## T2 · PIT fundamentals (restatements)

**中招:** you key a financial value to `statDate` (fiscal period end) and let it
enter the panel on that date. But the number wasn't *known* until `pubDate`
(publication), weeks-to-months later — and may have been **restated** afterward.
Aligning a Q2 figure (statDate 2024-06-30) to 2024-06-30 means you "knew" earnings
before they were announced: a multi-week look-ahead on every fundamental factor.

**自查:** every baostock financial API returns **both** `pubDate` and `statDate`
(`query_profit_data`, `query_growth_data`, `query_balance_data`, …) — key the value
to **pubDate**, admit it to the panel only on/after pubDate. The disclosure timeline
is *forecast → express → final*, each its **own** earlier as-of
(`query_forecast_report`, `query_performance_express_report` carry their own pub
dates). For a known name, plot known-as-of vs statDate and confirm the lag.
**Honest limit:** alpha-court's qlib-cn adapter loads a **price label only** — it has
**no fundamental path**, so all of T2 is baostock-side discipline, backed by no
alpha-court code.

## T3 · Forward-return alignment & lag

**中招:** you compute the return as `close_t / close_{t-1} − 1` and pair it with the
score at t — the *same* close both revealed the signal and priced the entry
(trade-at-signal-close look-ahead), which A-share **T+1** makes physically
impossible. Or you get the `Ref` sign backwards and shift the label the wrong way.

**自查: qlib-cn [LANDED]:** the reference label is
`Ref($close, -2)/Ref($close, -1) − 1` (`DEFAULT_LABEL_EXPR`, `adapters/qlib_cn.py`;
§4.2): score at t's close → enter at **t+1** close → hold to **t+2** close — a
one-day execution gap. **Leak probe [DESIGNED, not built]:** shift the label one
*extra* day and re-evaluate — a real signal degrades gracefully, a leak *survives*
the shift (it fires when your feature already contains t+1 information). This is
**not** `evaluate_shifted`: that routine circular-shifts the *score* row to build
the empirical-null jury and **never touches the label** (§7.3); the label-shift
hygiene probe is its own, unbuilt check. **baostock:** compute from adjusted close
and lag explicitly; never pair `score_t` with a return built from `close_t`.

## T4 · Survivorship bias

**中招:** you enumerate only currently-listed names — `bs.query_stock_basic()`
filtered to `status == 1`, or `query_all_stock(day=today)` — so delisted, merged,
and de-indexed names vanish and your backtest only ever sees the winners. (T1 is
this trap for an index; T4 is it for the whole universe.)

**自查: baostock:** `query_stock_basic()` returns `status` (1 listed / 0 delisted)
**and** `outDate` — **include** names whose `outDate` is after your window start;
resolve membership as-of each date, never as-of today. **qlib-cn [LANDED]:** the
pinned `chenditc/investment_data` pack + PIT interval filtering (T1) is
survivorship-free by construction (§5.1). Self-check: count names that enter the
universe and later leave it — if **nothing ever leaves**, you have survivorship. And
presence isn't enough: a delisted name needs its **terminal / delisting return** (often
a steep loss); including the name but dropping its final return is survivorship's quieter
half.

## T5 · Look-ahead inside features

**中招:** normalization that reaches into the future — z-scoring by a mean/std
computed over the **whole** history then applied at t; winsorizing to full-sample
quantiles; a `ffill` / `bfill` that pulls a later observation backward; or reading
**price levels** off a backward-adjusted series (`bs` `adjustflag="1"`, and qlib
`$close`, bake future splits/dividends into *past* levels — level factors leak,
though pct-**returns** are usually safe because the future factor cancels in the
ratio).

**自查:** compute every normalization stat on data **≤ t** only (expanding / rolling,
never full-sample). **Mechanical test:** null every row **after** t, recompute
`feature_t`, and assert it is unchanged — that catches a look-ahead no metric can
(a monotone renorm that moves RankIC changed ranks; see `factor-research-flow` §2 for
the invariance principle). qlib's label is ratio-safe by construction (§4.3); a factor
that reads adjusted **levels** is not — and even a ratio leaks if you mix adjusted price with
un-synced shares/EPS (see T10).

## T6 · Universe construction

**中招:** mixed definitions — ranking cross-sectionally over names that aren't
tradable that day; ST/*ST names silently in or out; the signal computed on one
universe and traded on another; or a cross-section that collapses on some days so
the rank / quantile is meaningless.

**自查:** fix **one** universe definition and apply it identically to signal and
label. **qlib-cn [LANDED]:** the per-day **joint mask** is `PIT ∧ score-finite ∧
label-finite` (`_shared_kernel`, `adapters/qlib_cn.py`), and a
**min_cross_section** floor (default 50) *raises* if any day's usable width falls
below it (§5.3) — fail-closed, never a silent thin day. **baostock:** the `isST`
field flags ST names; decide and **declare** whether they are in. Plot width per
day and assert a floor.

## T7 · Suspension / limit-up-down tradability

**中招:** you assume a t+1-close fill when the stock is **suspended** (no trade) or
**limit-locked** (涨停 can't buy / 跌停 can't sell). A suspended name carries a stale
price; a phantom fill at a limit inflates paper PnL.

**自查: baostock:** `tradestatus` (1 normal / 0 suspended) gates entry; there is no
direct limit flag, but `high == low` with `pctChg` at the band (±10%, ±20% STAR /
ChiNext, ±5% ST) is a limit-lock proxy — exclude such names at the execution date.
**qlib-cn [LANDED as *declared-not-modeled*]:** the adapter **declares** limit-up/down
and suspension-at-execution **not handled** (§5.4); a suspended name has a NaN label
and simply leaves the day's cross-section (pairwise exclusion, §5.3) — honest for a
*statistical* demo, **not** a tradability model. The discipline is the **§5.4
tradability declaration** riding in the manifest — a *distinct* string from the §4.4
`COST_DECLARATION` (which is about transaction costs, not tradability; don't conflate
them). If you don't model tradability, declare it there — never let a limit-locked
phantom fill into paper PnL unlabelled.

## T8 · Trading calendar & window edges

**中招:** a generic (weekends-only) calendar puts t+1 on a holiday that isn't a
trading day; two sources with different calendars so dates don't line up; or you
assume a forward return exists at the window edge (the last two days have no t+2).
*(Timezone/session-boundary bugs are a US/crypto worry — the two daily A-share
sources here are single-session; the trap only reappears if you add an intraday or
cross-market feed.)*

**自查:** one calendar is the source of truth. **qlib-cn [LANDED]:** `D.calendar()`
drives `_evaluation_dates_from_calendar` — an eval date must have **both** t+1 and
t+2 in the calendar with **t+2 ≤ end** (`adapters/qlib_cn.py`; §5.2), so the last
two window days drop out identically for every candidate; the date index is
`.normalize()`d to midnight so cross-source joins align. **baostock:** derive
trading days from `query_all_stock(day=…)` or an index K-line's `date` column —
never synthesize a calendar. Assert every t+1 / t+2 you reference is a real
trading day.

## T9 · Snapshot versioning & tag

**中招:** you read from a `latest` endpoint or a **live** API. baostock is a live
service — its answer for "CSI 300 members on 2024-12-31" or a restated fundamental
can **change between two runs**, so your "reproducible" study silently drifts; or
you refresh the data pack and your golden numbers move with no code change and you
can't tell drift from a bug.

**自查: qlib-cn [LANDED]:** pin `chenditc/investment_data` to a **fixed release tag**
(§6, currently `2026-07-05` — **never `latest`**); every result's `meta.data_version`
carries `{declared_tag, calendar_end (measured), n_instruments (measured)}`
(`_meta`, `adapters/qlib_cn.py`) so an auditor detects a tag/pack mismatch, and a
**golden-fingerprint** test fails loudly on silent drift (§8). **baostock has no
version tag [discipline / DESIGNED tooling]:** so **snapshot it yourself** — dump the
raw query to a dated, hashed file and read the snapshot, not the live API, for the
life of a study; re-run the same query on two days and diff. **Manifest:** attach
`{source, tag/hash, pull_date, calendar_end, n_instruments, universe_def,
label_expr, tradability_declaration}` to every downstream series, so the input is
reconstructable from the verdict alone.

## T10 · Cross-source reconciliation & field semantics

You run **both** qlib-cn and baostock — joining them is a first-order silent-bug surface.

**中招:** (a) **instrument codes don't match** — qlib emits `SH600000`, baostock emits
`sh.600000`; an unnormalized join silently drops or mis-pairs names and your cross-section
shrinks. (b) **baostock returns every field as a *string*, and non-trading fields come back
empty** — `turn` / `pctChg` / `peTTM` = `""` on a suspended day → `pd.to_numeric(…,
errors="coerce")` maps them to NaN and your factor silently loses exactly the names worth
reasoning about. (c) **valuation factors mix adjustment conventions** — back-adjusted price ×
point-in-time shares/EPS double-counts splits; ex-dividend gaps in a *raw* series masquerade
as returns.

**自查:** normalize codes to one canonical form at ingest and assert the joined width equals
the intersection you expect. Parse baostock fields explicitly; treat `""` as
*missing-because-untraded* (not zero, not a silent drop) and log how many names each coercion
removes per day. For valuation factors keep price adjustment and fundamental as-of on the
**same** convention (raw price ⇄ raw shares), or declare the mismatch. **All discipline —
there is no adapter code for cross-source joins.**

## A worked leak example (why the court structurally can't save you)

Build a "5-day reversal" factor but read it off qlib `$close` **levels** (T5) instead of
pct-returns. Back-adjustment has folded every future split/dividend into today's level, so
`feature_t` quietly carries post-t information. The series looks clean, RankIC a healthy
~0.04. Whether it clears DSR / PBO / the empirical null depends on |t|, N and family size —
but the court has **no as-of information to check**: the leak lives in the *bytes*, not the
statistics, so a look-ahead readily yields a clean-looking, **plausibly court-passing**
survivor. The only thing that catches it is T5's mechanical test (null rows after t, recompute
`feature_t`,
assert unchanged), run **here**, before the series ever reaches the court. That is the whole
reason this station exists upstream.

## What this is NOT — boundary vs court / quant-mentor / honest-validation / factor-research-flow

- **vs `court` (DSR / PBO / BHY / empirical-null).** The court runs on a *finished*
  result series to ask "is this survivor overfit?" This station runs **before any
  series exists**, on the data that will produce it. The court **cannot see** a
  look-ahead leak or a frozen universe — a leaked signal yields a clean-looking,
  court-*passing* series. This is the garbage-in gate the court structurally can't be.
- **vs `research-session-protocol` (the sibling upstream station).** RSP counts a knob —
  `adjustflag`, universe, horizon — as a **fork you owe the honest N**; this station audits
  the **same knob for contamination**. `adjustflag=1` is, to RSP, one search arm to log; to
  hygiene, a *level look-ahead* to catch (T5). RSP governs *how much you searched*; hygiene
  governs *whether the bytes you searched were clean* — both run before the court, on
  different failure modes.
- **vs `quant-mentor` (general judgment).** quant-mentor reasons about a *signal's*
  economics, capacity, and objective. This station reasons about **none of the idea**
  — it audits data *plumbing* (as-of dates, calendars, tags, membership spans). You
  run it once per dataset; it protects every idea. No mechanism talk here — that's a
  different station.
- **vs `honest-validation` (禁赢学).** 禁赢学 pre-registers a *study* and reads a
  *verdict* honestly, per-study. This station pre-flights a *dataset*, reusable across
  studies. Same ethos (declare-don't-pretend, fail-closed, null = survivor → here,
  *declared-not-modeled travels with the result*) applied one layer earlier: 禁赢学
  stops you *believing* a bad result; hygiene stops a bad result from being *computed*.
- **vs `factor-research-flow` (mechanism-first + net/capacity/orthogonality lenses).**
  FRF §2 says "construct the signal without look-ahead" as *one* research-design line,
  per idea. This station is the **data-ingress mechanics** of that line, per *dataset*,
  exhaustive and **source-specific**: the exact qlib-cn / baostock APIs and fields that
  silently leak, and the manifest that proves you didn't. FRF decides whether an idea
  deserves a backtest; hygiene guarantees the bytes that backtest reads are honest.
- **Not generic data engineering.** Nothing here is schema validation, null-counting,
  dbt tests, or pipeline orchestration — a generic data-QC tool passes every trap above
  **clean**. Each trap is a *quant* as-of / look-ahead / survivorship failure that only
  a returns-aware auditor catches.

## Honest form (D1) — what's built vs designed

This station is a **skill** (judgment → an L1 checklist + trap catalog, transferable
to any desk or data source), **not** a hook and **not** a memory. Its deliverable is
the §0 preflight + the §T* 中招/自查 catalog.

- **[LANDED]** — real code in `adapters/qlib_cn.py`, **qlib-cn path only**: PIT
  membership mask (T1/T4), execution-honest label + t+1/t+2 horizon fit + one-calendar
  source-of-truth (T3/T8), fail-closed finiteness + `min_cross_section` floor (T6),
  and the `data_version` triple + pinned-tag (T9). Two attributions kept honest: the §8
  **golden-fingerprint** is the *adapter's* determinism battery, reused here as a drift
  sentinel — not a gate this station implements; and the §4.4 `COST_DECLARATION` is a **cost**
  string, **not** the T7 *tradability* one. T7 tradability is declared-not-modeled contract
  prose (§5.4) + pairwise NaN exclusion — a runtime `tradability_declaration` field is
  **[DESIGNED]**, not built.
- **[DESIGNED, not built]** — the station's own **preflight *lint*** that runs §0 as a
  gate before any factor; the **manifest emitter**; the **label-shift leak probe** (a
  genuinely unbuilt hygiene check — *not* `evaluate_shifted`, which shifts the score for
  the null jury and never touches the label, §7.3); and **baostock snapshot/hash** tooling.
- **[discipline only]** — everything on the **baostock** side (there is no baostock
  adapter): PIT membership loop, pubDate-keyed fundamentals (T2), survivorship inclusion,
  feature look-ahead, `tradestatus`/`isST` gating, self-snapshotting. These are backed by
  baostock *fields*, not alpha-court code — don't claim a tooth here that isn't there.

## See also

`adapters/qlib_cn.py` (the reference guards), `docs/design/adapter-interface.md`
(§5.1 PIT universe, §5.3 pairwise exclusion + guard, §5.4 declared-not-modeled, §4.2
label, §6 version pinning, §8 determinism), the installed `baostock` skill (fields:
`pubDate`/`statDate`, `tradestatus`, `isST`, `status`/`outDate`,
`query_hs300_stocks(date=…)`), `factor-research-flow` (the per-idea research flow this
feeds), `honest-validation` / 禁赢学 (the downstream study-level judge),
`docs/design/killer-demo.md` (cost-basis honesty in practice).
