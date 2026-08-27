"""Sharpe-ratio estimator, moments, standard error, and Probabilistic Sharpe Ratio.

All quantities are at the **native** frequency of the return series.
Annualization (`annualized_sr`) is display-only and must not feed PSR/DSR.

References
----------
Bailey, D. H. & López de Prado, M. (2012). "The Sharpe Ratio Efficient Frontier."
*Journal of Risk*, 15(2), 3–44. Equations (4)–(5), (8), (11); §2.5.

Bailey, D. H. & López de Prado, M. (2014). "The Deflated Sharpe Ratio..."
*Journal of Portfolio Management*, 40(5), 94–107. (DSR uses PSR from this module.)

Implementation note: ``docs/research/dsr.md`` §2.a–§2.b, §3.a–§3.b, §5.1.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
from scipy.stats import kurtosis, norm, skew


class SeriesMoments(NamedTuple):
    """Sample moments of an excess-return series at native frequency.

    Attributes
    ----------
    n_obs :
        Observation count ``n``.
    mu_hat :
        Sample mean.
    sigma_hat :
        Sample standard deviation with Bessel correction (``n - 1``).
    sr_hat :
        Native-frequency Sharpe ratio ``mu_hat / sigma_hat``.
    skew_hat :
        Population (biased) sample skewness ``γ̂₃``.
    kurt_hat :
        Population (biased) **raw** kurtosis ``γ̂₄`` (Normal → 3.0).
    """

    n_obs: int
    mu_hat: float
    sigma_hat: float
    sr_hat: float
    skew_hat: float
    kurt_hat: float


def _require_finite(name: str, value: float) -> float:
    """Fail closed if a scalar float parameter is NaN or ±inf (spec §6)."""
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"non-finite scalar parameter {name}: got {value!r}")
    return v


def _as_1d_float_array(values: object) -> np.ndarray:
    """Coerce to 1-D float64; reject non-finite entries and non-1-D shapes."""
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"values must be 1-D, got shape {arr.shape}")
    if arr.size < 2:
        raise ValueError(f"n_obs < 2: need at least 2 observations, got {arr.size}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("values contain non-finite entries")
    return arr


def series_moments(values: object) -> SeriesMoments:
    """Estimate mean, Bessel σ, SR, skewness, and raw kurtosis.

    Formulas (Bailey & López de Prado 2012, §2 / Eqs. (4)–(11) context;
    ``docs/research/dsr.md`` §2.a):

    - ``μ̂ = mean(r)``
    - ``σ̂`` with Bessel ``n − 1``
    - ``SR̂ = μ̂ / σ̂`` at native frequency
    - ``γ̂₃``: ``scipy.stats.skew(x, bias=True)`` (ruling C1)
    - ``γ̂₄``: ``scipy.stats.kurtosis(x, fisher=False, bias=True)`` (raw; Normal → 3)

    Raises
    ------
    ValueError
        If ``n_obs < 2``, any non-finite value, or ``σ̂ == 0``.
    """
    arr = _as_1d_float_array(values)
    n_obs = int(arr.size)
    mu_hat = float(np.mean(arr))
    sigma_hat = float(np.std(arr, ddof=1))
    if sigma_hat == 0.0:
        raise ValueError("sigma_hat == 0: Sharpe ratio undefined")
    sr_hat = mu_hat / sigma_hat
    skew_hat = float(skew(arr, bias=True))
    kurt_hat = float(kurtosis(arr, fisher=False, bias=True))
    return SeriesMoments(
        n_obs=n_obs,
        mu_hat=mu_hat,
        sigma_hat=sigma_hat,
        sr_hat=sr_hat,
        skew_hat=skew_hat,
        kurt_hat=kurt_hat,
    )


def sharpe_ratio(values: object) -> float:
    """Native-frequency Sharpe ratio ``μ̂ / σ̂`` (Bessel σ̂).

    Bailey & López de Prado (2012), §2; ``docs/research/dsr.md`` §2.a.

    Lean path: mean and Bessel std only (no skew/kurtosis). Bit-identical to
    the SR̂ field of the full-moments helper; PBO-CSCV uses this as its metric.

    Raises
    ------
    ValueError
        If ``n_obs < 2``, non-finite values, or ``σ̂ == 0``.
    """
    arr = _as_1d_float_array(values)
    mu_hat = float(np.mean(arr))
    sigma_hat = float(np.std(arr, ddof=1))
    if sigma_hat == 0.0:
        raise ValueError("sigma_hat == 0: Sharpe ratio undefined")
    return mu_hat / sigma_hat


def sr_var_factor(sr_hat: float, skew_hat: float, kurt_hat: float) -> float:
    """Lo/Mertens variance factor of the SR estimator (collapsed form).

    .. math::

        1 - \\hat\\gamma_3 \\widehat{\\mathrm{SR}}
          + \\frac{\\hat\\gamma_4 - 1}{4}\\widehat{\\mathrm{SR}}^2

    Algebraically identical to the expanded Bailey & López de Prado (2012)
    Eq. (8) form
    ``1 + ½ SR² − γ₃ SR + (γ₄−3)/4 SR²`` (see ``docs/research/dsr.md`` §2.a).
    Under Normal moments (``γ₃=0``, ``γ₄=3``) recovers Lo's ``1 + SR²/2``.

    Parameters use **raw** kurtosis (Normal → 3.0). Does not raise on
    non-positive factor; callers that need a real SE (`sr_standard_error`,
    `psr`) enforce ``var_factor > 0``.

    Raises
    ------
    ValueError
        If any scalar float parameter is non-finite (NaN/±inf).
    """
    sr = _require_finite("sr_hat", sr_hat)
    g3 = _require_finite("skew_hat", skew_hat)
    g4 = _require_finite("kurt_hat", kurt_hat)
    return float(1.0 - g3 * sr + ((g4 - 1.0) / 4.0) * (sr * sr))


def _psr_details(
    sr_hat: float,
    sr_benchmark: float,
    n_obs: int,
    skew_hat: float,
    kurt_hat: float,
) -> tuple[float, float, float]:
    """Shared PSR path: return ``(psr_value, z, var_factor)``.

    Single derivation of the standardized statistic and its CDF
    (Bailey & López de Prado 2012, Eq. (11)). Used by ``psr`` and
    ``court.dsr.dsr`` so reported ``z`` and probability stay synchronized.
    """
    _require_finite("sr_hat", sr_hat)
    _require_finite("sr_benchmark", sr_benchmark)
    _require_finite("skew_hat", skew_hat)
    _require_finite("kurt_hat", kurt_hat)
    if n_obs < 2:
        raise ValueError(f"n_obs < 2: got {n_obs}")
    vf = sr_var_factor(sr_hat, skew_hat, kurt_hat)
    if vf <= 0.0:
        raise ValueError(f"var_factor <= 0: got {vf}")
    z = (float(sr_hat) - float(sr_benchmark)) * math.sqrt(n_obs - 1) / math.sqrt(vf)
    return float(norm.cdf(z)), float(z), float(vf)


def sr_standard_error(
    sr_hat: float, n_obs: int, skew_hat: float, kurt_hat: float
) -> float:
    """Estimated standard error of ``SR̂`` with Bessel ``n − 1``.

    Bailey & López de Prado (2012), §2.5 (after Eq. (8));
    ``docs/research/dsr.md`` §2.a:

    .. math::

        \\hat\\sigma_{\\widehat{\\mathrm{SR}}}
        = \\sqrt{\\mathrm{var\\_factor} / (n - 1)}

    Raises
    ------
    ValueError
        If any scalar float is non-finite, ``n_obs < 2``, or variance factor ``≤ 0``.
    """
    _require_finite("sr_hat", sr_hat)
    _require_finite("skew_hat", skew_hat)
    _require_finite("kurt_hat", kurt_hat)
    if n_obs < 2:
        raise ValueError(f"n_obs < 2: got {n_obs}")
    vf = sr_var_factor(sr_hat, skew_hat, kurt_hat)
    if vf <= 0.0:
        raise ValueError(f"var_factor <= 0: got {vf}")
    return math.sqrt(vf / (n_obs - 1))


def psr(
    sr_hat: float,
    sr_benchmark: float,
    n_obs: int,
    skew_hat: float,
    kurt_hat: float,
) -> float:
    """Probabilistic Sharpe Ratio: ``Φ((SR̂ − SR*) √(n−1) / √var_factor)``.

    Bailey & López de Prado (2012), Eq. (11); ``docs/research/dsr.md`` §2.b.
    Inputs must share the **native** frequency of the return series
    (``docs/research/dsr.md`` §5.1).

    Raises
    ------
    ValueError
        If any scalar float is non-finite, ``n_obs < 2``, or variance factor ``≤ 0``.
    """
    psr_value, _z, _vf = _psr_details(sr_hat, sr_benchmark, n_obs, skew_hat, kurt_hat)
    return psr_value


def annualized_sr(sr_hat: float, periods_per_year: float) -> float:
    """Annualized Sharpe ratio ``√q · SR̂`` — **display only**.

    Bailey & López de Prado (2012), Eq. (5); ``docs/research/dsr.md`` §5.1.
    Do **not** feed this value into ``psr``, ``dsr``, or related formulas
    without converting every other input to the same frequency.

    Raises
    ------
    ValueError
        If any scalar float is non-finite, or ``periods_per_year <= 0``.
    """
    sr = _require_finite("sr_hat", sr_hat)
    q = _require_finite("periods_per_year", periods_per_year)
    if q <= 0.0:
        raise ValueError(f"periods_per_year <= 0: got {periods_per_year}")
    return math.sqrt(q) * sr
