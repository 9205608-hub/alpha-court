# Ticket: v0.1-08e — court/noise.py: empirical null p-value (noise control)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus two repo documents
it names as authoritative (they are in your worktree; read them in full).

## Context

alpha-court is a "statistical court" for quantitative factor research. Its
fourth kernel statistic is the **noise control**: compare a candidate
factor's ranking statistic against a jury of information-free null factors
and compute an empirical (randomization) p-value. The court side is exactly
ONE pure function — jury generation, circular time-shifts, offset grids and
RNG all live on the adapter/demo side and are NOT in this ticket.

Authoritative documents (read BOTH in full before writing any code):

1. `docs/design/court-kernel-spec.md` — the implementation spec. Your
   contract is §3 (conventions, fail-closed), §4 rulings F1–F2, §5.6
   (`court/noise.py` signature and guards), §7 (test_noise.py rows).
2. `docs/design/noise-control.md` — the design contract: the add-one
   permutation p-value (§4.1), the two modes it serves (§4.2 individual jury /
   §4.3 pool-max, White 2000 Reality Check), and the four hand-worked test
   vectors (§8).

Non-negotiable points (the documents remain authoritative):

- Formula (Phipson & Smyth 2010, Eq. (2), cited in noise-control.md §4.1):

      p̂ = (1 + #{ null_j ≥ observed }) / (K + 1)

  Ties count AGAINST the candidate (`≥`, conservative); the add-one form can
  never return zero.
- Signature (spec §5.6): `empirical_null_p(observed, nulls, alpha=0.05)` →
  `NoiseResult(p_hat, decision, n_nulls, n_at_least)`; `decision` is the
  string `"pass"` iff p̂ ≤ α else `"reject"` (VerdictRecord decision
  vocabulary). Default α = 0.05 is a parameter default per the design doc —
  a verdict parameter, not a constant.
- The same arithmetic serves both modes; mode is input selection by the
  caller. This function neither generates nor shifts anything.
- Fail-closed (raise ValueError): `nulls` empty, not 1-D, or containing
  non-finite values; `observed` non-finite; `alpha` outside the open
  interval (0, 1).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality; do NOT build factor generation —
   in particular NO null-jury generation, NO circular shifting, NO RNG in
   this module (that is the adapter/demo side per noise-control.md §2).
2. `court/` imports only: Python stdlib, numpy, pandas, scipy. Keep
   `tests/test_smoke.py` green.
3. Pure function only: no ledger import, no I/O, no imports from other
   `court/` modules, deterministic.
4. Files you may create/modify: `court/noise.py`, `tests/test_noise.py` —
   NOTHING else. Do not touch `court/__init__.py` (reserved for v0.1-08f).
5. Code, docstrings, comments: English. Docstrings cite Phipson & Smyth
   (2010) Eq. (2), White (2000) for pool-mode semantics, and noise-control.md
   §4/§8 (project iron law).
6. TDD is contractual: write the failing tests FIRST from noise-control.md
   §8, confirm they fail, then implement to green. State in your receipt
   notes that tests were written first.

## Task

1. Write `tests/test_noise.py` from noise-control.md §8 (α = 0.05; exact
   rational anchors, use exact `==` where the value is a machine-exact
   fraction like 0.6, 0.5, 0.005):
   - Vector 1: observed=2.0, nulls=(1.0, 2.5, 0.5, 3.0), K=4 →
     n_at_least == 2, p̂ == 3/5 == 0.6, decision "reject".
   - Vector 2 (tie counts against): observed=2.0, nulls=(1.9, 2.0, 0.5),
     K=3 → n_at_least == 1, p̂ == 2/4 == 0.5, decision "reject".
   - Vector 3: observed=4.0, 199 nulls all < 4.0 → n_at_least == 0,
     p̂ == 1/200 == 0.005, decision "pass" at α=0.05.
   - Vector 4 (resolution floor): with K=199 the minimum attainable p̂ is
     0.005 — assert p̂ ≥ 1/200 for a sweep of observed values, and that p̂
     is never 0.0.
   - Guard tests: every raise condition listed in Context.
2. Implement `court/noise.py` per spec §5.6: `NoiseResult` and
   `empirical_null_p` — exact signature from the spec.
3. Full suite green; ruff clean.

## Acceptance criteria

Run from the repo root; record real exit codes:

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_noise.py -v` → exit 0, ≥ 6 tests passed
3. `.venv/bin/python -m pytest` → exit 0
4. `.venv/bin/ruff check .` → exit 0
5. `.venv/bin/python -c "
from court.noise import empirical_null_p
r = empirical_null_p(2.0, [1.9, 2.0, 0.5])
assert r.p_hat == 0.5 and r.decision == 'reject' and r.n_at_least == 1, r
"` → exit 0
6. `git show --stat HEAD` lists only `court/noise.py` and
   `tests/test_noise.py`
7. `git status --porcelain` after your final commit → empty

## Out of scope

- Null-jury generation: circular time-shift, offset grid, δ_min discipline,
  SeedSequence RNG (adapter/demo side — tickets 10/11).
- Computing the ranking statistic from a series (judge, ticket v0.1-08f).
- Verdict recording, mode orchestration, aggregation with other statistics.
- The trial ledger, `court/__init__.py` exports, other statistics.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.1-08e: empirical null p"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-08e`
