"""Agent governance layer: pre-registration gates, referee, and dispatch.

v0.2 certified-path modules in this package:
- ``aggregation_policy`` — pre-registration object and single unanimous-
  discriminating aggregation implementation (ticket 09)
- ``run`` / ``seal`` / ``anchor`` / ``verify`` — CertifiedRun loop, seal
  certificate, pluggable anchors, and tamper-evident verification
  (ticket 07; prereg-gate.md)

Pre-existing session-governance modules (unchanged):
``trial_counter``, ``confirm_gate``, ``anti_pattern_gate``.
"""

from harness.aggregation_policy import (
    AggregationPolicy,
    apply_policy,
    declare_policy,
    read_declared_policy,
)
from harness.anchor import FileAnchor, GitAnchor, NoopAnchor
from harness.run import CertificationError, CertifiedRun
from harness.verify import VerificationReport, verify

__all__ = [
    "AggregationPolicy",
    "CertificationError",
    "CertifiedRun",
    "FileAnchor",
    "GitAnchor",
    "NoopAnchor",
    "VerificationReport",
    "apply_policy",
    "declare_policy",
    "read_declared_policy",
    "verify",
]
