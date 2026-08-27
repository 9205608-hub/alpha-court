"""One-panel figure: pool-max null histogram + accused |t| (killer-demo.md §8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def build_caption(
    *,
    master_seed: int,
    t_len: int,
    data_tag: str,
    engine_version: str,
    universe: str = "csi300",
    metric_label: str = "RankIC",
    cost_declaration: str,
) -> str:
    """Mandatory caption items (killer-demo.md §8; adapter-interface.md §4.4)."""
    return (
        f"{cost_declaration}. "
        f"Metric: {metric_label}. Universe: {universe} (PIT). "
        f"T = {t_len} evaluation dates. Master seed = {master_seed}. "
        f"Data tag = {data_tag}. engine_version = {engine_version}."
    )


def render_figure(
    pool_max_nulls: np.ndarray | list[float],
    *,
    accused_abs_t: float,
    accused_name: str,
    accused_naive_p: float,
    pool_p_hat: float,
    n_survivors: int,
    n_candidates: int,
    caption: str,
    out_dir: str | Path,
    n_nulls: int | None = None,
) -> dict[str, Any]:
    """Write figure.png (300 dpi) and figure.svg; return figure numbers for tests.

    Returns a dict of the plotted scalars (for seed-determinism assertions).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nulls = np.asarray(pool_max_nulls, dtype=np.float64)
    if n_nulls is None:
        n_nulls = int(nulls.size)
    n_at_least = int(np.sum(nulls >= accused_abs_t))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    n_bins = min(30, max(10, n_nulls // 5))
    ax.hist(nulls, bins=n_bins, color="#4C72B0", alpha=0.75, edgecolor="white")
    # Shade tail null ≥ observed
    ylim = ax.get_ylim()
    ax.axvspan(
        accused_abs_t,
        max(nulls.max(), accused_abs_t) + 0.05,
        color="#C44E52",
        alpha=0.15,
    )
    ax.axvline(
        accused_abs_t,
        color="#C44E52",
        linewidth=2.0,
        label=f"accused |t|={accused_abs_t:.3f}",
    )
    ax.axvline(
        1.96,
        color="#555555",
        linestyle="--",
        linewidth=1.5,
        label="single-test 5% bar (|t|=1.96)",
    )
    ax.set_ylim(ylim)
    ax.set_xlabel("best-of-pool |t| under circular-shift null")
    ax.set_ylabel("count")
    stamp = f"REJECTED — {n_survivors}/{n_candidates} survived" if n_survivors == 0 else (
        f"{n_survivors}/{n_candidates} survived"
    )
    annotation = (
        f"{accused_name}\n"
        f"|t| = {accused_abs_t:.3f}\n"
        f"naive p = {accused_naive_p:.4g}\n"
        f"pool-max p̂ = {pool_p_hat:.4g}\n"
        f"tail count (#null ≥ obs) = {n_at_least}\n"
        f"{stamp}"
    )
    ax.text(
        0.98,
        0.98,
        annotation,
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Noise-control pool-max null vs naive discovery")
    fig.text(0.5, 0.01, caption, ha="center", va="bottom", fontsize=7, wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))

    png_path = out / "figure.png"
    svg_path = out / "figure.svg"
    fig.savefig(png_path, dpi=300)
    fig.savefig(svg_path)
    plt.close(fig)

    return {
        "accused_abs_t": float(accused_abs_t),
        "pool_p_hat": float(pool_p_hat),
        "n_at_least": n_at_least,
        "null_mean": float(nulls.mean()),
        "null_max": float(nulls.max()),
        "null_min": float(nulls.min()),
        "n_survivors": int(n_survivors),
        "caption": caption,
        "png": str(png_path),
        "svg": str(svg_path),
    }
