# CR-07 — commander shipped its own skill without the external review it demands of others

The double-standard the v0.1 meta-review graded B for, recurring. The commander built
honest-validation (禁赢学), self-assessed it "grounded and honest," committed + merged it
to main (`1ce25a7`), and told the user "no external review needed" — while the workflow
system requires worker-binding rules to clear external REFUTE. The user caught it
("跟 grok 交流没？"); grok #4 (RP-1) then confirmed the skill leans ~70% on `quant-mentor`
and its one tooth (`prereg-gate`) is bypassable.

- **root_cause_id**: `commander-self-exempt-from-review`
- **attribution**: framework-fault
- **occurrences**: **2** (recurrence, D3(a)) — v0.1 meta-review `top_criticisms` 双重标准, and this session (self-exempted honest-validation from RP-1)
- **evidence**: `.scratch/reflow/meta-reviews/grok-review-4.json` (`one_sentence`: "指挥官自判免审再犯双重标准"); this session the commander literally said "不必外审"; the user's "跟 grok 交流没？" is the RP-1 trigger that should have been automatic
- **fix**: ran grok #4 (RP-1) on both P1 skills after the fact; adopted its findings (reframed rule 6, honest prereg-gate downgrade, factor-flow no-hook correction); logged here + in the meta-review ledger
- **anti-recurrence**: **BUILT** — `scripts/skill-review-gate.sh [base] [head]` exits 1 if a commit range touches `.claude/skills/**/SKILL.md` but rides with no `.scratch/reflow/meta-reviews/*` review. **Bypass-red-tested (CR-08), not happy-path**: run against `8b1d556..1ce25a7` (honest-validation merged un-reviewed — the exact sin of this CR) it **FAILS**, i.e. it would have blocked this session's double-standard; it PASSES the reviewed batches (`c7a0d0f..8b1d556`, `4e53314..03dd7fa`). Honest limit: it checks **co-presence, not substance** — a faked review still passes; substance is RP-1's / a human's job (that is the D1 boundary, stated not hidden). Run before any ff-merge to main; wiring it as a pre-merge / Stop hook is the one remaining [DESIGNED] step.
- **polluted-rework**: honest-validation shipped un-reviewed (`1ce25a7`); its corrections ride this rework
