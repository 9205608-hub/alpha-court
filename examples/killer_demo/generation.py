"""Generation stub: pure-RNG AR(1) score panels (killer-demo.md §4).

Zero information by construction: scores never touch return data.
φ is the only operative disguise; pseudo-lookbacks are cosmetic metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from examples.killer_demo.config import (
    FAMILY_PHI,
    LIQUIDITY_LOOKBACKS,
    MOMENTUM_LOOKBACKS,
    REVERSAL_LOOKBACKS,
    VALUE_QUALITY_PROXIES,
    VARIANTS_PER_FAMILY,
    VOLATILITY_LOOKBACKS,
    DemoConfig,
)


@dataclass(frozen=True)
class FactorSpec:
    """One candidate's disclosed recipe (killer-demo.md §4.2)."""

    index: int  # 0..n_candidates-1
    family: str
    name: str
    phi: float
    pseudo_params: dict[str, Any]
    statement: str
    seed_path: tuple[int, ...]  # [0, i] under master spawn tree
    master_seed: int

    def to_ledger_spec(self) -> dict[str, Any]:
        """Full recipe disclosure for trial.spec (§4.2)."""
        return {
            "family": self.family,
            "name": self.name,
            "pseudo_params": dict(self.pseudo_params),
            "generator": {
                "kind": "ar1_noise",
                "phi": self.phi,
                "master_seed": self.master_seed,
                "seed_path": list(self.seed_path),
            },
        }


def _linear_phi(lo: float, hi: float, k: int, n: int = VARIANTS_PER_FAMILY) -> float:
    """Linear φ across n variants; k in 0..n-1."""
    if n == 1:
        return float(lo)
    return float(lo + (hi - lo) * k / (n - 1))


def _cosmetic_for(family: str, k: int) -> dict[str, Any]:
    if family == "momentum":
        return {"lookback": MOMENTUM_LOOKBACKS[k]}
    if family == "reversal":
        return {"lookback": REVERSAL_LOOKBACKS[k]}
    if family == "volatility":
        return {"lookback": VOLATILITY_LOOKBACKS[k]}
    if family == "liquidity":
        return {"lookback": LIQUIDITY_LOOKBACKS[k]}
    if family == "value_quality":
        return {"proxy": VALUE_QUALITY_PROXIES[k]}
    raise ValueError(f"unknown family {family!r}")


def _statement(family: str, cosmetic: dict[str, Any]) -> str:
    if family == "momentum":
        return f"{cosmetic['lookback']}-day price momentum predicts csi300 returns"
    if family == "reversal":
        return f"{cosmetic['lookback']}-day short-term reversal predicts csi300 returns"
    if family == "volatility":
        return f"{cosmetic['lookback']}-day realized volatility predicts csi300 returns"
    if family == "liquidity":
        return f"{cosmetic['lookback']}-day liquidity / turnover predicts csi300 returns"
    if family == "value_quality":
        return f"fundamental ratio proxy {cosmetic['proxy']!r} predicts csi300 returns"
    raise ValueError(f"unknown family {family!r}")


def _name(family: str, cosmetic: dict[str, Any], k: int) -> str:
    if family == "value_quality":
        return f"value_quality_{cosmetic['proxy']}"
    return f"{family}_lb{cosmetic['lookback']}_v{k:02d}"


def build_factor_specs(cfg: DemoConfig) -> list[FactorSpec]:
    """Build n_candidates factor specs in family order (§4.2–§4.3).

    Full menu is 5 × 20 = 100. Reduced runs take the first n_candidates in
    family-major order (momentum variants first, then reversal, …).
    """
    specs: list[FactorSpec] = []
    idx = 0
    for family in cfg.family_order:
        lo, hi = FAMILY_PHI[family]
        for k in range(VARIANTS_PER_FAMILY):
            if idx >= cfg.n_candidates:
                return specs
            cosmetic = _cosmetic_for(family, k)
            phi = _linear_phi(lo, hi, k)
            specs.append(
                FactorSpec(
                    index=idx,
                    family=family,
                    name=_name(family, cosmetic, k),
                    phi=phi,
                    pseudo_params=cosmetic,
                    statement=_statement(family, cosmetic),
                    seed_path=(0, idx),
                    master_seed=cfg.master_seed,
                )
            )
            idx += 1
    return specs


def spawn_seed_tree(master_seed: int) -> tuple[np.random.SeedSequence, np.random.SeedSequence]:
    """SeedSequence(master) → spawn(2): child0 candidates, child1 offsets (§4.4)."""
    root = np.random.SeedSequence(master_seed)
    child0, child1 = root.spawn(2)
    return child0, child1


def draw_offsets(
    offset_ss: np.random.SeedSequence,
    *,
    n_offsets: int,
    delta_min: int,
    t_len: int,
) -> list[int]:
    """Draw n_offsets unique integers from [δ_min, T−δ_min] without replacement (§5.3)."""
    low = delta_min
    high = t_len - delta_min  # inclusive upper bound per design
    if high < low:
        raise ValueError(
            f"empty offset range: delta_min={delta_min}, T={t_len} "
            f"⇒ [{low}, {high}]"
        )
    population = list(range(low, high + 1))
    if n_offsets > len(population):
        raise ValueError(
            f"n_offsets={n_offsets} exceeds population size {len(population)} "
            f"in [{low}, {high}]"
        )
    rng = np.random.default_rng(offset_ss)
    chosen = rng.choice(population, size=n_offsets, replace=False)
    # Stable list of plain Python ints (JSON / provenance)
    return [int(x) for x in chosen]


def ar1_panel(
    phi: float,
    rng: np.random.Generator,
    *,
    n_dates: int,
    n_instruments: int,
) -> np.ndarray:
    """Stationary AR(1) score panel (T, N); per-instrument independent (§4.1).

    s(0) ~ N(0,1); s(t) = φ s(t−1) + √(1−φ²) ε(t), ε ~ N(0,1) i.i.d.
    """
    if not (-1.0 < phi < 1.0):
        raise ValueError(f"phi must be in (-1, 1) for stationarity, got {phi}")
    innov_scale = float(np.sqrt(1.0 - phi * phi))
    panel = np.empty((n_dates, n_instruments), dtype=np.float64)
    panel[0] = rng.standard_normal(n_instruments)
    for t in range(1, n_dates):
        eps = rng.standard_normal(n_instruments)
        panel[t] = phi * panel[t - 1] + innov_scale * eps
    return panel


def generate_score_panels(
    specs: list[FactorSpec],
    candidate_ss: np.random.SeedSequence,
    *,
    dates: list[str],
    instruments: list[str],
) -> list[pd.DataFrame]:
    """Generate one dense AR(1) score DataFrame per factor (§4.1, §4.4).

    Factor i uses grandchild seed from candidate_ss.spawn(n)[i], reproducible
    from (master, seed_path=[0, i]) alone.
    """
    n = len(specs)
    grandchildren = candidate_ss.spawn(n)
    n_dates = len(dates)
    n_inst = len(instruments)
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    panels: list[pd.DataFrame] = []
    for i, spec in enumerate(specs):
        rng = np.random.default_rng(grandchildren[i])
        arr = ar1_panel(spec.phi, rng, n_dates=n_dates, n_instruments=n_inst)
        panels.append(pd.DataFrame(arr, index=idx, columns=instruments))
    return panels
