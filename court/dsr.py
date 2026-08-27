"""Deflated Sharpe Ratio: expected max SR, trial dependence, and DSR.

Pure functions over arrays and scalars. DSR is PSR evaluated at the
expected-maximum-SR benchmark under the null of no skill
(``E[{SR}] = 0``).

References
----------
Bailey, D. H. & López de Prado, M. (2014). "The Deflated Sharpe Ratio:
Correcting for Selection Bias, Backtest Overfitting and Non-Normality."
*Journal of Portfolio Management*, 40(5), 94–107. Equations (1)–(2);
App. A.1 Eqs. (5)–(6); App. A.3 Eqs. (7)–(9).

Bailey, D. H. & López de Prado, M. (2012). "The Sharpe Ratio Efficient
Frontier." *Journal of Risk*, 15(2), 3–44. Eq. (11) (PSR, used by DSR).

Implementation note: ``docs/research/dsr.md`` §2.c–§2.d, §3.c–§3.d, §5.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
from scipy.stats import norm

from court.sharpe import _psr_details

# float64-nearest Euler–Mascheroni constant (spec §3.4)
EULER_MASCHERONI: float = 0.5772156649015329


class DsrResult(NamedTuple):
    """Deflated Sharpe Ratio and intermediate quantities under the null.

    Attributes
    ----------
    dsr :
        ``PSR(SR̂*)`` — probability that true SR exceeds the multiple-testing
        hurdle.
    sr_star :
        Expected-max SR benchmark under ``E[{SR}] = 0``.
    z :
        Standardized statistic inside ``Φ``.
    var_factor :
        Lo/Mertens variance factor of the selected strategy.
    """

    dsr: float
    sr_star: float
    z: float
    var_factor: float


def _require_finite(name: str, value: float) -> float:
    """Fail closed if a scalar float parameter is NaN or ±inf (spec §6)."""
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"non-finite scalar parameter {name}: got {value!r}")
    return v


def implied_independent_trials(n_trials_raw: int, avg_corr: float) -> float:
    """Implied independent trial count from equal-correlation interpolation.

    Bailey & López de Prado (2014), App. A.3 Eq. (9);
    ``docs/research/dsr.md`` §2.c:

    .. math::

        \\hat N = 1 + (M - 1)(1 - \\hat\\rho)

    Limits: ``ρ̂ → 0 ⇒ N̂ → M``; ``ρ̂ → 1 ⇒ N̂ → 1``.

    ``avg_corr`` is accepted on ``(−1, 1]``. Negative ``ρ̂`` extrapolates
    Eq. (9) to ``N̂ > M`` — a **harsher** hurdle against the candidate
    (ruling C7; paper interpolates on ``[0, 1]``, but small negative sample
    correlations are routine for noise pools).

    Raises
    ------
    ValueError
        If ``n_trials_raw < 1``, ``avg_corr`` is non-finite, or ``avg_corr``
        is outside ``(−1, 1]``.
    """
    if n_trials_raw < 1:
        raise ValueError(f"n_trials_raw < 1: got {n_trials_raw}")
    rho = _require_finite("avg_corr", avg_corr)
    if not (-1.0 < rho <= 1.0):
        raise ValueError(f"avg_corr outside (-1, 1]: got {avg_corr}")
    return 1.0 + (n_trials_raw - 1) * (1.0 - rho)


def avg_pairwise_correlation(values: np.ndarray) -> float:
    """Mean of upper-triangle pairwise Pearson correlations of a T×M matrix.

    Columns are trial return series. Used as ``ρ̂`` for
    ``implied_independent_trials`` (Bailey & López de Prado 2014, App. A.3;
    ``docs/research/dsr.md`` §3.c; ruling C6).

    Raises
    ------
    ValueError
        If ``values`` is not 2-D, ``M < 2``, ``T < 2``, any non-finite entry,
        or any column is constant (Pearson undefined).
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"values must be 2-D (T×M), got ndim={arr.ndim}")
    t_obs, n_trials = arr.shape
    if n_trials < 2:
        raise ValueError(f"M < 2 (need at least 2 trial columns): got M={n_trials}")
    if t_obs < 2:
        raise ValueError(f"T < 2 (need at least 2 observations): got T={t_obs}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("values contain non-finite entries")
    # Constant columns make Pearson undefined
    col_std = np.std(arr, axis=0, ddof=1)
    if np.any(col_std == 0.0):
        raise ValueError("constant column in correlation matrix (σ̂ = 0)")

    corr = np.corrcoef(arr, rowvar=False)
    # Upper triangle excluding diagonal
    iu = np.triu_indices(n_trials, k=1)
    return float(np.mean(corr[iu]))


def rho_is_ill_conditioned(n_obs: int, n_trials_raw: int) -> bool:
    """Whether the pairwise-correlation estimate is ill-conditioned.

    Bailey & López de Prado (2014), App. A.3 caveat;
    ``docs/research/dsr.md`` §5.3; ruling C8:

    Returns ``True`` iff ``T < ½ M(M − 1)`` (more unknown pairs than
    independent observation pairs). This is a **disclosed caveat**, not an
    error — callers record it in the verdict and never block.
    """
    return n_obs < 0.5 * n_trials_raw * (n_trials_raw - 1)


def expected_max_sr(
    sr_trials_mean: float, sr_trials_std: float, n_trials: float
) -> float:
    """Expected maximum Sharpe ratio after ``N`` independent trials.

    Bailey & López de Prado (2014), Eq. (1) / App. A.1 Eqs. (5)–(6);
    ``docs/research/dsr.md`` §2.c:

    .. math::

        \\mathbb{E}[\\max\\{\\widehat{\\mathrm{SR}}\\}]
        \\approx
        \\mathbb{E}[\\{\\widehat{\\mathrm{SR}}\\}]
        + \\sqrt{\\mathbb{V}}
          \\Bigl[
            (1-\\gamma) Z^{-1}(1-1/N)
            + \\gamma Z^{-1}(1-1/(N e))
          \\Bigr]

    **EVT approximation:** Eq. (1) is an extreme-value-theory approximation
    conditioned on ``N ≫ 1``. The paper does not give an analytic error bound
    for small ``N``; finite-sample accuracy is only checked by Monte Carlo
    (App. A.2). Implementers and callers must treat this as the paper's
    working formula, not an identity at every ``N``.

    Right-tail quantiles use the complementary survival function
    ``norm.isf(p)`` ≡ ``Z⁻¹(1 − p)`` rather than ``norm.ppf(1 − p)``, so the
    argument never materializes as ``1 − 1/N`` in float64 (dsr.md §5.5).

    Special cases (ruling C4):

    - ``N == 1``: returns ``sr_trials_mean`` exactly (max of one draw; no EVT).
    - ``sr_trials_std == 0``: returns ``sr_trials_mean`` (degenerate dispersion).
    - ``1 < N < ~1.29``: the EVT approximation dips below the mean; the result
      is clamped so the hurdle is never below ``sr_trials_mean`` (``max_z ≥ 0``).
      ``E[max]`` of ``N ≥ 1`` draws is ``≥`` the single-draw mean, so a
      multiplicity adjustment must never *lower* the bar. Without the clamp DSR
      is anti-conservative for ``N̂ ∈ (1, 2)`` (a few highly-correlated trials)
      and can certify near-zero-skill strategies (§5.5 guard; ruling C4 amended).

    ``n_trials`` is real-valued (``N̂`` from Eq. (9) is a float; ruling C5).

    Raises
    ------
    ValueError
        If any scalar float is non-finite, ``n_trials < 1``, or
        ``sr_trials_std < 0``.
    """
    mean = _require_finite("sr_trials_mean", sr_trials_mean)
    std = _require_finite("sr_trials_std", sr_trials_std)
    n = _require_finite("n_trials", n_trials)
    if n < 1.0:
        raise ValueError(f"n_trials < 1: got {n_trials}")
    if std < 0.0:
        raise ValueError(f"sr_trials_std < 0: got {sr_trials_std}")
    if n == 1.0 or std == 0.0:
        return mean

    gamma = EULER_MASCHERONI
    # Complementary tail: isf(p) = ppf(1-p) without forming 1-p (dsr.md §5.5)
    z1 = float(norm.isf(1.0 / n))
    z2 = float(norm.isf(1.0 / (n * math.e)))
    # E[max of N≥1 draws] ≥ E[{SR}] always (equality at N=1). Eq. (1) is an EVT
    # approximation valid for N≫1 and dips *below* the mean for N in (1, ~1.29);
    # clamp max_z ≥ 0 so the multiplicity hurdle can never fall below the
    # single-trial baseline. Without this the DSR deflation turns
    # anti-conservative and can certify near-zero-skill strategies — reachable
    # whenever N̂ ∈ (1, 2), i.e. a few highly-correlated trials (dsr.md §5.5,
    # which contemplates N as low as 2; ruling C4 special-cased only N==1 and
    # left the (1, 2) float band exposed).
    max_z = max((1.0 - gamma) * z1 + gamma * z2, 0.0)
    return mean + std * max_z


def dsr(
    sr_hat: float,
    n_obs: int,
    skew_hat: float,
    kurt_hat: float,
    sr_trials_std: float,
    n_trials: float,
) -> DsrResult:
    """Deflated Sharpe Ratio: PSR at the expected-max benchmark under the null.

    Bailey & López de Prado (2014), Eq. (2); ``docs/research/dsr.md`` §2.d.
    Internally sets ``SR̂* = expected_max_sr(0.0, sr_trials_std, n_trials)``
    (null ``E[{SR}] = 0``; ruling C10) and evaluates
    ``PSR(SR̂*)`` via Bailey & López de Prado (2012), Eq. (11).

    ``dsr`` and ``z`` are taken from one shared PSR computation
    (``court.sharpe._psr_details``) so they cannot desynchronize.

    All Sharpe ratios and the cross-trial std must be at **native** frequency
    (``docs/research/dsr.md`` §5.1).

    Raises
    ------
    ValueError
        If any scalar float is non-finite, or guards from ``expected_max_sr`` /
        PSR fail (``n_trials < 1``, ``sr_trials_std < 0``, ``n_obs < 2``,
        ``var_factor ≤ 0``).
    """
    # Finite checks on dsr-owned scalars; remaining floats validated in callees.
    _require_finite("sr_hat", sr_hat)
    _require_finite("skew_hat", skew_hat)
    _require_finite("kurt_hat", kurt_hat)
    _require_finite("sr_trials_std", sr_trials_std)
    _require_finite("n_trials", n_trials)

    sr_star = expected_max_sr(0.0, sr_trials_std, n_trials)
    dsr_value, z, vf = _psr_details(sr_hat, sr_star, n_obs, skew_hat, kurt_hat)
    return DsrResult(dsr=dsr_value, sr_star=sr_star, z=z, var_factor=vf)
