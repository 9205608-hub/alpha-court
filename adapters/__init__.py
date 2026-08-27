"""Data and backtest adapters (qlib China data first).

The only layer allowed to know about markets. Optional qlib support lives here,
not in the court kernel.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "COST_DECLARATION",
    "EvalGrid",
    "EvalResult",
    "QlibCNFactorEvaluator",
]


def __getattr__(name: str) -> Any:
    """Lazy-export qlib_cn symbols so ``import adapters`` stays qlib-free."""
    if name in __all__:
        from adapters import qlib_cn

        return getattr(qlib_cn, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
