# Rework 01 — v0.2-05 power-calibration harness

Your delivery (commit `6f42e59f`) was independently re-run and reviewed by a
5-lens adversarial referee panel (every finding was reproduced by the referee
before this note). **The calibration math and the verdict vertical slice are
ACCEPTED** — zero findings on ICIR / PCHIP / Wilson / seed-independence /
β\*=mean / no-realized-write-back; and aggregation reuse (no second code path),
won=argmax **signed** t, the greater battery via `court.judge`, B frozen at the
first R₀ seeds, and noise-cache cross-seed isolation were all confirmed correct.
Honest receipt. Good work.

**Five fixes below** — all inside your existing file ownership. Fix them in your
existing worktree (resume). Two underlying issues were **contract-faults already
fixed on the commander side** (the amended contract text is pasted inline so this
note is self-contained — your worktree's `docs/` copy is the old one; follow the
pasted text, it wins). Attribution is stated per fix so the ledger is honest.

---

## FIX 1 — [MAJOR, attribution: worker-primary + contract-secondary] β=0 directional-size estimator is statistically hollow

**Referee evidence (verbatim):** "run.py:504 `n_a_pass = sum(1 for o in outcomes
if o.won and o.unanimous_pass)`; run.py:515-527 gate_tpr among won. At β=0 the
injected is pure noise (mix_factor β=0 → noise), exchangeable with the 99 noise,
so P(injected = argmax t) ≈ 1/N. At real N=100, R₀=40, E[n_won]=0.4 → typically 0
wins → A=NaN and every gate_tpr=NaN. The battery produces a champion every seed,
but run.py records gate_pass only for the injected trial (run.py:430) and counts
it only when o.won, discarding ~99% of champions. Book §6 requires a measurable
P(pass)≈α at β=0; the harness cannot deliver it."

**AMENDED CONTRACT — book §6 directional-size Estimator ruling (2026-07-17), paste:**
> The size-panel per-gate `P(pass) ≈ α` is the **accused champion's** per-gate
> pass rate over **all R₀ seeds — UNCONDITIONAL on which trial is the champion**.
> At β=0 the injected wins argmax t only ≈1/N of the time, so a
> `P(pass | injected won)` estimator has ≈0 wins at N=100/R₀=40 → NaN. The size
> panel must instead judge whatever champion the directed scan selects each seed
> (one champion always exists) and report its per-gate pass rate → ~R₀ samples and
> a measurable ≈α. The hero curve's β=0 point stays `P(unanimous | won)`
> (informational, wide CI); the size-panel numbers are the **unconditional
> champion rate** and bear the `≈α` assertion. Report both, labeled as different
> estimands, never conflated.

**Fix:** for the directional-size panel, every seed's champion = argmax signed t
over the pool (it always exists). Judge that champion through the greater battery
and record **the champion's** per-gate decisions (not only the injected's — you
currently record gate_pass for the injected trial at run.py:430; also record the
selected champion's per-gate pass). Compute the size panel's per-gate P(pass) as
the champion's pass rate over ALL R₀ seeds (unconditional). Keep the hero curve's
β=0 point as P(unanimous|won). This applies at least at β=0 (the size anchor); if
cheap, expose the unconditional champion rate at every strength as a diagnostic,
but the ≈α assertion is the β=0 unconditional number. Add a red-first test that
the β=0 size per-gate numbers are non-NaN with ~R₀ samples at a reduced N.

---

## FIX 2 — [MAJOR, attribution: worker] β_t appendix never runs the battery

**Referee evidence (verbatim):** "beta_t.py contains NO
judge/build_greater_applications/unanimous/trial_survives/Application call
(`grep` → only the docstring). run_beta_t_appendix records only `realized_icir`
per arm (BetaTArmResult has no pass/TPR field). report.py:190-216 prints the ICIR
table under a heading that states 'Answers: points unanimous/PBO-TPR drops
constant → matched episodic', but no TPR is computed. Book §7: 'The appendix
answers one number: how many points unanimous/PBO-TPR drops from constant edge to
matched-ICIR episodic edge... otherwise the hero is victory theater.'"

**Fix:** add the code path in `beta_t.py` that runs the **greater-battery over the
constant-β and matched-ICIR episodic arms across R seeds** and emits the actual
unanimous-TPR and PBO-TPR **drop** number (constant → matched episodic). Reuse
`court.judge.judge` + `harness.aggregation_policy` exactly as `run.py` does — no
second code path. Per the compute boundary, the real R-seed numbers are the
referee's real-data job (like the main sweep), but **the code path must exist and
be exercised on the reduced config** (reduced-test asserts the drop number is
computed and finite on a tiny synthetic config; real magnitude deferred). Once the
path exists, report.py's "Answers: drops" line is truthful — keep it. Your honest
docstring ("Does not re-run the full battery") should be updated to reflect the
new path.

---

## FIX 3 — [MAJOR→minor, attribution: worker] non-enforcing size guard + hardcoded threshold

**Referee evidence (verbatim):** "report.py:83 unconditionally appends the header
'## Directional size...'; the honesty guard report.py:255-257 checks only
'\"Directional size\" in text', which the header always satisfies — so
`report_has_size_beside_power` returns True on a report whose size panel is
entirely omitted. test_reduced_e2e relies on this guard, giving false assurance
for the iron law." Also: "run.py:531 `underpowered = n_won < 20 and strength > 0`
— 20 is hardcoded while cfg.n_won_target is configurable, and the `strength > 0`
clause means the β=0 size row is never flagged."

**Fix:** make `report_has_size_beside_power` **and** the e2e test assert the β=0
size **DATA** row is present (n_seeds/n_won/per-gate numbers rendered), not just
the header substring; OR have `render_report` raise when `0.0 ∉ grid` rather than
silently emit an omission note. Replace the literal `20` at run.py:531 with
`cfg.n_won_target`. Consider flagging the β=0 size row on its own small n
(now that FIX 1 gives it ~R₀ unconditional samples, this is less acute).

---

## FIX 4 — [minor, attribution: worker] submission drops pool_max silently

**Referee evidence (verbatim):** "run.py:459-470 forces injected as DSR/PBO
selected + judged individual, but pool_max has no force knob, so it still judges
the argmax champion; trial_survives only counts gates whose decisions include the
forced injected. So submission power is unanimous over 4 gates for a non-winning
injected but 5 gates when it wins — systematically easier to pass in the weak
regime the submission table characterises."

**Fix:** either (a) document in report.py's submission footnote that the forced
non-champion faces one fewer gate (pool_max cannot vote on a non-champion), OR
(b) exclude pool_max from the submission unanimous denominator explicitly so the
gate set is **stated, not incidental**. (b) is cleaner. Submission is a secondary
table never overlaid on A, so scope is contained — but state it.

---

## FIX 5 — [minor, attribution: contract/book-wording] signal transform naming

**Referee evidence (verbatim):** "signal.py:75 comment `# Blom mid-rank
transform`; L77-78 `u = (ranks - 0.5) / m` — this is the Hazen/rankit position,
not Blom (which is (r-3/8)/(m+1/4)); the fn/docstring/book call it 'van der
Waerden' (canonical vdW is r/(m+1)). Numeric experiment unaffected — naming only.
var of Φ⁻¹((r-0.5)/m) = 0.767 at m=5, 0.959 at m=30 — 'unit-variance' is only
asymptotic."

**AMENDED CONTRACT — book §4.1 (paste):** the transform is the **Hazen/rankit
position `Φ⁻¹((r − 0.5)/m)`** (loosely "van der Waerden normal scores"; canonical
vdW is `r/(m+1)`, but Hazen is the one implemented and calibrated against), and
each term is **approximately** unit-variance cross-sectionally (exact as m→∞).

**Fix:** correct the signal.py:75 comment (it is Hazen/rankit, NOT Blom); qualify
the "unit-variance" docstring as "approximately unit-variance (exact as m→∞)". No
code / numeric change. (You may keep the "van der Waerden" name if you add the
"(Hazen position (r−0.5)/m)" qualifier.)

---

## ALREADY RESOLVED ON COMMANDER SIDE — no action, informational

- **pyproject packages line (was receipt deviation a):** RATIFIED — **keep it**.
  The referee proved it is unnecessary for the editable install (the lenient
  finder resolves `examples.power_calibration` via the top-level `examples` key),
  but it is packaging-correct and mirrors the `examples.killer_demo` precedent, so
  iron-law #8 and AC-5 were amended to permit that one line. You **win** this
  deviation — it is a contract-fault (AC-5 was too tight), not a worker-fault.
- **POWER_SEED_ROOT=420260711 (was receipt deviation b):** RATIFIED in book §4.2
  as a commander ruling. Keep `config.py:22` as-is. (The ticket's earlier "book's
  separate roots" wording was a false-fact; the book had pinned only the
  calibration root — corrected. Contract-fault, not yours.)
- **TDD red-phase (was receipt deviation d):** accepted as nominally satisfying
  AC-6 (receipt-based). For THIS rework, please capture a genuine red run for the
  new FIX-1 and FIX-2 tests in the receipt `self_test` (non-zero exit before
  green) so the red phase is auditable.

---

## Delivery protocol (unchanged from the original ticket)

1. Resume in your existing worktree; work here only.
2. TDD contractual: **failing tests FIRST** for the new size-estimator (FIX 1) and
   the β_t battery path (FIX 2) — record the red run (non-zero exit) in the
   receipt `self_test`, then green.
3. Re-run the AC and record each with its real exit code:
   - `.venv/bin/python -m pytest tests/test_power_calibration.py -v` → 0 (no qlib,
     seconds; keep n_splits small — PBO cost is C(n_splits, n_splits/2)).
   - `python3 -m pytest` → 0 (nothing else regresses).
   - `.venv/bin/ruff check .` → 0.
   - `git diff --stat $BASE..HEAD` touches ONLY `examples/power_calibration/`,
     `tests/test_power_calibration.py`, and the one `examples.power_calibration`
     line in `pyproject.toml`.
4. Commit all work. Final output = ONLY the JSON receipt (status / branch /
   commit / files_changed / self_test with real exit codes / deviations /
   open_questions). Honest `partial` beats dishonest `done`.
