"""Bypass red-tests for the 工位三 anti-pattern grep gate.

Written BEFORE the implementation (CR-08). The bypass *set* was enumerated by a 4-lens
workflow (false-positives / evasions / scoping / structural limits) grounded in the real
`court/` source, because the standing failure mode is under-enumerating bypasses.

- POSITIVE: a real hand-rolled duplicate the gate MUST flag (a naive gate would miss the
  aliased/evaded spellings).
- NEGATIVE: legitimate code the gate must NOT flag — the naive bare-token grep's fatal
  false positives (the audited court source, a call to court, a comment). A grep that
  cries wolf here gets ignored.
- LIMIT: what a line-grep structurally cannot catch — pinned so the limit can't be
  silently forgotten.
"""

from __future__ import annotations

import os
from pathlib import Path

from harness import anti_pattern_gate as ap


def _flagged(code: str) -> bool:
    return bool(ap.scan_text(code, path="<t>.py"))


_SHARPE_SRC = "def sharpe_ratio(r):\n    return r.mean() / r.std()\n"
_IC_SRC = "def sharpe_like(c):\n    return np.corrcoef(c, c)[0, 1]\n"


# ---- POSITIVES: must flag (incl. evaded spellings the enumeration surfaced) ----
POSITIVES = {
    "def sharpe": "def sharpe_ratio(r):\n    return r.mean() / r.std()\n",
    "def Sharpe (case)": "def SharpeRatio(r):\n    return r.mean() / r.std(ddof=1)\n",
    "inline .std(ddof=1)+ann": "sr = r.mean() / r.std(ddof=1) * 244 ** 0.5\n",
    "inline np.std+np.sqrt": "sr = np.mean(r) / np.std(r, ddof=1) * np.sqrt(250)\n",
    "corrcoef bare": "rho = np.corrcoef(x, y)[0, 1]\n",
    "corrcoef aliased import": "from numpy import corrcoef as ic\n",
    "corrcoef spaced dot": "rho = np . corrcoef(x, y)[0, 1]\n",
    "corrwith IC": "ic = scores.rank(axis=1).corrwith(fwd.rank(axis=1), axis=1)\n",
    "spearmanr IC": "ic = spearmanr(a, b).correlation\n",
    "pearsonr IC": "ic = pearsonr(a, b).statistic\n",
    "pearsonr aliased import": "from scipy.stats import pearsonr as pr\n",
    "vectorized equity cumprod": "equity = (1 + strat_ret).cumprod()\n",
    "def my_pbo": "def my_pbo(mat, s):\n    return 0.0\n",
    "def dsr (remedy-aligned)": "def dsr(sr, n, sk, ku, std, m):\n    return 0.0\n",
    "def fdr_by (remedy-aligned)": "def fdr_by(pvals, q):\n    return []\n",
    "trailing comment not suppressed": "ic = np.corrcoef(s, f)[0, 1]   # cross-sectional IC\n",
    "escaped quote does not hide code": 's = "foo\\" # x"; ic = np.corrcoef(a, b)[0, 1]\n',
}

# ---- NEGATIVES: must NOT flag (the naive bare-token grep's false positives) ----
NEGATIVES = {
    "court import + call": "from court.sharpe import sharpe_ratio\nsr = sharpe_ratio(ic_series)\n",
    "court.dsr n_trials kwarg": "res = court.dsr(m.sr, m.n, m.sk, m.ku, std, n_trials=N)\n",
    "pbo_cscv call": "oracle = pbo_cscv(mat, 16, metric=court.sharpe_ratio)\n",
    "annualized_sr reuse": "disp = annualized_sr(sr, 252)\n",
    "pure comment": "# never hand-roll np.corrcoef as an IC or a for d in dates PnL loop\n",
    "config string metric": 'cfg = {"metric": "sharpe", "gate": "pbo_cscv"}\n',
    "deflated var holds court result": "deflated = court.dsr(sr, n_trials=N)\n",
    "range n_dates index loop": "for t in range(1, n_dates):\n    panel[t] = phi * panel[t - 1]\n",
    "cumulative feature (not equity)": "mom = ret.rolling(20).sum()\n",
    "volatility factor (std, no mean)": "vol = ret.std(ddof=1) * np.sqrt(252)\n",
    "single-line docstring mention": '"""Never hand-roll np.corrcoef as an IC."""\n',
    "date loop that only loads/masks": "for d in trading_dates:\n    m = pit_mask[d]\n",
}

# ---- LIMITS: a line-grep cannot catch these — pinned as NOT flagged + documented ----
LIMITS = {
    # hand-expanded Pearson arithmetic — no correlation token at all
    "DIY pearson arithmetic": "ic = (xc @ yc) / np.sqrt((xc @ xc) * (yc @ yc))\n",
    # the WORST duplicate per the skill: SR standard error dropping skew/kurtosis — tokenless
    "DIY SR standard error": "se = math.sqrt((1 - g3 * sr + (g4 - 1) / 4 * sr**2) / (n - 1))\n",
    # aliased name + native-frequency (no 'sharpe', no annualization literal)
    "aliased native-freq sharpe": "def perf(r):\n    return r.mean() / r.std(ddof=1)\n",
    # a for-loop equity accumulation: the 'dates' iteration is common for legit loading, so
    # a bare date-loop pattern cries wolf — the equity is confirmable only in the loop body
    # (a line grep can't join lines). Caught instead via the vectorized `equity=...cumprod`.
    "for-loop equity over dates": "for d in trading_dates:\n    equity *= 1 + ret[d]\n",
}


def test_positives_flagged():
    missed = [name for name, code in POSITIVES.items() if not _flagged(code)]
    assert not missed, f"anti-patterns not flagged (evasions slipped through): {missed}"


def test_negatives_not_flagged():
    barked = [name for name, code in NEGATIVES.items() if _flagged(code)]
    assert not barked, f"false positives (gate cries wolf on legit code): {barked}"


def test_stated_limits_are_not_flagged():
    """These are honest limits — a line grep can't catch them; pin so we don't pretend."""
    caught = [name for name, code in LIMITS.items() if _flagged(code)]
    assert not caught, f"unexpectedly flagged a documented grep-blind limit: {caught}"


def test_comment_strip_does_not_suppress_code(tmp_path: Path):
    """A trailing #-comment must not turn an offending line into a no-op."""
    assert _flagged("ic = np.corrcoef(s, f)[0, 1]  # IC\n") is True
    assert _flagged("# ic = np.corrcoef(s, f)  is what NOT to do\n") is False


def test_excludes_audited_dirs_by_path_component(tmp_path: Path):
    """court/ and adapters/ (audited source) are excluded; research/ is scanned."""
    (tmp_path / "court").mkdir()
    (tmp_path / "court" / "sharpe.py").write_text(_SHARPE_SRC)
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "f.py").write_text(_SHARPE_SRC)
    findings = ap.scan_tree(tmp_path)
    paths = {str(f.path) for f in findings}
    assert not any("court/sharpe.py" in p for p in paths), "audited court/ must not be flagged"
    assert any("research/f.py" in p for p in paths), "factor code under research/ must be scanned"


def test_alpha_court_substring_is_not_a_total_bypass(tmp_path: Path):
    """The repo lives under 'alpha-court/' — a substring exclusion on 'court' would skip
    the whole tree. Exclusion must be by path *component*, so a factor file under an
    'alpha-court'-named root is still scanned."""
    root = tmp_path / "alpha-court" / "research"
    root.mkdir(parents=True)
    (root / "f.py").write_text("ic = np.corrcoef(s, f)[0, 1]\n")
    findings = ap.scan_tree(tmp_path / "alpha-court")
    assert findings, "a factor file under an 'alpha-court' path must still be scanned"


def test_tests_and_gate_self_excluded(tmp_path: Path):
    """tests/ (fixtures exercise the oracle) and harness/ (the gate's own literals) are excluded."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(_IC_SRC)
    (tmp_path / "harness").mkdir()
    (tmp_path / "harness" / "anti_pattern_gate.py").write_text("PAT = 'np.corrcoef'\n")
    assert ap.scan_tree(tmp_path) == []


def test_notebooks_reported_not_silently_skipped(tmp_path: Path):
    """.ipynb research is out of scope for v1 — but the skip must be LOUD, not silent."""
    (tmp_path / "n.ipynb").write_text('{"cells": []}\n')
    result = ap.scan_paths([tmp_path])
    assert result.skipped_notebooks >= 1


def test_directly_passed_file_in_audited_dir_is_skipped(tmp_path: Path):
    """Passing court/x.py directly must behave like the tree walk: audited dir, not flagged."""
    (tmp_path / "court").mkdir()
    f = tmp_path / "court" / "x.py"
    f.write_text(_SHARPE_SRC)
    assert ap.scan_paths([f]).findings == []


def test_repo_self_scan_is_clean():
    """The gate must not flag the project's own audited/demo code (else it's a standing red)."""
    import subprocess
    import sys

    repo = Path(ap.__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "-m", "harness.anti_pattern_gate", str(repo)],
        cwd=repo,
        env={"PYTHONPATH": str(repo), "PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"repo self-scan flagged something:\n{r.stderr}"


# ============================================================================
# reuse-ok acknowledge — bypass red-tests (written BEFORE impl; grok-enum lens)
# The acknowledge is a NEW mechanism: a flagged physical line is exempted iff it
# carries a real trailing `# reuse-ok: <non-empty reason>` COMMENT. Every bypass
# below must be REJECTED (still flagged) except the one legit case.
# ============================================================================

_HARDROLL = "sr = r.mean() / r.std(ddof=1) * np.sqrt(252)"


def test_ack_legit_trailing_comment_exempts():
    code = _HARDROLL + "  # reuse-ok: reuses court.sharpe pending refactor\n"
    assert ap.scan_text(code, "<t>.py") == []  # exempted


def test_ack_empty_reason_still_flagged():  # ACK-04
    code = _HARDROLL + "  # reuse-ok:\n"
    assert ap.scan_text(code, "<t>.py"), "empty reason must NOT exempt"


def test_ack_whitespace_reason_still_flagged():  # ACK-04
    code = _HARDROLL + "  # reuse-ok:    \n"
    assert ap.scan_text(code, "<t>.py"), "whitespace-only reason must NOT exempt"


def test_ack_inside_string_literal_still_flagged():  # ACK-01
    code = 's = "# reuse-ok: totally fine"; ' + _HARDROLL + "\n"
    assert ap.scan_text(code, "<t>.py"), "marker inside a string must NOT exempt"


def test_ack_file_level_blanket_does_not_exempt_other_lines():  # ACK-02
    code = "# reuse-ok: everything in this file\n" + _HARDROLL + "\n"
    findings = ap.scan_text(code, "<t>.py")
    assert findings, "a blanket top-of-file reuse-ok must NOT exempt a later line"


def test_ack_on_different_line_does_not_exempt():  # ACK-07
    code = "# reuse-ok: for the next line\n" + _HARDROLL + "\n"
    assert ap.scan_text(code, "<t>.py"), "ack on a different physical line must NOT exempt"


def test_ack_noqa_is_not_reuse_ok():  # ACK-10
    code = _HARDROLL + "  # noqa: E501\n"
    assert ap.scan_text(code, "<t>.py"), "# noqa must NOT be read as reuse-ok"


def test_ack_prose_mention_without_colon_does_not_exempt():  # ACK-10
    code = _HARDROLL + "  # this is reuse-ok honestly\n"
    assert ap.scan_text(code, "<t>.py"), "prose mention w/o 'reuse-ok:' form must NOT exempt"


def test_ack_hash_in_reason_still_exempts():  # ACK-13 (fails safe the other way: must PASS)
    code = _HARDROLL + "  # reuse-ok: see issue #42 for the refactor\n"
    assert ap.scan_text(code, "<t>.py") == [], "a '#' inside the reason must not break exemption"


def test_ack_only_exempts_its_own_line():
    code = _HARDROLL + "  # reuse-ok: justified\n" + "ic = np.corrcoef(x, y)[0, 1]\n"
    findings = ap.scan_text(code, "<t>.py")
    assert len(findings) == 1 and "corrcoef" in (findings[0].pattern + findings[0].line)


def test_ack_after_type_ignore_still_exempts():  # grok RP-1: type:ignore then reuse-ok
    code = _HARDROLL + "  # type: ignore  # reuse-ok: reuses court.sharpe pending refactor\n"
    assert ap.scan_text(code, "<t>.py") == [], "reuse-ok after another comment must still exempt"
