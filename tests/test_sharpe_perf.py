"""Lean sharpe_ratio: bit-identity, PBO φ-invariance, and PBO wall-time bound.

Ticket v0.2-14: ``sharpe_ratio`` must compute μ̂/σ̂ directly (mean + Bessel std)
without routing through ``series_moments`` (which also computes skew/kurtosis).
Numeric SR is frozen bit-identical; PBO ranking is unchanged; PBO cost drops.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from court.judge import Application, judge
from court.ledger import (
    DeclaredProtocol,
    Ledger,
    SeConvention,
    Series,
    Window,
)
from court.pbo import pbo_cscv
from court.sharpe import series_moments, sharpe_ratio


def _lean_mean_std_metric(values: object) -> float:
    """Frozen reference metric: μ̂/σ̂ with Bessel σ̂ (same arithmetic as lean SR)."""
    arr = np.asarray(values, dtype=np.float64)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma == 0.0:
        raise ValueError("sigma_hat == 0: Sharpe ratio undefined")
    return mu / sigma


def test_sharpe_ratio_bit_identical_to_mean_std_and_series_moments() -> None:
    """sharpe_ratio(x) == mean/std == series_moments(x).sr_hat exactly (atol=0)."""
    rng = np.random.default_rng(20260718)
    lengths = (2, 3, 8, 17, 64, 240, 480)
    scales = (1e-4, 1e-2, 1.0, 10.0)
    signs = (1.0, -1.0)

    for n in lengths:
        for scale in scales:
            for sign in signs:
                x = sign * scale * rng.standard_normal(n)
                # Ensure non-zero variance (σ̂==0 is a separate raise case).
                if float(np.std(x, ddof=1)) == 0.0:
                    x = x + np.linspace(0.0, 1e-6, n)
                ref = float(np.mean(x)) / float(np.std(x, ddof=1))
                got = sharpe_ratio(x)
                via_moments = series_moments(x).sr_hat
                assert got == ref
                assert got == via_moments


def test_sharpe_ratio_raise_cases_preserved() -> None:
    """σ̂==0, n<2, non-finite: same exceptions/messages as series_moments path."""
    with pytest.raises(ValueError, match="sigma_hat == 0"):
        sharpe_ratio([2.0, 2.0])
    with pytest.raises(ValueError, match="n_obs < 2"):
        sharpe_ratio([1.0])
    with pytest.raises(ValueError, match="non-finite"):
        sharpe_ratio([0.0, float("inf")])


def test_pbo_phi_bit_identical_to_lean_metric_reference(tmp_path: Path) -> None:
    """judge-driven pbo_cscv φ / n_lambda_negative match a local mean/std metric."""
    t, n = 240, 40
    n_splits = 8
    rng = np.random.default_rng(42)
    mat = rng.standard_normal((t, n))
    # Avoid zero-variance half-samples under CSCV (metric must be defined).
    mat = mat + 0.01 * np.arange(t, dtype=np.float64)[:, None]

    ref = pbo_cscv(mat, n_splits, metric=_lean_mean_std_metric)

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("pbo phi invariance")
    index = tuple(f"t{i}" for i in range(t))
    declared = DeclaredProtocol(
        metric="returns",
        window=Window(start="2020-01-01", end="2020-12-31"),
        periods_per_year=252.0,
        direction="greater",
        se=SeConvention(kind="iid"),
    )
    scope: list[str] = []
    for j in range(n):
        tid = ledger.register(
            hid,
            {"kind": "toy", "j": j},
            {"n": t},
            declared,
        )
        ledger.record(
            tid,
            Series(index=index, values=tuple(float(v) for v in mat[:, j])),
        )
        scope.append(tid)

    selected = scope[0]
    judge(
        ledger,
        scope,
        [
            Application(
                statistic="pbo_cscv",
                params={
                    "selected_trial_id": selected,
                    "n_splits": n_splits,
                    "phi_threshold": 1.0,
                    "metric": "sharpe",
                },
            )
        ],
    )
    v = ledger.verdicts()[0]
    assert v.computed["phi"] == ref.phi
    assert v.computed["n_lambda_negative"] == ref.n_lambda_negative
    assert v.computed["n_combinations"] == ref.n_combinations


def test_pbo_via_judge_completes_under_five_seconds(tmp_path: Path) -> None:
    """(T=480, N=100) PBO n_splits=12 via judge finishes in < 5.0 s when SR is lean."""
    t, n = 480, 100
    n_splits = 12
    rng = np.random.default_rng(7)
    mat = rng.standard_normal((t, n))
    mat = mat + 0.01 * np.arange(t, dtype=np.float64)[:, None]

    ledger = Ledger.open(tmp_path / "ledger.jsonl")
    hid = ledger.register_hypothesis("pbo perf")
    index = tuple(f"t{i}" for i in range(t))
    declared = DeclaredProtocol(
        metric="returns",
        window=Window(start="2020-01-01", end="2020-12-31"),
        periods_per_year=252.0,
        direction="greater",
        se=SeConvention(kind="iid"),
    )
    scope: list[str] = []
    for j in range(n):
        tid = ledger.register(
            hid,
            {"kind": "toy", "j": j},
            {"n": t},
            declared,
        )
        ledger.record(
            tid,
            Series(index=index, values=tuple(float(v) for v in mat[:, j])),
        )
        scope.append(tid)

    selected = scope[0]
    t0 = time.perf_counter()
    judge(
        ledger,
        scope,
        [
            Application(
                statistic="pbo_cscv",
                params={
                    "selected_trial_id": selected,
                    "n_splits": n_splits,
                    "phi_threshold": 1.0,
                    "metric": "sharpe",
                },
            )
        ],
    )
    elapsed = time.perf_counter() - t0
    # Pre-change cost ~70 s at n_splits=12; lean path ~1.5 s. Bound 5.0 s.
    assert elapsed < 5.0, f"PBO via judge took {elapsed:.3f}s (need < 5.0s)"
