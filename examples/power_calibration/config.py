"""Pinned power-calibration constants (power-calibration.md §4–§5).

Frozen before any power run. Do not retune after seeing results.
Amendments require a design-doc changelog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Seed roots (power-calibration.md §4.2, §5)
# ---------------------------------------------------------------------------
# Calibration root is book-pinned; must not collide with killer-demo sweep
# reserve 20260710–20260730 (audit revision 2026-07-12).
CALIBRATION_SEED_ROOT = 320260711
CALIBRATION_K = 64

# Power-sweep root: outside killer-demo reserve and distinct from calibration.
# Algorithmic sequence: SeedSequence(POWER_SEED_ROOT).spawn(R_MAX)[i] is seed i.
POWER_SEED_ROOT = 420260711
R0 = 40
R_MAX = 120
N_WON_TARGET = 20

# ---------------------------------------------------------------------------
# Calibration β grid and strength targets (§4.2–§4.3)
# ---------------------------------------------------------------------------
# Re-centered 2026-07-17 after the first real csi300 calibration: the oracle is a
# near-perfect predictor (RankIC≈1 with the forward return), so at csi300's daily
# IC vol (~0.058) even β=0.02 yields annualized ICIR≈4.4 — overshooting the whole
# transition band (2.0–3.6). The grid is shifted DOWN ~10× (floor 0.02→0.002) so
# the transition/low bands resolve to distinct β*<0.02. Pre-registration amendment,
# made from the calibration ICIR(β) curve BEFORE any power/sweep result (book §4.2).
CALIBRATION_BETA_GRID: tuple[float, ...] = tuple(
    round(0.002 + 0.002 * i, 3) for i in range(15)
)  # 0.002, 0.004, …, 0.030

# Annualized ICIR targets (project ICIR = daily · √252). Optional 8.0 is a hook.
STRENGTH_GRID_LOW: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5)
STRENGTH_GRID_TRANSITION: tuple[float, ...] = (
    2.0,
    2.3,
    2.6,
    2.9,
    3.2,
    3.6,
    4.0,
    4.5,
    5.0,
)
STRENGTH_GRID_UPPER: tuple[float, ...] = (6.0,)
# Transition band that may adaptively re-seed (§5)
TRANSITION_ADAPTIVE_BAND: tuple[float, float] = (2.0, 3.6)

FROZEN_STRENGTH_GRID: tuple[float, ...] = (
    STRENGTH_GRID_LOW + STRENGTH_GRID_TRANSITION + STRENGTH_GRID_UPPER
)

# ---------------------------------------------------------------------------
# Window / battery defaults (mirror killer-demo; direction=greater)
# ---------------------------------------------------------------------------
TARGET_T = 480
N_SPLITS = 16  # real-data; reduced tests use small n_splits (e.g. 4)
PERIODS_PER_YEAR = 252.0
UNIVERSE = "csi300"
METRIC = "ic"
DECLARED_DATA_TAG = "2026-07-05"
LABEL_EXPR = "Ref($close, -2)/Ref($close, -1) - 1"
COST_DECLARATION = "gross paper series — no transaction costs, no market impact"
DIRECTION = "greater"

N_NOISE = 99  # + 1 injected = N=100
N_CANDIDATES = N_NOISE + 1
B_OFFSETS = 199
DELTA_MIN = 60

FDR_Q = 0.05
DSR_CONFIDENCE = 0.95
PBO_PHI_THRESHOLD = 0.2
NOISE_ALPHA = 0.05
RANKING_STAT = "t_iid"  # directed t under greater (NOT abs_t_iid)
NOISE_RECIPE = "circular_shift"

AGGREGATION_POLICY_ID = "unanimous-discriminating-v1"

# First-screen honesty (§1 + §4.3 unit footnote)
CLAIM_SCOPE = (
    "UNCERTIFIED calibration experiment (direct court, not harness.run). "
    "Constructed oracle ≠ discoverable alpha: the injected factor peeks at the "
    "forward return by construction (power-calibration.md §1). This measures "
    "discrimination (TPR for approximately-stationary mean-IC signals), not "
    "discovery. No costs, no capacity, no regime realism."
)
UNIT_FOOTNOTE = (
    "Axis unit: project-annualized ICIR = ICIR_daily · √252 ≈ ICIR_daily × 16. "
    "Industry 'ICIR ≈ 0.3–0.8' is usually the daily non-annualized ratio → "
    "project annualized ≈ 5–13."
)

DEFAULT_OUT_DIR = "examples/power_calibration/out"


@dataclass
class PowerConfig:
    """Runtime configuration for one power run (full or reduced for tests).

    Full-run defaults match power-calibration.md pre-registration. Tests shrink
    n_noise / n_offsets / n_splits / target_t / R0 / strength grid for speed.
    """

    # Seeds / replication
    calibration_seed_root: int = CALIBRATION_SEED_ROOT
    calibration_k: int = CALIBRATION_K
    power_seed_root: int = POWER_SEED_ROOT
    r0: int = R0
    r_max: int = R_MAX
    n_won_target: int = N_WON_TARGET

    # Pool / window / battery
    n_noise: int = N_NOISE
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
    out_dir: str = DEFAULT_OUT_DIR
    skip_download: bool = False

    # Strengths / calibration
    strength_grid: tuple[float, ...] = FROZEN_STRENGTH_GRID
    calibration_beta_grid: tuple[float, ...] = CALIBRATION_BETA_GRID
    # Frozen φ (median of 100 demo shells); set at calibration if None
    shell_phi: float | None = None
    # Frozen β* table: target_icir -> beta (set by calibrate before sweep)
    beta_star: dict[float, float] = field(default_factory=dict)

    # Window / synthetic
    window: dict[str, str] | None = None
    synthetic: dict[str, Any] | None = None

    # Adaptive band
    adaptive_band: tuple[float, float] = TRANSITION_ADAPTIVE_BAND

    # Appendix hooks (β_t matched-ICIR targets)
    beta_t_icir_targets: tuple[float, ...] = (4.0, 3.0)
    run_beta_t_appendix: bool = True

    @property
    def n_candidates(self) -> int:
        return self.n_noise + 1

    def offset_high(self) -> int:
        """Inclusive upper bound for offset draw: T − δ_min."""
        return self.target_t - self.delta_min

    def in_adaptive_band(self, strength: float) -> bool:
        lo, hi = self.adaptive_band
        return lo <= strength <= hi
