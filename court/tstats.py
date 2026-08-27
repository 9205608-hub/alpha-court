"""t-statistic and p-value from t (standard normal asymptotics).

Formulas:
  iid SE: se = σ̂(Bessel)/√T  (bhy.md §4.1)
  Newey-West SE: Bartlett LRV with γ̂ℓ = (1/T) autocovariances;
    se = √(LRV/T)  (Newey & West 1987; bhy.md §4.3; ruling E3)
  p-values: two-sided 2(1−Φ(|t|)); greater 1−Φ(t); less Φ(t)
    (HLZ 2016 §3.5 fn 26; bhy.md §4.2; ruling E1)

Citations: Newey & West (1987); Harvey, Liu & Zhu (2016) §3.4 opening /
§3.5 footnote 26; docs/research/bhy.md §4.1–§4.3; court-kernel-spec.md §5.4.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from scipy.stats import norm


class TStatResult(NamedTuple):
    t: float
    mean: float
    se: float
    n_obs: int


def t_stat(
    values,
    se_kind: str = "iid",
    lags: int | None = None,
) -> TStatResult:
    """One-sample t-statistic of a mean series with declared SE convention.

    Parameters
    ----------
    values :
        1-D sequence of floats (IC or returns).
    se_kind :
        ``"iid"`` → se = σ̂(Bessel)/√T;
        ``"newey_west"`` → Newey-West Bartlett HAC (requires ``lags``).
    lags :
        Lag truncation L for Newey-West. Required when se_kind is
        ``"newey_west"``; forbidden when se_kind is ``"iid"``.

    Returns
    -------
    TStatResult
        t = mean / se, plus mean, se, n_obs.

    Raises
    ------
    ValueError
        n_obs < 2; non-finite values; se == 0; unknown se_kind; newey_west
        without valid lags; lags supplied with iid.

    Notes
    -----
    Newey-West LRV (Newey & West 1987; bhy.md §4.3; ruling E3)::

        γ̂_ℓ = (1/T) Σ_{t=1}^{T-ℓ} (x_t − x̄)(x_{t+ℓ} − x̄)
        LRV = γ̂_0 + 2 Σ_{ℓ=1..L} (1 − ℓ/(L+1)) γ̂_ℓ
        se  = √(LRV / T)

    iid SE uses Bessel sample standard deviation (ruling E3 / C1).
    """
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1:
        raise ValueError("values must be a 1-D array or sequence")
    n_obs = int(x.size)
    if n_obs < 2:
        raise ValueError(f"n_obs < 2 (got n_obs={n_obs})")
    if not np.all(np.isfinite(x)):
        raise ValueError("values contain non-finite entries")

    if se_kind == "iid":
        if lags is not None:
            raise ValueError("lags must not be supplied when se_kind='iid'")
        se = _se_iid(x)
    elif se_kind == "newey_west":
        se = _se_newey_west(x, lags)
    else:
        raise ValueError(
            f"unknown se_kind={se_kind!r}; expected 'iid' or 'newey_west'"
        )

    if se == 0.0 or not np.isfinite(se):
        raise ValueError(f"se == 0 or non-finite (se={se})")

    mean = float(np.mean(x))
    t = mean / se
    return TStatResult(t=float(t), mean=mean, se=float(se), n_obs=n_obs)


def p_from_t(t: float, direction: str) -> float:
    """Convert a t (or z) statistic to a p-value via standard normal asymptotics.

    Parameters
    ----------
    t :
        Test statistic.
    direction :
        ``"two-sided"`` → 2(1−Φ(|t|));
        ``"greater"`` → 1−Φ(t);
        ``"less"`` → Φ(t).

    Returns
    -------
    float
        p-value in [0, 1].

    Raises
    ------
    ValueError
        Non-finite t; unknown direction.

    Notes
    -----
    HLZ convention uses standard normal, not Student-t
    (Harvey, Liu & Zhu 2016 §3.5 fn 26; bhy.md §4.2; ruling E1).
    """
    if not np.isfinite(t):
        raise ValueError(f"t must be finite (got t={t})")
    # Right-tail probabilities use the survival function norm.sf ≡ 1−Φ directly,
    # never 1 − norm.cdf, which cancels to an exact 0.0 for |t| ≳ 8.3 and would
    # feed spurious zero p-values into BHY adjusted-p. Same extreme-tail
    # discipline as expected_max_sr's isf (dsr.md §5.5). The "less" tail is Φ(t)
    # itself (left tail, no cancellation), so it stays as norm.cdf.
    if direction == "two-sided":
        return float(2.0 * norm.sf(abs(t)))
    if direction == "greater":
        return float(norm.sf(t))
    if direction == "less":
        return float(norm.cdf(t))
    raise ValueError(
        f"unknown direction={direction!r}; "
        "expected 'two-sided', 'greater', or 'less'"
    )


def _se_iid(x: np.ndarray) -> float:
    """se = σ̂(Bessel)/√T."""
    t = x.size
    sigma = float(np.std(x, ddof=1))
    return sigma / np.sqrt(t)


def _se_newey_west(x: np.ndarray, lags: int | None) -> float:
    """Newey-West Bartlett HAC SE for the sample mean."""
    if lags is None:
        raise ValueError("lags is required when se_kind='newey_west'")
    if not isinstance(lags, (int, np.integer)) or isinstance(lags, bool):
        raise ValueError(f"lags must be a non-negative int (got {lags!r})")
    lags = int(lags)
    t = x.size
    if lags < 0:
        raise ValueError(f"lags must be >= 0 (got lags={lags})")
    if lags >= t:
        raise ValueError(f"lags must be < n_obs (got lags={lags}, n_obs={t})")

    mean = float(np.mean(x))
    d = x - mean
    # γ̂_0
    gamma_0 = float(np.dot(d, d) / t)
    lrv = gamma_0
    for ell in range(1, lags + 1):
        # γ̂_ℓ = (1/T) Σ_{t=1}^{T-ℓ} d_t d_{t+ℓ}
        gamma_ell = float(np.dot(d[: t - ell], d[ell:]) / t)
        weight = 1.0 - ell / (lags + 1)
        lrv += 2.0 * weight * gamma_ell

    if lrv < 0.0:
        # Numerically possible with estimated autocovariances; treat as invalid SE
        raise ValueError(f"Newey-West LRV is negative (LRV={lrv})")
    return float(np.sqrt(lrv / t))
