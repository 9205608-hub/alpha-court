"""Regenerate the official hero figure for the accepted 2026-07-18/19 sweep.

Provenance (stated plainly): the 31h run crashed inside figure rendering before
rework-02 (float-noise negative yerr at a P=0 row — see rework-02 FIX-C referee
probe), so per-strength summary objects were never persisted. This script
reconstructs them from the INTEGER counts in the committed ``report.md`` hero
table (n, n_won, passes = A·n_won, all exact at 3dp) — A-panel CIs are recomputed
exactly through the same ``stats_util.wilson_interval`` the sweep used — and
renders through the accepted ``figure.py`` with the frozen calibration. Per-gate
TPR values are taken at report precision (3dp); the difference from the exact
fractions is ≤5e-4 and invisible at plot scale. Numbers are never smoothed,
extrapolated, or hand-adjusted.

Usage: PYTHONPATH=. .venv-regen/bin/python .scratch/v0.2/power-sweep-results/make_hero_figure.py
"""

from __future__ import annotations

from types import SimpleNamespace

from examples.power_calibration.calibrate import load_calibration
from examples.power_calibration.figure import render_figures
from examples.power_calibration.stats_util import wilson_interval

# (strength, n_won, passes, B) from report.md hero table (integer-exact)
ROWS = [
    (0.0, 0, 0, 0.000),
    (0.5, 2, 0, 0.050),
    (1.0, 10, 0, 0.250),
    (1.5, 14, 0, 0.350),
    (2.0, 22, 3, 0.550),
    (2.3, 29, 5, 0.725),
    (2.6, 35, 12, 0.875),
    (2.9, 38, 16, 0.950),
    (3.2, 38, 19, 0.950),
    (3.6, 40, 30, 1.000),
    (4.0, 40, 35, 1.000),
    (4.5, 40, 39, 1.000),
    (5.0, 40, 40, 1.000),
    (6.0, 40, 40, 1.000),
]

# Per-gate TPR among won, report.md §per-gate panel (3dp as printed; 0.0 row NaN)
GATE_KEYS = ("dsr", "fdr_by", "noise_individual", "noise_pool_max", "pbo_cscv")
GATE_ROWS = {
    0.0: (float("nan"),) * 5,
    0.5: (0.000, 0.000, 0.500, 0.000, 0.500),
    1.0: (0.000, 0.000, 0.900, 0.000, 0.100),
    1.5: (0.000, 0.143, 1.000, 0.429, 0.143),
    2.0: (0.136, 0.409, 0.955, 0.500, 0.364),
    2.3: (0.172, 0.379, 0.966, 0.621, 0.448),
    2.6: (0.343, 0.486, 1.000, 0.743, 0.457),
    2.9: (0.421, 0.632, 1.000, 0.895, 0.632),
    3.2: (0.500, 0.868, 1.000, 0.921, 0.789),
    3.6: (0.750, 0.875, 1.000, 0.950, 0.925),
    4.0: (0.875, 0.975, 1.000, 0.975, 0.975),
    4.5: (0.975, 1.000, 1.000, 1.000, 1.000),
    5.0: (1.000, 1.000, 1.000, 1.000, 1.000),
    6.0: (1.000, 1.000, 1.000, 1.000, 1.000),
}


def main() -> int:
    summaries = []
    for strength, n_won, passes, b_hat in ROWS:
        if n_won == 0:
            a_hat = a_lo = a_hi = float("nan")
        else:
            a_hat, a_lo, a_hi = wilson_interval(passes, n_won)
        summaries.append(
            SimpleNamespace(
                strength=strength,
                a_hat=a_hat,
                a_lo=a_lo,
                a_hi=a_hi,
                b_hat=b_hat,
                gate_tpr=dict(zip(GATE_KEYS, GATE_ROWS[strength], strict=True)),
            )
        )
    calibration = load_calibration(".scratch/v0.2/power-frozen/calibration.json")
    render_figures(
        out_dir=".scratch/v0.2/power-sweep-results",
        summaries=summaries,
        calibration=calibration,
    )
    print("[hero-figure] wrote figure.png / figure.svg", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
