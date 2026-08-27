# CR-11 — the 05 book/ticket asserted a 禁赢学 statistic (size P(pass)≈α) that its own specified estimator cannot measure at the pre-registered scale, plus two smaller contract over-claims

- **root_cause_id**: `ticket-self-contradiction`
- **attribution**: contract-fault (commander)
- **occurrences**: 5th of `ticket-self-contradiction` (CR-09 ×4 = AC unsatisfiable at
  base; CR-10 = frozen-spec security fail-opens; this = an asserted honesty *statistic*
  is degenerate at the frozen N/R under the estimator the contract itself specified).
  Distinct sub-shape, mapped to the nearest frozen id (vocab is append-only behind an
  RP-1 gate — not minting `spec-asserts-unmeasurable-statistic` unilaterally; flag it
  for a future id if the class recurs). Three instances THIS round, all one class:
  1. **book §6 (M2, the load-bearing one):** "directional size at β=0 asserts
     `P(pass) ≈ nominal α` for FDR/pool-max/individual." But §6 also marked the β=0
     point ON the `P(unanimous | won)` hero curve, and the delivered harness reused the
     won-conditioned estimator for the size panel. At β=0 the injected is pure noise and
     wins argmax t only ≈1/N, so at N=100/R₀=40 → E[n_won]=0.4 → typically 0 wins →
     A=NaN and every per-gate TPR=NaN. **The contract asserted a number its own
     specified estimator returns as NaN.**
  2. **ticket §3 wiring (minor-b):** claimed "the sweep uses the book's separate roots";
     the v3 book pinned ONLY the calibration root 320260711 — the sweep root did not
     exist in the contract (a false-fact over-claim; worker had to choose 420260711).
  3. **ticket AC-5 / iron-law #8 (M4):** the ownership boundary forbade touching
     pyproject, but the repo's own `examples.killer_demo` packaging precedent lists
     sibling `examples.*` subpackages — so the AC forbade the packaging-correct action.
     (The referee separately proved the line is unnecessary for the editable install, so
     the worker wins the deviation on both counts.)
- **evidence**: adversarial referee panel (5 REFUTE lenses), every finding
  **independently re-reproduced by the referee before ruling**:
  - M2: `run.py:504` `n_a_pass = sum(o.won and o.unanimous_pass)`, `run.py:515-527`
    gate_tpr among won only; book §6 quote "P(pass) ≈ nominal α"; panel probe (N=21,R₀=25)
    → n_won=2, A Wilson [0,0.658]; at frozen N=100,R₀=40 → E[n_won]=0.4 → NaN. Commander
    re-read `run.py:495-531` + book `docs/design/power-calibration.md` §6:220 to confirm.
  - minor-b: `grep -n '320260711\|420260711\|root' docs/design/power-calibration.md`
    → only the calibration root; ticket §3 "book's separate roots" resolves to nothing.
  - M4: `git diff --stat 3f87be24..6f42e59f` shows `pyproject.toml`; commander reverted
    it and confirmed the worker's own `.venv` still `import examples.power_calibration`
    and `python -m examples.power_calibration --help` (lenient MAPPING finder resolves via
    the top-level `examples` key) → the edit is unnecessary; killer_demo lists siblings.
- **fix** (commit `638f515c`, contract amendments BEFORE the worker rework, contract-freeze):
  - book §6: **ruling** — the size-panel per-gate `P(pass)≈α` is the *accused champion's*
    per-gate pass rate over ALL R₀ seeds, **unconditional on which trial is champion**
    (one champion exists every seed → ~R₀ samples); the hero curve's β=0 point stays
    `P(unanimous|won)` (informational). Two estimands, never conflated.
  - book §4.2: ratify `POWER_SEED_ROOT = 420260711` for the sweep (was under-specified);
    ticket §3 "book's separate roots" corrected.
  - book §4.1: name the transform Hazen/rankit `(r−0.5)/m` (loosely "van der Waerden");
    qualify "unit-variance" as approximate (exact m→∞). [signal minors]
  - ticket iron-law #8 + AC-5: permit the one `examples.power_calibration` pyproject line.
  - worker rework-01 (`.scratch/dispatch/v0.2-05-power-harness/rework-01.md`): FIX-1
    re-estimates the β=0 size panel from the champion unconditionally; FIX-2 gives β_t a
    real battery path; FIX-3 makes the size guard assert the DATA row.
- **anti-recurrence** (binds the commander; strengthens `/worker-dispatch` rule 3 lint):
  the pre-dispatch adversarial lint must add a **"measurability-at-frozen-scale" pass** —
  for every quantitative ASSERTION the ticket/book makes (`P(pass)≈α`, a TPR-drop, a
  monotone-β claim, "size beside power"), name the code path that produces it AND prove it
  yields a **non-degenerate** estimate at the frozen N/R (not NaN, not a ~1/N-sample
  Wilson [0,1]). This session's pre-dispatch lint checked the 3 landing BLOCKERs + env
  ACs but **did not** probe whether each asserted honesty statistic is measurable at the
  pre-registered scale — that is the coverage gap that let M2 through to delivery (the
  referee PANEL caught it, so the system held, but the lint should have).
  **Re-runnable assertion:** the FIX-1 reduced-config test must assert the β=0 size-panel
  per-gate numbers are **finite (non-NaN) with ~R₀ samples** at a reduced N — a test that
  FAILS if the won-conditioned (degenerate) estimator is ever reintroduced. Added to
  `tests/test_power_calibration.py` in rework-01.
- **polluted-rework**: `.scratch/dispatch/v0.2-05-power-harness/rework-01.md` (worker
  rework-01). Of its 5 fixes, FIX-1 (M2, contract-half) / minor-b / M4 are this CR's
  contract-faults issued as NEW rulings, NOT post-hoc legislation against the worker;
  FIX-2 (β_t stub) / FIX-3 (non-enforcing guard) / the "Blom" comment are genuine
  worker-fault. The worker WINS deviations (a) pyproject and (b) seed-root.
