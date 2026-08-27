"""Pinned demo constants (killer-demo.md pre-registration; §4–§7).

Do not retune after seeing results. Amendments require a design-doc changelog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Master seed and sweep list — killer-demo.md §4.4, §7.1, §7.4
DEFAULT_MASTER_SEED = 20260710
SWEEP_SEEDS: tuple[int, ...] = tuple(range(20260711, 20260731))

# Window / battery — §5.2, §5.4
TARGET_T = 480
N_SPLITS = 16  # S; require T % S == 0
PERIODS_PER_YEAR = 252.0
UNIVERSE = "csi300"
METRIC = "ic"
DECLARED_DATA_TAG = "2026-07-05"
LABEL_EXPR = "Ref($close, -2)/Ref($close, -1) - 1"
COST_DECLARATION = "gross paper series — no transaction costs, no market impact"

# Candidate menu — §4.2
N_CANDIDATES = 100
N_FAMILIES = 5
VARIANTS_PER_FAMILY = 20

# Offset grid — §5.3; noise-control.md §3.3, §5
B_OFFSETS = 199
DELTA_MIN = 60  # δ_min; draw from [δ_min, T - δ_min] inclusive

# Decision lines — §5.4
FDR_Q = 0.05
DSR_CONFIDENCE = 0.95
PBO_PHI_THRESHOLD = 0.2
NOISE_ALPHA = 0.05
RANKING_STAT = "abs_t_iid"
NOISE_RECIPE = "circular_shift"

# Family φ menus (linear across 20 variants) — §4.2
FAMILY_PHI: dict[str, tuple[float, float]] = {
    "momentum": (0.90, 0.97),
    "reversal": (0.20, 0.60),
    "volatility": (0.95, 0.99),
    "liquidity": (0.97, 0.995),
    "value_quality": (0.995, 0.999),
}

FAMILY_ORDER: tuple[str, ...] = (
    "momentum",
    "reversal",
    "volatility",
    "liquidity",
    "value_quality",
)

# Cosmetic lookbacks / proxies — §4.2 (do not reach the generator)
MOMENTUM_LOOKBACKS = tuple(range(5, 101, 5))  # 5..100
REVERSAL_LOOKBACKS = tuple(range(1, 21))  # 1..20
VOLATILITY_LOOKBACKS = tuple(range(10, 201, 10))  # 10..200
LIQUIDITY_LOOKBACKS = tuple(range(10, 201, 10))  # 10..200
VALUE_QUALITY_PROXIES: tuple[str, ...] = (
    "pe_ttm",
    "pb",
    "ps_ttm",
    "pcf_ttm",
    "ev_ebitda",
    "roe",
    "roa",
    "roic",
    "gross_margin",
    "net_margin",
    "asset_turnover",
    "current_ratio",
    "debt_to_equity",
    "interest_coverage",
    "fcf_yield",
    "dividend_yield",
    "earnings_yield",
    "book_to_market",
    "sales_to_price",
    "cash_to_price",
)

# Default calendar span used to locate the most recent TARGET_T eval dates — §3
PROVISIONAL_WINDOW_START = "2020-01-01"
PROVISIONAL_WINDOW_END = "2026-07-03"

DATA_DOWNLOAD_URL = (
    f"https://github.com/chenditc/investment_data/releases/download/"
    f"{DECLARED_DATA_TAG}/qlib_bin.tar.gz"
)


@dataclass
class DemoConfig:
    """Runtime configuration for one demo run (full or reduced for tests).

    Full-run defaults match killer-demo.md pre-registration. Tests may shrink
    n_candidates / n_offsets / n_splits / target_t for speed while preserving
    mechanism invariants (seed tree, aggregation, window % S).
    """

    master_seed: int = DEFAULT_MASTER_SEED
    n_candidates: int = N_CANDIDATES
    n_offsets: int = B_OFFSETS
    delta_min: int = DELTA_MIN
    target_t: int = TARGET_T
    n_splits: int = N_SPLITS
    fdr_q: float = FDR_Q
    dsr_confidence: float = DSR_CONFIDENCE
    pbo_phi_threshold: float = PBO_PHI_THRESHOLD
    noise_alpha: float = NOISE_ALPHA
    periods_per_year: float = PERIODS_PER_YEAR
    universe: str = UNIVERSE
    metric: str = METRIC
    declared_data_tag: str = DECLARED_DATA_TAG
    label_expr: str = LABEL_EXPR
    min_cross_section: int = 50
    provider_uri: str | None = None
    out_dir: str = "examples/killer_demo/out"
    skip_download: bool = False
    # Optional override of declared window; if None, computed for target_t.
    window: dict[str, str] | None = None
    # When set, use synthetic from_panels path (tests only).
    synthetic: dict[str, Any] | None = None
    # Family subset for reduced runs (default: full menu, first n_candidates).
    family_order: tuple[str, ...] = field(default_factory=lambda: FAMILY_ORDER)

    def offset_high(self) -> int:
        """Inclusive upper bound for offset draw: T - δ_min (killer-demo.md §5.3)."""
        return self.target_t - self.delta_min
