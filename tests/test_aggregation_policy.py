"""Tests for harness.aggregation_policy (ticket v0.2-09).

Pre-registration object, declaration-event ordering, single code path for
unanimous-discriminating aggregation.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from court.ledger import DeclaredProtocol, Ledger, Series, Window

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _window() -> Window:
    return Window(start="2020-01-01", end="2020-12-31")


def _declared() -> DeclaredProtocol:
    return DeclaredProtocol(
        metric="returns",
        window=_window(),
        periods_per_year=252.0,
    )


def _series() -> Series:
    return Series(index=("d1", "d2", "d3"), values=(0.01, -0.02, 0.03))


def _canonical_policy():
    from harness.aggregation_policy import AggregationPolicy

    return AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params={},
    )


def _v(statistic: str, decisions: dict[str, str], **kwargs):
    return SimpleNamespace(statistic=statistic, decisions=decisions, **kwargs)


def _ledger_with_one_verdict(tmp_path: Path) -> Ledger:
    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("claim")
    tid = ledger.register(hid, {}, {}, _declared())
    ledger.record(tid, _series())
    ledger.append_verdict("dsr", [tid], {}, {}, {tid: "pass"}, role="discriminating")
    return ledger


# ---------------------------------------------------------------------------
# Construction & payload
# ---------------------------------------------------------------------------


def test_construction_empty_policy_id_raises():
    from harness.aggregation_policy import AggregationPolicy

    with pytest.raises(ValueError):
        AggregationPolicy(policy_id="", rule="unanimous-discriminating", params={})


def test_construction_unknown_rule_raises():
    from harness.aggregation_policy import AggregationPolicy

    with pytest.raises(ValueError):
        AggregationPolicy(
            policy_id="unanimous-discriminating-v1",
            rule="majority-vote",
            params={},
        )


def test_construction_nonempty_params_raises():
    from harness.aggregation_policy import AggregationPolicy

    with pytest.raises(ValueError):
        AggregationPolicy(
            policy_id="unanimous-discriminating-v1",
            rule="unanimous-discriminating",
            params={"k": 1},
        )


def test_payload_round_trip():
    from harness.aggregation_policy import AggregationPolicy

    policy = _canonical_policy()
    payload = policy.to_payload()
    assert payload == {
        "kind": "aggregation_policy",
        "policy_id": "unanimous-discriminating-v1",
        "rule": "unanimous-discriminating",
        "params": {},
    }
    back = AggregationPolicy.from_payload(payload)
    assert back == policy


def test_from_payload_rejects_wrong_kind():
    from harness.aggregation_policy import AggregationPolicy

    with pytest.raises(ValueError):
        AggregationPolicy.from_payload(
            {
                "kind": "run_config",
                "policy_id": "unanimous-discriminating-v1",
                "rule": "unanimous-discriminating",
                "params": {},
            }
        )


def test_from_payload_rejects_missing_keys():
    from harness.aggregation_policy import AggregationPolicy

    with pytest.raises(ValueError):
        AggregationPolicy.from_payload(
            {
                "kind": "aggregation_policy",
                "policy_id": "unanimous-discriminating-v1",
                "rule": "unanimous-discriminating",
            }
        )


def test_from_payload_rejects_junk_types():
    from harness.aggregation_policy import AggregationPolicy

    with pytest.raises(ValueError):
        AggregationPolicy.from_payload("not-a-dict")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        AggregationPolicy.from_payload(
            {
                "kind": "aggregation_policy",
                "policy_id": 123,
                "rule": "unanimous-discriminating",
                "params": {},
            }
        )


# ---------------------------------------------------------------------------
# declare / read pre-registration
# ---------------------------------------------------------------------------


def test_declare_and_read_round_trip_advances_chain(tmp_path: Path):
    from harness.aggregation_policy import declare_policy, read_declared_policy

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    assert ledger.chain_head == "0" * 64
    policy = _canonical_policy()
    did = declare_policy(ledger, policy)
    assert did == "d-000001"
    head_after = ledger.chain_head
    assert head_after is not None
    assert head_after != "0" * 64

    found = read_declared_policy(ledger)
    assert found is not None
    declaration_id, back = found
    assert declaration_id == did
    assert back == policy


def test_declare_after_verdict_raises(tmp_path: Path):
    from harness.aggregation_policy import declare_policy

    ledger = _ledger_with_one_verdict(tmp_path)
    assert ledger.verdicts()
    with pytest.raises(ValueError):
        declare_policy(ledger, _canonical_policy())


def test_duplicate_declare_raises(tmp_path: Path):
    from harness.aggregation_policy import declare_policy

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    policy = _canonical_policy()
    declare_policy(ledger, policy)
    with pytest.raises(ValueError):
        declare_policy(ledger, policy)


def test_second_different_policy_raises(tmp_path: Path):
    from harness.aggregation_policy import AggregationPolicy, declare_policy

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    declare_policy(ledger, _canonical_policy())
    other = AggregationPolicy(
        policy_id="other-id",
        rule="unanimous-discriminating",
        params={},
    )
    with pytest.raises(ValueError):
        declare_policy(ledger, other)


def test_read_two_policy_declarations_raises(tmp_path: Path):
    from harness.aggregation_policy import read_declared_policy

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    payload = _canonical_policy().to_payload()
    ledger.append_declaration(payload)
    ledger.append_declaration(
        {
            "kind": "aggregation_policy",
            "policy_id": "other-id",
            "rule": "unanimous-discriminating",
            "params": {},
        }
    )
    with pytest.raises(ValueError):
        read_declared_policy(ledger)


def test_read_absent_returns_none(tmp_path: Path):
    from harness.aggregation_policy import read_declared_policy

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    ledger.append_declaration({"kind": "run_config", "n": 1})
    assert read_declared_policy(ledger) is None


# ---------------------------------------------------------------------------
# apply_policy / aggregation semantics (role-aware, ticket 08)
# ---------------------------------------------------------------------------


def test_apply_policy_informational_reject_cannot_kill():
    from harness.aggregation_policy import apply_policy, survivor_count, survivor_ids

    verdicts = [
        _v("fdr_by", {"t0001": "pass"}),
        SimpleNamespace(
            statistic="dsr",
            decisions={"t0001": "reject"},
            role="informational",
        ),
        _v("pbo_cscv", {"t0001": "pass"}),
    ]
    policy = _canonical_policy()
    out = apply_policy(policy, ["t0001"], verdicts)
    assert out == {"survivor_ids": ["t0001"], "n_survivors": 1}
    assert survivor_ids(["t0001"], verdicts) == out["survivor_ids"]
    assert survivor_count(["t0001"], verdicts) == out["n_survivors"]


def test_apply_policy_discriminating_reject_kills():
    from harness.aggregation_policy import apply_policy

    verdicts = [
        _v("fdr_by", {"t0001": "pass", "t0002": "reject"}),
        _v("dsr", {"t0001": "pass"}),
    ]
    out = apply_policy(_canonical_policy(), ["t0001", "t0002"], verdicts)
    assert out["survivor_ids"] == ["t0001"]
    assert out["n_survivors"] == 1


def test_apply_policy_none_role_counts_as_discriminating():
    from harness.aggregation_policy import apply_policy

    verdicts = [
        SimpleNamespace(decisions={"t0001": "pass"}, role=None),
        SimpleNamespace(decisions={"t0001": "reject"}, role=None),
    ]
    out = apply_policy(_canonical_policy(), ["t0001"], verdicts)
    assert out["n_survivors"] == 0


def test_apply_policy_missing_role_attribute_counts():
    from harness.aggregation_policy import apply_policy

    # Stub without role attribute (legacy)
    verdicts = [
        SimpleNamespace(decisions={"t0001": "pass"}),
        SimpleNamespace(decisions={"t0001": "reject"}),
    ]
    out = apply_policy(_canonical_policy(), ["t0001"], verdicts)
    assert out["n_survivors"] == 0


def test_apply_policy_no_free_pass():
    from harness.aggregation_policy import apply_policy, trial_survives

    verdicts: list = []
    assert trial_survives("t0001", verdicts) is False
    out = apply_policy(_canonical_policy(), ["t0001"], verdicts)
    assert out == {"survivor_ids": [], "n_survivors": 0}


def test_apply_policy_unknown_rule_raises():
    from harness.aggregation_policy import AggregationPolicy, apply_policy

    bad = object.__new__(AggregationPolicy)
    object.__setattr__(bad, "policy_id", "x")
    object.__setattr__(bad, "rule", "unknown-rule")
    object.__setattr__(bad, "params", {})
    with pytest.raises(ValueError):
        apply_policy(bad, ["t0001"], [])


def test_demo_delegation_is_identity():
    """Single code path: demo re-exports the harness functions by identity."""
    import examples.killer_demo.aggregate as demo_agg
    import harness.aggregation_policy as harness_agg

    assert demo_agg.trial_survives is harness_agg.trial_survives
    assert demo_agg.verdicts_deciding is harness_agg.verdicts_deciding
    assert demo_agg.survivor_ids is harness_agg.survivor_ids
    assert demo_agg.survivor_count is harness_agg.survivor_count
    assert demo_agg.gates_faced_passed is harness_agg.gates_faced_passed


def test_params_not_aliased_to_caller_dict():
    """Construction validates params == {}; storing the caller's dict by
    reference lets post-construction mutation bypass that invariant (v0.2-12 G)."""
    from harness.aggregation_policy import AggregationPolicy

    p: dict = {}
    policy = AggregationPolicy(
        policy_id="unanimous-discriminating-v1",
        rule="unanimous-discriminating",
        params=p,
    )
    p["smuggled"] = 1
    assert policy.params == {}
