# Ticket: v0.1-04 — DSR literature note (implementation-grade)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court is a "statistical court" for quantitative factor research: it
consumes return/IC series and rules on whether an apparent alpha should be
believed. One of its four kernel statistics is the **Deflated Sharpe Ratio
(DSR)**. Before any code is written, we need an implementation-grade
literature note that rewrites every needed formula cleanly from the PUBLIC
literature, with citations precise enough that a later reviewer can put the
paper and the code side by side and check them line by line.

This is a research/documentation ticket. You have web search/fetch — use it
to consult the actual papers (SSRN preprints are freely accessible).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Every formula must carry a citation: paper, equation number (or page /
   section if unnumbered), using the paper's own notation first.
2. Write everything fresh from public literature. Do not reproduce long
   verbatim passages (short quoted definitions are fine); no material from
   any proprietary source.
3. NO code in this ticket — the deliverable is a markdown document only.
4. Language: English.
5. Create/modify ONLY `docs/research/dsr.md`. Do not touch any other file.

## Task

Write `docs/research/dsr.md` covering, in this order:

1. **Sources** — full bibliographic entries for at least:
   - Bailey, D. H. & López de Prado, M. (2014), "The Deflated Sharpe Ratio:
     Correcting for Selection Bias, Backtest Overfitting and Non-Normality",
     Journal of Portfolio Management 40(5). (SSRN preprint available.)
   - Bailey, D. H. & López de Prado, M. (2012), "The Sharpe Ratio Efficient
     Frontier", Journal of Risk 15(2) — source of the Probabilistic Sharpe
     Ratio (PSR).
   Plus any auxiliary source you actually rely on.
2. **Formulas, each with citation + symbol table**:
   a. Sharpe ratio estimator and the distribution of the SR estimator under
      non-normal returns (variance of the SR estimator including skewness and
      kurtosis terms).
   b. PSR: probability that the true SR exceeds a benchmark SR*, with the
      skew/kurtosis-adjusted standard error.
   c. Expected maximum Sharpe ratio across N independent trials
      (the expression involving the Euler-Mascheroni constant and inverse
      normal CDF terms), and the role of the cross-trial variance of SRs.
   d. DSR: the final criterion — PSR evaluated at the expected-max benchmark.
3. **Code-mapping plan** — for each formula, a table: paper symbol → intended
   Python variable name → where the value comes from at runtime (e.g. "N =
   number of trials, from the trial ledger"; "gamma_3 = sample skewness of the
   return series"). Do NOT write the code itself.
4. **Test vectors** — for PSR, expected-max-SR, and DSR: at least one worked
   numeric example each, computed by hand step by step, with all inputs and
   intermediate values shown to ≥6 significant digits (these become pytest
   cases later). Use small, clean inputs (e.g. T=24 observations, N=10 trials).
   Show your arithmetic so a reviewer can recompute every line.
5. **Implementation pitfalls** — at minimum: annualization vs native
   frequency (which frequency the formulas assume); autocorrelated returns;
   the difference between the number of *independent* trials and raw ledger
   count; estimating the cross-trial SR variance; numerical issues in the
   inverse normal CDF tails.

## Acceptance criteria

1. `test -f docs/research/dsr.md` → exit 0
2. The document contains all five sections above; every displayed formula has
   a bracketed citation with equation number or page/section.
3. Test-vector section shows hand-worked intermediate values, not just final
   numbers.
4. `git status --porcelain` after your final commit → empty
5. `git log --oneline -1` message: `v0.1-04: DSR literature note`

## Out of scope

Any code, any other statistic (PBO, BHY, noise controls), any repo config.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit: `git add docs/research/dsr.md && git commit -m "v0.1-04: DSR literature note"`.
4. Your final output must be ONLY the JSON receipt (schema enforced by the
   dispatch harness). Gather first: `branch` = `git branch --show-current`,
   `commit` = `git rev-parse HEAD`, `worktree_path` = `pwd`,
   `ticket_id` = `v0.1-04`.
