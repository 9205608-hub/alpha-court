"""Magnitude vs turnover: a pure economic-floor blade.

net(c) = r_gross − c · tau, with tau the declared per-period one-sided
turnover fraction and c a cost per unit turnover (same period units as
returns). The blade reports break-even c* = mean_gross / tau and a cost-grid
table of net means. Flag condition: E[net] ≤ 0 at the spec-declared c_ref.

Statistical significance is out of scope by design (blades-design-draft-v2
§2.3): no t-stats, no p-values. Significance belongs to the battery's
FDR/noise gates.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

_NAME = "magnitude_vs_turnover"
_DEFAULT_GRID = (0.0, 0.0005, 0.001, 0.002, 0.005)


def _is_real(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_cost_grid(cost_grid: tuple[float, ...]) -> tuple[float, ...]:
    if not cost_grid:
        raise ValueError("cost_grid must be non-empty")
    out: list[float] = []
    prev: float | None = None
    for c in cost_grid:
        if not _is_real(c) or not math.isfinite(float(c)):
            raise ValueError(f"cost_grid entries must be finite numbers, got {c!r}")
        v = float(c)
        if v < 0.0:
            raise ValueError(f"cost_grid entries must be >= 0, got {v}")
        if prev is not None and not (v > prev):
            raise ValueError("cost_grid must be strictly increasing")
        out.append(v)
        prev = v
    return tuple(out)


def _lookup_c_ref(spec: Any) -> Any:
    if not isinstance(spec, dict):
        return None
    blades = spec.get("blades", {})
    if not isinstance(blades, dict):
        return None
    cfg = blades.get(_NAME, {})
    if not isinstance(cfg, dict):
        return None
    return cfg.get("c_ref")


def _parse_scalar(
    value: Any, *, name: str, allow_negative: bool
) -> tuple[float | None, str | None]:
    if value is None:
        return None, f"{name} is missing"
    if not _is_real(value):
        return None, f"{name} is non-numeric"
    x = float(value)
    if not math.isfinite(x):
        return None, f"{name} is non-numeric"
    if not allow_negative and x < 0.0:
        return None, f"{name} is negative"
    return x, None


class MagnitudeVsTurnoverBlade:
    """Pure economic-floor blade: does gross mean survive turnover at c_ref?

    Formula: net(c) = mean(r_gross) − c · tau. Flag iff E[net] ≤ 0 at the
    spec-declared reference cost c_ref. Break-even c* = mean_gross / tau
    (None when tau == 0: a zero-turnover candidate is never cost-killed).

    Significance (t-stats, p-values) is out of scope by design (§2.3).
    """

    name = _NAME

    def __init__(self, cost_grid: tuple[float, ...] = _DEFAULT_GRID) -> None:
        self.cost_grid = _validate_cost_grid(tuple(cost_grid))

    def run(
        self,
        trial_id: str,
        spec: dict,
        params: dict,
        declared: Any,
        series: Any,
    ) -> dict:
        del trial_id, declared
        reasons: list[str] = []

        tau_raw = params.get("turnover") if isinstance(params, dict) else None
        tau, tau_err = _parse_scalar(tau_raw, name="turnover", allow_negative=False)
        if tau_err is not None:
            reasons.append(tau_err)

        c_ref, c_err = _parse_scalar(
            _lookup_c_ref(spec), name="c_ref", allow_negative=True
        )
        if c_err is not None:
            reasons.append(c_err)

        arr = np.asarray(getattr(series, "values", ()), dtype=np.float64).reshape(-1)
        n_obs = int(arr.size)
        if n_obs == 0:
            reasons.append("series is empty (n_obs == 0)")
        elif not bool(np.all(np.isfinite(arr))):
            reasons.append("series contains non-finite values")

        params_out = {"cost_grid": [float(c) for c in self.cost_grid]}
        if reasons:
            return {
                "blade": self.name,
                "flagged": False,
                "statistics": {
                    "evaluable": False,
                    "mean_gross": None,
                    "n_obs": n_obs,
                    "turnover": tau,
                    "c_ref": c_ref,
                    "net_mean_grid": None,
                    "break_even_c": None,
                    "net_at_c_ref": None,
                },
                "evidence": {"reasons": reasons},
                "params": params_out,
            }

        assert tau is not None and c_ref is not None
        mean_gross = float(np.mean(arr))
        net_mean_grid = [[float(c), float(mean_gross - c * tau)] for c in self.cost_grid]
        net_at_c_ref = float(mean_gross - c_ref * tau)
        if tau == 0.0:
            break_even_c = None
            flagged = False
            evidence: dict[str, Any] = {
                "note": (
                    "zero-turnover candidate is never cost-killed; "
                    "break_even_c is None"
                )
            }
        else:
            break_even_c = float(mean_gross / tau)
            flagged = net_at_c_ref <= 0.0
            evidence = {}

        return {
            "blade": self.name,
            "flagged": flagged,
            "statistics": {
                "evaluable": True,
                "mean_gross": mean_gross,
                "n_obs": n_obs,
                "turnover": tau,
                "c_ref": c_ref,
                "net_mean_grid": net_mean_grid,
                "break_even_c": break_even_c,
                "net_at_c_ref": net_at_c_ref,
            },
            "evidence": evidence,
            "params": params_out,
        }
