# Ticket: v0.1-08c — court/pbo.py: PBO via CSCV

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus two repo documents
it names as authoritative (they are in your worktree; read them in full).

## Context

alpha-court is a "statistical court" for quantitative factor research. One of
its four kernel statistics is the **Probability of Backtest Overfitting
(PBO)** estimated by Combinatorially Symmetric Cross-Validation (CSCV): split
the T×N performance matrix into S row-blocks, form all C(S, S/2) symmetric
train/test halves, and measure how often the in-sample best trial ranks in
the bottom half out-of-sample. You are implementing it as one pure function,
test-first from the note's hand-worked S=4 fixture.

Authoritative documents (read BOTH in full before writing any code):

1. `docs/design/court-kernel-spec.md` — the implementation spec. Your
   contract is §3 (conventions, fail-closed), §4 rulings D1–D6, §5.3
   (`court/pbo.py` signature, step table, guards), §7 (test_pbo.py rows).
2. `docs/research/pbo-cscv.md` — the implementation-grade literature note:
   Bailey, Borwein, López de Prado & Zhu (2017) Algorithm 2.3 step by step
   (§3), the S=4/N=3/T=8 hand-worked fixture (§5), pitfalls (§6). It also
   documents two published errata you must NOT reproduce: the paper's
   Alg. 2.3(c) train/test label slip and the printed "12,780" for C(16,8).

Non-negotiable algorithm points (the documents remain authoritative):

- Signature (spec §5.3): `pbo_cscv(values, n_splits, metric) -> PboResult`
  with `PboResult(phi, logits, n_combinations, n_lambda_negative)`.
  `metric` is a REQUIRED callable (1-D array → float), no default — the
  procedure is metric-agnostic (note §2.3); the judge wires Sharpe later.
- Blocks are contiguous, time order preserved; halves are concatenated in
  original time order. Combination enumeration order is pinned to
  `itertools.combinations(range(S), S//2)` so the fixture's logit sequence is
  positional (spec ruling D6).
- Ranks: higher = better, best = N; ties → midranks
  (`scipy.stats.rankdata(..., method="average")`); IS-best n* = argmax with
  smallest-index tie-break (spec ruling D2).
- ω̄c = r̄_{n*}/(N+1); λc = ln(ω̄c/(1−ω̄c)); φ = #{λc < 0}/C(S,S/2) with
  STRICT λ < 0 — λ == 0 does not count. Operational identity:
  λc < 0 ⟺ r̄_{n*} < (N+1)/2. The paper's literal Eq. (2.2) threshold N/2 is
  NOT the implemented rule (note §3.5; spec ruling D4).
- Fail-closed (raise ValueError): `values` not 2-D or containing non-finite
  entries; N < 2 (single trial is vacuous); `n_splits` odd or < 2;
  T % n_splits != 0; non-finite metric output on ANY half → raise the whole
  run, never drop a column per-combination (note §6.3; spec ruling D3).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality; do NOT build factor generation.
2. `court/` imports only: Python stdlib, numpy, pandas, scipy. Keep
   `tests/test_smoke.py` green.
3. Pure function only: no ledger import, no I/O, no imports from other
   `court/` modules (in particular NOT `court.sharpe` — the metric arrives as
   a parameter).
4. Files you may create/modify: `court/pbo.py`, `tests/test_pbo.py` —
   NOTHING else. Do not touch `court/__init__.py` (reserved for v0.1-08f).
5. Code, docstrings, comments: English. Docstrings cite the paper (Alg. 2.3
   steps, §3.1) and pbo-cscv.md sections (project iron law).
6. TDD is contractual: write the failing tests FIRST from pbo-cscv.md §5,
   confirm they fail, then implement to green. State in your receipt notes
   that tests were written first.

## Task

1. Write `tests/test_pbo.py`:
   - The §5 fixture: the exact 8×3 matrix printed in pbo-cscv.md §5.1, S=4,
     `metric = lambda col: float(np.mean(col))` (the note's §5 metric is the
     arithmetic mean — allowed by metric pluggability). Assert positionally:
     `logits == (0, ln(1/3), 0, 0, ln(1/3), ln(1/3))` in the pinned
     combination order (ln(1/3) ≈ −1.0986122886681098, tolerance 1e-12),
     `phi == 0.5` exactly, `n_combinations == 6`, `n_lambda_negative == 3`.
   - λ == 0 combinations do not count toward φ (visible in the fixture:
     three zero logits, φ = 3/6 not 6/6).
   - Guard tests: every raise condition listed in Context, including a
     metric that returns NaN on some half (e.g. a zero-variance column with a
     Sharpe-like metric) → whole run raises.
2. Implement `court/pbo.py` per spec §5.3: `PboResult` and `pbo_cscv` with
   the exact signature. Prefer index masks/views over materializing every
   J/J̄ (note §4.2), but correctness beats cleverness at v0.1 scale.
3. Full suite green; ruff clean.

## Acceptance criteria

Run from the repo root; record real exit codes:

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_pbo.py -v` → exit 0, ≥ 7 tests passed
3. `.venv/bin/python -m pytest` → exit 0
4. `.venv/bin/ruff check .` → exit 0
5. `.venv/bin/python -c "
import numpy as np
from court.pbo import pbo_cscv
M = np.array([[3,0,4],[3,2,1],[3,4,6],[3,1,5],[4,4,0],[2,5,5],[3,5,5],[2,6,2]], dtype=float)
r = pbo_cscv(M, 4, lambda c: float(np.mean(c)))
assert r.phi == 0.5 and r.n_combinations == 6, r
"` → exit 0
6. `git show --stat HEAD` lists only `court/pbo.py` and `tests/test_pbo.py`
7. `git status --porcelain` after your final commit → empty

## Out of scope

- The paper's other three diagnostics (performance degradation, probability
  of loss, stochastic dominance) — pbo-cscv.md §6.6: v0.1 implements φ only.
- The φ decision threshold (judge parameter, ticket v0.1-08f) and S selection
  policy (demo design, ticket 11).
- The trial ledger, judge, `court/__init__.py` exports, other statistics.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.1-08c: pbo via cscv"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-08c`
