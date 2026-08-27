"""Qlib China A-share factor evaluator adapter.

Implements the market gate in ``docs/design/adapter-interface.md`` §7.
All qlib imports live in this module; ``court/`` stays market-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ADAPTER_VERSION = "0.1.0"
COST_DECLARATION = "gross paper series — no transaction costs, no market impact"
DEFAULT_LABEL_EXPR = "Ref($close, -2)/Ref($close, -1) - 1"
DEFAULT_PROVIDER = str(Path.home() / ".qlib" / "qlib_data" / "cn_data")


@dataclass(frozen=True)
class EvalResult:
    """Single-panel evaluation result (contract §7.2 / §7.4)."""

    index: list[str]
    values: np.ndarray
    meta: dict[str, Any]


@dataclass(frozen=True)
class EvalGrid:
    """Shifted-grid evaluation result (contract §7.3 / §7.4)."""

    index: list[str]
    offsets: list[int]
    values: np.ndarray
    meta: dict[str, Any]


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = x - x.mean()
    y = y - y.mean()
    denom = np.sqrt(np.dot(x, x) * np.dot(y, y))
    if denom == 0.0:
        return float("nan")
    return float(np.dot(x, y) / denom)


def _rankdata_1d(x: np.ndarray) -> np.ndarray:
    """Average ranks, 1..n, matching pandas Spearman (stable mergesort ties)."""
    n = x.shape[0]
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    sorted_x = x[order]
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_x[j] == sorted_x[i]:
            j += 1
        avg = 0.5 * (i + 1 + j)
        ranks[order[i:j]] = avg
        i = j
    return ranks


def _rank_panel(panel: np.ndarray) -> np.ndarray:
    """Per-row average ranks on each row's own finite support; NaN stays NaN.

    Fast-path material for IC when the joint mask equals that full finite support
    (dense / no exclusion). When the joint mask drops any finite cell, the IC
    path re-ranks within the joint (contract §4.1 / §5.3).
    """
    t_len, n_inst = panel.shape
    ranks = np.full((t_len, n_inst), np.nan, dtype=np.float64)
    for t in range(t_len):
        row = panel[t]
        m = np.isfinite(row)
        if not m.any():
            continue
        ranks[t, m] = _rankdata_1d(row[m])
    return ranks


def _ranks_within_joint(
    values: np.ndarray,
    order: np.ndarray,
    joint: np.ndarray,
) -> np.ndarray:
    """Average ranks of ``values`` restricted to ``joint``, via precomputed argsort.

    Filters a full-row mergesort order down to the joint subset (O(N), no re-sort)
    so joint-then-rank Spearman matches pandas / qlib ``calc_ic`` ric (§4.1, §5.3).
    """
    selected = order[joint[order]]
    n = int(selected.shape[0])
    ranks_sel = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i + 1
        vi = values[selected[i]]
        while j < n and values[selected[j]] == vi:
            j += 1
        ranks_sel[i:j] = 0.5 * (i + 1 + j)
        i = j
    by_index = np.empty(values.shape[0], dtype=np.float64)
    by_index[selected] = ranks_sel
    return by_index[joint]


def _masked_row_pearson(
    rx: np.ndarray,
    ry: np.ndarray,
    joint: np.ndarray,
) -> np.ndarray:
    """Row-wise Pearson of rank panels on a joint mask (vectorized).

    For each date row: center on the joint mean, zero non-joint cells after
    centering, then full-width ``np.sum`` dots. Matches ``_pearson`` on the
    compacted joint vectors up to float summation order (~1e-15), within the
    oracle bar ``rtol=1e-12, atol=0``. On pure joint-rank panels (no
    zero-padding of excluded finite cells) the result is bit-identical.
    ``denom == 0.0`` yields NaN (same rule as ``_pearson``).
    """
    n = joint.sum(axis=1, keepdims=True).astype(np.float64)
    # Joint means (non-joint contribute 0 to the sum)
    mx = np.where(joint, rx, 0.0).sum(axis=1, keepdims=True) / n
    my = np.where(joint, ry, 0.0).sum(axis=1, keepdims=True) / n
    dx = np.where(joint, rx - mx, 0.0)
    dy = np.where(joint, ry - my, 0.0)
    xy = (dx * dy).sum(axis=1)
    xx = (dx * dx).sum(axis=1)
    yy = (dy * dy).sum(axis=1)
    denom = np.sqrt(xx * yy)
    out = np.empty(rx.shape[0], dtype=np.float64)
    zero = denom == 0.0
    out[zero] = np.nan
    nz = ~zero
    out[nz] = xy[nz] / denom[nz]
    return out


def _masked_avg_ranks(values: np.ndarray, joint: np.ndarray) -> np.ndarray:
    """Average ranks (1..m) of ``values`` within each row's joint mask.

    Vectorized across rows; matches ``_ranks_within_joint`` (stable mergesort
    tie order). Non-joint positions receive ranks among the full row width after
    masking excluded cells to +inf (ignored by ``_masked_row_pearson``).
    """
    _t_len, n_inst = values.shape
    # Push non-joint to the end of a stable ascending sort
    x_sort = np.where(joint, values, np.inf)
    order = np.argsort(x_sort, axis=1, kind="stable")
    x_sorted = np.take_along_axis(x_sort, order, axis=1)
    pos = np.broadcast_to(np.arange(n_inst, dtype=np.intp), x_sort.shape)
    same = np.zeros(x_sort.shape, dtype=bool)
    same[:, 1:] = x_sorted[:, 1:] == x_sorted[:, :-1]
    grp_start = np.maximum.accumulate(np.where(~same, pos, -1), axis=1)
    is_end = np.zeros(x_sort.shape, dtype=bool)
    is_end[:, :-1] = x_sorted[:, 1:] != x_sorted[:, :-1]
    is_end[:, -1] = True
    grp_end = np.minimum.accumulate(np.where(is_end, pos, n_inst)[:, ::-1], axis=1)[
        :, ::-1
    ]
    # 1-indexed average ordinal rank (matches _ranks_within_joint / pandas)
    ranks_sorted = 0.5 * (grp_start + grp_end) + 1.0
    ranks = np.empty(values.shape, dtype=np.float64)
    np.put_along_axis(ranks, order, ranks_sorted, axis=1)
    return ranks


def _shared_kernel(
    scores: np.ndarray,
    labels: np.ndarray,
    pit_mask: np.ndarray,
    *,
    metric: str,
    quantile: float,
    min_cross_section: int,
    offsets: list[int],
) -> np.ndarray:
    """One shared evaluation kernel for ``evaluate`` and ``evaluate_shifted``.

    Contract §7.3: both entry points route here so the equivalence invariant holds
    by construction. Shape: scores/labels/pit_mask are (T, N); returns
    float array (n_offsets, T) of finite values (raises if any day fails).

    IC semantics (§4.1 / §5.3): Spearman ranks are computed **within** the
    per-date joint mask (PIT ∧ score-finite ∧ label-finite), matching qlib
    ``calc_ic`` ric. Implemented as a unified vectorized masked-rank path
    (``_masked_avg_ranks`` + ``_masked_row_pearson``) per offset — no Python
    loop over dates. When scores are fully finite the joint is offset-independent
    and label ranks are reused across offsets.
    """
    if metric not in ("ic", "returns"):
        raise ValueError(f"metric must be 'ic' or 'returns', got {metric!r}")
    t_len, n_inst = scores.shape
    if labels.shape != scores.shape or pit_mask.shape != scores.shape:
        raise ValueError("scores, labels, and pit_mask must share shape (T, N)")

    score_finite = np.isfinite(scores)
    label_finite = np.isfinite(labels)
    out = np.empty((len(offsets), t_len), dtype=np.float64)

    if metric == "ic":
        # Offset-independent base: PIT ∧ label-finite
        base_ok = pit_mask & label_finite
        t_idx = np.arange(t_len)
        # Dense scores ⇒ joint == base_ok for every offset; rank labels once
        scores_dense = bool(score_finite.all())
        label_ranks_cached: np.ndarray | None = None
        if scores_dense:
            n_cs0 = base_ok.sum(axis=1)
            if (n_cs0 < min_cross_section).any():
                t = int(np.flatnonzero(n_cs0 < min_cross_section)[0])
                raise ValueError(
                    f"min_cross_section violated on evaluation date index {t}: "
                    f"usable cross-section {int(n_cs0[t])} < {min_cross_section}"
                )
            label_ranks_cached = _masked_avg_ranks(labels, base_ok)

        for oi, delta in enumerate(offsets):
            src = (t_idx - delta) % t_len
            sc = scores[src]
            if scores_dense:
                joint = base_ok
                ry = label_ranks_cached
            else:
                joint = base_ok & score_finite[src]
                n_cs = joint.sum(axis=1)
                if (n_cs < min_cross_section).any():
                    t = int(np.flatnonzero(n_cs < min_cross_section)[0])
                    raise ValueError(
                        f"min_cross_section violated on evaluation date index {t}: "
                        f"usable cross-section {int(n_cs[t])} < {min_cross_section}"
                    )
                ry = _masked_avg_ranks(labels, joint)
            rx = _masked_avg_ranks(sc, joint)
            vals = _masked_row_pearson(rx, ry, joint)
            bad = ~np.isfinite(vals)
            if bad.any():
                t = int(np.flatnonzero(bad)[0])
                raise ValueError(
                    f"non-finite ic on evaluation date index {t} "
                    f"(zero variance or degenerate cross-section)"
                )
            out[oi] = vals
        return out

    # metric == "returns": precompute nlargest/nsmallest order per score row
    score_order_asc = np.argsort(scores, axis=1, kind="mergesort")
    score_order_desc = np.empty_like(score_order_asc)
    pos = np.arange(n_inst)
    for t in range(t_len):
        score_order_desc[t] = np.lexsort((pos, -scores[t]))

    for oi, delta in enumerate(offsets):
        src = (np.arange(t_len) - delta) % t_len
        for t in range(t_len):
            s = int(src[t])
            joint = pit_mask[t] & score_finite[s] & label_finite[t]
            n_cs = int(joint.sum())
            if n_cs < min_cross_section:
                raise ValueError(
                    f"min_cross_section violated on evaluation date index {t}: "
                    f"usable cross-section {n_cs} < {min_cross_section}"
                )
            val = _long_short_from_orders(
                labels[t],
                joint,
                score_order_desc[s],
                score_order_asc[s],
                quantile,
            )
            if not np.isfinite(val):
                raise ValueError(
                    f"non-finite returns on evaluation date index {t} "
                    f"(zero variance or degenerate cross-section)"
                )
            out[oi, t] = val
    return out


def _long_short_from_orders(
    label: np.ndarray,
    joint: np.ndarray,
    order_desc: np.ndarray,
    order_asc: np.ndarray,
    quantile: float,
) -> float:
    """Equal-weight top/bottom quantile long-short (r_long - r_short) / 2.

    Matches ``qlib.contrib.eva.alpha.calc_long_short_return`` after pairwise
    finite + PIT filtering (contract §4.1, §5.3). Uses precomputed sort orders.
    """
    n = int(joint.sum())
    k = int(n * quantile)
    if k < 1:
        raise ValueError(f"quantile {quantile} yields empty long/short leg for n={n}")
    long_idx = order_desc[joint[order_desc]][:k]
    short_idx = order_asc[joint[order_asc]][:k]
    r_long = float(label[long_idx].mean())
    r_short = float(label[short_idx].mean())
    return (r_long - r_short) / 2.0


def _require_str(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"config.{name} must be str, got {type(value).__name__}")
    return value


def _require_float(name: str, value: Any) -> float:
    # Strict: real float only (reject str, bool, int coercion/repair — §7.1).
    if type(value) is not float:
        raise TypeError(f"config.{name} must be float, got {type(value).__name__}")
    return value


def _require_int(name: str, value: Any) -> int:
    # Strict: real int only (reject bool, float truncation — §7.1 no-repair).
    if type(value) is not int:
        raise TypeError(f"config.{name} must be int, got {type(value).__name__}")
    return value


def _normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate config fields with fail-closed types (contract §7.1, no repair)."""
    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    if "window" not in config:
        raise ValueError("config.window is required ({start, end})")
    if "declared_data_tag" not in config:
        raise ValueError("config.declared_data_tag is required")
    window = config["window"]
    if not isinstance(window, dict) or "start" not in window or "end" not in window:
        raise ValueError("config.window must be {start, end}")
    start = _require_str("window.start", window["start"])
    end = _require_str("window.end", window["end"])
    provider_uri = (
        DEFAULT_PROVIDER
        if "provider_uri" not in config
        else _require_str("provider_uri", config["provider_uri"])
    )
    universe = (
        "csi300" if "universe" not in config else _require_str("universe", config["universe"])
    )
    label_expr = (
        DEFAULT_LABEL_EXPR
        if "label_expr" not in config
        else _require_str("label_expr", config["label_expr"])
    )
    quantile = 0.2 if "quantile" not in config else _require_float("quantile", config["quantile"])
    min_cs = (
        50
        if "min_cross_section" not in config
        else _require_int("min_cross_section", config["min_cross_section"])
    )
    declared = _require_str("declared_data_tag", config["declared_data_tag"])
    return {
        "provider_uri": provider_uri,
        "universe": universe,
        "window": {"start": start, "end": end},
        "label_expr": label_expr,
        "quantile": quantile,
        "min_cross_section": min_cs,
        "declared_data_tag": declared,
    }


def _iso_dates(index: pd.DatetimeIndex | pd.Index) -> list[str]:
    return [pd.Timestamp(ts).strftime("%Y-%m-%d") for ts in index]


def _evaluation_dates_from_calendar(
    calendar: list[pd.Timestamp],
    start: str,
    end: str,
) -> list[pd.Timestamp]:
    """Evaluation dates per contract §5.2."""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    cal = sorted(pd.Timestamp(c) for c in calendar)
    cal_set = set(cal)
    # map each date to its position for t+1 / t+2 lookups on the full calendar
    pos = {d: i for i, d in enumerate(cal)}
    out: list[pd.Timestamp] = []
    for d in cal:
        if d < start_ts or d > end_ts:
            continue
        i = pos[d]
        if i + 2 >= len(cal):
            continue
        t1, t2 = cal[i + 1], cal[i + 2]
        if t1 not in cal_set or t2 not in cal_set:
            continue
        if t2 > end_ts:
            continue
        out.append(d)
    return out


def _build_pit_mask(
    instruments: list[str],
    eval_dates: list[pd.Timestamp],
    membership: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]],
) -> np.ndarray:
    """Boolean (T, N) mask: instrument is a PIT member on that evaluation date."""
    t_len = len(eval_dates)
    n = len(instruments)
    mask = np.zeros((t_len, n), dtype=bool)
    for j, inst in enumerate(instruments):
        spans = membership.get(inst, [])
        for i, d in enumerate(eval_dates):
            for a, b in spans:
                if a <= d <= b:
                    mask[i, j] = True
                    break
    return mask


class QlibCNFactorEvaluator:
    """Factor score panel → RankIC / long-short return series (contract §7.1).

    Construction loads the label panel and PIT membership once; evaluations are
    pure numpy thereafter via :func:`_shared_kernel`.
    """

    def _finalize(
        self,
        *,
        cfg: dict[str, Any],
        synthetic: bool,
        qlib_version: str,
        eval_dates: list[pd.Timestamp],
        instruments: list[str],
        labels: np.ndarray,
        pit_mask: np.ndarray,
        calendar_end: str,
    ) -> None:
        """Set EVERY instance attribute, for both constructor paths.

        ``__init__`` and ``from_panels`` used to hand-copy the attribute list
        and silently diverged (``_n_instruments_measured``: PIT-active count
        vs. total columns — v0.2-12 slice E). Derived attributes are computed
        here so a future attribute has exactly one home.
        """
        self._cfg = cfg
        self._synthetic = synthetic
        self._qlib_version = qlib_version
        self._eval_dates = list(eval_dates)
        self._eval_index = _iso_dates(self._eval_dates)
        self._instruments = instruments
        self._labels = labels
        self._pit_mask = pit_mask
        self._calendar_end = calendar_end
        self._n_instruments_measured = int(self._pit_mask.any(axis=0).sum())

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize qlib (kernels=1), load labels + PIT (contract §7.1)."""
        cfg = _normalize_config(config)

        import qlib
        from qlib.constant import REG_CN
        from qlib.data import D

        qlib.init(
            provider_uri=cfg["provider_uri"],
            region=REG_CN,
            kernels=1,
        )
        qlib_version = getattr(qlib, "__version__", "unknown")

        start, end = cfg["window"]["start"], cfg["window"]["end"]
        full_cal = [pd.Timestamp(c) for c in D.calendar()]
        eval_dates = _evaluation_dates_from_calendar(full_cal, start, end)
        if not eval_dates:
            raise ValueError(
                f"no evaluation dates in window [{start}, {end}] "
                "(need room for t+1 and t+2 within the window; contract §5.2)"
            )

        inst_cfg = D.instruments(cfg["universe"])
        membership_raw = D.list_instruments(
            inst_cfg,
            start_time=start,
            end_time=end,
            as_list=False,
        )
        instruments = sorted(membership_raw.keys())
        if not instruments:
            raise ValueError(f"no instruments for universe {cfg['universe']!r}")

        membership: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = {}
        for inst, spans in membership_raw.items():
            membership[inst] = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in spans]

        # Load labels over the window; restrict rows to evaluation dates.
        # Window end already admits t+2 for every eval date (§5.2); no end extension.
        label_df = D.features(
            instruments,
            [cfg["label_expr"]],
            start_time=start,
            end_time=end,
        )
        label_df = label_df.copy()
        label_df.columns = ["label"]
        # qlib MultiIndex is (instrument, datetime) or (datetime, instrument);
        # unstack instrument either way yields date × instrument.
        panel = label_df["label"].unstack(level="instrument")
        panel.index = pd.DatetimeIndex(pd.to_datetime(panel.index)).normalize()
        panel = panel.reindex(columns=instruments)
        panel = panel.reindex(pd.DatetimeIndex(eval_dates))

        self._finalize(
            cfg=cfg,
            synthetic=False,
            qlib_version=qlib_version,
            eval_dates=list(eval_dates),
            instruments=instruments,
            labels=panel.to_numpy(dtype=np.float64),
            pit_mask=_build_pit_mask(instruments, eval_dates, membership),
            calendar_end=pd.Timestamp(full_cal[-1]).strftime("%Y-%m-%d"),
        )

    @classmethod
    def from_panels(
        cls,
        label_panel: pd.DataFrame,
        config: dict[str, Any],
        *,
        pit_mask: np.ndarray | None = None,
    ) -> QlibCNFactorEvaluator:
        """Build an evaluator from an in-memory label panel (tests / synthetic).

        Not part of the public §7 construction path for production demos; used so
        oracle, equivalence, and determinism tests run without the data pack.
        """
        cfg = _normalize_config(config)
        if not isinstance(label_panel.index, pd.DatetimeIndex):
            label_panel = label_panel.copy()
            label_panel.index = pd.DatetimeIndex(label_panel.index)
        instruments = sorted(str(c) for c in label_panel.columns)
        label_panel = label_panel.reindex(columns=instruments)
        eval_dates = [pd.Timestamp(d).normalize() for d in label_panel.index]
        labels = label_panel.to_numpy(dtype=np.float64)
        t_len, n = labels.shape
        if pit_mask is None:
            mask = np.ones((t_len, n), dtype=bool)
        else:
            if pit_mask.shape != (t_len, n):
                raise ValueError("pit_mask shape must match label panel")
            mask = pit_mask.astype(bool, copy=False)
        eval_index = _iso_dates(eval_dates)
        obj = object.__new__(cls)
        obj._finalize(
            cfg=cfg,
            synthetic=True,
            qlib_version="synthetic",
            eval_dates=eval_dates,
            instruments=instruments,
            labels=labels,
            pit_mask=mask,
            calendar_end=eval_index[-1] if eval_index else "",
        )
        return obj

    @property
    def evaluation_dates(self) -> list[str]:
        """ISO evaluation-date labels (contract §5.2 / §3)."""
        return list(self._eval_index)

    @property
    def instruments(self) -> list[str]:
        """Lexicographically sorted instrument columns used by the kernel."""
        return list(self._instruments)

    @property
    def labels(self) -> np.ndarray:
        """Forward-return label panel the evaluator scores against (§7.1).

        Shape (T, N), float64, rows aligned to :attr:`evaluation_dates` and
        columns to :attr:`instruments`; NaN where no label exists. Returns a
        defensive copy so callers (e.g. the power-calibration oracle,
        ``docs/design/power-calibration.md`` §4.1) cannot mutate kernel state.
        """
        return self._labels.copy()

    def _meta(self, metric: str) -> dict[str, Any]:
        """Build §7.4 metadata plus meta.config (every constructor field, §7.1)."""
        cfg = {
            "provider_uri": self._cfg["provider_uri"],
            "universe": self._cfg["universe"],
            "window": dict(self._cfg["window"]),
            "label_expr": self._cfg["label_expr"],
            "quantile": self._cfg["quantile"],
            "min_cross_section": self._cfg["min_cross_section"],
            "declared_data_tag": self._cfg["declared_data_tag"],
        }
        return {
            "metric": metric,
            "metric_params": {"quantile": self._cfg["quantile"]}
            if metric == "returns"
            else {},
            "label_expr": self._cfg["label_expr"],
            "price_field": "$close",
            "universe": self._cfg["universe"],
            "window": dict(self._cfg["window"]),
            "n_evaluation_dates": len(self._eval_index),
            "cost_declaration": COST_DECLARATION,
            "data_version": {
                "declared_tag": self._cfg["declared_data_tag"],
                "calendar_end": self._calendar_end,
                "n_instruments": self._n_instruments_measured,
            },
            "qlib_version": self._qlib_version,
            "adapter_version": ADAPTER_VERSION,
            "config": cfg,
        }

    def _align_scores(self, scores: pd.DataFrame) -> np.ndarray:
        """Align score panel to evaluation dates × instruments; fail closed."""
        if not isinstance(scores, pd.DataFrame):
            raise TypeError("scores must be a pandas DataFrame")
        if not isinstance(scores.index, pd.DatetimeIndex):
            try:
                scores = scores.copy()
                scores.index = pd.DatetimeIndex(scores.index)
            except Exception as exc:  # noqa: BLE001 — re-raise as contract error
                raise TypeError("scores index must be DatetimeIndex") from exc

        scores = scores.sort_index()
        # Canonical instrument order; extra cols ignored, missing cols → NaN (§7.2)
        scores = scores.reindex(columns=self._instruments)

        expected = pd.DatetimeIndex(self._eval_dates)
        # require a row for every evaluation date
        score_idx = pd.DatetimeIndex(pd.to_datetime(scores.index)).normalize()
        scores = scores.copy()
        scores.index = score_idx
        missing = expected.difference(scores.index)
        if len(missing) > 0:
            miss = [pd.Timestamp(m).strftime("%Y-%m-%d") for m in missing[:5]]
            raise ValueError(
                f"scores missing evaluation-date rows (contract §7.2): {miss}"
                + ("..." if len(missing) > 5 else "")
            )
        aligned = scores.reindex(expected)
        return aligned.to_numpy(dtype=np.float64)

    def _validate_offsets(self, offsets: list[int]) -> list[int]:
        t_len = len(self._eval_index)
        if len(offsets) == 0:
            raise ValueError("offsets must be a non-empty list (contract §7.3 erratum)")
        out: list[int] = []
        for d in offsets:
            if not isinstance(d, (int, np.integer)) or isinstance(d, bool):
                raise TypeError(f"offset must be int, got {type(d).__name__}")
            di = int(d)
            # Contract §7.3 erratum (2026-07-11): validate 0 ≤ δ < T (δ=0 allowed).
            if di < 0 or di >= t_len:
                raise ValueError(
                    f"offset δ={di} out of range: require 0 <= δ < T={t_len} "
                    "(contract §7.3 erratum 2026-07-11)"
                )
            out.append(di)
        return out

    def evaluate(self, scores: pd.DataFrame, metric: str) -> EvalResult:
        """Evaluate one score panel → series (contract §7.2).

        ``scores`` must contain a row for every evaluation date (missing rows
        raise). Rows whose dates fall outside the evaluation-date set are
        ignored by definition — only the evaluation-date sub-panel is used.
        Extra instrument columns are ignored; missing instruments become NaN
        and are pairwise-excluded (§5.3).

        Routes through the shared kernel with offset ``[0]`` so
        ``evaluate_shifted(S, m, [0])`` matches bit-for-bit (§7.3).
        """
        score_arr = self._align_scores(scores)
        values = _shared_kernel(
            score_arr,
            self._labels,
            self._pit_mask,
            metric=metric,
            quantile=self._cfg["quantile"],
            min_cross_section=self._cfg["min_cross_section"],
            offsets=[0],
        )
        return EvalResult(
            index=list(self._eval_index),
            values=values[0].copy(),
            meta=self._meta(metric),
        )

    def evaluate_shifted(
        self,
        scores: pd.DataFrame,
        metric: str,
        offsets: list[int],
    ) -> EvalGrid:
        """Circular time-shift grid over offsets (contract §7.3, noise-control §3.1).

        Label panel is never shifted. Offsets are caller-supplied; the adapter
        draws nothing. Shared kernel with ``evaluate`` for bit-equal δ paths.
        """
        if not isinstance(offsets, (list, tuple)):
            raise TypeError("offsets must be a list of ints")
        offs = self._validate_offsets(list(offsets))
        score_arr = self._align_scores(scores)
        values = _shared_kernel(
            score_arr,
            self._labels,
            self._pit_mask,
            metric=metric,
            quantile=self._cfg["quantile"],
            min_cross_section=self._cfg["min_cross_section"],
            offsets=offs,
        )
        return EvalGrid(
            index=list(self._eval_index),
            offsets=list(offs),
            values=values.copy(),
            meta=self._meta(metric),
        )
