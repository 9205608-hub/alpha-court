"""Empirical null p-value (noise control) for the court kernel.

Pure arithmetic only: the caller supplies the observed ranking statistic and the
jury of null statistics. Null generation (circular time-shift, offset grids, RNG)
lives on the adapter/demo side and is intentionally absent here.

References
----------
- Phipson, B. & Smyth, G. K. (2010), "Permutation P-values Should Never Be Zero",
  *Statistical Applications in Genetics and Molecular Biology* 9(1), Article 39,
  Eq. (2) — the add-one estimator used by ``empirical_null_p``.
- White, H. (2000), "A Reality Check for Data Snooping", *Econometrica* 68(5) —
  pool-max mode semantics (same arithmetic; mode is input selection by the caller).
- ``docs/design/noise-control.md`` §4 (court-side function, individual / pool-max
  modes) and §8 (hand-worked test vectors).
- ``docs/design/court-kernel-spec.md`` §5.6 (signature and guards), ruling F1.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np


class NoiseResult(NamedTuple):
    """Result of an empirical null (randomization) p-value comparison.

    Attributes
    ----------
    p_hat:
        Add-one permutation p-value
        ``(1 + #{null_j >= observed}) / (K + 1)`` (Phipson & Smyth 2010, Eq. (2)).
    decision:
        ``"pass"`` iff ``p_hat <= alpha``, else ``"reject"``
        (VerdictRecord decision vocabulary).
    n_nulls:
        Jury size ``K``.
    n_at_least:
        ``#{null_j >= observed}`` — ties count against the candidate.
    """

    p_hat: float
    decision: str
    n_nulls: int
    n_at_least: int


def empirical_null_p(
    observed: float,
    nulls,
    alpha: float = 0.05,
) -> NoiseResult:
    """Compare ``observed`` against an information-free null jury.

    Computes the add-one permutation p-value of Phipson & Smyth (2010, Eq. (2)):

        p̂ = (1 + #{ j : null_j ≥ observed }) / (K + 1)

    Ties count against the candidate (``≥`` is conservative). The add-one form
    can never return zero. Decision: ``"pass"`` iff ``p̂ ≤ α``; default
    ``alpha=0.05`` is a verdict parameter, not a module constant
    (``noise-control.md`` §4.1).

    The same arithmetic serves both individual-jury and pool-max (White 2000
    Reality Check) modes; mode is solely a matter of how the caller builds
    ``observed`` and ``nulls`` (``noise-control.md`` §4.2–§4.3). This function
    neither generates nor shifts null factors.

    Parameters
    ----------
    observed:
        Ranking statistic of the accused (or of the selection max in pool mode).
    nulls:
        1-D sequence or array of K null ranking statistics.
    alpha:
        Significance level in the open interval (0, 1). Default 0.05.

    Returns
    -------
    NoiseResult
        ``p_hat``, ``decision``, ``n_nulls``, ``n_at_least``.

    Raises
    ------
    ValueError
        In-contract guard violations: ``nulls`` empty, not 1-D, or containing
        non-finite values; ``observed`` non-finite; ``alpha`` not in (0, 1).
    TypeError
        May propagate from numpy conversion when an argument has a type that
        is not array-like or numeric at all (e.g. a generator as ``nulls``,
        or ``observed=None``). Fail-closed either way; this path is not part
        of the contracted guard table.
    """
    if not np.isfinite(observed):
        raise ValueError("observed must be finite")

    if not np.isfinite(alpha) or not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in the open interval (0, 1)")

    arr = np.asarray(nulls, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("nulls must be 1-D")
    if arr.size == 0:
        raise ValueError("nulls must be non-empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError("nulls must contain only finite values")

    k = int(arr.size)
    n_at_least = int(np.sum(arr >= observed))
    p_hat = (1 + n_at_least) / (k + 1)
    decision = "pass" if p_hat <= alpha else "reject"
    return NoiseResult(
        p_hat=float(p_hat),
        decision=decision,
        n_nulls=k,
        n_at_least=n_at_least,
    )
