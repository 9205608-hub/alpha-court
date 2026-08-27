"""Cheap pre-screening checks ("cheap knives").

v0.3 blades in this package: ``identity_degeneracy`` and ``pool_redundancy``.
Thresholds (``rho_max``, ``rho_pool``) are constructor inputs owned by
pre-registered calibration — never hard-coded in the blades.
"""

from __future__ import annotations

from gates.identity_degeneracy import IdentityDegeneracyBlade
from gates.pool_redundancy import PoolRedundancyBlade

__all__ = [
    "IdentityDegeneracyBlade",
    "PoolRedundancyBlade",
]
