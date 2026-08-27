"""Smoke tests for the engineering scaffold."""

from __future__ import annotations

import subprocess
import sys


def test_packages_importable() -> None:
    """All scaffold packages import successfully."""
    import adapters
    import court
    import gates
    import harness

    assert court is not None
    assert harness is not None
    assert gates is not None
    assert adapters is not None


def test_court_market_agnostic() -> None:
    """Importing court must not pull in qlib or adapters (iron law 4)."""
    code = """
import sys

import court

assert court is not None
qlib_modules = [name for name in sys.modules if name == "qlib" or name.startswith("qlib.")]
assert not qlib_modules, f"qlib modules leaked into sys.modules: {qlib_modules}"
adapters_modules = [
    name for name in sys.modules if name == "adapters" or name.startswith("adapters.")
]
assert not adapters_modules, f"adapters modules imported with court: {adapters_modules}"
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"subprocess failed (exit {result.returncode}):\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
