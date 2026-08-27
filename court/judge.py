"""Thin judge orchestrator: ledger evidence + pure statistics → VerdictRecords.

The judge is the only component that knows both the ledger and the statistics.
It reads evidence through the ledger read surface, computes each statistic under
every trial's declared protocol, appends one immutable VerdictRecord per
application, and returns a summary. No aggregation across statistics — battery
composition and survival policy belong to the demo design (ticket 11).

Implements court-kernel-spec.md §5.8 (Application / Judgment / judge,
per-application contracts, decision polarity table); rulings F2, G1–G5;
trial-ledger.md §5.3 / §7.4; noise-control.md §4 / §6.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, NamedTuple

import numpy as np

from court.dsr import (
    avg_pairwise_correlation,
    dsr,
    implied_independent_trials,
    rho_is_ill_conditioned,
)
from court.fdr import fdr_bh, fdr_by
from court.ledger import Ledger
from court.noise import empirical_null_p
from court.pbo import pbo_cscv
from court.sharpe import series_moments, sharpe_ratio
from court.tstats import p_from_t, t_stat


def _abs_sharpe(series: Any) -> float:
    """Absolute Sharpe — direction-consistent PBO metric under two-sided.

    CSCV is metric-agnostic (Bailey et al. 2017); |R| ranks the same arms as
    a max|t| selection. See docs/design/selection-verdict-isomorphism.md §2–§3.
    """
    return float(abs(sharpe_ratio(series)))


def _neg_sharpe(series: Any) -> float:
    """Negated Sharpe — direction-consistent PBO metric under less.

    CSCV's IS-argmax takes the largest metric; under a pre-declared short
    hypothesis the ranking must prefer the most-negative signed SR, which is
    the largest −SR. See docs/design/selection-verdict-isomorphism.md §2–§3.
    """
    return float(-sharpe_ratio(series))


# PBO metric registry (ruling G5 + selection-verdict-isomorphism.md §4):
# base name from caller; absolute/negated forms resolved by the judge.
# Verdict params must record the *resolved* R name actually used.
_METRIC_REGISTRY: dict[str, Callable[[Any], float]] = {
    "sharpe": sharpe_ratio,
    "abs_sharpe": _abs_sharpe,
    "neg_sharpe": _neg_sharpe,
}
_BASE_METRICS = frozenset({"sharpe"})

_PROVENANCE_KEYS = ("recipe", "delta_min", "seed", "offsets", "ranking_stat")

_KNOWN_STATISTICS = frozenset(
    {"dsr", "pbo_cscv", "fdr_by", "fdr_bh", "noise_control"}
)


class Application(NamedTuple):
    """One statistic application requested of the judge (spec §5.8)."""

    statistic: str  # "dsr" | "pbo_cscv" | "fdr_by" | "fdr_bh" | "noise_control"
    params: dict


class Judgment(NamedTuple):
    """Summary of a judge run: verdict ids and per-application decisions (§5.8)."""

    verdict_ids: tuple[str, ...]
    decisions: dict[str, dict[str, str]]  # verdict_id -> {trial_id: "pass"|"reject"}


def judge(
    ledger: Ledger,
    scope: Sequence[str],
    config: Sequence[Application],
) -> Judgment:
    """Apply each configured statistic to ``scope`` and append VerdictRecords.

    Parameters
    ----------
    ledger :
        Trial ledger (read surface + ``append_verdict``).
    scope :
        Explicit trial ids used as evidence (pool / family). Recorded verbatim
        on every verdict.
    config :
        Ordered sequence of ``Application(statistic, params)``. One
        VerdictRecord is appended per application (ruling G1).

    Returns
    -------
    Judgment
        ``verdict_ids`` in application order; ``decisions`` maps each
        verdict_id to the per-trial pass/reject map of that application
        (collision-free by construction — repeated applications of the same
        statistic each keep their own entry; join on ``verdict_ids``).

    Raises
    ------
    ValueError
        Empty scope; empty config; unknown statistic; any trial in scope not
        ``evaluated`` (ruling G3); missing or malformed required params
        (ruling G3); heterogeneous ``declared.direction`` across the scope
        (selection-verdict-isomorphism.md mixed-direction rule).
    """
    if not scope:
        raise ValueError("scope must be non-empty")
    if not config:
        raise ValueError("config must be non-empty")

    scope_list = list(scope)
    for tid in scope_list:
        status = ledger.status(tid)
        if status == "registered":
            raise ValueError(
                f"trial {tid!r} in scope is not evaluated (status={status!r})"
            )
        # "evaluated" and "judged" are both acceptable evidence sources.
        if status not in ("evaluated", "judged"):
            raise ValueError(
                f"trial {tid!r} in scope is not evaluated (status={status!r})"
            )

    family_direction = _require_homogeneous_direction(ledger, scope_list)

    engine_version = _engine_version()
    verdict_ids: list[str] = []
    decisions_out: dict[str, dict[str, str]] = {}

    for app in config:
        if app.statistic not in _KNOWN_STATISTICS:
            raise ValueError(f"unknown statistic {app.statistic!r}")
        if not isinstance(app.params, dict):
            raise ValueError(
                f"params for statistic {app.statistic!r} must be a dict"
            )

        if app.statistic in ("fdr_by", "fdr_bh"):
            vparams, computed, decisions = _apply_fdr(
                ledger, scope_list, app.statistic, app.params
            )
        elif app.statistic == "dsr":
            vparams, computed, decisions = _apply_dsr(
                ledger, scope_list, app.params, family_direction
            )
        elif app.statistic == "pbo_cscv":
            vparams, computed, decisions = _apply_pbo(
                ledger, scope_list, app.params, family_direction
            )
        else:  # noise_control
            vparams, computed, decisions = _apply_noise(
                ledger, scope_list, app.params
            )

        role = _gate_role(app.statistic, family_direction)
        vid = ledger.append_verdict(
            statistic=app.statistic,
            scope=scope_list,
            params=vparams,
            computed=computed,
            decisions=decisions,
            engine_version=engine_version,
            role=role,
        )
        verdict_ids.append(vid)
        decisions_out[vid] = dict(decisions)

    return Judgment(verdict_ids=tuple(verdict_ids), decisions=decisions_out)


def _engine_version() -> str:
    """Stamp VerdictRecord.engine_version from court.__version__ (ruling G4)."""
    import court

    return court.__version__


def _require_param(params: dict, key: str, statistic: str) -> Any:
    if key not in params:
        raise ValueError(
            f"missing required param {key!r} for statistic {statistic!r}"
        )
    return params[key]


def _require_homogeneous_direction(
    ledger: Ledger, scope: list[str]
) -> str:
    """Family-level gates require a single declared.direction (fail-closed).

    Mixed-direction scopes have no principled single branch for FDR / DSR /
    PBO / pool-max. See docs/design/selection-verdict-isomorphism.md Q2
    (mixed-direction scope rule).
    """
    directions: set[str] = set()
    for tid in scope:
        rec = ledger.trials([tid])[0]
        directions.add(rec.declared.direction)
    if len(directions) != 1:
        raise ValueError(
            f"heterogeneous declared.direction in scope: "
            f"{sorted(directions)!r}; family-level gates require a "
            f"direction-homogeneous scope"
        )
    return next(iter(directions))


def _gate_role(statistic: str, direction: str) -> str:
    """Derive verdict role from gate × declared.direction (isomorphism Q3).

    DSR under two-sided has no clean literature form matching a max|t|
    selection, so it abstains as informational. All other gate/direction
    pairs in the Q2 table are discriminating.
    See docs/design/selection-verdict-isomorphism.md §2–§3.
    """
    if statistic == "dsr" and direction == "two-sided":
        return "informational"
    return "discriminating"


def _resolve_pbo_metric(caller_name: str, direction: str) -> str:
    """Map caller base metric + direction → resolved registry name (G5).

    Callers pass the base name (e.g. ``\"sharpe\"``); the judge selects the
    direction-consistent form and records that resolved name on the verdict.
    Passing ``abs_*`` / ``neg_*`` forms directly is rejected — form is the
    judge's ruling, not a caller choice.
    """
    if caller_name.startswith("abs_") or caller_name.startswith("neg_"):
        raise ValueError(
            f"pbo_cscv metric form is the judge's ruling, not a caller "
            f"choice; got {caller_name!r} (pass the base name, e.g. 'sharpe')"
        )
    if caller_name not in _BASE_METRICS:
        raise ValueError(
            f"unknown pbo_cscv metric {caller_name!r}; "
            f"known base metrics: {sorted(_BASE_METRICS)}"
        )
    if direction == "two-sided":
        return f"abs_{caller_name}"
    if direction == "greater":
        return caller_name
    if direction == "less":
        return f"neg_{caller_name}"
    raise ValueError(f"unsupported declared direction {direction!r}")


def _ranking_statistic(values: Any, declared: Any) -> float:
    """Directed ranking statistic under the trial's declared protocol (ruling F2).

    two-sided → |t|; greater → t; less → −t (larger = more extreme in the
    declared direction). noise-control.md §4.1; court-kernel-spec.md ruling F2.
    """
    tr = t_stat(values, se_kind=declared.se.kind, lags=declared.se.lags)
    direction = declared.direction
    if direction == "two-sided":
        return float(abs(tr.t))
    if direction == "greater":
        return float(tr.t)
    if direction == "less":
        return float(-tr.t)
    raise ValueError(f"unsupported declared direction {direction!r}")


def _apply_fdr(
    ledger: Ledger,
    scope: list[str],
    statistic: str,
    params: dict,
) -> tuple[dict, dict, dict[str, str]]:
    """FDR family over the full scope (spec §5.8; ledger contract §4.2)."""
    q = _require_param(params, "q", statistic)
    try:
        q = float(q)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"param 'q' must be a float for {statistic!r}") from exc

    trial_ids: list[str] = []
    p_list: list[float] = []
    t_list: list[float] = []
    direction_list: list[str] = []
    se_kind_list: list[str] = []

    for tid in scope:
        rec = ledger.trials([tid])[0]
        series = rec.series
        assert series is not None  # evaluated precondition
        tr = t_stat(
            series.values,
            se_kind=rec.declared.se.kind,
            lags=rec.declared.se.lags,
        )
        p = p_from_t(tr.t, rec.declared.direction)
        trial_ids.append(tid)
        p_list.append(float(p))
        t_list.append(float(tr.t))
        direction_list.append(rec.declared.direction)
        se_kind_list.append(rec.declared.se.kind)

    if statistic == "fdr_by":
        result = fdr_by(p_list, q)
    else:
        result = fdr_bh(p_list, q)

    # Decision polarity (ruling G2): in FDR rejection set (H0 rejected) → "pass".
    decisions: dict[str, str] = {}
    for i, tid in enumerate(trial_ids):
        decisions[tid] = "pass" if result.reject[i] else "reject"

    vparams = {"q": q}
    computed = {
        "k_star": int(result.k_star),
        "c_factor": float(result.c_factor),
        "q": q,
        "trial_ids": list(trial_ids),
        "p": p_list,
        "t": t_list,
        "direction": direction_list,
        "se_kind": se_kind_list,
    }
    return vparams, computed, decisions


def _apply_dsr(
    ledger: Ledger,
    scope: list[str],
    params: dict,
    direction: str,
) -> tuple[dict, dict, dict[str, str]]:
    """DSR on the selected trial with multiplicity from the full scope (§5.8).

    Direction-aware forms (selection-verdict-isomorphism.md Q2 / §2–§3):

    - ``two-sided``: signed DSR as today (verdict role is informational —
      one-sided DSR does not match a |t| selection).
    - ``greater``: original signed DSR on the series as stored.
    - ``less``: negate the series matrix and the selected series, recompute
      moments, then apply the original signed DSR — never feed a negative-SR
      accused to the signed hurdle. Pairwise correlations are negation-
      invariant, so ρ̂ / N̂ are unchanged under the flip.

    Citations: Bailey & López de Prado (DSR); direction forms per
    docs/design/selection-verdict-isomorphism.md §2–§3.
    """
    selected = _require_param(params, "selected_trial_id", "dsr")
    confidence = _require_param(params, "confidence", "dsr")
    if selected not in scope:
        raise ValueError(
            f"selected_trial_id {selected!r} is not in scope for statistic 'dsr'"
        )
    try:
        confidence = float(confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("param 'confidence' must be a float for 'dsr'") from exc

    _index, mat = ledger.matrix(scope)
    selected_values = np.asarray(ledger.series(selected).values, dtype=np.float64)
    # Under less: flip the entire menu so the pre-declared short hypothesis is
    # judged by the original signed DSR machinery (N unchanged; ρ̂ invariant).
    if direction == "less":
        mat = -mat
        selected_values = -selected_values

    n_obs, n_trials_raw = mat.shape
    srs = np.array(
        [sharpe_ratio(mat[:, j]) for j in range(n_trials_raw)],
        dtype=np.float64,
    )
    # Cross-trial SR sample std with ddof=1 (ruling C9).
    if n_trials_raw < 2:
        raise ValueError(
            "dsr requires at least 2 trials in scope for cross-trial SR variance"
        )
    sr_trials_std = float(np.std(srs, ddof=1))
    rho_hat = float(avg_pairwise_correlation(mat))
    n_eff = float(implied_independent_trials(n_trials_raw, rho_hat))

    mom = series_moments(selected_values)
    result = dsr(
        mom.sr_hat,
        mom.n_obs,
        mom.skew_hat,
        mom.kurt_hat,
        sr_trials_std,
        n_eff,
    )

    # Polarity: DSR ≥ confidence → "pass" for selected_trial_id only (ruling G2).
    decision = "pass" if result.dsr >= confidence else "reject"
    decisions = {selected: decision}

    vparams = {
        "selected_trial_id": selected,
        "confidence": confidence,
    }
    computed = {
        "dsr": float(result.dsr),
        "sr_selected": float(mom.sr_hat),
        "sr_star": float(result.sr_star),
        "z": float(result.z),
        "var_factor": float(result.var_factor),
        "sr_trials_std": sr_trials_std,
        "rho_hat": rho_hat,
        "n_trials_raw": int(n_trials_raw),
        "n_trials_effective": n_eff,
        "rho_ill_conditioned": bool(
            rho_is_ill_conditioned(int(n_obs), int(n_trials_raw))
        ),
        "n_obs": int(mom.n_obs),
    }
    return vparams, computed, decisions


def _apply_pbo(
    ledger: Ledger,
    scope: list[str],
    params: dict,
    direction: str,
) -> tuple[dict, dict, dict[str, str]]:
    """PBO-CSCV on the selection pool; decide selected_trial_id only (§5.8).

    Direction-consistent metric forms (selection-verdict-isomorphism.md Q2):

    - ``two-sided`` → absolute form (``abs_sharpe``)
    - ``greater`` → signed form (``sharpe``)
    - ``less`` → negated form (``neg_sharpe``); raw signed metric under less
      would pick the most-positive column and invert the isomorphism.

    Callers pass the base name; verdict params record the resolved R name
    (G5 auditability). Citations: Bailey et al. 2017 CSCV; direction forms
    per docs/design/selection-verdict-isomorphism.md §2–§3.
    """
    selected = _require_param(params, "selected_trial_id", "pbo_cscv")
    n_splits = _require_param(params, "n_splits", "pbo_cscv")
    phi_threshold = _require_param(params, "phi_threshold", "pbo_cscv")
    base_metric = _require_param(params, "metric", "pbo_cscv")

    if selected not in scope:
        raise ValueError(
            f"selected_trial_id {selected!r} is not in scope for statistic 'pbo_cscv'"
        )
    resolved_metric = _resolve_pbo_metric(str(base_metric), direction)
    if resolved_metric not in _METRIC_REGISTRY:
        raise ValueError(
            f"unknown pbo_cscv metric {resolved_metric!r}; "
            f"known: {sorted(_METRIC_REGISTRY)}"
        )
    try:
        n_splits = int(n_splits)
    except (TypeError, ValueError) as exc:
        raise ValueError("param 'n_splits' must be an int for 'pbo_cscv'") from exc
    try:
        phi_threshold = float(phi_threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "param 'phi_threshold' must be a float for 'pbo_cscv'"
        ) from exc

    metric_fn = _METRIC_REGISTRY[resolved_metric]
    _index, mat = ledger.matrix(scope)
    result = pbo_cscv(mat, n_splits, metric=metric_fn)

    # Polarity: φ ≤ phi_threshold → "pass" for selected_trial_id only (ruling G2).
    decision = "pass" if result.phi <= phi_threshold else "reject"
    decisions = {selected: decision}

    vparams = {
        "selected_trial_id": selected,
        "n_splits": n_splits,
        "phi_threshold": phi_threshold,
        "metric": resolved_metric,
    }
    computed = {
        "phi": float(result.phi),
        "n_combinations": int(result.n_combinations),
        "n_lambda_negative": int(result.n_lambda_negative),
    }
    return vparams, computed, decisions


def _apply_noise(
    ledger: Ledger,
    scope: list[str],
    params: dict,
) -> tuple[dict, dict, dict[str, str]]:
    """Noise-control empirical null comparison (spec §5.8; noise-control.md §4/§6)."""
    mode = _require_param(params, "mode", "noise_control")
    alpha = _require_param(params, "alpha", "noise_control")
    null_stats = _require_param(params, "null_stats", "noise_control")

    if mode not in ("individual", "pool_max"):
        raise ValueError(
            f"param 'mode' for 'noise_control' must be 'individual' or "
            f"'pool_max', got {mode!r}"
        )
    try:
        alpha = float(alpha)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "param 'alpha' must be a float for 'noise_control'"
        ) from exc

    null_list = [float(x) for x in null_stats]

    if mode == "individual":
        judged = _require_param(params, "judged_trial_id", "noise_control")
        if judged not in scope:
            raise ValueError(
                f"judged_trial_id {judged!r} is not in scope for "
                f"statistic 'noise_control'"
            )
        rec = ledger.trials([judged])[0]
        assert rec.series is not None
        observed = _ranking_statistic(rec.series.values, rec.declared)
        selected_for_decision = judged
        selected_extra: dict[str, Any] = {}
    else:
        # pool_max: observed = max ranking stat over scope; argmax is judged.
        best_tid: str | None = None
        best_obs = float("-inf")
        for tid in scope:
            rec = ledger.trials([tid])[0]
            assert rec.series is not None
            obs = _ranking_statistic(rec.series.values, rec.declared)
            if obs > best_obs:
                best_obs = obs
                best_tid = tid
        assert best_tid is not None
        observed = best_obs
        selected_for_decision = best_tid
        selected_extra = {"selected_trial_id": best_tid}

    result = empirical_null_p(observed, null_list, alpha=alpha)
    # Polarity: p̂ ≤ α → "pass" for the judged/selected trial only (ruling G2 / F1).
    decisions = {selected_for_decision: result.decision}

    vparams: dict[str, Any] = {
        "mode": mode,
        "alpha": alpha,
        "null_stats": list(null_list),
    }
    if mode == "individual":
        vparams["judged_trial_id"] = selected_for_decision
    # Provenance keys copied VERBATIM and never interpreted (noise-control.md §6).
    for key in _PROVENANCE_KEYS:
        if key in params:
            vparams[key] = params[key]

    computed: dict[str, Any] = {
        "observed": float(observed),
        "p_hat": float(result.p_hat),
        "n_at_least": int(result.n_at_least),
        "n_nulls": int(result.n_nulls),
        "null_stats": list(null_list),
    }
    computed.update(selected_extra)
    return vparams, computed, decisions
