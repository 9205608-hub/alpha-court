# Ticket: v0.1-08b — court/sharpe.py + court/dsr.py: PSR and Deflated Sharpe Ratio

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus two repo documents
it names as authoritative (they are in your worktree; read them in full).

## Context

alpha-court is a "statistical court" for quantitative factor research. One of
its four kernel statistics is the **Deflated Sharpe Ratio (DSR)**: PSR
evaluated at the expected-maximum-SR benchmark implied by the number of
trials. You are implementing the full chain — SR estimator and moments, SR
standard error, PSR, expected max SR, implied independent trial count, DSR —
as pure functions over arrays and scalars (they must hold no reference to any
ledger), test-first from hand-worked literature vectors.

Authoritative documents (read BOTH in full before writing any code):

1. `docs/design/court-kernel-spec.md` — the implementation spec. Your
   contract is §3 (conventions, fail-closed), §4 rulings C1–C10, §5.1
   (`court/sharpe.py`) and §5.2 (`court/dsr.py`) with their formula
   correspondence tables and guards, §7 (test_sharpe.py / test_dsr.py rows).
2. `docs/research/dsr.md` — the implementation-grade literature note:
   formulas with paper equation numbers (§2), code-mapping tables (§3),
   hand-worked test vectors §4.1–§4.5, pitfalls (§5). Your docstrings cite
   Bailey & López de Prado (2012) and (2014) equation numbers exactly as this
   note does.

Non-negotiable formula points (the documents remain authoritative):

- Everything at NATIVE frequency; annualization (`annualized_sr`, √q·SR̂) is
  display-only and enters no other formula (dsr.md §5.1).
- Variance factor: collapsed form 1 − γ̂₃·SR̂ + (γ̂₄−1)/4·SR̂² with RAW
  kurtosis (Normal → 3.0). The Normal special case must recover 1 + SR̂²/2.
- σ̂ uses Bessel (n−1); PSR numerator uses √(n−1) [2012 Eq. (11)].
- Moment conventions (spec ruling C1): `scipy.stats.skew(x, bias=True)`,
  `scipy.stats.kurtosis(x, fisher=False, bias=True)`.
- `expected_max_sr` implements 2014 Eq. (1) — an EVT approximation whose
  docstring MUST state it is conditioned on N ≫ 1 (dsr.md §2.c). N is
  real-valued (N̂ = 1 + (M−1)(1−ρ̂) from 2014 Eq. (9) is a float). N == 1
  returns `sr_trials_mean` exactly; N < 1 raises.
- ρ̂ = mean of upper-triangle pairwise Pearson correlations of the T×M series
  matrix; accepted on (−1, 1]; negative ρ̂ is a documented conservative
  extrapolation (N̂ > M, harsher hurdle). `rho_is_ill_conditioned(T, M)` is
  True iff T < ½M(M−1) — a disclosed caveat, NOT an error.
- Fail-closed (raise ValueError, never clamp): n_obs < 2; non-finite inputs;
  σ̂ = 0; var_factor ≤ 0; n_trials < 1; sr_trials_std < 0; ρ̂ outside (−1, 1];
  constant column in the correlation matrix.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality; do NOT build factor generation.
2. `court/` imports only: Python stdlib, numpy, pandas, scipy. Keep
   `tests/test_smoke.py` green.
3. Pure functions only: no ledger import, no I/O, no global state.
   `court/dsr.py` may import from `court.sharpe` (same ticket); no other
   court-internal imports.
4. Files you may create/modify: `court/sharpe.py`, `court/dsr.py`,
   `tests/test_sharpe.py`, `tests/test_dsr.py` — NOTHING else. Do not touch
   `court/__init__.py` (reserved for ticket v0.1-08f).
5. Code, docstrings, comments: English. Every public function's docstring
   cites paper + equation number and the dsr.md section (project iron law).
6. TDD is contractual: write the failing tests FIRST from dsr.md §4.1–§4.5
   (exact inputs and anchors are printed there and in spec §7), confirm they
   fail, then implement to green. State in your receipt notes that tests were
   written first.

## Task

1. Write `tests/test_sharpe.py` and `tests/test_dsr.py` from the spec §7
   rows. Vector-to-test mapping (inputs/intermediates verbatim from dsr.md;
   tolerance `pytest.approx(abs=1e-9)` unless stated):
   - dsr.md §4.1 → PSR Normal: var_factor == 1.125, z ≈ 2.26077666104,
     psr ≈ 0.98811345473.
   - dsr.md §4.2 → PSR non-Normal: var_factor == 1.4375, z ≈ 2.0,
     psr ≈ 0.97724986805.
   - dsr.md §4.3 → expected_max_sr(0.0, 0.5, 10): ≈ 0.78729915067.
   - dsr.md §4.4 → dsr(sr=1.0, n=24, skew=−0.2, kurt=3.5, std=0.5, N=10):
     sr_star ≈ 0.78729915067, z ≈ 0.75509519676, dsr ≈ 0.77490406751.
   - dsr.md §4.5 → paper cross-check (native-frequency inputs printed there):
     N=100 → dsr ≈ 0.90039683445; N=46 → ≈ 0.95050170688; Normal moments
     (γ₃=0, γ₄=3) N=88 → ≈ 0.9505 within 5e-4.
   - Normal-case identity: sr_var_factor(sr, 0.0, 3.0) == 1 + sr²/2 for
     sr ∈ {0.0, 0.5, 1.0}.
   - implied_independent_trials limits: ρ̂=0 → N̂=M; ρ̂=1 → N̂=1.
   - Guard tests: every raise condition listed in Context.
2. Implement `court/sharpe.py` per spec §5.1: `SeriesMoments`,
   `series_moments`, `sharpe_ratio`, `sr_var_factor`, `sr_standard_error`,
   `psr`, `annualized_sr` — exact signatures from the spec.
3. Implement `court/dsr.py` per spec §5.2: `EULER_MASCHERONI`
   (0.5772156649015329), `DsrResult`, `implied_independent_trials`,
   `avg_pairwise_correlation`, `rho_is_ill_conditioned`, `expected_max_sr`,
   `dsr` — exact signatures from the spec.
4. Full suite green; ruff clean.

## Acceptance criteria

Run from the repo root; record real exit codes:

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_sharpe.py tests/test_dsr.py -v` → exit 0, ≥ 14 tests passed
3. `.venv/bin/python -m pytest` → exit 0
4. `.venv/bin/ruff check .` → exit 0
5. `.venv/bin/python -c "from court.dsr import expected_max_sr; v = expected_max_sr(0.0, 0.5, 10.0); assert abs(v - 0.78729915067) < 1e-9, v"` → exit 0
6. `git show --stat HEAD` lists only the four files in constraint 4
7. `git status --porcelain` after your final commit → empty

## Out of scope

- The trial ledger, judge orchestration, `court/__init__.py` exports.
- PBO, FDR, t-statistics, noise control (other tickets).
- HAC standard errors for SR (documented v0.1 assumption, dsr.md §5.2).
- Monte Carlo validation of the EVT approximation (dsr.md §5.5).

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.1-08b: sharpe + dsr"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-08b`
