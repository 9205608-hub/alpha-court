"""Identity-degeneracy blade: max |Spearman| of a candidate vs lagged refs.

Transform family ``T = {lag k': |k'| <= K}`` (identity is ``k' = 0``).
Negate and rank are omitted: they are redundant under |Spearman|.

A positive lag ``k'`` compares ``candidate[t]`` with ``ref[t - k']`` after
the two series have been inner-joined on index labels (values shifted
against aligned positions; non-overlapping ends dropped).

References
----------
Spearman, C. (1904). "The proof and measurement of association between
two things." *American Journal of Psychology*, 15(1), 72–101.

Implemented via :func:`scipy.stats.spearmanr`.
"""

from __future__ import annotations

from typing import Any

from scipy.stats import spearmanr

from gates.base import align, make_report


def _require_open_unit_interval(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a float in (0, 1), got {value!r}")
    out = float(value)
    if not (0.0 < out < 1.0):
        raise ValueError(f"{name} must be in (0, 1), got {value!r}")
    return out


def _is_constant(arr) -> bool:
    return arr.size == 0 or bool(arr.max() == arr.min())


def _shift_lag(x, r, lag: int):
    """Shift *values* against aligned positions; drop non-overlapping ends."""
    if lag == 0:
        return x, r
    if lag > 0:
        return x[lag:], r[:-lag]
    return x[:lag], r[-lag:]


class IdentityDegeneracyBlade:
    """Flag a candidate that is a lagged copy (or rank-monotone transform) of a ref."""

    name = "identity_degeneracy"

    def __init__(
        self,
        refs: dict[str, tuple[tuple[str, ...], tuple[float, ...]]],
        rho_max: float,
        k: int = 5,
        min_overlap: int = 30,
    ) -> None:
        if not refs:
            raise ValueError("refs must be non-empty")
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError(f"k must be an int >= 1, got {k!r}")
        self.refs = refs
        self.rho_max = _require_open_unit_interval(rho_max, "rho_max")
        self.k = k
        self.min_overlap = min_overlap

    def run(
        self,
        trial_id: str,
        spec: dict,
        params: dict,
        declared: Any,
        series: Any,
    ) -> dict:
        hits: list[tuple[float, str, int, int]] = []
        n_skipped_overlap = 0
        n_skipped_degenerate = 0
        for ref_name, (ref_index, ref_values) in self.refs.items():
            x_al, r_al = align(series.index, series.values, ref_index, ref_values)
            for lag in range(-self.k, self.k + 1):
                x_lag, r_lag = _shift_lag(x_al, r_al, lag)
                overlap = int(x_lag.size)
                if overlap < self.min_overlap:
                    n_skipped_overlap += 1
                    continue
                if _is_constant(x_lag) or _is_constant(r_lag):
                    n_skipped_degenerate += 1
                    continue
                rho = float(spearmanr(x_lag, r_lag).statistic)
                if rho != rho:
                    n_skipped_degenerate += 1
                    continue
                hits.append((abs(rho), ref_name, lag, overlap))

        n_effective = len(self.refs) * (2 * self.k + 1)
        params_out = {
            "rho_max": self.rho_max,
            "k": self.k,
            "min_overlap": self.min_overlap,
            "n_refs": len(self.refs),
        }
        evidence: dict[str, Any] = {
            "n_skipped_insufficient_overlap": n_skipped_overlap,
            "n_skipped_degenerate": n_skipped_degenerate,
        }
        if not hits:
            evidence["reason"] = (
                "all ref/lag pairs skipped (insufficient overlap or degenerate series)"
            )
            statistics = {
                "max_abs_spearman": None,
                "second_max_abs_spearman": None,
                "argmax_ref": None,
                "argmax_lag": None,
                "n_pairs_evaluated": 0,
                "n_effective_hypotheses": n_effective,
            }
            return make_report(self.name, False, statistics, evidence, params_out)

        hits.sort(key=lambda row: row[0], reverse=True)
        max_rho, argmax_ref, argmax_lag, overlap = hits[0]
        second = hits[1][0] if len(hits) > 1 else None
        evidence["overlap_at_argmax"] = overlap
        statistics = {
            "max_abs_spearman": max_rho,
            "second_max_abs_spearman": second,
            "argmax_ref": argmax_ref,
            "argmax_lag": argmax_lag,
            "n_pairs_evaluated": len(hits),
            "n_effective_hypotheses": n_effective,
        }
        flagged = max_rho >= self.rho_max
        return make_report(self.name, flagged, statistics, evidence, params_out)
