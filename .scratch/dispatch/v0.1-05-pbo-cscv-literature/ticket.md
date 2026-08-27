# Ticket: v0.1-05 — PBO/CSCV literature note (implementation-grade)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court is a "statistical court" for quantitative factor research. One of
its four kernel statistics is the **Probability of Backtest Overfitting
(PBO)** estimated via **CSCV (Combinatorially Symmetric Cross-Validation)**.
Before any code is written, we need an implementation-grade literature note
that rewrites the full algorithm cleanly from the PUBLIC literature, precise
enough that a later reviewer can put the paper and the code side by side.

This is a research/documentation ticket. You have web search/fetch — use it
to consult the actual papers (the SSRN preprint is freely accessible).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Every formula/algorithm step must carry a citation: paper, equation or
   section number, using the paper's own notation first.
2. Write everything fresh from public literature; no long verbatim passages;
   no material from any proprietary source.
3. NO code — markdown document only (pseudocode IS allowed and required).
4. Language: English.
5. Create/modify ONLY `docs/research/pbo-cscv.md`. Do not touch any other file.

## Task

Write `docs/research/pbo-cscv.md` covering, in this order:

1. **Sources** — full bibliographic entries for at least:
   - Bailey, D. H., Borwein, J., López de Prado, M. & Zhu, Q. J. (2017),
     "The Probability of Backtest Overfitting", Journal of Computational
     Finance 20(4). (SSRN preprint 2013, id 2326253.)
   Plus any auxiliary source you actually rely on.
2. **The input matrix M** — precise requirements: T×N matrix of performance
   series (T time observations, N trials/strategies), alignment and
   equal-length requirements, what the performance metric is (Sharpe ratio by
   default; note the paper's stance on metric pluggability).
3. **The CSCV algorithm, step by step, with pseudocode**:
   a. Partition rows into S equal-size disjoint submatrices (paper's
      recommendation on S, and that S must be even for the symmetric split).
   b. Form all C(S, S/2) combinations of S/2 submatrices as in-sample (IS),
      complement as out-of-sample (OOS).
   c. For each combination: rank trials by IS metric, pick IS-best n*; compute
      its OOS metric rank; relative rank ω̄_c; logit λ_c = ln(ω̄_c/(1−ω̄_c)).
   d. PBO = fraction of combinations with λ_c < 0 (equivalently the mass of
      the λ distribution below zero). State the exact tie-handling and
      rank-normalization conventions the paper uses.
4. **Complexity note** — combination counts for practical S (e.g. C(16,8) =
   12870), memory/time considerations, why S trades off resolution vs cost.
5. **Test vector** — a fully hand-worked small example: S=4 (C(4,2)=6
   combinations), N=3 trials, T=8 rows of small integer "returns" you choose.
   Show the matrix, every split, every IS/OOS ranking, every λ_c, and the
   final PBO, so a reviewer can recompute every line. This becomes a pytest
   case later.
6. **Implementation pitfalls** — at minimum: series of unequal length;
   sensitivity to S; NaN handling; degenerate cases (N=1, ties everywhere);
   the difference between PBO and out-of-sample performance degradation
   (the paper's other diagnostics), and which of those we are NOT implementing
   in v0.1.

## Acceptance criteria

1. `test -f docs/research/pbo-cscv.md` → exit 0
2. Document contains all six sections; every algorithm step cites the paper.
3. The S=4 test vector is complete: all 6 splits enumerated with worked
   rankings and λ values.
4. `git status --porcelain` after your final commit → empty
5. `git log --oneline -1` message: `v0.1-05: PBO/CSCV literature note`

## Out of scope

Any code, any other statistic (DSR, BHY, noise controls), any repo config.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit: `git add docs/research/pbo-cscv.md && git commit -m "v0.1-05: PBO/CSCV literature note"`.
4. Your final output must be ONLY the JSON receipt (schema enforced by the
   dispatch harness). Gather first: `branch` = `git branch --show-current`,
   `commit` = `git rev-parse HEAD`, `worktree_path` = `pwd`,
   `ticket_id` = `v0.1-05`.
