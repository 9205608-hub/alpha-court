# Ticket: v0.1-08d — court/tstats.py + court/fdr.py: t/p computation and FDR step-up procedures

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file plus two repo documents
it names as authoritative (they are in your worktree; read them in full).

## Context

alpha-court is a "statistical court" for quantitative factor research. One of
its four kernel statistics is **false-discovery-rate control** over a family
of many factor trials: the Benjamini-Hochberg (BH) step-up procedure and the
Benjamini-Yekutieli (BY) harmonic-corrected variant valid under arbitrary
dependence. Upstream of them sits the t-statistic / p-value computation
(iid or Newey-West standard errors, declared sidedness). You are implementing
both modules as pure functions, test-first from the note's N=10 hand-worked
table.

Authoritative documents (read BOTH in full before writing any code):

1. `docs/design/court-kernel-spec.md` — the implementation spec. Your
   contract is §3 (conventions, fail-closed), §4 rulings E1–E8, §5.4
   (`court/tstats.py`) and §5.5 (`court/fdr.py`) with formula tables, guards,
   and this ticket's hand-worked t vectors, §7 (test_tstats.py / test_fdr.py
   rows).
2. `docs/research/bhy.md` — the implementation-grade literature note:
   BH/BY procedures with theorem citations (§2–§3), p-value provenance
   (§4: t statistics, sidedness, Newey-West), the N=10 hand-worked fixture
   (§6), pitfalls (§7).

Non-negotiable points (the documents remain authoritative):

- NAMING: the functions are `fdr_bh` and `fdr_by`. The string "BHY" must not
  appear in code — Harvey-Liu-Zhu's "BHY" IS the BY procedure and the name
  collision is a documented trap (bhy.md §7.5).
- STEP-UP, not step-down: k* = max{i : p₍ᵢ₎ ≤ τᵢ}; reject the WHOLE initial
  segment 1..k*, including ranks that fail their own line (bhy.md §7.1; the
  fixture's rank 5 is the canary). Boundary p₍ᵢ₎ == τᵢ counts (`≤`).
- BH: τᵢ = (i/N)·q. BY: τᵢ = i·q/(N·c(N)) with
  `harmonic_number(n)` = ascending float64 sum Σ 1/i;
  `harmonic_number(10) == 2.9289682539682538` EXACTLY (bhy.md §6.1 pins the
  summation convention).
- Adjusted p-values: backward min recurrence on the sorted list, clipped to
  [0,1], mapped back to input order via the STABLE sort permutation
  (`np.argsort(..., kind="stable")`); monotone non-decreasing in sorted order
  (bhy.md §2.4/§3.2/§7.2).
- `q` is a REQUIRED argument (no default) — the court never silently defaults
  a significance level. Empty p-vector → k*=0, empty tuples, returns (bhy.md
  §7.4). p outside [0,1] or non-finite → raise.
- t/p: p-values via STANDARD NORMAL asymptotics (HLZ convention, bhy.md §4.2
  and §3.5 fn 26): two-sided 2(1−Φ(|t|)); greater 1−Φ(t); less Φ(t).
- SE conventions (spec rulings E2/E3): `se_kind="iid"` → σ̂(Bessel)/√T;
  `se_kind="newey_west"` → Bartlett LRV = γ̂₀ + 2Σ(1−ℓ/(L+1))γ̂ℓ with
  γ̂ℓ = (1/T)Σ(x_t−x̄)(x_{t+ℓ}−x̄), se = √(LRV/T); `lags` is REQUIRED for
  newey_west (no automatic lag rule) and FORBIDDEN for iid.
- Fail-closed (raise ValueError): n_obs < 2; non-finite values; se == 0;
  unknown se_kind or direction; lags None/negative/non-int/≥T for
  newey_west; lags supplied with iid; non-finite t in p_from_t;
  q outside (0,1).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality; do NOT build factor generation.
2. `court/` imports only: Python stdlib, numpy, pandas, scipy. Keep
   `tests/test_smoke.py` green.
3. Pure functions only: no ledger import, no I/O, no imports from other
   `court/` modules.
4. Files you may create/modify: `court/tstats.py`, `court/fdr.py`,
   `tests/test_tstats.py`, `tests/test_fdr.py` — NOTHING else. Do not touch
   `court/__init__.py` (reserved for v0.1-08f).
5. Code, docstrings, comments: English. Docstrings cite BH 1995 expr. (1),
   BY 2001 Thm 1.3, Newey & West 1987, HLZ 2016 §3.4.3 and the bhy.md
   sections (project iron law).
6. TDD is contractual: write the failing tests FIRST from bhy.md §6 and the
   spec §5.4 vectors, confirm they fail, then implement to green. State in
   your receipt notes that tests were written first.

## Task

1. Write `tests/test_tstats.py` (anchors from spec §5.4; tolerance
   `pytest.approx(abs=1e-9)`):
   - `t_stat([1.0, 2.0, 3.0])` → t == 2√3 ≈ 3.4641016151377544,
     se ≈ 0.5773502691896258.
   - `t_stat([1.0, 2.0, 3.0], se_kind="newey_west", lags=1)` →
     t == 3√2 ≈ 4.242640687119285, se ≈ 0.4714045207910317
     (γ̂₀ = 2/3, γ̂₁ = 0, LRV = 2/3 — re-derive in the test docstring).
   - `p_from_t(1.959963984540054, "two-sided") ≈ 0.05`;
     `p_from_t(1.6448536269514722, "greater") ≈ 0.05`;
     `p_from_t(-1.6448536269514722, "less") ≈ 0.05`.
   - Guard tests: every raise condition listed in Context.
2. Write `tests/test_fdr.py` from the bhy.md §6 fixture (raw p-values by
   label in §6.3, input order H1..H10 = [0.0400, 0.0008, 0.0280, 0.0900,
   0.0050, 0.0260, 0.0100, 0.0450, 0.0030, 0.0280], q = 0.05):
   - `harmonic_number(10) == 2.9289682539682538` (exact `==`).
   - `fdr_bh`: k* == 9; reject everything except H4 (input position 3);
     rank-5 trial H6 (p=0.026 fails its own τ=0.025) IS rejected (step-up);
     boundary equalities H1 (p=0.0400) and H8 (p=0.0450) ARE rejected (`≤`).
   - `fdr_by`: k* == 3; rejection set == {H2, H9, H5} (input positions
     1, 8, 4); c_factor == harmonic_number(10).
   - Adjusted-p properties: monotone in sorted order; all ≤ 1;
     `adjusted_p[i] ≤ q ⟺ reject[i]` for both procedures on the fixture.
   - Empty input → k* == 0, empty tuples. Guards: p > 1, p < 0, NaN, bad q
     each raise.
3. Implement `court/tstats.py` per spec §5.4 (`TStatResult`, `t_stat`,
   `p_from_t`) and `court/fdr.py` per spec §5.5 (`FdrResult`,
   `harmonic_number`, `fdr_bh`, `fdr_by`) — exact signatures from the spec.
4. Full suite green; ruff clean.

## Acceptance criteria

Run from the repo root; record real exit codes:

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
2. `.venv/bin/python -m pytest tests/test_tstats.py tests/test_fdr.py -v` → exit 0, ≥ 14 tests passed
3. `.venv/bin/python -m pytest` → exit 0
4. `.venv/bin/ruff check .` → exit 0
5. `.venv/bin/python -c "
from court.fdr import fdr_by, harmonic_number
assert harmonic_number(10) == 2.9289682539682538
p = [0.0400, 0.0008, 0.0280, 0.0900, 0.0050, 0.0260, 0.0100, 0.0450, 0.0030, 0.0280]
r = fdr_by(p, 0.05)
assert r.k_star == 3 and [i for i, x in enumerate(r.reject) if x] == [1, 4, 8], r
"` → exit 0
6. `git show --stat HEAD` lists only the four files in constraint 4
7. `git status --porcelain` after your final commit → empty

## Out of scope

- Choosing q, assembling the FDR family from the ledger, per-trial declared
  protocols (judge, ticket v0.1-08f; family policy is ledger contract §4.2).
- The v0.2 per-hypothesis representative policy (bhy.md / ledger contract).
- Automatic Newey-West lag selection (spec ruling E2 forbids it in v0.1).
- The trial ledger, judge, `court/__init__.py` exports, other statistics.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.1-08d: tstats + fdr"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-08d`
