# Case-study disclosure boundary — pre-registration

*Committed **before** a single word of `docs/case-study.md` is written. This is
禁赢学 (honest-validation) turned on the writeup itself: the boundary of what the
public case study may and may not contain is frozen here first, so it cannot be
quietly widened after the prose exists. Commit ordering is the tamper-evidence
(same mechanism `scripts/prereg-gate.sh` checks for a study: pre-registration
precedes results). Pre-registered 2026-07-12.*

## Purpose

A public "How it was built" case study for the alpha-court repo, CV-linkable. It
must be an honest technical narrative that stands on its own — its résumé value is
implicit in *what it shows*, never asserted in the text.

## In scope — citable evidence (all public-git-tracked, no private material)

- **Product results**: the killer demo (survivors, |t|, naive p, p̂, T, factor
  count, best-of-null pool) — read from `report.md` / manifests / `report.md`
  ledger, **not from memory**.
- **The court battery + literature**: DSR (Bailey & López de Prado), PBO/CSCV,
  BHY multiple-testing — methods cited from public literature only (already cited
  in `docs/design/*` and code).
- **Architecture**: `court/` ↔ `adapters/` decoupling; pre-registration discipline.
- **Process evidence** from public-tracked `.scratch/` (dispatch tickets, worker
  raw JSON, `meta-review-ledger.md`, `meta-reviews/grok-review-*.json`) and git
  history: dispatch/rework counts, test counts, ticket count, caught-error
  precedents (BY worker-wins, CR-06/07/08, grok #5 rejection, reflow fired 4×).
- **Tooling names**: Claude Code (commander), grok / SuperGrok (headless worker),
  qlib (reused backtest oracle). Naming the tools is fine.

**Every number in the case study is read from the repo/git at write time and
cross-checked, never quoted from memory** (memory itself carries conflicts:
24 vs 26 dispatches, 129 vs 158 tests — these must be reconciled against source).

## Out of scope — forbidden (hard rules, CLAUDE.md 铁律 + design doc ④)

- **Zero `docs/private/` content** (gitignored; job-hunt strategy and private
  context live only there).
- **Zero prior-employer (前实习单位) code, data, or identifiers.** Statistical
  methods rewritten from public literature and cited item-by-item — never carried
  from any prior workplace.
- **No naming of a target employer** ([REDACTED-EMPLOYER] / any firm). Employer targeting lives in
  the CV-link context, not in the public document. Naming a firm reads as pandering.
- **No "this is for my résumé / I am job-hunting" framing** inside the document. It
  stands as a project retrospective; the job-search framing is how the CV *links*
  to it, not text in it.
- **No inflated or unverifiable claims** (禁赢学): every process claim anchors to a
  concrete caught error; honest status tags ([LANDED]/[DESIGNED]/[DEFERRED]) are
  shown, not hidden. The enforcement layer is partly manual and some teeth are
  designed-not-built — this is stated plainly, because hiding it would be the exact
  self-deception the project is about.

## Locked decisions (grilled 2026-07-12, all per recommendation)

1. Do **not** name [REDACTED-EMPLOYER] / target employer in the public doc.
2. Do **not** put job-hunt framing in the doc.
3. First-person "I" is fine; real-name / handle attribution is the author's call
   (GitHub `SpenSir123` is already public).
4. **Cite** `.scratch/` process evidence — it is the "anchored to a caught error"
   proof backbone.

## Pre-publish cleanup items (NOT this session — recorded so they aren't forgotten)

Publishing the repo publicly is a separate, outward-facing, author-authorized step.
Before it happens:

- `docs/design/quant-workflow-system.md` currently **names [REDACTED-EMPLOYER] and contains the
  résumé strategy** in public-tracked git. Decide: keep / move to `docs/private/` /
  desensitize.
- Scan all public-tracked `.scratch/` dispatch tickets and worker JSON for any
  prior-employer or private identifier before the repo goes public.
- Bilingual README + demo recording + repo creation (v0.1 wrap-up checklist).
- RP-1: run a fresh cross-model (grok) adversarial review of the finished case
  study before it is considered publish-ready (a public claim-making artifact must
  clear external adjudication, not the commander's own read).

## Status

- [x] Boundary pre-registered and committed (this file).
- [x] `docs/case-study.md` written within this boundary (English `9c2bf63`, Simplified Chinese thereafter).
- [x] Claim-audit pass — 5-slice adversarial workflow; 6 MISLEADING findings fixed.
- [x] Artifact rendered from the final markdown (private; re-rendered after each revision).
- [x] grok RP-1 external review — grade B / revise; 2 major + minors adjudicated and fixed
  (seed-sweep honesty debt disclosed, B-grade de-medalled, throughput facade cut, CR-07/CR-08
  separated, §6 de-certified). Raw at `.scratch/reflow/meta-reviews/case-study-review-raw.json`.
- [ ] (queued, user-authorized outward actions) public repo + desensitization + CV link.
