# CR-08 — mechanical gates red-tested on the happy path, never the actual bypass

A pattern across three gates this session: each was red-tested against easy or inverted
inputs, passed, and was declared a "tooth" — while the actual sin it names walks straight
through. This is the deepest recurring commander failure of the session and the reason
grok kept catching "theater" after each "fix."

- **root_cause_id**: `gate-tests-happy-path-not-bypass`
- **attribution**: framework-fault
- **occurrences**: **3** (recurrence, D3(a)) — `reflow-gate` checks field presence not honesty (`x/y/z` passes, grok #3); CR-05's dirty-tree gate blocks pre-dispatch not the post-dispatch override that was the real sin (grok #3); `prereg-gate` checks commit ordering not content freeze — backfill thresholds after seeing results and it passes (grok #4)
- **evidence**: `.scratch/reflow/meta-reviews/grok-review-3.json` (reflow-gate `x/y/z` PASS; CR-05 mislabel) and `grok-review-4.json` (`prereg_gate_real_or_bypassable`: empty-shell prereg then backfill = PASS)
- **fix**: honestly relabel each gate to what it actually checks (reflow-gate + CR-05 in the grok #3 round; prereg-gate this round); the real content-binding teeth stay queued [DESIGNED], not claimed done
- **anti-recurrence**: standing rule for every new gate — **write the bypass red-test first**: a test that performs the actual sin (post-hoc threshold edit, empty confession, override phrasing) and asserts the gate FAILS. A gate with only happy-path / inversion tests is not landed. (Process rule; not itself mechanizable — declared, per TEMPLATE.)
- **polluted-rework**: `reflow-gate`, CR-05's dirty-tree claim, and `prereg-gate` all shipped with happy-path-only red-tests
