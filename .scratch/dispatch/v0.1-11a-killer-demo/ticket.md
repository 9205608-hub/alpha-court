# Ticket: v0.1-11a — examples/killer_demo: the reason this project exists

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus the repo documents
it names as authoritative (in your worktree; read them in full).

## Context

Everything is built: the court kernel (`court/`, 129 tests, public API 44
names) and the qlib_cn adapter (`adapters/`, referee-verified against qlib's
own semantics). You are assembling the killer demo: 100 pure-noise factors →
naive selection "discovers" fake alpha → the court's five-gate battery
rejects it, with a one-figure proof and a four-part verdict report.

Authoritative documents (read ALL before code; the first one IS your spec —
it is deliberately written as the demo's PRE-REGISTRATION: seeds, decision
lines, and aggregation are pinned there and you may not adjust them to make
results prettier):

1. `docs/design/killer-demo.md` — THE design. §4 generation stub (AR(1),
   5 families × 20, seed tree SeedSequence(20260710)), §5 the two arms +
   battery config + offset grid, §6 unanimous aggregation, §7 honesty
   protocol (expected magnitudes are WRITTEN DOWN — report what comes out),
   §8 the figure, §9 entry point + run manifest, §10 report.md four parts,
   §11 your test obligations (five pieces).
2. `docs/design/adapter-interface.md` §7 — the adapter API you consume
   (evaluate / evaluate_shifted; meta.config).
3. `docs/design/trial-ledger.md` §7 + `docs/design/court-kernel-spec.md`
   §5.7/§5.8 and §4 G-rulings — Ledger and judge APIs (see court/judge.py:
   `judge(ledger, scope, [Application(statistic, params)])`; ALL statistic
   params are required, no defaults: dsr needs confidence + selected_trial_id;
   pbo_cscv needs n_splits + phi_threshold + metric + selected_trial_id;
   fdr_by needs q; noise_control needs mode/alpha/null_stats/judged_trial_id
   + provenance params).
4. `docs/design/noise-control.md` §5–§7 — grid layout, verdict recording
   (offsets verbatim), seed discipline.

Environment facts: data pack at `~/.qlib/qlib_data/cn_data` (tag 2026-07-05,
granted read exception); measured grid cost ≈26.8s per candidate for IC
(100 candidates ≈ 45 min) — run the E2E DETACHED (`nohup ... > run.log 2>&1 &`)
and poll the log; never block one command that long.

## Hard constraints (project iron laws — violations = rejected delivery)

1. 禁赢学 (honesty): the design doc §7 is a pre-registration. Run with master
   seed 20260710, report whatever comes out (survivors included — §7.3 has
   the pre-written interpretation), never re-roll seeds for a prettier
   headline. The report and figure caption must carry the §8/§9.2 mandatory
   declarations (gross series, seed, data tag, engine version).
2. No backtesting engine, no real factor formulas — the generation stub is
   pure RNG AR(1) per §4.1 (that zero information is CONSTRUCTIVE is the
   whole point).
3. `court/` and `adapters/` are read-only to you.
4. Files you may create/modify: `examples/killer_demo/` (a package: include
   `__init__.py`, `__main__.py`, modules as you see fit),
   `tests/test_killer_demo.py`, and pyproject.toml ONLY to add a `demo`
   optional-dependency group (matplotlib). NOTHING else. Delete
   `examples/.gitkeep` when the package lands.
5. English code/docstrings; cite design sections in docstrings.

## Task

Implement `python -m examples.killer_demo` per killer-demo.md §9.1 exactly
(flags: --seed default 20260710, --sweep, --skip-download, --data-dir, --out):

1. Generation stub (§4): 100 AR(1) score panels, 5 families × 20 variants
   with the §4.2 φ menu; seed tree §4.4; specs carry full recipe disclosure.
2. Evaluation + ledger (§4.3, §5.3): one hypothesis + one trial each;
   register (declared protocol: metric "ic", two-sided, window, 252, iid) →
   adapter evaluate → record. Window: choose calendar dates so T = exactly
   480 evaluation dates (§5.2 pins 480 = 16×30; the full 2024-07→2026-07
   window gives 483 — trim the start).
3. Naive arm (§5.1): max |t_iid| over the full window, same t function as
   the court (court.tstats.t_stat).
4. Court arm (§5.2–§5.4): the five-gate battery in the pinned order with the
   pinned params — fdr_by(q=.05, family=all 100) → dsr(conf=.95, accused) →
   pbo_cscv(S=16, φ≤0.2, metric sharpe, accused) → noise pool_max(α=.05,
   accused) → noise individual(α=.05) × 100. Offsets: 199 unique draws from
   [60, 420] under the offset seed branch, fed to evaluate_shifted; grid
   columns are individual juries, row-max is the pool null. 104 verdicts
   total in the ledger.
5. Aggregation (§6): unanimous — a trial survives iff every verdict that
   judged it says pass. Headline = survivors/100.
6. Figure (§8): single panel, 199 best-of-null |t| histogram + accused line +
   1.96 dashed line; caption with all mandatory declarations. Save png+svg.
7. Report (§10): four parts (headline + battery table; 100-row morgue table
   keyed by trial_id; one specimen autopsy; calibration appendix). Ledger is
   the archive; report is the tour.
8. Manifest (§9.2): out/run_config.json with every listed field.
9. Sweep (§7.4): implement --sweep (seeds 20260711–30); its aggregation
   logic must be unit-tested, but do NOT run the full 20-seed sweep in this
   ticket (≈15 h) — that decision belongs to the acceptance ticket.
10. Tests (§11 five obligations): seed determinism (two runs → identical
    ledger series values and figure numbers — use a REDUCED config for test
    runtime, e.g. 10 candidates × 20 offsets × synthetic labels via
    adapter.from_panels, asserting the mechanism not the headline); §5.3
    consistency assertion; window arithmetic (exactly 480, divisible by 16);
    aggregation unit tests on hand-built verdict sets (both polarities);
    report smoke (four sections render, caption complete). TDD: failing
    tests first; say so in the receipt.

## Acceptance criteria

1. `python3.11 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,qlib,demo]"` → 0
2. `.venv/bin/python -m pytest -q` → 0 (full suite + yours)
3. `.venv/bin/ruff check .` → 0
4. **The real thing**: `.venv/bin/python -m examples.killer_demo --skip-download`
   (detached + polled) completes; `out/` contains ledger.jsonl (104 verdicts),
   figure.png+svg, report.md (four parts), run_config.json. Paste the headline
   (survivors/100, accused |t|, its five gate outcomes) into your receipt
   notes VERBATIM — whatever it says.
5. `git status --porcelain` after final commit → empty (add out/ to
   .gitignore? NO — do not touch .gitignore; put outputs under
   examples/killer_demo/out/ and commit them: they are the demo's evidence).
6. Grid wall-clock in receipt notes.

## Out of scope

The 20-seed sweep RUN (implement the flag, don't run it); README; recording;
any tuning of pinned parameters.

## Operational notes

- Write files incrementally (a previous ticket died on max_tokens emitting
  one giant file).
- The E2E run is ≈45–60 min: nohup + poll, report real wall-clock.

## Delivery protocol

Fresh worktree; granted exceptions: data pack read, .venv. Run acceptance
yourself, real exit codes, honest partial beats dishonest done. Commit:
`git add -A && git commit -m "v0.1-11a: killer demo"`. Final output = ONLY
the JSON receipt (ticket_id `v0.1-11a`).
