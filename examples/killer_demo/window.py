"""Evaluation-window arithmetic (killer-demo.md §3, §5.2).

Pins T = 480 evaluation dates (16 × 30) so PBO's T % S == 0 constraint is
absorbed by the window, not the statistic.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from adapters.qlib_cn import _evaluation_dates_from_calendar
from examples.killer_demo.config import (
    PROVISIONAL_WINDOW_START,
    TARGET_T,
)


def load_day_calendar(provider_uri: str | Path) -> list[pd.Timestamp]:
    """Load qlib day calendar from ``calendars/day.txt`` under the data pack."""
    path = Path(provider_uri) / "calendars" / "day.txt"
    if not path.is_file():
        raise FileNotFoundError(f"calendar not found: {path}")
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [pd.Timestamp(ln) for ln in lines]


def evaluation_dates_for_window(
    calendar: list[pd.Timestamp],
    start: str,
    end: str,
) -> list[pd.Timestamp]:
    """Adapter evaluation-date rule (adapter-interface.md §5.2)."""
    return _evaluation_dates_from_calendar(calendar, start, end)


def choose_window_for_t(
    calendar: list[pd.Timestamp],
    *,
    target_t: int = TARGET_T,
    provisional_start: str = PROVISIONAL_WINDOW_START,
    provisional_end: str | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Pick declared window yielding exactly ``target_t`` evaluation dates (§3).

    Takes the most recent ``target_t`` evaluation dates under a provisional
    window ending at the pack calendar end (or ``provisional_end``), then sets
    ``start`` to the first of those dates so the adapter returns exactly them.

    Returns
    -------
    window :
        ``{start, end}`` ISO date strings for adapter config / declared protocol.
    eval_iso :
        The ``target_t`` evaluation-date ISO labels.
    """
    if target_t <= 0:
        raise ValueError(f"target_t must be positive, got {target_t}")

    end = provisional_end
    if end is None:
        end = pd.Timestamp(calendar[-1]).strftime("%Y-%m-%d")

    all_eval = evaluation_dates_for_window(calendar, provisional_start, end)
    if len(all_eval) < target_t:
        raise ValueError(
            f"only {len(all_eval)} evaluation dates in "
            f"[{provisional_start}, {end}]; need target_t={target_t}"
        )

    selected = all_eval[-target_t:]
    start = pd.Timestamp(selected[0]).strftime("%Y-%m-%d")
    # Re-check: with this start/end the adapter must yield exactly selected.
    check = evaluation_dates_for_window(calendar, start, end)
    if len(check) != target_t:
        raise RuntimeError(
            f"window arithmetic failed: expected {target_t} eval dates, "
            f"got {len(check)} for window [{start}, {end}]"
        )
    if [pd.Timestamp(d) for d in check] != list(selected):
        raise RuntimeError(
            "window arithmetic failed: selected eval dates do not match "
            f"adapter rule for window [{start}, {end}]"
        )

    eval_iso = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in selected]
    return {"start": start, "end": end}, eval_iso


def assert_window_constraints(t_len: int, n_splits: int) -> None:
    """Fail closed if T is wrong or not divisible by S (killer-demo.md §5.2)."""
    if t_len <= 0:
        raise ValueError(f"T must be positive, got {t_len}")
    if t_len % n_splits != 0:
        raise ValueError(
            f"T={t_len} is not divisible by n_splits={n_splits} "
            "(PBO requires T % S == 0; absorb in the window)"
        )
