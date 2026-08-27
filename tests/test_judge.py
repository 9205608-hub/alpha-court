"""Tests for court/judge.py — thin orchestrator + public API (ticket v0.1-08f).

Maps to court-kernel-spec.md §5.8 and §7 (test_judge.py rows); polarity table
ruling G2; noise-control.md §4 / §6; trial-ledger.md §5.3 / §7.4.

Toy ledgers use short hand-chosen series so expected t/p/DSR/PBO outcomes are
re-derivable from the pure functions (already vector-tested in 08b–08e).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from court.dsr import (
    avg_pairwise_correlation,
    dsr,
    implied_independent_trials,
    rho_is_ill_conditioned,
)
from court.fdr import fdr_bh, fdr_by
from court.judge import Application, Judgment, judge
from court.ledger import (
    DeclaredProtocol,
    Ledger,
    SeConvention,
    Series,
    Window,
)
from court.noise import empirical_null_p
from court.pbo import pbo_cscv
from court.sharpe import series_moments, sharpe_ratio
from court.tstats import p_from_t, t_stat

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Spec §5.4 pipeline pin for values = [1, 2, 3], se_kind=iid.
SERIES_STRONG = [1.0, 2.0, 3.0]
T_STRONG = 3.464101615137754  # 2.0 / (1.0 / sqrt(3)) pipeline value
INDEX_3 = ("d1", "d2", "d3")
INDEX_8 = tuple(f"r{i}" for i in range(8))

# Aligned T=8 pool for DSR / PBO. Constructed so (a) every CSCV half has σ̂>0
# under the registry metric ``sharpe_ratio`` (ruling D3) and (b) φ > 0 under
# sharpe (so both pass and reject polarity can be forced via phi_threshold).
# Seed-0 construction verified offline: phi = 2/6 under S=4.
POOL_COL0 = [
    2.12573,
    2.1049,
    3.304,
    0.734579,
    -2.325031,
    -0.732267,
    0.411631,
    1.366463,
]
POOL_COL1 = [
    -0.132105,
    -0.535669,
    0.947081,
    -0.623274,
    1.781208,
    1.455741,
    3.042513,
    1.334805,
]
POOL_COL2 = [
    0.640423,
    0.361595,
    -0.703735,
    0.041326,
    -1.245911,
    -0.3163,
    -0.128535,
    0.35151,
]


def _window() -> Window:
    return Window(start="2020-01-01", end="2020-12-31")


def _declared(**kwargs) -> DeclaredProtocol:
    base = dict(
        metric="returns",
        window=_window(),
        periods_per_year=252.0,
        direction="two-sided",
        se=SeConvention(kind="iid"),
    )
    base.update(kwargs)
    return DeclaredProtocol(**base)


def _series(values: list[float], index: tuple[str, ...] | None = None) -> Series:
    if index is None:
        index = tuple(f"t{i}" for i in range(len(values)))
    return Series(index=index, values=tuple(values))


def _open(tmp_path: Path) -> Ledger:
    return Ledger.open(tmp_path / "ledger.jsonl")


def _register_eval(
    ledger: Ledger,
    values: list[float],
    *,
    index: tuple[str, ...] | None = None,
    declared: DeclaredProtocol | None = None,
    hid: str | None = None,
) -> str:
    if hid is None:
        hid = ledger.register_hypothesis("claim")
    tid = ledger.register(
        hid,
        {"kind": "toy"},
        {"n": len(values)},
        declared if declared is not None else _declared(),
    )
    ledger.record(tid, _series(values, index=index))
    return tid


# ---------------------------------------------------------------------------
# fdr_by end-to-end
# ---------------------------------------------------------------------------


def test_fdr_by_application_end_to_end(tmp_path: Path) -> None:
    """One VerdictRecord; scope verbatim; discovery ⟺ pass; audit lists present.

    Three iid two-sided trials (hand-chosen short series):
      A = [1,2,3]           → t ≈ 3.464 (spec §5.4 pin), tiny p
      B = [0.1, -0.05, 0.02] → near-zero mean, large p
      C = [0.8, 0.9, 1.0]    → positive mean, intermediate p

    With q large enough that at least the strongest discovery lands in the
    rejection set; polarity: reject[i] True → decision \"pass\".
    """
    ledger = _open(tmp_path)
    hid = ledger.register_hypothesis("family of three")
    t_a = _register_eval(ledger, SERIES_STRONG, index=INDEX_3, hid=hid)
    t_b = _register_eval(ledger, [0.1, -0.05, 0.02], index=INDEX_3, hid=hid)
    t_c = _register_eval(ledger, [0.8, 0.9, 1.0], index=INDEX_3, hid=hid)
    scope = [t_a, t_b, t_c]
    q = 0.20

    # Pure-function oracle for expected polarity / k_star.
    p_vec = []
    t_vec = []
    for tid in scope:
        rec = ledger.trials([tid])[0]
        tr = t_stat(rec.series.values, se_kind=rec.declared.se.kind, lags=rec.declared.se.lags)
        t_vec.append(tr.t)
        p_vec.append(p_from_t(tr.t, rec.declared.direction))
    oracle = fdr_by(p_vec, q)

    judgment = judge(
        ledger,
        scope,
        [Application(statistic="fdr_by", params={"q": q})],
    )

    assert isinstance(judgment, Judgment)
    assert len(judgment.verdict_ids) == 1
    verdicts = ledger.verdicts()
    assert len(verdicts) == 1
    v = verdicts[0]
    assert v.verdict_id == judgment.verdict_ids[0]
    assert v.statistic == "fdr_by"
    assert list(v.scope) == scope
    assert v.params["q"] == q
    assert v.engine_version is not None

    # Decisions cover whole scope; discovery (FDR reject True) ⟺ court "pass".
    assert set(v.decisions.keys()) == set(scope)
    for i, tid in enumerate(scope):
        expected = "pass" if oracle.reject[i] else "reject"
        assert v.decisions[tid] == expected
        assert judgment.decisions[judgment.verdict_ids[0]][tid] == expected

    # At least one discovery under q=0.20 with this family (strong A).
    assert oracle.k_star >= 1
    assert any(d == "pass" for d in v.decisions.values())

    c = v.computed
    assert c["k_star"] == oracle.k_star
    assert c["c_factor"] == pytest.approx(oracle.c_factor, abs=1e-9)
    assert c["q"] == q
    assert list(c["trial_ids"]) == scope
    # p list is raw p-values in scope order (not adjusted).
    assert len(c["p"]) == 3
    for i in range(3):
        assert c["p"][i] == pytest.approx(p_vec[i], abs=1e-9)
        assert c["t"][i] == pytest.approx(t_vec[i], abs=1e-9)
    assert list(c["direction"]) == ["two-sided", "two-sided", "two-sided"]
    assert list(c["se_kind"]) == ["iid", "iid", "iid"]
    # Strong trial pin.
    assert c["t"][0] == pytest.approx(T_STRONG, abs=1e-9)


def test_fdr_bh_polarity_also_available(tmp_path: Path) -> None:
    """fdr_bh uses the same discovery ⟺ pass polarity as fdr_by."""
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, SERIES_STRONG, index=INDEX_3)
    q = 0.10
    tr = t_stat(SERIES_STRONG)
    p = p_from_t(tr.t, "two-sided")
    oracle = fdr_bh([p], q)

    judgment = judge(
        ledger,
        [tid],
        [Application(statistic="fdr_bh", params={"q": q})],
    )
    v = ledger.verdicts()[0]
    assert v.statistic == "fdr_bh"
    expected = "pass" if oracle.reject[0] else "reject"
    assert v.decisions[tid] == expected
    assert judgment.decisions[judgment.verdict_ids[0]][tid] == expected
    assert oracle.k_star == 1  # single tiny p under q=0.10


# ---------------------------------------------------------------------------
# noise_control
# ---------------------------------------------------------------------------


def test_noise_control_individual_provenance_and_decision(tmp_path: Path) -> None:
    """Individual mode: provenance verbatim in params; null_stats in computed.

    Observed ranking stat for two-sided trial on [1,2,3] is |t| = T_STRONG.
    null_stats = [1.0, 2.0, 3.0, 4.0]: only 4.0 ≥ observed → n_at_least=1,
    p̂ = 2/5 = 0.4. At α=0.05 → reject; at α=0.5 → pass (second application).
    """
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, SERIES_STRONG, index=INDEX_3)
    null_stats = [1.0, 2.0, 3.0, 4.0]
    provenance = {
        "recipe": "circular_shift",
        "delta_min": 5,
        "seed": 42,
        "offsets": [7, 11, 19, 23],
        "ranking_stat": "abs_t_iid",
    }

    # Reject direction (α small).
    j1 = judge(
        ledger,
        [tid],
        [
            Application(
                statistic="noise_control",
                params={
                    "mode": "individual",
                    "alpha": 0.05,
                    "null_stats": null_stats,
                    "judged_trial_id": tid,
                    **provenance,
                },
            )
        ],
    )
    v1 = ledger.verdicts()[0]
    assert j1.verdict_ids[0] == v1.verdict_id
    assert v1.statistic == "noise_control"
    for k, val in provenance.items():
        assert v1.params[k] == val
    assert v1.params["mode"] == "individual"
    assert v1.params["alpha"] == 0.05
    assert v1.params["judged_trial_id"] == tid

    oracle = empirical_null_p(T_STRONG, null_stats, alpha=0.05)
    assert oracle.p_hat == pytest.approx(0.4, abs=1e-12)
    assert oracle.decision == "reject"
    assert v1.computed["observed"] == pytest.approx(T_STRONG, abs=1e-9)
    assert v1.computed["p_hat"] == pytest.approx(0.4, abs=1e-12)
    assert v1.computed["n_at_least"] == 1
    assert v1.computed["n_nulls"] == 4
    assert list(v1.computed["null_stats"]) == null_stats
    assert v1.decisions == {tid: "reject"}
    assert j1.decisions[j1.verdict_ids[0]][tid] == "reject"

    # Pass direction (α large enough that 0.4 ≤ α).
    j2 = judge(
        ledger,
        [tid],
        [
            Application(
                statistic="noise_control",
                params={
                    "mode": "individual",
                    "alpha": 0.5,
                    "null_stats": null_stats,
                    "judged_trial_id": tid,
                    **provenance,
                },
            )
        ],
    )
    v2 = ledger.verdicts()[1]
    assert v2.decisions[tid] == "pass"
    assert j2.decisions[j2.verdict_ids[0]][tid] == "pass"
    assert v2.computed["p_hat"] == pytest.approx(0.4, abs=1e-12)


def test_noise_control_pool_max_argmax(tmp_path: Path) -> None:
    """Pool-max: observed = max ranking stat over scope; argmax is judged.

    A = [1,2,3] → |t| ≈ 3.464; B = high-variance near-zero mean → smaller |t|.
    observed = max = |t_A|; selected_trial_id = A.
    nulls all below observed → p̂ = 1/(K+1) = 0.25 at K=3; α=0.05 → reject.
    """
    ledger = _open(tmp_path)
    hid = ledger.register_hypothesis("pool")
    # Weak counterpart: large dispersion around a small mean ⇒ modest |t|.
    weak_vals = [1.0, -1.0, 0.5]
    t_a = _register_eval(ledger, SERIES_STRONG, index=INDEX_3, hid=hid)
    t_b = _register_eval(ledger, weak_vals, index=INDEX_3, hid=hid)
    scope = [t_a, t_b]
    null_stats = [0.5, 1.0, 1.5]

    tr_a = t_stat(SERIES_STRONG)
    tr_b = t_stat(weak_vals)
    observed = max(abs(tr_a.t), abs(tr_b.t))
    assert abs(tr_a.t) > abs(tr_b.t)
    assert observed == pytest.approx(abs(tr_a.t), abs=1e-12)

    judgment = judge(
        ledger,
        scope,
        [
            Application(
                statistic="noise_control",
                params={
                    "mode": "pool_max",
                    "alpha": 0.05,
                    "null_stats": null_stats,
                    "recipe": "circular_shift",
                    "delta_min": 3,
                    "seed": 7,
                    "offsets": [1, 2, 3],
                    "ranking_stat": "abs_t_iid",
                },
            )
        ],
    )
    v = ledger.verdicts()[0]
    assert v.computed["observed"] == pytest.approx(observed, abs=1e-9)
    assert v.computed["selected_trial_id"] == t_a
    assert set(v.decisions.keys()) == {t_a}
    oracle = empirical_null_p(observed, null_stats, alpha=0.05)
    assert v.decisions[t_a] == oracle.decision
    assert judgment.decisions[judgment.verdict_ids[0]][t_a] == oracle.decision
    # No decision recorded for the non-selected trial.
    assert t_b not in v.decisions


# ---------------------------------------------------------------------------
# dsr / pbo_cscv polarity (selected trial only)
# ---------------------------------------------------------------------------


def _aligned_three_trials(ledger: Ledger) -> list[str]:
    """Three aligned series (T=8) suitable for DSR ρ̂ and PBO S=4.

    Declared direction is ``greater`` so the signed-sharpe PBO oracle in
    ``test_pbo_cscv_pass_and_reject`` remains the correct form under the
    v0.2 direction-aware metric resolution (ticket v0.2-08 authorized fix).
    DSR numerics are unchanged under greater vs two-sided (signed pipeline).
    """
    hid = ledger.register_hypothesis("aligned pool")
    ids = []
    declared = _declared(direction="greater")
    for col in (POOL_COL0, POOL_COL1, POOL_COL2):
        ids.append(
            _register_eval(ledger, col, index=INDEX_8, hid=hid, declared=declared)
        )
    return ids


def test_dsr_verdict_stores_dsr_probability(tmp_path: Path) -> None:
    """The DSR verdict records the DSR probability itself, not only its z-path.

    The ledger is the court's audit trail; the headline statistic must be
    reproducible from it directly, not reconstructed downstream via Φ(z).
    """
    ledger = _open(tmp_path)
    scope = _aligned_three_trials(ledger)
    selected = scope[0]

    _, mat = ledger.matrix(scope)
    srs = [sharpe_ratio(mat[:, j]) for j in range(mat.shape[1])]
    sr_std = float(np.std(srs, ddof=1))
    rho = avg_pairwise_correlation(mat)
    n_eff = implied_independent_trials(mat.shape[1], rho)
    mom = series_moments(ledger.series(selected).values)
    result = dsr(mom.sr_hat, mom.n_obs, mom.skew_hat, mom.kurt_hat, sr_std, n_eff)

    judge(
        ledger,
        scope,
        [
            Application(
                statistic="dsr",
                params={"selected_trial_id": selected, "confidence": 0.95},
            )
        ],
    )
    c = ledger.verdicts()[0].computed
    assert c["dsr"] == pytest.approx(result.dsr, abs=1e-12)


def test_dsr_pass_and_reject(tmp_path: Path) -> None:
    """DSR: decisions only for selected_trial_id; both polarity directions.

    Pipeline matches §5.8: matrix → per-col SR → std(ddof=1) + ρ̂ → N̂ → dsr.
    Pass when confidence ≤ DSR; reject when confidence > DSR.
    """
    ledger = _open(tmp_path)
    scope = _aligned_three_trials(ledger)
    selected = scope[0]

    index, mat = ledger.matrix(scope)
    assert len(index) == 8
    srs = [sharpe_ratio(mat[:, j]) for j in range(mat.shape[1])]
    sr_std = float(np.std(srs, ddof=1))
    rho = avg_pairwise_correlation(mat)
    n_eff = implied_independent_trials(mat.shape[1], rho)
    mom = series_moments(ledger.series(selected).values)
    result = dsr(
        mom.sr_hat, mom.n_obs, mom.skew_hat, mom.kurt_hat, sr_std, n_eff
    )

    # Pass direction: confidence at or below DSR.
    conf_pass = min(result.dsr, 0.5)  # always ≤ dsr if dsr >= 0.5 else = dsr
    conf_pass = result.dsr  # boundary: DSR ≥ confidence
    j_pass = judge(
        ledger,
        scope,
        [
            Application(
                statistic="dsr",
                params={"selected_trial_id": selected, "confidence": conf_pass},
            )
        ],
    )
    v_pass = ledger.verdicts()[0]
    assert set(v_pass.decisions.keys()) == {selected}
    assert v_pass.decisions[selected] == "pass"
    assert j_pass.decisions[j_pass.verdict_ids[0]][selected] == "pass"
    c = v_pass.computed
    assert c["sr_selected"] == pytest.approx(mom.sr_hat, abs=1e-9)
    assert c["sr_star"] == pytest.approx(result.sr_star, abs=1e-9)
    assert c["z"] == pytest.approx(result.z, abs=1e-9)
    assert c["var_factor"] == pytest.approx(result.var_factor, abs=1e-9)
    assert c["sr_trials_std"] == pytest.approx(sr_std, abs=1e-9)
    assert c["rho_hat"] == pytest.approx(rho, abs=1e-9)
    assert c["n_trials_raw"] == 3
    assert c["n_trials_effective"] == pytest.approx(n_eff, abs=1e-9)
    assert c["rho_ill_conditioned"] == rho_is_ill_conditioned(8, 3)
    assert c["n_obs"] == 8

    # Reject direction: confidence strictly above DSR (clamp into (0,1) if needed).
    conf_reject = min(0.999999, result.dsr + 0.05)
    if conf_reject <= result.dsr:
        conf_reject = 0.999999
        assert conf_reject > result.dsr
    j_rej = judge(
        ledger,
        scope,
        [
            Application(
                statistic="dsr",
                params={"selected_trial_id": selected, "confidence": conf_reject},
            )
        ],
    )
    v_rej = ledger.verdicts()[1]
    assert set(v_rej.decisions.keys()) == {selected}
    assert v_rej.decisions[selected] == "reject"
    assert j_rej.decisions[j_rej.verdict_ids[0]][selected] == "reject"
    # Non-selected trials remain unevaluated-as-judged until a verdict decides them.
    for other in scope[1:]:
        assert other not in v_pass.decisions
        assert other not in v_rej.decisions


def test_pbo_cscv_pass_and_reject(tmp_path: Path) -> None:
    """PBO: decisions on selected_trial_id only; pass when φ ≤ threshold."""
    ledger = _open(tmp_path)
    scope = _aligned_three_trials(ledger)
    selected = scope[1]
    n_splits = 4

    _, mat = ledger.matrix(scope)
    oracle = pbo_cscv(mat, n_splits, metric=sharpe_ratio)
    assert 0.0 <= oracle.phi <= 1.0

    # Pass: threshold at least φ.
    j_pass = judge(
        ledger,
        scope,
        [
            Application(
                statistic="pbo_cscv",
                params={
                    "selected_trial_id": selected,
                    "n_splits": n_splits,
                    "phi_threshold": oracle.phi,
                    "metric": "sharpe",
                },
            )
        ],
    )
    v_pass = ledger.verdicts()[0]
    assert set(v_pass.decisions.keys()) == {selected}
    assert v_pass.decisions[selected] == "pass"
    assert j_pass.decisions[j_pass.verdict_ids[0]][selected] == "pass"
    assert v_pass.computed["phi"] == pytest.approx(oracle.phi, abs=1e-12)
    assert v_pass.computed["n_combinations"] == oracle.n_combinations
    assert v_pass.computed["n_lambda_negative"] == oracle.n_lambda_negative
    assert "logits" not in v_pass.computed  # contract: counts only, not the vector
    assert v_pass.params["metric"] == "sharpe"
    assert v_pass.params["n_splits"] == n_splits
    assert v_pass.params["phi_threshold"] == oracle.phi
    assert v_pass.params["selected_trial_id"] == selected

    # Reject: threshold strictly below φ. Fixture is constructed so φ > 0.
    assert oracle.phi > 0.0
    thr_reject = 0.0
    assert thr_reject < oracle.phi

    j_rej = judge(
        ledger,
        scope,
        [
            Application(
                statistic="pbo_cscv",
                params={
                    "selected_trial_id": selected,
                    "n_splits": n_splits,
                    "phi_threshold": thr_reject,
                    "metric": "sharpe",
                },
            )
        ],
    )
    v_rej = ledger.verdicts()[1]
    assert v_rej.decisions[selected] == "reject"
    assert j_rej.decisions[j_rej.verdict_ids[0]][selected] == "reject"


# ---------------------------------------------------------------------------
# status → judged
# ---------------------------------------------------------------------------


def test_status_becomes_judged_after_verdict_covers_trial(tmp_path: Path) -> None:
    """status is judged only for trials appearing in verdict decisions."""
    ledger = _open(tmp_path)
    hid = ledger.register_hypothesis("status")
    t_a = _register_eval(ledger, SERIES_STRONG, index=INDEX_3, hid=hid)
    t_b = _register_eval(ledger, [0.1, 0.2, 0.15], index=INDEX_3, hid=hid)
    assert ledger.status(t_a) == "evaluated"
    assert ledger.status(t_b) == "evaluated"

    judge(
        ledger,
        [t_a, t_b],
        [
            Application(
                statistic="dsr",
                params={"selected_trial_id": t_a, "confidence": 0.99},
            )
        ],
    )
    assert ledger.status(t_a) == "judged"
    # t_b is in scope but not in decisions → still evaluated only.
    assert ledger.status(t_b) == "evaluated"

    judge(
        ledger,
        [t_a, t_b],
        [Application(statistic="fdr_by", params={"q": 0.10})],
    )
    assert ledger.status(t_a) == "judged"
    assert ledger.status(t_b) == "judged"


# ---------------------------------------------------------------------------
# Guards (fail-closed)
# ---------------------------------------------------------------------------


def test_guard_unevaluated_trial_in_scope(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    hid = ledger.register_hypothesis("g")
    tid = ledger.register(hid, {"k": 1}, {}, _declared())
    # registered but not recorded
    with pytest.raises(ValueError, match="evaluated"):
        judge(
            ledger,
            [tid],
            [Application(statistic="fdr_by", params={"q": 0.1})],
        )


def test_guard_unknown_statistic(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, SERIES_STRONG, index=INDEX_3)
    with pytest.raises(ValueError, match="unknown statistic"):
        judge(
            ledger,
            [tid],
            [Application(statistic="not_a_real_stat", params={"q": 0.1})],
        )


def test_guard_empty_scope(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    with pytest.raises(ValueError, match="scope"):
        judge(
            ledger,
            [],
            [Application(statistic="fdr_by", params={"q": 0.1})],
        )


def test_guard_empty_config(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, SERIES_STRONG, index=INDEX_3)
    with pytest.raises(ValueError, match="config"):
        judge(ledger, [tid], [])


def test_guard_missing_required_param(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, SERIES_STRONG, index=INDEX_3)
    with pytest.raises(ValueError, match="q"):
        judge(
            ledger,
            [tid],
            [Application(statistic="fdr_by", params={})],
        )
    with pytest.raises(ValueError, match="selected_trial_id|confidence"):
        judge(
            ledger,
            [tid],
            [Application(statistic="dsr", params={"confidence": 0.95})],
        )
    with pytest.raises(ValueError, match="judged_trial_id|mode|null_stats|alpha"):
        judge(
            ledger,
            [tid],
            [
                Application(
                    statistic="noise_control",
                    params={"mode": "individual", "alpha": 0.05, "null_stats": [1.0]},
                )
            ],
        )


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------


def test_public_api_reexports() -> None:
    """import court resolves judge, Ledger, statistics, and __version__."""
    import court

    assert court.__version__ == "0.1.0.dev0"
    assert court.judge is judge
    assert court.Ledger is Ledger
    assert court.Application is Application
    assert court.Judgment is Judgment
    assert callable(court.empirical_null_p)
    assert callable(court.fdr_by)
    assert callable(court.dsr)
    assert callable(court.pbo_cscv)
    assert callable(court.sharpe_ratio)
    assert callable(court.t_stat)
    assert callable(court.p_from_t)
    assert callable(court.fdr_bh)
    assert court.LedgerCorruptionError is not None


# ---------------------------------------------------------------------------
# v0.2-12 slice C: Judgment.decisions keyed by verdict_id
# ---------------------------------------------------------------------------


def test_repeated_statistic_keeps_both_summaries(tmp_path: Path) -> None:
    """Repeated applications of one statistic must not overwrite each other."""
    ledger = _open(tmp_path)
    tid_a = _register_eval(ledger, [1.0, 2.0, 3.0])
    tid_b = _register_eval(ledger, [0.1, -0.05, 0.02])
    scope = [tid_a, tid_b]
    judgment = judge(
        ledger,
        scope,
        [
            Application(statistic="fdr_by", params={"q": 0.20}),
            Application(statistic="fdr_by", params={"q": 0.0001}),
        ],
    )
    assert len(judgment.verdict_ids) == 2
    assert set(judgment.decisions.keys()) == set(judgment.verdict_ids)
    assert len(judgment.decisions) == 2
