# Ticket: v0.1-10a — adapters/qlib_cn: factor evaluator implementation

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus the repo documents
it names as authoritative (they are in your worktree; read them in full).

## Context

alpha-court's court kernel (`court/`, complete, 129 tests) consumes
performance series through an append-only trial ledger. The adapter you are
building is the ONLY gate between the court and the Chinese A-share market:
it turns factor score panels into daily RankIC or long-short return series
using qlib's own evaluation semantics. The killer demo (next ticket) will
push a 100-candidate × 199-offset noise grid through it.

Authoritative documents (read ALL before writing code):

1. `docs/design/adapter-interface.md` — THE contract. §3 series contract,
   §4 evaluation paths + qlib citations, §5 market handling, §6 data pinning,
   §7 API surface (§7.5 = your testing obligations, verbatim), §8 determinism.
2. `docs/research/qlib-cn-data.md` — measured facts about the data pack on
   THIS machine (§2.3 kernels=1 + file-entrypoint pitfall; §3.3 SH600519
   spot values; §5 reproduce instructions).
3. `docs/design/noise-control.md` §3.1 — the circular-shift definition your
   `evaluate_shifted` implements.

Environment facts:

- The data pack ALREADY EXISTS at `~/.qlib/qlib_data/cn_data` (813 MB,
  community tag 2026-07-05, calendar through 2026-07-03). Do not re-download.
  Reading it is a granted exception to worktree isolation.
- pyqlib 0.9.7 installs cleanly on python3.11 (`python3.11 -m venv .venv`).
  qlib is an optional dependency group `[qlib]` in pyproject — the COURT
  kernel must stay importable without qlib (tests/test_smoke.py enforces it;
  keep it green).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality (no positions, no PnL engine, no
   cost model — §4.4/§4.5 of the contract). Reuse qlib evaluation semantics.
2. `court/` must remain untouched and qlib-free. qlib imports live ONLY in
   `adapters/`.
3. Fail closed everywhere: raise on violated preconditions; never repair,
   coerce, or silently drop (contract §7 preamble).
4. Code, docstrings, comments: English. Cite the contract section in each
   public function's docstring.
5. Files you may create/modify: `adapters/qlib_cn.py` (or an
   `adapters/qlib_cn/` package if you prefer), `adapters/__init__.py`
   (exports only), `tests/test_adapter_qlib_cn.py`, and pyproject.toml ONLY
   if the `[qlib]` optional group needs an addition. NOTHING else.

## Task

Implement, per `adapter-interface.md` §7 exactly:

1. `QlibCNFactorEvaluator(config)` — §7.1: config fields/defaults as in the
   table; `qlib.init(provider_uri=..., region=REG_CN, kernels=1)` (kernels=1
   MANDATORY); label panel + PIT membership loaded once at construction.
2. `evaluate(scores, metric) -> EvalResult` — §7.2: DataFrame in, series out;
   missing evaluation-date rows raise; NaN cells legal (pairwise exclusion
   §5.3 with min_cross_section fail-closed guard); metric "ic" = per-date
   Spearman RankIC vs the label; metric "returns" = equal-weight top/bottom
   quantile long-short `(r_long − r_short)/2`.
3. `evaluate_shifted(scores, metric, offsets) -> EvalGrid` — §7.3: circular
   row-shift on the evaluation-date index; label panel never shifted; adapter
   validates 0 < δ < T and draws nothing.
4. **One shared kernel** for both entry points — the §7.3 equivalence
   invariant must hold bit-for-bit by construction. The §7.3 performance note
   (precompute per-date ranks once; offsets as vectorized row-wise
   correlations) is the intended implementation shape: the full 100×199 grid
   must run in seconds-to-minutes, not half an hour.
5. `EvalResult`/`EvalGrid` with the §7.4 meta schema (all fields listed
   there, including `data_version` triple per §6 and `cost_declaration`
   string per §4.4).
6. Tests — the §7.5 four obligations, verbatim:
   a. Oracle: tie-free synthetic panels, "ic" vs `calc_ic().ric` and
      "returns" vs `calc_long_short_return().long_short_r`, rtol ≤ 1e-12.
   b. Equivalence invariant with `np.array_equal` (no tolerance), incl. δ=0.
   c. Determinism (§8): same-process double run → `array_equal`.
   d. Convention spot-check on the real pack (SH600519 values per
      qlib-cn-data.md §3.3) — mark with a pytest skip-if-data-missing guard.
   TDD: write failing tests from the contract first; state so in the receipt.

## Acceptance criteria

Run from the repo root, record real exit codes:

1. `python3.11 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,qlib]"` → 0
2. `.venv/bin/python -m pytest -q` → 0 (full suite: kernel 129 + yours)
3. `.venv/bin/ruff check .` → 0
4. `.venv/bin/python -c "import court"` in a subprocess WITHOUT qlib installed
   is already covered by test_smoke — just confirm test_smoke passes unchanged.
5. A short grid benchmark (in your receipt notes, not a test): time of one
   candidate × 199 offsets on the real pack.
6. `git status --porcelain` after final commit → empty.

## Out of scope

Factor generation, ledger writes, statistics, the demo orchestration, any
cost/turnover modeling, non-daily frequencies, universes beyond csi300.

## Operational note

A previous large-file ticket died emitting one giant response
(`max_tokens_truncation`). Write files INCREMENTALLY — several smaller
edits, never one huge write. Keep each response well under the output
ceiling.

## Delivery protocol

1. Fresh git worktree; the granted exceptions are `~/.qlib/qlib_data/cn_data`
   (read) and `.venv` (gitignored).
2. Run acceptance yourself; record real exit codes; honest `partial` beats
   dishonest `done`.
3. Commit: `git add -A && git commit -m "v0.1-10a: qlib_cn adapter"`.
4. Final output = ONLY the JSON receipt (`ticket_id` `v0.1-10a`; branch,
   commit, worktree_path from git).
