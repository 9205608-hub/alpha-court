"""Pool-redundancy blade: max |Pearson| and |Spearman| vs pool members.

Lag 0 only (no lag family). Both measures are always reported so a monotone
nonlinear clone can still flag when Pearson is moderate. Separate from
identity-degeneracy so attribution can tell "reinvented a reference" from
"duplicate of an already-pooled candidate".

References
----------
Pearson, K. (1895). "Notes on regression and inheritance in the case of two
parents." *Proceedings of the Royal Society of London*, 58, 240–242.
Implemented via :func:`scipy.stats.pearsonr`.

Spearman, C. (1904). "The proof and measurement of association between
two things." *American Journal of Psychology*, 15(1), 72–101.
Implemented via :func:`scipy.stats.spearmanr`.
"""

from __future__ import annotations

from typing import Any

from scipy.stats import pearsonr, spearmanr

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


class PoolRedundancyBlade:
    """Flag a candidate whose lag-0 correlation with a pool member is too high."""

    name = "pool_redundancy"

    def __init__(
        self,
        pool: dict[str, tuple[tuple[str, ...], tuple[float, ...]]],
        rho_pool: float,
        min_overlap: int = 30,
    ) -> None:
        if not pool:
            raise ValueError("pool must be non-empty")
        self.pool = pool
        self.rho_pool = _require_open_unit_interval(rho_pool, "rho_pool")
        self.min_overlap = min_overlap

    def run(
        self,
        trial_id: str,
        spec: dict,
        params: dict,
        declared: Any,
        series: Any,
    ) -> dict:
        pearson_hits: list[tuple[float, str, int]] = []
        spearman_hits: list[tuple[float, str, int]] = []
        n_skipped_overlap = 0
        n_skipped_degenerate = 0
        for member, (p_index, p_values) in self.pool.items():
            x_al, p_al = align(series.index, series.values, p_index, p_values)
            overlap = int(x_al.size)
            if overlap < self.min_overlap:
                n_skipped_overlap += 1
                continue
            if _is_constant(x_al) or _is_constant(p_al):
                n_skipped_degenerate += 1
                continue
            pearson_stat = float(pearsonr(x_al, p_al).statistic)
            spearman_stat = float(spearmanr(x_al, p_al).statistic)
            if pearson_stat != pearson_stat or spearman_stat != spearman_stat:
                n_skipped_degenerate += 1
                continue
            pearson_hits.append((abs(pearson_stat), member, overlap))
            spearman_hits.append((abs(spearman_stat), member, overlap))

        params_out = {
            "rho_pool": self.rho_pool,
            "min_overlap": self.min_overlap,
            "n_pool": len(self.pool),
        }
        evidence: dict[str, Any] = {
            "n_skipped_insufficient_overlap": n_skipped_overlap,
            "n_skipped_degenerate": n_skipped_degenerate,
        }
        if not pearson_hits:
            evidence["reason"] = (
                "all pool members skipped (insufficient overlap or degenerate series)"
            )
            statistics = {
                "max_abs_pearson": None,
                "max_abs_spearman": None,
                "top5_abs_pearson": [],
                "top5_abs_spearman": [],
                "n_members_evaluated": 0,
            }
            return make_report(self.name, False, statistics, evidence, params_out)

        pearson_hits.sort(key=lambda row: row[0], reverse=True)
        spearman_hits.sort(key=lambda row: row[0], reverse=True)
        max_pearson, argmax_p, overlap_p = pearson_hits[0]
        max_spearman, argmax_s, overlap_s = spearman_hits[0]
        evidence["argmax_pearson_member"] = argmax_p
        evidence["argmax_spearman_member"] = argmax_s
        evidence["overlap_at_argmax_pearson"] = overlap_p
        evidence["overlap_at_argmax_spearman"] = overlap_s
        statistics = {
            "max_abs_pearson": max_pearson,
            "max_abs_spearman": max_spearman,
            "top5_abs_pearson": [(name, rho) for rho, name, _ in pearson_hits[:5]],
            "top5_abs_spearman": [(name, rho) for rho, name, _ in spearman_hits[:5]],
            "n_members_evaluated": len(pearson_hits),
        }
        flagged = max(max_pearson, max_spearman) >= self.rho_pool
        return make_report(self.name, flagged, statistics, evidence, params_out)
