# Rework 02 — v0.2-05 power-calibration harness (post real-data acceptance)

The commander ran the full real-data sweep against your rework-01 delivery
(head `c987a5b9`, 2026-07-18 10:16 → 2026-07-19 17:15, ~31h, 880 arms).
**The main sweep is ACCEPTED**: all 14 strengths landed, β=0 shows zero false
submissions (champion-unanimous 0.000, Wilson [0, 0.088]), A/B/submission are
monotone throughout, 80% submission power at ICIR≈4.0. Your hero-side code held
up under a 31-hour production run. Good work.

**Three defects surfaced in the β_t appendix + figure path** — every one was
reproduced by the commander from `report.md` output plus your source before this
note was written. All are inside your existing file ownership. Fix them in your
existing worktree (resume). Note the run itself ended `EXIT=1` from FIX-C's
crash *after* all data had landed; no data was lost.

A shared theme, stated so you can generalize: all three are **silent-degradation
paths on inputs outside the happy path** (missing table key → silent fallback;
solution at search boundary → silent clamp; NaN row → crash at the last step).
The fix pattern in every case is fail-closed + red-first test.

---

## FIX-A — [BLOCKER, attribution: worker-primary (silent fail-open fallback);
## contract-secondary (the β* freeze did not cover all configured appendix targets)]

**Commander evidence (verbatim from the real run):** report.md appendix table row:
"| constant | 3.00 | 0.1500 | 39.0121 | 40 | 1.000 | 1.000 |" — target ICIR 3.0,
realized ICIR **39.0**. The frozen β* table has no 3.0 entry (grid: …2.9, 3.2…),
while `config.py:157` sets `beta_t_icir_targets: tuple[float, ...] = (4.0, 3.0)`.
`beta_t.py` fell through to `b_const = min(0.3, max(0.05, float(target) / 20.0))`
= 0.15 ≈ 10× the interpolated value — the entire t3.0 row (160 arms, ~10h of
compute) is uninformative: every TPR is trivially 1.000.

**Fix:**
1. Delete the silent fallback. At startup — **before any arm executes** — validate
   that every entry of `beta_t_icir_targets` resolves to a β* entry in the provided
   calibration (same float/str-key lookup you use today). A missing target is a
   hard error naming the target and the available keys. Day-one check, not mid-run.
2. Extend `calibrate` to also solve β* (same PCHIP machinery, same seed policy,
   no new code path) for every configured `beta_t_icir_targets` entry not already
   on the main grid, and store it in `calibration.json`. The commander re-freezes
   the real-data table afterwards — running the real calibration is NOT your job;
   your job is that the code path exists and is exercised on the reduced config.

**Red-first:** a test asserting that a `beta_t` run with a target absent from the
calibration raises (today it silently proceeds → test exits 1 pre-fix). A second
test asserting reduced-config `calibrate` output contains β* for the configured
appendix targets.

---

## FIX-B — [BLOCKER, attribution: worker (search bracket floor above the
## required solution; no interior/matched-quality assertions)]

**Commander evidence (verbatim):** `beta_t.py:147`
`beta_grid = [round(0.05 + 0.05 * i, 2) for i in range(12)]  # 0.05..0.60`.
For target 4.0 the constant arm used frozen β*=0.0185; a half-window matched arm
needs on-β ≈ 2×0.0185 = **0.037 < 0.05**, i.e. below the grid floor. Real-run
result rows: forward_off_matched and backward_off_matched both report
"β used 0.0500" with realized ICIR **5.6284 / 5.7257** against the constant arm's
realized **3.7900** — the "matched" arms are not matched; the headline drop
(−0.200) and the entire primary contrast are boundary-clamp artifacts.

**Fix:**
1. The search bracket for `solve_matched_beta` must contain the plausible solution
   range: for a constant-arm β* = b, the bracket must span at least [b/2, 4b]
   (build it relative to b, or extend/refine the fixed grid — your choice).
2. Post-solve hard assertions (production behavior = raise with diagnostics, not
   warn): (i) the solution is strictly interior to the bracket (never the first or
   last grid point); (ii) matched quality — the matched arm's realized full-sample
   ICIR is within 20% relative tolerance of the constant arm's realized ICIR at
   the same target. Tolerance check must be exercised by the reduced-config test.

**Red-first:** a test that today's grid + b=0.0185 returns the boundary value 0.05
(assert interior-solution → exits 1 pre-fix; post-fix the assertion holds or the
solver raises before burning seeds).

---

## FIX-C — [MAJOR, attribution: worker-primary; contract-secondary in that the
## rework-01 FIX-1 dual-estimand ruling made hero A=NaN at β=0 a *designed*
## reachable input that the figure path was never re-tested against]

**Commander evidence (verbatim from sweep.log):**
"File "…/examples/power_calibration/figure.py", line 44, in render_figures
ax_a.errorbar( … ValueError: 'yerr' must not contain negative values" — the β=0
hero row is A=nan, Wilson [nan, nan] (by design, per FIX-1's dual estimands);
`yerr=[a_hat - a_lo, a_hi - a_hat]` propagates NaN into matplotlib's validator.
Consequence: the 31h run produced no figure.png/figure.svg and exited 1.

**Fix:** in `render_figures`, mask non-finite hero rows (`np.isfinite` over
a_hat/a_lo/a_hi) out of the errorbar call; keep the β=0 `axvline` marker and the
B-panel point (B is finite at β=0); clip the masked yerr at 0 for float-noise
safety. The function must never raise on the canonical real-run summaries (which
include the NaN row). The hero β=0 estimand itself is UNCHANGED — report.md keeps
printing `nan` exactly as today; only the renderer becomes total.

**Red-first:** a test feeding `render_figures` a summaries list containing the
β=0 NaN row — it raises ValueError today (exit 1 pre-fix); post-fix both
figure.png and figure.svg exist and are non-empty.

---

## Acceptance criteria (the referee panel judges at exactly this scale)

- AC-1: each fix has a **named red-first test**; the receipt shows the pre-fix
  exit-1 run for each (genuine red evidence, same bar as rework-01).
- AC-2: the reduced-config (no-qlib) battery exercises all three new behaviors:
  fail-closed target validation, interior+matched-quality assertions, NaN-safe
  figure render.
- AC-3: `ruff check examples/power_calibration/` clean and
  `pytest tests/test_power_calibration.py` green (verified satisfiable at your
  base by the commander pre-dispatch: ruff "All checks passed!", 27 collected).
- AC-4: full suite green; no files touched outside ownership.
- AC-5: locked invariants stay locked: no second aggregation path; realized ICIR
  never written back onto the strength axis; hero β=0 estimand unchanged.
- The real 320-arm appendix re-run is the commander's job after acceptance —
  do NOT attempt it (same compute boundary as the original ticket).

## File ownership (disjoint; unchanged from your ticket)

`examples/power_calibration/config.py`, `calibrate.py`, `beta_t.py`, `figure.py`
(+ whichever existing module defines `solve_matched_beta`), and
`tests/test_power_calibration.py`. Nothing else.

## Protocol reminders (unchanged)

Iron laws still bind: court/ imports no market code (untouched here); ugly
numbers are reported as-is — no smoothing, no survivor-only reporting; statistical
implementations keep their literature citations; code and docstrings in English.
Operational: incremental file writes (no single giant emission); detach-and-poll
any command over ~2 minutes; do not touch `.venv*`. Deliver the same
schema-constrained JSON receipt: status / branch / commit / files /
commands-with-real-exit-codes / deviations / open_questions. An honest `partial`
outranks a dishonest `done`.
