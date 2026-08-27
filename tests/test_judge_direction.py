"""Direction-aware battery, verdict role, and ledger role round-trip (v0.2-08).

Binding design: docs/design/selection-verdict-isomorphism.md v2 Q2/Q3 / §4.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from court.dsr import (
    avg_pairwise_correlation,
    dsr,
    implied_independent_trials,
)
from court.judge import Application, judge
from court.ledger import (
    DeclaredProtocol,
    Ledger,
    SeConvention,
    Series,
    Window,
)
from court.sharpe import series_moments, sharpe_ratio
from examples.killer_demo.aggregate import (
    gates_faced_passed,
    trial_survives,
)

# Shared pool with existing test_judge fixtures (T=8, PBO-safe under sharpe).
INDEX_8 = tuple(f"r{i}" for i in range(8))
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


def _declared(direction: str = "two-sided") -> DeclaredProtocol:
    return DeclaredProtocol(
        metric="returns",
        window=_window(),
        periods_per_year=252.0,
        direction=direction,
        se=SeConvention(kind="iid"),
    )


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
    direction: str = "two-sided",
    index: tuple[str, ...] | None = None,
    hid: str | None = None,
) -> str:
    if hid is None:
        hid = ledger.register_hypothesis("claim")
    tid = ledger.register(
        hid,
        {"kind": "toy"},
        {"n": len(values)},
        _declared(direction=direction),
    )
    ledger.record(tid, _series(values, index=index))
    return tid


def _aligned_pool(
    ledger: Ledger,
    *,
    direction: str = "two-sided",
) -> list[str]:
    hid = ledger.register_hypothesis(f"pool-{direction}")
    ids: list[str] = []
    for col in (POOL_COL0, POOL_COL1, POOL_COL2):
        ids.append(
            _register_eval(
                ledger, col, direction=direction, index=INDEX_8, hid=hid
            )
        )
    return ids


def _full_battery(selected: str, *, conf: float = 0.95, phi_thr: float = 0.2) -> list:
    """Five-gate battery; noise nulls set so individual/pool pass a strong series."""
    # Large nulls → small p_hat so pool_max and individual pass.
    null_stats = [0.1, 0.2, 0.3, 0.4]
    return [
        Application("fdr_by", {"q": 0.99}),
        Application(
            "dsr",
            {"selected_trial_id": selected, "confidence": conf},
        ),
        Application(
            "pbo_cscv",
            {
                "selected_trial_id": selected,
                "n_splits": 4,
                "phi_threshold": phi_thr,
                "metric": "sharpe",
            },
        ),
        Application(
            "noise_control",
            {
                "mode": "pool_max",
                "alpha": 0.99,
                "null_stats": null_stats,
                "recipe": "toy",
                "delta_min": 1,
                "seed": 0,
                "offsets": [1, 2, 3, 4],
                "ranking_stat": "abs_t_iid",
            },
        ),
        Application(
            "noise_control",
            {
                "mode": "individual",
                "alpha": 0.99,
                "judged_trial_id": selected,
                "null_stats": null_stats,
                "recipe": "toy",
                "delta_min": 1,
                "seed": 0,
                "offsets": [1, 2, 3, 4],
                "ranking_stat": "abs_t_iid",
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Ledger role round-trip (must live here — test_ledger*.py frozen)
# ---------------------------------------------------------------------------


def test_append_verdict_role_round_trip(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, [1.0, 2.0, 3.0])
    vid = ledger.append_verdict(
        statistic="dsr",
        scope=[tid],
        params={"selected_trial_id": tid},
        computed={"z": 0.0},
        decisions={tid: "reject"},
        role="informational",
    )
    v = ledger.verdicts()[0]
    assert v.verdict_id == vid
    assert v.role == "informational"

    reopened = Ledger.open(tmp_path / "ledger.jsonl")
    v2 = reopened.verdicts()[0]
    assert v2.role == "informational"


def test_append_verdict_invalid_role_raises(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, [1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="role"):
        ledger.append_verdict(
            statistic="dsr",
            scope=[tid],
            params={},
            computed={},
            decisions={tid: "pass"},
            role="advisory",
        )


def test_legacy_verdict_event_without_role_replays_none(tmp_path: Path) -> None:
    """Events lacking the role key replay as role=None (pre-v0.2).

    ``append_verdict(role=None)`` omits the key; reopen → role=None.
    """
    path = tmp_path / "ledger.jsonl"
    ledger = _open(tmp_path)
    tid = _register_eval(ledger, [1.0, 2.0, 3.0])
    ledger.append_verdict(
        statistic="fdr_by",
        scope=[tid],
        params={"q": 0.05},
        computed={"k_star": 0},
        decisions={tid: "reject"},
        role=None,
    )
    # Confirm the stored event has no role key (legacy shape).
    import json

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    verdict_events = [
        json.loads(line) for line in lines if json.loads(line).get("type") == "verdict"
    ]
    assert verdict_events
    assert "role" not in verdict_events[0]

    reopened = Ledger.open(path)
    assert reopened.verdicts()[0].role is None


# ---------------------------------------------------------------------------
# Homogeneity guard
# ---------------------------------------------------------------------------


def test_mixed_direction_scope_raises(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    hid = ledger.register_hypothesis("mixed")
    t_a = _register_eval(
        ledger, [1.0, 2.0, 3.0], direction="greater", hid=hid
    )
    t_b = _register_eval(
        ledger, [0.1, -0.05, 0.02], direction="less", hid=hid
    )
    with pytest.raises(ValueError, match="direction"):
        judge(
            ledger,
            [t_a, t_b],
            [Application("fdr_by", {"q": 0.1})],
        )


# ---------------------------------------------------------------------------
# Metric registry / caller form forbidden
# ---------------------------------------------------------------------------


def test_caller_passing_abs_sharpe_raises(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    scope = _aligned_pool(ledger, direction="two-sided")
    with pytest.raises(ValueError, match="ruling, not a caller choice"):
        judge(
            ledger,
            scope,
            [
                Application(
                    "pbo_cscv",
                    {
                        "selected_trial_id": scope[0],
                        "n_splits": 4,
                        "phi_threshold": 0.5,
                        "metric": "abs_sharpe",
                    },
                )
            ],
        )


def test_caller_passing_neg_sharpe_raises(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    scope = _aligned_pool(ledger, direction="less")
    with pytest.raises(ValueError, match="ruling, not a caller choice"):
        judge(
            ledger,
            scope,
            [
                Application(
                    "pbo_cscv",
                    {
                        "selected_trial_id": scope[0],
                        "n_splits": 4,
                        "phi_threshold": 0.5,
                        "metric": "neg_sharpe",
                    },
                )
            ],
        )


# ---------------------------------------------------------------------------
# Three-branch invariant (03 Q2)
# ---------------------------------------------------------------------------


def test_three_branch_two_sided_dsr_informational_pbo_abs(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    scope = _aligned_pool(ledger, direction="two-sided")
    selected = scope[0]
    judge(ledger, scope, _full_battery(selected, conf=0.0, phi_thr=1.0))

    by_stat: dict[str, list] = {}
    for v in ledger.verdicts():
        by_stat.setdefault(v.statistic, []).append(v)

    dsr_v = by_stat["dsr"][0]
    assert dsr_v.role == "informational"
    pbo_v = by_stat["pbo_cscv"][0]
    assert pbo_v.role == "discriminating"
    assert pbo_v.params["metric"] == "abs_sharpe"
    assert by_stat["fdr_by"][0].role == "discriminating"
    for nv in by_stat["noise_control"]:
        assert nv.role == "discriminating"


def test_three_branch_greater_all_discriminating_pbo_signed(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    scope = _aligned_pool(ledger, direction="greater")
    selected = scope[0]
    judge(ledger, scope, _full_battery(selected, conf=0.0, phi_thr=1.0))

    roles = {v.role for v in ledger.verdicts()}
    assert roles == {"discriminating"}
    pbo_v = next(v for v in ledger.verdicts() if v.statistic == "pbo_cscv")
    assert pbo_v.params["metric"] == "sharpe"


def test_three_branch_less_pbo_neg_and_dsr_flip_equivalence(tmp_path: Path) -> None:
    """PBO metric=neg_sharpe; DSR(less on X) equals DSR(greater on −X)."""
    # Branch less on X
    ledger_less = _open(tmp_path / "less")
    scope_less = _aligned_pool(ledger_less, direction="less")
    selected_less = scope_less[0]
    judge(
        ledger_less,
        scope_less,
        [
            Application(
                "dsr",
                {"selected_trial_id": selected_less, "confidence": 0.5},
            ),
            Application(
                "pbo_cscv",
                {
                    "selected_trial_id": selected_less,
                    "n_splits": 4,
                    "phi_threshold": 1.0,
                    "metric": "sharpe",
                },
            ),
        ],
    )
    dsr_less = next(v for v in ledger_less.verdicts() if v.statistic == "dsr")
    pbo_less = next(v for v in ledger_less.verdicts() if v.statistic == "pbo_cscv")
    assert dsr_less.role == "discriminating"
    assert pbo_less.params["metric"] == "neg_sharpe"

    # Branch greater on −X (same numeric series negated)
    ledger_g = _open(tmp_path / "greater")
    hid = ledger_g.register_hypothesis("negated")
    cols = (POOL_COL0, POOL_COL1, POOL_COL2)
    scope_g: list[str] = []
    for col in cols:
        neg = [-x for x in col]
        scope_g.append(
            _register_eval(
                ledger_g, neg, direction="greater", index=INDEX_8, hid=hid
            )
        )
    selected_g = scope_g[0]
    judge(
        ledger_g,
        scope_g,
        [
            Application(
                "dsr",
                {"selected_trial_id": selected_g, "confidence": 0.5},
            )
        ],
    )
    dsr_g = ledger_g.verdicts()[0]
    assert dsr_g.computed["z"] == pytest.approx(dsr_less.computed["z"], abs=1e-9)
    assert abs(dsr_g.computed["sr_star"]) == pytest.approx(
        abs(dsr_less.computed["sr_star"]), abs=1e-9
    )


# ---------------------------------------------------------------------------
# Idle-gate red→green (03 §7): informational DSR cannot kill survival
# ---------------------------------------------------------------------------


def test_idle_gate_informational_dsr_cannot_kill_survival(tmp_path: Path) -> None:
    """Two-sided: pass FDR+PBO(abs)+pool+indiv, DSR reject → still survives.

    The DSR verdict exists, is role=informational, and records its decision.
    Select the pool-max argmax (scope[1]: highest |t|) so pool_max decides it.
    """
    ledger = _open(tmp_path)
    scope = _aligned_pool(ledger, direction="two-sided")
    # POOL_COL1 has the largest |t| under two-sided → pool_max argmax.
    selected = scope[1]

    # Force DSR reject: confidence strictly above achievable DSR.
    _, mat = ledger.matrix(scope)
    srs = [sharpe_ratio(mat[:, j]) for j in range(mat.shape[1])]
    sr_std = float(np.std(srs, ddof=1))
    rho = avg_pairwise_correlation(mat)
    n_eff = implied_independent_trials(mat.shape[1], rho)
    mom = series_moments(ledger.series(selected).values)
    result = dsr(
        mom.sr_hat, mom.n_obs, mom.skew_hat, mom.kurt_hat, sr_std, n_eff
    )
    conf_reject = min(0.999999, result.dsr + 0.05)
    if conf_reject <= result.dsr:
        conf_reject = 0.999999
        assert conf_reject > result.dsr

    judge(
        ledger,
        scope,
        _full_battery(selected, conf=conf_reject, phi_thr=1.0),
    )
    verdicts = ledger.verdicts()
    dsr_v = next(v for v in verdicts if v.statistic == "dsr")
    assert dsr_v.role == "informational"
    assert dsr_v.decisions[selected] == "reject"

    # Discriminating gates for selected all pass under soft thresholds.
    disc = [
        v
        for v in verdicts
        if selected in v.decisions and getattr(v, "role", None) != "informational"
    ]
    assert all(v.decisions[selected] == "pass" for v in disc)
    assert len(disc) >= 4

    assert trial_survives(selected, verdicts) is True
    n_pass, n_face = gates_faced_passed(selected, verdicts)
    assert n_face == len(disc)
    assert n_pass == n_face


# ---------------------------------------------------------------------------
# Aggregation unit: informational cannot flip; role=None still counts
# ---------------------------------------------------------------------------


def test_aggregation_informational_reject_does_not_kill() -> None:
    from types import SimpleNamespace

    verdicts = [
        SimpleNamespace(
            statistic="fdr_by",
            decisions={"t1": "pass"},
            params={},
            role="discriminating",
        ),
        SimpleNamespace(
            statistic="dsr",
            decisions={"t1": "reject"},
            params={},
            role="informational",
        ),
        SimpleNamespace(
            statistic="pbo_cscv",
            decisions={"t1": "pass"},
            params={},
            role="discriminating",
        ),
        SimpleNamespace(
            statistic="noise_control",
            decisions={"t1": "pass"},
            params={"mode": "pool_max"},
            role="discriminating",
        ),
        SimpleNamespace(
            statistic="noise_control",
            decisions={"t1": "pass"},
            params={"mode": "individual"},
            role="discriminating",
        ),
    ]
    assert trial_survives("t1", verdicts) is True
    n_pass, n_face = gates_faced_passed("t1", verdicts)
    assert n_face == 4
    assert n_pass == 4


def test_aggregation_role_none_counts_as_discriminating() -> None:
    from types import SimpleNamespace

    # Legacy: role=None is discriminating and a reject kills.
    verdicts = [
        SimpleNamespace(
            statistic="fdr_by",
            decisions={"t1": "pass"},
            params={},
            role=None,
        ),
        SimpleNamespace(
            statistic="dsr",
            decisions={"t1": "reject"},
            params={},
            role=None,
        ),
    ]
    assert trial_survives("t1", verdicts) is False


def test_aggregation_missing_role_attr_counts_as_discriminating() -> None:
    from types import SimpleNamespace

    # Stubs without .role (existing tests) remain discriminating.
    verdicts = [
        SimpleNamespace(statistic="fdr_by", decisions={"t1": "pass"}, params={}),
        SimpleNamespace(statistic="dsr", decisions={"t1": "reject"}, params={}),
    ]
    assert trial_survives("t1", verdicts) is False


def test_judge_stamps_explicit_role_on_every_verdict(tmp_path: Path) -> None:
    ledger = _open(tmp_path)
    scope = _aligned_pool(ledger, direction="two-sided")
    judge(ledger, scope, _full_battery(scope[0], conf=0.0, phi_thr=1.0))
    for v in ledger.verdicts():
        assert v.role in ("discriminating", "informational")


def test_dsr_less_negation_invariance_of_rho(tmp_path: Path) -> None:
    """Pairwise ρ̂ is negation-invariant; less branch uses negated series."""
    ledger = _open(tmp_path)
    scope = _aligned_pool(ledger, direction="less")
    selected = scope[0]
    _, mat = ledger.matrix(scope)
    rho_raw = float(avg_pairwise_correlation(mat))
    rho_neg = float(avg_pairwise_correlation(-mat))
    assert rho_raw == pytest.approx(rho_neg, abs=1e-12)

    judge(
        ledger,
        scope,
        [
            Application(
                "dsr",
                {"selected_trial_id": selected, "confidence": 0.5},
            )
        ],
    )
    c = ledger.verdicts()[0].computed
    assert c["rho_hat"] == pytest.approx(rho_raw, abs=1e-9)
    # Selected SR under less must be the negated-series SR (positive if raw negative).
    mom_neg = series_moments((-np.asarray(ledger.series(selected).values)).tolist())
    assert c["sr_selected"] == pytest.approx(mom_neg.sr_hat, abs=1e-9)
