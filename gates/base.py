"""Minimal shared helpers for the identity and pool blades.

Only ``align`` and ``make_report`` live here. Sibling blades (magnitude,
single-year luck) must not grow this module.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def align(
    series_a_index,
    series_a_values,
    series_b_index,
    series_b_values,
) -> tuple[np.ndarray, np.ndarray]:
    """Inner-join two series on index labels, preserving ``series_a`` order.

    Duplicate labels in ``series_b`` keep the last value. Labels in ``a`` that
    are missing from ``b`` are dropped. Returns two float64 value arrays of
    equal length (possibly empty).
    """
    lookup = {label: value for label, value in zip(series_b_index, series_b_values)}
    xs: list[Any] = []
    ys: list[Any] = []
    for label, value in zip(series_a_index, series_a_values):
        if label in lookup:
            xs.append(value)
            ys.append(lookup[label])
    return (
        np.asarray(xs, dtype=np.float64),
        np.asarray(ys, dtype=np.float64),
    )


def make_report(
    blade: str,
    flagged: bool,
    statistics: dict,
    evidence: dict,
    params: dict,
) -> dict:
    """Assemble a JSON-serializable blade report (protocol keys only).

    Numpy scalars are deep-cast to Python ``int`` / ``float`` / ``bool``.
    NaN (and other non-finite floats) raise ``ValueError`` rather than being
    emitted — the harness rejects ``allow_nan=False`` failures as
    ``CertificationError``.
    """
    return {
        "blade": str(blade),
        "flagged": bool(flagged),
        "statistics": _jsonable(statistics),
        "evidence": _jsonable(evidence),
        "params": _jsonable(params),
    }


def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, int):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        value = float(obj)
        if not math.isfinite(value):
            raise ValueError("non-finite float is not allowed in blade reports")
        return value
    if isinstance(obj, dict):
        return {key: _jsonable(value) for key, value in obj.items()}
    if isinstance(obj, tuple):
        return tuple(_jsonable(value) for value in obj)
    if isinstance(obj, list):
        return [_jsonable(value) for value in obj]
    if isinstance(obj, np.ndarray):
        return _jsonable(obj.tolist())
    raise ValueError(f"unsupported type in blade report: {type(obj).__name__}")
