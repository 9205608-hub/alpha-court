"""Discriminating-only survival aggregation (killer-demo.md §6, v0.2 revision).

Thin re-export of the single harness implementation
(``harness.aggregation_policy``). The demo remains an uncertified calculator
and does not write declaration events; certified runs declare the policy via
``declare_policy`` (ticket 07).

``aggregate_sweep_rows`` stays here: it aggregates sweep-row dicts for the
§7.4 calibration appendix, not verdict records.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from harness.aggregation_policy import (
    gates_faced_passed,
    survivor_count,
    survivor_ids,
    trial_survives,
    verdicts_deciding,
)

__all__ = [
    "aggregate_sweep_rows",
    "gates_faced_passed",
    "survivor_count",
    "survivor_ids",
    "trial_survives",
    "verdicts_deciding",
]


def aggregate_sweep_rows(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-seed sweep rows into calibration frequencies (§7.4).

    Each row must include at least:
    - ``seed``: int
    - ``n_survivors``: int
    - ``accused_gate_verdicts``: mapping gate name → ``\"pass\"``|``\"reject\"``

    Returns counts and empirical pass rates per gate over the provided seeds.
    Unit-tested; the full 20-seed run is out of scope for this ticket.
    """
    rows_list = list(rows)
    n = len(rows_list)
    if n == 0:
        return {
            "n_seeds": 0,
            "mean_survivors": 0.0,
            "gate_pass_counts": {},
            "gate_pass_rates": {},
            "survivor_counts": [],
        }

    survivor_counts = [int(r["n_survivors"]) for r in rows_list]
    gate_pass_counts: dict[str, int] = {}
    for r in rows_list:
        for gate, decision in r["accused_gate_verdicts"].items():
            gate_pass_counts.setdefault(gate, 0)
            if decision == "pass":
                gate_pass_counts[gate] += 1

    gate_pass_rates = {g: c / n for g, c in gate_pass_counts.items()}
    return {
        "n_seeds": n,
        "mean_survivors": sum(survivor_counts) / n,
        "gate_pass_counts": gate_pass_counts,
        "gate_pass_rates": gate_pass_rates,
        "survivor_counts": survivor_counts,
    }
