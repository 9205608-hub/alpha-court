"""Power-curve figures (power-calibration.md §6). Matplotlib is a [demo] extra."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from examples.power_calibration.calibrate import CalibrationResult
from examples.power_calibration.config import CLAIM_SCOPE, UNIT_FOOTNOTE


def render_figures(
    *,
    out_dir: str | Path,
    summaries: list[Any],
    calibration: CalibrationResult,
) -> dict[str, Any]:
    """Write figure.png / figure.svg; return plotted scalars.

    Guards: import matplotlib only inside this function so non-figure tests
    do not require the [demo] extra.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    strengths = np.array([s.strength for s in summaries], dtype=np.float64)
    a_hat = np.array([s.a_hat for s in summaries], dtype=np.float64)
    a_lo = np.array([s.a_lo for s in summaries], dtype=np.float64)
    a_hi = np.array([s.a_hi for s in summaries], dtype=np.float64)
    b_hat = np.array([s.b_hat for s in summaries], dtype=np.float64)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
    ax_a, ax_b = axes[0, 0], axes[0, 1]
    ax_g, ax_c = axes[1, 0], axes[1, 1]

    # Hero A — rework-02 FIX-C: mask non-finite rows (β=0 A=NaN is by design
    # under dual-estimand ruling). Keep axvline and B-panel; never raise.
    finite_a = (
        np.isfinite(a_hat) & np.isfinite(a_lo) & np.isfinite(a_hi) & np.isfinite(strengths)
    )
    if np.any(finite_a):
        yerr_lo = np.clip(a_hat[finite_a] - a_lo[finite_a], 0.0, None)
        yerr_hi = np.clip(a_hi[finite_a] - a_hat[finite_a], 0.0, None)
        ax_a.errorbar(
            strengths[finite_a],
            a_hat[finite_a],
            yerr=[yerr_lo, yerr_hi],
            fmt="o-",
            color="#4C72B0",
            label="A = P(pass|won)",
            capsize=3,
        )
    if 0.0 in strengths or np.any(np.isclose(strengths, 0.0)):
        ax_a.axvline(0.0, color="#C44E52", linestyle="--", alpha=0.6, label="β=0 size")
    ax_a.set_xlabel("target annualized ICIR (frozen axis)")
    ax_a.set_ylabel("A")
    ax_a.set_ylim(-0.05, 1.05)
    ax_a.set_title("Hero: court ROC given natural win")
    ax_a.legend(loc="best", fontsize=8)

    # B beside (β=0 B is finite — always plot finite points)
    finite_b = np.isfinite(b_hat) & np.isfinite(strengths)
    if np.any(finite_b):
        ax_b.plot(
            strengths[finite_b],
            b_hat[finite_b],
            "s-",
            color="#55A868",
            label="B = P(win) [R₀]",
        )
    ax_b.set_xlabel("target annualized ICIR")
    ax_b.set_ylabel("B")
    ax_b.set_ylim(-0.05, 1.05)
    ax_b.set_title("Natural selection rate (first R₀ seeds)")
    ax_b.legend(loc="best", fontsize=8)

    # Per-gate TPR
    gate_keys: list[str] = []
    for s in summaries:
        for g in s.gate_tpr:
            if g not in gate_keys:
                gate_keys.append(g)
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(gate_keys), 1)))
    for gi, g in enumerate(gate_keys):
        ys = [s.gate_tpr.get(g, np.nan) for s in summaries]
        ax_g.plot(strengths, ys, "o-", color=colors[gi], label=g, markersize=4)
    ax_g.set_xlabel("target annualized ICIR")
    ax_g.set_ylabel("TPR among won")
    ax_g.set_ylim(-0.05, 1.05)
    ax_g.set_title("Per-gate TPR (default panel)")
    if gate_keys:
        ax_g.legend(loc="best", fontsize=7)

    # Calibration decomposition
    if calibration.beta_grid and calibration.mean_icir:
        bg = np.asarray(calibration.beta_grid, dtype=np.float64)
        ax_c.plot(bg, calibration.mean_icir, "o-", color="#8172B2", label="mean ICIR")
        if calibration.mean_ic:
            ax_c2 = ax_c.twinx()
            ax_c2.plot(
                bg, calibration.mean_ic, "--", color="#CCB974", label="E[IC]", alpha=0.8
            )
            ax_c2.set_ylabel("E[IC]")
        ax_c.set_xlabel("β")
        ax_c.set_ylabel("annualized ICIR")
        ax_c.set_title("Calibration: ICIR(β) / E[IC](β)")
        ax_c.legend(loc="upper left", fontsize=8)
    else:
        ax_c.text(0.5, 0.5, "no calibration curve", ha="center", va="center")
        ax_c.set_axis_off()

    fig.suptitle(
        "Power calibration (uncertified; constructed oracle ≠ discoverable alpha)",
        fontsize=11,
    )
    fig.text(0.5, 0.01, UNIT_FOOTNOTE[:120] + "…", ha="center", fontsize=7, wrap=True)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))

    png = out / "figure.png"
    svg = out / "figure.svg"
    fig.savefig(png, dpi=150)
    fig.savefig(svg)
    plt.close(fig)

    return {
        "strengths": strengths.tolist(),
        "a_hat": a_hat.tolist(),
        "b_hat": b_hat.tolist(),
        "claim_scope_present": True,
        "unit_footnote": UNIT_FOOTNOTE,
        "claim_scope": CLAIM_SCOPE[:80],
    }
