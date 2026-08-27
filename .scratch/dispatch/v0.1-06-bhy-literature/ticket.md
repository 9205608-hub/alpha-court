# Ticket: v0.1-06 — BHY multiple-testing literature note (implementation-grade)

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court is a "statistical court" for quantitative factor research. One of
its four kernel statistics is **false-discovery-rate control via
Benjamini-Hochberg-Yekutieli (BHY)** applied to the significance tests of many
factor trials. Before any code is written, we need an implementation-grade
literature note rewriting the procedures cleanly from the PUBLIC literature,
precise enough that a later reviewer can put the papers and the code side by
side.

This is a research/documentation ticket. You have web search/fetch — use it
to consult the actual papers.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Every formula/procedure step must carry a citation: paper, theorem /
   equation / section number, using the papers' own notation first.
2. Write everything fresh from public literature; no long verbatim passages;
   no material from any proprietary source.
3. NO code — markdown document only.
4. Language: English.
5. Create/modify ONLY `docs/research/bhy.md`. Do not touch any other file.

## Task

Write `docs/research/bhy.md` covering, in this order:

1. **Sources** — full bibliographic entries for at least:
   - Benjamini, Y. & Hochberg, Y. (1995), "Controlling the False Discovery
     Rate: A Practical and Powerful Approach to Multiple Testing", JRSS-B 57(1).
   - Benjamini, Y. & Yekutieli, D. (2001), "The Control of the False Discovery
     Rate in Multiple Testing under Dependency", Annals of Statistics 29(4).
   - Harvey, C. R., Liu, Y. & Zhu, H. (2016), "…and the Cross-Section of
     Expected Returns", Review of Financial Studies 29(1) — for the
     finance-context usage and threshold discussion.
2. **The BH step-up procedure** — ordered p-values, the k* = max{i : p_(i) ≤
   (i/N)·q} criterion, rejection set, the independence/PRDS condition under
   which BH controls FDR at q.
3. **The BY correction** — the c(N) = Σ_{i=1..N} 1/i factor, the adjusted
   criterion p_(i) ≤ i·q/(N·c(N)), validity under arbitrary dependence, and
   the power cost.
4. **Where the p-values come from in our setting** — t-statistic of the mean
   of an IC (or return) series; one-sided vs two-sided choice and its
   consequences; the option of Newey-West/HAC standard errors for
   autocorrelated series (cite Newey & West 1987); how N must align with the
   trial ledger's count.
5. **BH vs BY decision guidance** — when factor trials are strongly
   dependent (correlated factors on the same data), which procedure the
   literature supports, incl. Harvey-Liu-Zhu's practice.
6. **Test vector** — one fully hand-worked example: N=10 p-values you choose
   (include ties and a borderline case), worked through BOTH BH and BY at
   q=0.05: show the sorted table, each threshold i·q/N and i·q/(N·c(10)),
   c(10) computed explicitly, and the resulting rejection sets. This becomes
   a pytest case later.
7. **Implementation pitfalls** — at minimum: the step-up (not step-down)
   direction; adjusted p-values vs rejection decisions (monotonicity
   enforcement when reporting q-values); numerical care with tiny p-values;
   behavior at N=1.

## Acceptance criteria

1. `test -f docs/research/bhy.md` → exit 0
2. Document contains all seven sections; every procedure step cites its paper.
3. The N=10 test vector shows the full worked table for both BH and BY,
   including c(10) ≈ 2.928968 computed explicitly.
4. `git status --porcelain` after your final commit → empty
5. `git log --oneline -1` message: `v0.1-06: BHY literature note`

## Out of scope

Any code, any other statistic (DSR, PBO, noise controls), any repo config.

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit: `git add docs/research/bhy.md && git commit -m "v0.1-06: BHY literature note"`.
4. Your final output must be ONLY the JSON receipt (schema enforced by the
   dispatch harness). Gather first: `branch` = `git branch --show-current`,
   `commit` = `git rev-parse HEAD`, `worktree_path` = `pwd`,
   `ticket_id` = `v0.1-06`.
