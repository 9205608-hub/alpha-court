"""Aggregation / selection policy as a pre-registration object (prereg-gate.md §4.2 / §7).

v0.2 ships a single rule: unanimous over discriminating verdicts only
(selection-verdict-isomorphism.md Q3; ticket 08 role semantics). The policy
must be declared on the ledger before the first verdict so it cannot be
cherry-picked post-hoc. Seal-side cross-check is ticket 07.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

_KIND = "aggregation_policy"
_RULE_UNANIMOUS_DISCRIMINATING = "unanimous-discriminating"
_REQUIRED_PAYLOAD_KEYS = frozenset({"kind", "policy_id", "rule", "params"})


@dataclass(frozen=True)
class AggregationPolicy:
    """Serializable pre-registration object for verdict aggregation.

    Parameters
    ----------
    policy_id:
        Non-empty identifier. Canonical v0.2 instance:
        ``\"unanimous-discriminating-v1\"``.
    rule:
        Literal ``\"unanimous-discriminating\"`` (only rule in v0.2).
    params:
        Must be ``{}`` in v0.2 (reserved for future rule knobs).
    """

    policy_id: str
    rule: str
    params: dict

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id:
            raise ValueError(
                f"policy_id must be a non-empty str, got {self.policy_id!r}"
            )
        if self.rule != _RULE_UNANIMOUS_DISCRIMINATING:
            raise ValueError(
                f"unknown aggregation rule {self.rule!r}; "
                f"v0.2 supports only {_RULE_UNANIMOUS_DISCRIMINATING!r}"
            )
        if not isinstance(self.params, dict) or self.params != {}:
            raise ValueError(
                f"params must be empty dict {{}} in v0.2, got {self.params!r}"
            )
        # Detach from the caller's dict: an aliased reference lets
        # post-construction mutation bypass the == {} invariant (v0.2-12 G).
        object.__setattr__(self, "params", {})

    def to_payload(self) -> dict:
        """Court-opaque declaration payload (kind + fields)."""
        return {
            "kind": _KIND,
            "policy_id": self.policy_id,
            "rule": self.rule,
            "params": {},
        }

    @classmethod
    def from_payload(cls, payload: dict) -> AggregationPolicy:
        """Parse and validate a declaration payload; fail-closed on junk."""
        if not isinstance(payload, dict):
            raise ValueError(
                f"aggregation_policy payload must be a dict, got {type(payload).__name__}"
            )
        missing = _REQUIRED_PAYLOAD_KEYS - set(payload.keys())
        if missing:
            raise ValueError(
                f"aggregation_policy payload missing keys: {sorted(missing)}"
            )
        kind = payload.get("kind")
        if kind != _KIND:
            raise ValueError(
                f"aggregation_policy payload kind must be {_KIND!r}, got {kind!r}"
            )
        policy_id = payload.get("policy_id")
        rule = payload.get("rule")
        params = payload.get("params")
        if not isinstance(policy_id, str):
            raise ValueError(
                f"policy_id must be a str, got {type(policy_id).__name__}"
            )
        if not isinstance(rule, str):
            raise ValueError(f"rule must be a str, got {type(rule).__name__}")
        if not isinstance(params, dict):
            raise ValueError(f"params must be a dict, got {type(params).__name__}")
        return cls(policy_id=policy_id, rule=rule, params=params)


def _is_policy_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("kind") == _KIND


def declare_policy(ledger: Any, policy: AggregationPolicy) -> str:
    """Append the policy as a court-opaque declaration; return declaration id.

    Fail-closed ordering (prereg-gate.md §7): policy must precede the first
    verdict, and at most one policy declaration per ledger.
    """
    if not isinstance(policy, AggregationPolicy):
        raise ValueError(
            f"policy must be AggregationPolicy, got {type(policy).__name__}"
        )
    if ledger.verdicts():
        raise ValueError(
            "aggregation policy must be declared before the first verdict"
        )
    if read_declared_policy(ledger) is not None:
        raise ValueError("aggregation policy already declared on this ledger")
    return ledger.append_declaration(policy.to_payload())


def read_declared_policy(
    ledger: Any,
) -> tuple[str, AggregationPolicy] | None:
    """Return ``(declaration_id, policy)`` if exactly one policy is declared.

    ``None`` if absent; more than one raises (corrupt pre-registration).
    """
    found: list[tuple[str, AggregationPolicy]] = []
    for rec in ledger.declarations():
        payload = rec.payload
        if not _is_policy_payload(payload):
            continue
        found.append((rec.declaration_id, AggregationPolicy.from_payload(payload)))
    if not found:
        return None
    if len(found) > 1:
        raise ValueError(
            f"corrupt pre-registration: {len(found)} aggregation_policy "
            "declarations on ledger (expected at most one)"
        )
    return found[0]


# ---------------------------------------------------------------------------
# Unanimous-discriminating rule (single implementation; demo re-exports)
# ---------------------------------------------------------------------------


def _is_discriminating(verdict: Any) -> bool:
    """True unless role is explicitly informational (legacy None → count)."""
    role = getattr(verdict, "role", None)
    return role != "informational"


def verdicts_deciding(
    trial_id: str,
    verdicts: Sequence[Any],
) -> list[Any]:
    """Return verdict records whose ``decisions`` map includes ``trial_id``."""
    return [v for v in verdicts if trial_id in getattr(v, "decisions", {})]


def trial_survives(
    trial_id: str,
    verdicts: Sequence[Any],
) -> bool:
    """Unanimous over discriminating gates only.

    Every deciding verdict with ``role != \"informational\"`` must be
    ``\"pass\"``. Informational verdicts do not vote. If no discriminating
    verdict decides the trial, it does not survive (no free pass).
    """
    deciding = [
        v for v in verdicts_deciding(trial_id, verdicts) if _is_discriminating(v)
    ]
    if not deciding:
        return False
    return all(v.decisions[trial_id] == "pass" for v in deciding)


def gates_faced_passed(
    trial_id: str,
    verdicts: Sequence[Any],
) -> tuple[int, int]:
    """Return ``(n_passed, n_faced)`` over discriminating verdicts only."""
    deciding = [
        v for v in verdicts_deciding(trial_id, verdicts) if _is_discriminating(v)
    ]
    n_faced = len(deciding)
    n_passed = sum(1 for v in deciding if v.decisions[trial_id] == "pass")
    return n_passed, n_faced


def survivor_ids(
    trial_ids: Sequence[str],
    verdicts: Sequence[Any],
) -> list[str]:
    """Trial ids that survive under the discriminating-unanimous rule, in order."""
    return [tid for tid in trial_ids if trial_survives(tid, verdicts)]


def survivor_count(
    trial_ids: Sequence[str],
    verdicts: Sequence[Any],
) -> int:
    """Number of survivors out of ``len(trial_ids)``."""
    return len(survivor_ids(trial_ids, verdicts))


def apply_policy(
    policy: AggregationPolicy,
    trial_ids: Sequence[str],
    verdicts: Sequence[Any],
) -> dict:
    """Apply a known aggregation policy; return survivor_ids and n_survivors.

    Validates that ``policy.rule`` is a known rule (fail-closed). Does not
    re-run construction guards (unknown rules may arrive via dataclass bypass).
    """
    if not isinstance(policy, AggregationPolicy):
        raise ValueError(
            f"policy must be AggregationPolicy, got {type(policy).__name__}"
        )
    if policy.rule != _RULE_UNANIMOUS_DISCRIMINATING:
        raise ValueError(
            f"unknown aggregation rule {policy.rule!r}; "
            f"v0.2 supports only {_RULE_UNANIMOUS_DISCRIMINATING!r}"
        )
    ids = survivor_ids(trial_ids, verdicts)
    return {"survivor_ids": ids, "n_survivors": len(ids)}
