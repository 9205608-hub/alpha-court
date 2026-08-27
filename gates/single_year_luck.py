"""Single-year luck blade: concentration of series contribution across opaque blocks.

Flag ⇔ LOBO_min ≤ 0 OR HHI-p < p_min. Thresholds are constructor inputs (never
hard-coded); joint null calibration lives in ``scripts/blade_calibration_syl.py``.

References
----------
- Herfindahl, O. C. (1950), *Concentration in the Steel Industry*, Ph.D.
  dissertation, Columbia University — Herfindahl–Hirschman index (HHI) of
  concentration over absolute block contributions.
- Hirschman, A. O. (1945), *National Power and the Structure of Foreign Trade*,
  University of California Press — precursor concentration index.
- Phipson, B. & Smyth, G. K. (2010), "Permutation P-values Should Never Be Zero",
  *Statistical Applications in Genetics and Molecular Biology* 9(1), Article 39,
  Eq. (2) — add-one estimator ``(1 + #{perm HHI ≥ observed}) / (1 + n_perm)``.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _hhi(contrib: np.ndarray) -> float | None:
    """HHI of absolute contributions; None when Σ|C_b| = 0 (undefined)."""
    abs_c = np.abs(contrib, dtype=np.float64)
    denom = float(abs_c.sum())
    if denom == 0.0:
        return None
    shares = abs_c / denom
    return float(np.dot(shares, shares))


def _permutation_hhis(
    values: np.ndarray,
    blocks: np.ndarray,
    labels: np.ndarray,
    n_perm: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """HHI under random reassignment of values to blocks (label permutation)."""
    n = int(values.size)
    tiled = np.empty((n_perm, n), dtype=blocks.dtype)
    tiled[:] = blocks
    perm = rng.permuted(tiled, axis=1)
    n_lab = int(labels.size)
    contribs = np.empty((n_perm, n_lab), dtype=np.float64)
    for j, lab in enumerate(labels):
        contribs[:, j] = (perm == lab) @ values
    abs_c = np.abs(contribs)
    denom = abs_c.sum(axis=1)
    out = np.full(n_perm, np.nan, dtype=np.float64)
    ok = denom > 0.0
    shares = abs_c[ok] / denom[ok, None]
    out[ok] = np.einsum("ij,ij->i", shares, shares)
    return out


class SingleYearLuckBlade:
    """Leave-one-block-out sign check OR HHI concentration permutation test.

    Blocks are adapter-supplied opaque integer labels (never parsed as dates).
    """

    name = "single_year_luck"

    def __init__(
        self,
        p_min: float,
        n_perm: int = 2000,
        seed: int = 0,
        min_blocks: int = 2,
    ) -> None:
        p = float(p_min)
        if not (0.0 < p < 1.0):
            raise ValueError(f"p_min must be in (0, 1), got {p_min!r}")
        n = int(n_perm)
        if n < 100:
            raise ValueError(f"n_perm must be >= 100, got {n_perm!r}")
        self._p_min = p
        self._n_perm = n
        self._seed = int(seed)
        self._min_blocks = int(min_blocks)

    def _params(self) -> dict[str, Any]:
        return {
            "p_min": float(self._p_min),
            "n_perm": int(self._n_perm),
            "seed": int(self._seed),
            "min_blocks": int(self._min_blocks),
        }

    def _unevaluable(self, culprit: str, n_obs: int | None = None) -> dict[str, Any]:
        statistics: dict[str, Any] = {}
        if n_obs is not None:
            statistics["n_obs"] = int(n_obs)
        return {
            "blade": self.name,
            "flagged": False,
            "statistics": statistics,
            "evidence": {"evaluable": False, "culprit": culprit},
            "params": self._params(),
        }

    def run(
        self,
        trial_id: str,
        spec: dict,
        params: dict,
        declared: Any,
        series: Any,
    ) -> dict[str, Any]:
        """Evaluate one trial series; never raises on trial-input problems."""
        del trial_id, spec, declared
        values = np.asarray(getattr(series, "values", ()), dtype=np.float64).reshape(-1)
        n_obs = int(values.size)

        if not isinstance(params, dict) or "blocks" not in params:
            return self._unevaluable("missing blocks", n_obs)

        try:
            blocks = np.asarray(params["blocks"], dtype=np.int64)
        except (TypeError, ValueError):
            return self._unevaluable("length mismatch", n_obs)
        if blocks.ndim != 1 or int(blocks.size) != n_obs:
            return self._unevaluable("length mismatch", n_obs)

        labels = np.unique(blocks)
        n_blocks = int(labels.size)
        if n_blocks < self._min_blocks:
            return self._unevaluable("fewer than min_blocks distinct labels", n_obs)

        contrib = np.array(
            [float(values[blocks == lab].sum()) for lab in labels],
            dtype=np.float64,
        )
        total = float(contrib.sum())
        lobo_vals = total - contrib
        argmin_idx = int(np.argmin(lobo_vals))
        lobo_min = float(lobo_vals[argmin_idx])
        lobo_argmin = int(labels[argmin_idx])
        contributions = {str(int(lab)): float(c) for lab, c in zip(labels, contrib, strict=True)}

        hhi = _hhi(contrib)
        hhi_p: float | None
        if hhi is None:
            hhi_p = None
            flagged = False
            evidence: dict[str, Any] = {
                "evaluable": True,
                "degenerate": True,
                "culprit": "sum of absolute contributions is 0",
            }
        else:
            rng = np.random.default_rng(self._seed)
            perm_hhi = _permutation_hhis(values, blocks, labels, self._n_perm, rng)
            n_ge = int(np.sum((~np.isnan(perm_hhi)) & (perm_hhi >= hhi)))
            hhi_p = float((1 + n_ge) / (1 + self._n_perm))
            lobo_hit = bool(lobo_min <= 0.0)
            hhi_hit = bool(hhi_p < self._p_min)
            flagged = bool(lobo_hit or hhi_hit)
            evidence = {
                "evaluable": True,
                "lobo_argmin": lobo_argmin,
                "lobo_triggered": lobo_hit,
                "hhi_triggered": hhi_hit,
            }

        return {
            "blade": self.name,
            "flagged": flagged,
            "statistics": {
                "contributions": contributions,
                "total": total,
                "lobo_min": lobo_min,
                "lobo_argmin": lobo_argmin,
                "hhi": hhi,
                "hhi_p": hhi_p,
                "n_blocks": n_blocks,
                "n_obs": n_obs,
                "n_perm": int(self._n_perm),
            },
            "evidence": evidence,
            "params": self._params(),
        }
