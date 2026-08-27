"""Small pure stats helpers for power reporting (Wilson CI, annualized ICIR)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import norm


def annualized_icir(
    ic_series: np.ndarray | list[float],
    *,
    periods_per_year: float = 252.0,
) -> tuple[float, float, float]:
    """Return (mean_ic, std_ic_ddof1, annualized_icir).

    annualized ICIR = mean/std · √periods_per_year (power-calibration.md §4.2).
    """
    x = np.asarray(ic_series, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size < 2:
        raise ValueError(f"need ≥2 finite IC observations, got {x.size}")
    mean = float(np.mean(x))
    std = float(np.std(x, ddof=1))
    if std == 0.0:
        raise ValueError("IC std is zero; ICIR undefined")
    icir = mean / std * math.sqrt(periods_per_year)
    return mean, std, float(icir)


def wilson_interval(
    n_success: int,
    n_total: int,
    *,
    z: float = 1.959963984540054,  # ≈ Φ⁻¹(0.975)
) -> tuple[float, float, float]:
    """Wilson score interval for a binomial proportion.

    Returns (p_hat, lo, hi). When n_total == 0, returns (nan, nan, nan).

    Reference: Wilson (1927); used for A / B / submission-power CIs
    (power-calibration.md §5).
    """
    if n_total < 0 or n_success < 0 or n_success > n_total:
        raise ValueError(f"invalid counts: success={n_success} total={n_total}")
    if n_total == 0:
        return float("nan"), float("nan"), float("nan")
    n = float(n_total)
    p = n_success / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2.0 * n)
    margin = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return float(p), float(max(0.0, lo)), float(min(1.0, hi))


def wilson_half_width(n_success: int, n_total: int) -> float:
    """Half-width of the Wilson 95% interval (honest precision disclosure)."""
    p, lo, hi = wilson_interval(n_success, n_total)
    if math.isnan(p):
        return float("nan")
    return 0.5 * (hi - lo)


def pchip_beta_for_icir(
    beta_grid: list[float] | np.ndarray,
    mean_icir: list[float] | np.ndarray,
    target_icir: float,
    *,
    clamp: bool = True,
) -> float:
    """Solve β* for target annualized ICIR via monotone PCHIP (§4.2 step 5).

    Root-finds on the interpolant of ICIR(β). When ``clamp=True`` (default,
    main-grid calibration), extrapolates by clamping to the grid endpoints.
    When ``clamp=False`` (matched-β search, rework-02 FIX-B), raises if the
    target lies outside the observed ICIR range so the caller can expand the
    bracket instead of silently returning a boundary value.
    """
    from scipy.interpolate import PchipInterpolator

    b = np.asarray(beta_grid, dtype=np.float64)
    y = np.asarray(mean_icir, dtype=np.float64)
    if b.size != y.size or b.size < 2:
        raise ValueError("beta_grid and mean_icir need equal length ≥ 2")
    # Ensure strictly increasing β
    order = np.argsort(b)
    b = b[order]
    y = y[order]
    if target_icir <= float(y[0]):
        if not clamp:
            raise ValueError(
                f"target ICIR {target_icir} ≤ min ICIR(β)={float(y[0])} on "
                f"bracket [{float(b[0])}, {float(b[-1])}]; expand search grid"
            )
        return float(b[0]) if target_icir > 0 else 0.0
    if target_icir >= float(y[-1]):
        if not clamp:
            raise ValueError(
                f"target ICIR {target_icir} ≥ max ICIR(β)={float(y[-1])} on "
                f"bracket [{float(b[0])}, {float(b[-1])}]; expand search grid"
            )
        return float(b[-1])
    # Invert via root on f(β) = ICIR(β) − target
    interp = PchipInterpolator(b, y)

    def f(x: float) -> float:
        return float(interp(x) - target_icir)

    lo, hi = float(b[0]), float(b[-1])
    # Bisection (monotone)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if f(mid) >= 0.0:
            hi = mid
        else:
            lo = mid
    return float(0.5 * (lo + hi))


def gate_key(statistic: str, params: dict[str, Any]) -> str:
    """Stable per-gate name for TPR tables."""
    if statistic == "noise_control":
        mode = params.get("mode", "noise")
        return f"noise_{mode}"
    return statistic


# Silence unused import warning path for norm if only used externally
_ = norm
