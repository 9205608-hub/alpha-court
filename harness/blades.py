"""Blade declaration helpers and the structural blade protocol.

v0.3 blades are cheap second-scale gates that screen trial candidates before
the expensive battery. This module owns only the on-chain declaration
mechanics (kinds ``blade_calibration`` / ``blade_report`` / ``blade_roster``)
and report validation. No blade statistics live here.

Blade protocol (structural; no ABC required)
--------------------------------------------
A blade is any object with:

- attribute ``name: str``
- method ``run(trial_id: str, spec: dict, params: dict, declared, series) -> dict``

``run`` returns a report dict whose ``"blade"`` key equals ``blade.name``.
Required report keys are validated by ``validate_blade_report``. Threshold
calibration must be on chain (kind ``blade_calibration``) before the first
``blade_report``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from court.ledger import DeclarationRecord, Ledger

BLADE_REPORT_KIND = "blade_report"
BLADE_CALIBRATION_KIND = "blade_calibration"
BLADE_ROSTER_KIND = "blade_roster"

_REQUIRED_REPORT_KEYS = ("blade", "flagged", "statistics", "evidence", "params")


def validate_blade_report(report: dict) -> None:
    """Raise ``ValueError`` if ``report`` is not a well-formed blade report.

    Required top-level keys: ``blade`` (non-empty str), ``flagged`` (bool),
    ``statistics`` / ``evidence`` / ``params`` (dicts). Unknown extra keys
    are allowed.
    """
    if not isinstance(report, dict):
        raise ValueError(f"blade report must be a dict, got {type(report).__name__}")
    missing = [k for k in _REQUIRED_REPORT_KEYS if k not in report]
    if missing:
        raise ValueError(f"blade report missing required key(s): {missing}")
    blade = report["blade"]
    if not isinstance(blade, str) or not blade:
        raise ValueError(f"blade report 'blade' must be a non-empty str, got {blade!r}")
    if not isinstance(report["flagged"], bool):
        raise ValueError(
            f"blade report 'flagged' must be a bool, got {type(report['flagged']).__name__}"
        )
    for key in ("statistics", "evidence", "params"):
        if not isinstance(report[key], dict):
            raise ValueError(
                f"blade report {key!r} must be a dict, got {type(report[key]).__name__}"
            )


def _require_open_unit_interval(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a float in (0, 1), got {value!r}")
    if not (0.0 < float(value) < 1.0):
        raise ValueError(f"{name} must be in (0, 1), got {value!r}")


def append_blade_calibration(
    ledger: Ledger,
    *,
    seed_root: int,
    null_recipe: dict,
    target_fpr: dict,
    thresholds: dict,
    calibration_fingerprint: str,
) -> str:
    """Append a ``blade_calibration`` declaration; return its declaration id."""
    if not isinstance(null_recipe, dict):
        raise ValueError(f"null_recipe must be a dict, got {type(null_recipe).__name__}")
    if not isinstance(thresholds, dict):
        raise ValueError(f"thresholds must be a dict, got {type(thresholds).__name__}")
    if not isinstance(calibration_fingerprint, str) or not calibration_fingerprint:
        raise ValueError("calibration_fingerprint must be a non-empty str")
    if not isinstance(target_fpr, dict):
        raise ValueError(f"target_fpr must be a dict, got {type(target_fpr).__name__}")
    if "per_blade" not in target_fpr or "joint" not in target_fpr:
        raise ValueError("target_fpr must contain float keys 'per_blade' and 'joint'")
    _require_open_unit_interval(target_fpr["per_blade"], "target_fpr['per_blade']")
    _require_open_unit_interval(target_fpr["joint"], "target_fpr['joint']")
    if find_blade_calibration(ledger) is not None:
        raise ValueError("blade_calibration declaration already exists on ledger")
    return ledger.append_declaration(
        {
            "kind": BLADE_CALIBRATION_KIND,
            "seed_root": seed_root,
            "null_recipe": null_recipe,
            "target_fpr": target_fpr,
            "thresholds": thresholds,
            "calibration_fingerprint": calibration_fingerprint,
        }
    )


def find_blade_calibration_record(ledger: Ledger) -> DeclarationRecord | None:
    """First ``blade_calibration`` declaration record, else ``None``."""
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_CALIBRATION_KIND:
            return rec
    return None


def find_blade_calibration(ledger: Ledger) -> dict | None:
    """Payload of the first ``blade_calibration`` declaration, else ``None``."""
    rec = find_blade_calibration_record(ledger)
    return rec.payload if rec is not None else None


def roster_entry(blade: Any) -> dict:
    """``{name, params_fingerprint}`` for one attached blade.

    Fingerprint is sha256 hex of canonical JSON (sorted keys, compact
    separators) of ``getattr(blade, "roster_params", {})``. Blades without
    ``roster_params`` fingerprint the empty dict.
    """
    params = getattr(blade, "roster_params", {})
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"name": blade.name, "params_fingerprint": fingerprint}


def append_blade_roster(ledger: Ledger, blades: Sequence[Any]) -> str:
    """Append a ``blade_roster`` declaration; return its declaration id.

    Roster order is attachment order. A second roster on the same ledger
    raises ``ValueError``.
    """
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_ROSTER_KIND:
            raise ValueError("blade_roster declaration already exists on ledger")
    return ledger.append_declaration(
        {
            "kind": BLADE_ROSTER_KIND,
            "roster": [roster_entry(b) for b in blades],
        }
    )


def find_blade_roster(ledger: Ledger) -> list[dict] | None:
    """Roster list of the first ``blade_roster`` declaration, else ``None``."""
    for rec in ledger.declarations():
        payload = rec.payload
        if isinstance(payload, dict) and payload.get("kind") == BLADE_ROSTER_KIND:
            roster = payload.get("roster")
            return roster if isinstance(roster, list) else None
    return None
