"""Injected-factor construction (power-calibration.md §4.1).

oracle_i,t  = Φ⁻¹(rank_xs(forward_return_i,t))   # van der Waerden of labels
noise_i,t   = Φ⁻¹(rank_xs(AR1_i,t(φ)))
factor_i,t  = β · oracle + √(1−β²) · noise

Both terms are cross-sectionally rank-then-normal-quantile transformed so β is
a well-defined mixing weight. The oracle peeks at the same forward-return
label the adapter evaluates against — a deliberate, disclosed look-ahead.

Reuses ``examples.killer_demo.generation`` for AR(1) shells and seed trees only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

from examples.killer_demo.config import DemoConfig
from examples.killer_demo.generation import (
    ar1_panel,
    build_factor_specs,
    spawn_seed_tree,
)


def median_demo_shell_phi(*, n_candidates: int = 100) -> float:
    """Median φ over the killer-demo shell menu (power-calibration.md §4.2).

    Computed from the full 100-candidate menu (not the reduced test subset)
    so the recorded φ is the book-pinned population median.
    """
    cfg = DemoConfig(n_candidates=n_candidates)
    specs = build_factor_specs(cfg)
    if len(specs) != n_candidates:
        raise RuntimeError(f"expected {n_candidates} shells, got {len(specs)}")
    phis = np.asarray([s.phi for s in specs], dtype=np.float64)
    return float(np.median(phis))


def van_der_waerden_xs(panel: np.ndarray) -> np.ndarray:
    """Cross-sectional normal scores per row (power-calibration.md §4.1).

    For each day t, ranks finite values among instruments and maps via the
    **Hazen / rankit** position ``Φ⁻¹((r − 0.5) / m)`` (loosely called "van der
    Waerden normal scores"; canonical vdW is ``r/(m+1)``, but Hazen is the form
    implemented and calibrated against). m is the count of finite instruments
    that day. NaN labels stay NaN; days with m < 2 stay all-NaN.

    Parameters
    ----------
    panel:
        Shape (T, N) float array.

    Returns
    -------
    np.ndarray
        Same shape; **approximately** unit-variance cross-sectionally on finite
        rows (exact as m→∞; finite-m variance of Φ⁻¹((r−0.5)/m) is < 1).
    """
    x = np.asarray(panel, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError(f"panel must be 2-D (T, N), got shape {x.shape}")
    out = np.full_like(x, np.nan)
    t_len, _n = x.shape
    for t in range(t_len):
        row = x[t]
        finite = np.isfinite(row)
        m = int(finite.sum())
        if m < 2:
            continue
        vals = row[finite]
        # average ranks for ties; rankdata is 1..m
        ranks = rankdata(vals, method="average")
        # Hazen/rankit position (r−0.5)/m — NOT Blom (r−3/8)/(m+1/4)
        u = (ranks - 0.5) / m
        # Clamp away from exact 0/1 for numerical safety
        u = np.clip(u, 1e-12, 1.0 - 1e-12)
        out[t, finite] = norm.ppf(u)
    return out


def oracle_panel_from_labels(labels: np.ndarray) -> np.ndarray:
    """Van der Waerden transform of ``evaluator.labels`` (§4.1).

    Use the public ``evaluator.labels`` property (defensive copy); do not
    re-derive labels from qlib and do not touch private ``_labels``.
    """
    return van_der_waerden_xs(labels)


def noise_shell_panel(
    *,
    phi: float,
    seed_sequence: np.random.SeedSequence,
    n_dates: int,
    n_instruments: int,
) -> np.ndarray:
    """AR(1) shell → van der Waerden cross-section (§4.1).

    Reuses ``examples.killer_demo.generation.ar1_panel``.
    """
    rng = np.random.default_rng(seed_sequence)
    raw = ar1_panel(phi, rng, n_dates=n_dates, n_instruments=n_instruments)
    return van_der_waerden_xs(raw)


def mix_factor(oracle: np.ndarray, noise: np.ndarray, beta: float) -> np.ndarray:
    """β · oracle + √(1−β²) · noise (power-calibration.md §4.1).

    β ∈ [0, 1]. NaNs propagate from either input.
    """
    b = float(beta)
    if not (0.0 <= b <= 1.0):
        raise ValueError(f"beta must be in [0, 1], got {b}")
    o = np.asarray(oracle, dtype=np.float64)
    n = np.asarray(noise, dtype=np.float64)
    if o.shape != n.shape:
        raise ValueError(f"oracle/noise shape mismatch: {o.shape} vs {n.shape}")
    w_noise = float(np.sqrt(max(0.0, 1.0 - b * b)))
    return b * o + w_noise * n


def build_injected_panel(
    labels: np.ndarray,
    *,
    beta: float,
    phi: float,
    seed_sequence: np.random.SeedSequence,
    dates: list[str] | None = None,
    instruments: list[str] | None = None,
) -> pd.DataFrame | np.ndarray:
    """Full injected factor panel as DataFrame when dates/instruments given.

    Parameters
    ----------
    labels:
        (T, N) from ``evaluator.labels``.
    beta:
        Mixing weight.
    phi:
        AR(1) shell φ (median of demo shells for the real experiment).
    seed_sequence:
        Noise realization seed (must not reuse calibration seeds in the sweep).
    dates, instruments:
        If both provided, return a labeled DataFrame; else raw ndarray.
    """
    oracle = oracle_panel_from_labels(labels)
    t_len, n_inst = oracle.shape
    noise = noise_shell_panel(
        phi=phi,
        seed_sequence=seed_sequence,
        n_dates=t_len,
        n_instruments=n_inst,
    )
    factor = mix_factor(oracle, noise, beta)
    if dates is None or instruments is None:
        return factor
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    return pd.DataFrame(factor, index=idx, columns=list(instruments))


def build_noise_panels(
    *,
    n_noise: int,
    phi: float,
    candidate_ss: np.random.SeedSequence,
    dates: list[str],
    instruments: list[str],
) -> list[pd.DataFrame]:
    """Generate n_noise pure-noise AR(1) score panels (van der Waerden'd).

    Uses grandchild seeds from ``candidate_ss.spawn(n_noise)`` — same tree
    shape as killer_demo generation, but all shells share the fixed median φ
    (power-calibration.md §4.1: φ fixed to one median value).
    """
    grandchildren = candidate_ss.spawn(n_noise)
    n_dates = len(dates)
    n_inst = len(instruments)
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    panels: list[pd.DataFrame] = []
    for i in range(n_noise):
        arr = noise_shell_panel(
            phi=phi,
            seed_sequence=grandchildren[i],
            n_dates=n_dates,
            n_instruments=n_inst,
        )
        panels.append(pd.DataFrame(arr, index=idx, columns=instruments))
    return panels


def spawn_power_seed_tree(
    master_seed: int,
) -> tuple[np.random.SeedSequence, np.random.SeedSequence, np.random.SeedSequence]:
    """Spawn three children: noise candidates, offsets, injected-noise shell.

    Child layout under one power master seed (per replication seed):
      spawn(3) → [noise_pool, offsets, injected_shell]
    Distinct from killer_demo's spawn(2) so injected noise is independent of
    the 99-pool realizations.
    """
    root = np.random.SeedSequence(master_seed)
    c0, c1, c2 = root.spawn(3)
    return c0, c1, c2


def power_master_seeds(power_seed_root: int, r_max: int) -> list[int]:
    """Pre-registered algorithmic seed list for the power sweep (§5).

    ``SeedSequence(root).spawn(r_max)`` children are hashed to stable int
    master seeds written into run_config before any result is seen.
    """
    children = np.random.SeedSequence(power_seed_root).spawn(r_max)
    # Use the entropy of each SeedSequence as a stable int seed
    out: list[int] = []
    for ss in children:
        # Spawn a generator and draw one uint64 for a compact master int
        rng = np.random.default_rng(ss)
        out.append(int(rng.integers(0, 2**31 - 1)))
    return out


# Re-export for callers that need the killer-demo tree helpers
__all__ = [
    "median_demo_shell_phi",
    "van_der_waerden_xs",
    "oracle_panel_from_labels",
    "noise_shell_panel",
    "mix_factor",
    "build_injected_panel",
    "build_noise_panels",
    "spawn_power_seed_tree",
    "power_master_seeds",
    "spawn_seed_tree",
    "ar1_panel",
]


def _phi_from_any(cfg_like: Any) -> float:
    """Helper used by tests: prefer explicit shell_phi else demo median."""
    phi = getattr(cfg_like, "shell_phi", None)
    if phi is not None:
        return float(phi)
    return median_demo_shell_phi()
