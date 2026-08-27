# Ticket: v0.1-08f — court/judge.py: thin orchestrator + public API

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus the repo documents
it names as authoritative (they are in your worktree; read them in full).

PRECONDITION: tickets v0.1-08a…08e are merged. `court/ledger.py`,
`court/sharpe.py`, `court/dsr.py`, `court/pbo.py`, `court/tstats.py`,
`court/fdr.py`, `court/noise.py` and their test files exist and the full
suite is green. If any of these is missing, STOP and report `blocked` in the
receipt instead of improvising.

## Context

alpha-court is a "statistical court" for quantitative factor research. The
**judge** is the only component that knows both the ledger and the
statistics: it reads evidence through the ledger's read surface, computes
each statistic under every trial's declared protocol, appends one immutable
VerdictRecord per statistic application, and returns a summary. It does NO
aggregation across statistics — battery composition and survival policy
belong to the demo design (ticket 11).

Authoritative documents (read ALL before writing any code):

1. `docs/design/court-kernel-spec.md` — the implementation spec. Your
   contract is §3 (conventions, fail-closed), §4 rulings F2 and G1–G5, §5.8
   (Application/Judgment types, per-application contracts, the decision
   polarity table), §7 (test_judge.py rows).
2. `docs/design/trial-ledger.md` §5.3 (VerdictRecord semantics) and §7.4
   (judge layer definition).
3. `docs/design/noise-control.md` §4 and §6 (noise-control verdict recording:
   what goes in params vs computed).

Non-negotiable points (the documents remain authoritative):

- Signature: `judge(ledger, scope, config) -> Judgment` with
  `Application(statistic, params)` and
  `Judgment(verdict_ids, decisions)` exactly as spec §5.8.
- One VerdictRecord per application via `ledger.append_verdict`;
  `engine_version` stamped automatically from `court.__version__`.
- DECISION POLARITY (spec §5.8 table — implement it exactly; the FDR
  "rejection set" naming inversion is the classic bug here): statistical
  discovery ⟺ court `"pass"`. fdr_*: trial in the FDR rejection set →
  "pass", decisions cover every trial in scope. dsr: DSR ≥ confidence →
  "pass" for selected_trial_id only. pbo_cscv: φ ≤ phi_threshold → "pass"
  for selected_trial_id only. noise_control: p̂ ≤ alpha → "pass" for the
  judged (individual mode) or argmax-selected (pool_max mode) trial.
- Per-application params and computed contents: exactly the lists in spec
  §5.8 (fdr: q + per-trial parallel audit lists; dsr: selected_trial_id +
  confidence, computed includes rho_hat, n_trials_effective,
  rho_ill_conditioned via `rho_is_ill_conditioned`; pbo_cscv:
  selected_trial_id + n_splits + phi_threshold + metric name resolved via
  the registry {"sharpe": sharpe_ratio}; noise_control: mode + alpha +
  null_stats + judged_trial_id for individual mode, provenance keys recipe /
  delta_min / seed / offsets / ranking_stat copied VERBATIM into verdict
  params and never interpreted, null_stats stored under computed).
- Noise ranking statistic (spec ruling F2): from the trial's series under its
  declared protocol via `t_stat(series, se_kind=declared.se.kind,
  lags=declared.se.lags)` — two-sided → |t|; greater → t; less → −t.
- FDR p-values: per trial, `p_from_t(t, declared.direction)` with t from the
  trial's declared SE convention; the full scope enters the family (ledger
  contract §4.2: one trial = one hypothesis test in v0.1).
- DSR pipeline (spec §5.8): matrix(scope) → per-column sharpe_ratio →
  cross-trial SR std (ddof=1) and avg_pairwise_correlation → N̂ =
  implied_independent_trials(M, ρ̂) → selected trial's series_moments →
  dsr(...).
- Fail-closed (raise ValueError): empty scope; empty config; unknown
  statistic name; any trial in scope not `evaluated`; missing or malformed
  required params (spec ruling G3).
- Finalize `court/__init__.py`: set `__version__ = "0.1.0.dev0"` and
  re-export the public API — `Ledger`, `LedgerCorruptionError`, the record
  and protocol dataclasses, all public functions of sharpe/dsr/pbo/tstats/
  fdr/noise, `Application`, `Judgment`, `judge`. Keep the existing module
  docstring; keep `tests/test_smoke.py` green (importing court must still
  not import qlib or adapters).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality; do NOT build factor generation.
2. `court/` imports only: Python stdlib, numpy, pandas, scipy.
3. Do NOT modify any existing `court/*.py` module except `court/__init__.py`,
   and do NOT modify any existing test file. If a delivered module deviates
   from spec §5.1–§5.7 in a way that blocks you, report `blocked` with
   details in the receipt — the referee owns cross-ticket fixes.
4. Files you may create/modify: `court/judge.py`, `court/__init__.py`,
   `tests/test_judge.py` — NOTHING else.
5. Code, docstrings, comments: English; docstrings cite the contract
   sections implemented (project iron law).
6. TDD is contractual: write the failing tests FIRST (spec §7 test_judge.py
   rows), confirm they fail, then implement to green. State in your receipt
   notes that tests were written first.

## Task

1. Write `tests/test_judge.py` (build toy ledgers in tmp_path with 3–5
   hand-chosen short series; every expected number hand-derivable):
   - `fdr_by` application end-to-end: one VerdictRecord appended; scope
     recorded verbatim; decisions cover the whole scope with correct
     polarity (discovery ⟺ "pass"); computed carries k_star, c_factor, q,
     and per-trial parallel lists (trial_ids, p, t, direction, se_kind).
   - `noise_control` individual mode: provenance keys land verbatim in
     verdict params; null_stats land in computed; decision matches
     `empirical_null_p`; observed == |t| for a two-sided trial.
   - `noise_control` pool_max mode: observed = max over scope; argmax trial
     recorded as computed.selected_trial_id and judged.
   - `dsr` and `pbo_cscv` applications: decisions on selected_trial_id only;
     both pass/reject directions exercised across the polarity table (one
     case per statistic per direction, parameters chosen to force each
     outcome).
   - `status(trial_id)` becomes "judged" after a verdict covers it.
   - Guards: unevaluated trial in scope raises; unknown statistic raises;
     empty scope raises; empty config raises; missing required param raises.
   - Public API: `import court; court.judge, court.Ledger,
     court.empirical_null_p, court.fdr_by, court.dsr, court.pbo_cscv,
     court.__version__` all resolve.
2. Implement `court/judge.py` per spec §5.8 (`Application`, `Judgment`,
   `judge`, the metric registry, the polarity table).
3. Finalize `court/__init__.py` as described in Context.
4. Full suite green (all seven test modules + smoke); ruff clean.

## Acceptance criteria

Run from the repo root; record real exit codes:

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_judge.py -v` → exit 0, ≥ 10 tests passed
3. `.venv/bin/python -m pytest` → exit 0 (entire suite, all modules)
4. `.venv/bin/ruff check .` → exit 0
5. `.venv/bin/python -c "import court; assert court.__version__ == '0.1.0.dev0'; court.judge; court.Ledger; court.fdr_by; court.empirical_null_p"` → exit 0
6. `git show --stat HEAD` lists only `court/judge.py`, `court/__init__.py`,
   `tests/test_judge.py`
7. `git status --porcelain` after your final commit → empty

## Out of scope

- Aggregation across statistics, battery composition, survival policy,
  demo-facing defaults for q/alpha/confidence/S (ticket 11).
- Null-jury generation and the offset grid (adapter/demo side).
- Any change to the statistics modules or the ledger (constraint 3).

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.1-08f: judge + public API"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-08f`
