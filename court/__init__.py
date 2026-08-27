"""Statistical court kernel: trial ledger and deflation/overfitting statistics.

Market-agnostic by iron law. Runtime dependencies are limited to numpy, pandas,
and scipy; this package must not import market-specific adapters or libraries.
"""

from __future__ import annotations

__version__ = "0.1.0.dev0"

from court.dsr import (
    EULER_MASCHERONI,
    DsrResult,
    avg_pairwise_correlation,
    dsr,
    expected_max_sr,
    implied_independent_trials,
    rho_is_ill_conditioned,
)
from court.fdr import FdrResult, fdr_bh, fdr_by, harmonic_number
from court.judge import Application, Judgment, judge
from court.ledger import (
    DeclarationRecord,
    DeclaredProtocol,
    HypothesisRecord,
    Ledger,
    LedgerCorruptionError,
    SealRecord,
    SeConvention,
    Series,
    TrialRecord,
    VerdictRecord,
    Window,
)
from court.noise import NoiseResult, empirical_null_p
from court.pbo import PboResult, pbo_cscv
from court.sharpe import (
    SeriesMoments,
    annualized_sr,
    psr,
    series_moments,
    sharpe_ratio,
    sr_standard_error,
    sr_var_factor,
)
from court.tstats import TStatResult, p_from_t, t_stat

__all__ = [
    "__version__",
    # ledger
    "Ledger",
    "LedgerCorruptionError",
    "SeConvention",
    "Window",
    "DeclaredProtocol",
    "Series",
    "HypothesisRecord",
    "TrialRecord",
    "VerdictRecord",
    "DeclarationRecord",
    "SealRecord",
    # sharpe
    "SeriesMoments",
    "series_moments",
    "sharpe_ratio",
    "sr_var_factor",
    "sr_standard_error",
    "psr",
    "annualized_sr",
    # dsr
    "EULER_MASCHERONI",
    "DsrResult",
    "implied_independent_trials",
    "avg_pairwise_correlation",
    "rho_is_ill_conditioned",
    "expected_max_sr",
    "dsr",
    # pbo
    "PboResult",
    "pbo_cscv",
    # tstats
    "TStatResult",
    "t_stat",
    "p_from_t",
    # fdr
    "FdrResult",
    "harmonic_number",
    "fdr_bh",
    "fdr_by",
    # noise
    "NoiseResult",
    "empirical_null_p",
    # judge
    "Application",
    "Judgment",
    "judge",
]
