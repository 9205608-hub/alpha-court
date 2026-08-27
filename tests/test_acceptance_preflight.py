"""Commander-side acceptance preflight (v0.2 meta-review top-criticism #2).

Asserts, against the COMMITTED frozen artifacts, the invariants that must hold
BEFORE any multi-hour real-data burn is launched. Historical red: at `c987a5b9`
(the pre-sweep freeze) this test would have FAILED — `beta_t_icir_targets`
contained 3.0 but the frozen β* table had no 3.0 key, which cost 160
uninformative arms (~10h) in the 2026-07-18/19 sweep and forced the appendix
re-run. Added 2026-07-20 when the role-reversal review ruled that
"contract-secondary" prose was not a re-runnable guard.

Scope (stated after grok RP-1 review, same day): these tests bind the
DEFAULT `PowerConfig` against the committed frozen table — the default path is
what launch commands actually use. A CLI-overridden target list is guarded at
runtime instead by `require_beta_star_targets` (rework-02 FIX-A, fail-closed
before any arm runs); the two layers together cover both routes.
"""

from __future__ import annotations

import json
from pathlib import Path

FROZEN = Path(__file__).resolve().parent.parent / ".scratch/v0.2/power-frozen/calibration.json"


def test_frozen_beta_star_covers_configured_beta_t_targets() -> None:
    from examples.power_calibration.config import PowerConfig

    cfg = PowerConfig(out_dir="unused")
    frozen = json.loads(FROZEN.read_text())
    keys = {float(k) for k in frozen["beta_star"]}
    missing = [t for t in cfg.beta_t_icir_targets if float(t) not in keys]
    assert not missing, (
        f"frozen β* table {FROZEN} lacks configured beta_t targets {missing}; "
        "re-run calibrate (it freezes strength_grid ∪ beta_t_icir_targets) "
        "BEFORE launching any sweep"
    )


def test_frozen_beta_star_covers_strength_grid() -> None:
    from examples.power_calibration.config import FROZEN_STRENGTH_GRID

    frozen = json.loads(FROZEN.read_text())
    keys = {float(k) for k in frozen["beta_star"]}
    missing = [s for s in FROZEN_STRENGTH_GRID if float(s) not in keys]
    assert not missing, f"frozen β* table lacks strength-grid entries {missing}"
