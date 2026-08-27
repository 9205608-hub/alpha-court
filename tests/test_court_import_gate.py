"""Bypass red-tests for candidate A — static AST court-import boundary gate.

Written BEFORE the implementation (CR-08). The bypass set was enumerated by a 4-lens workflow
(import-form / allowlist-boundary / scope-carrier / ast-mechanics), 63 vectors, frozen in
`.scratch/court-import/bypass-enum-raw.json`.

Iron law #2: `court/` (the market-agnostic kernel) must import ONLY stdlib + __future__ +
court.* + {numpy, scipy}. This STATIC gate reads the source; it complements — does not replace —
the existing IMPORT-TIME dynamic smoke (which only sees imports that execute at `import court`).

- BYPASS: a market import that must be FLAGGED.
- FALSE-FLAG: a legit import that must PASS (a gate that barks on the clean tree gets disabled).
- DECLARED-LIMIT: coupling AST cannot see — asserted to PASS and documented, never oversold.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from harness import court_import_gate as cig

REPO = Path(__file__).resolve().parents[1]


def _flag(code: str, path: str = "court/probe.py") -> list:
    return cig.check_source(code, path)


def _flagged(code: str, path: str = "court/probe.py") -> bool:
    return bool(_flag(code, path))


# ========================= the day-one guard (V02) =========================


def test_clean_court_tree_has_zero_violations():
    """The REAL court/ must pass — a gate that reds on the clean tree gets disabled."""
    violations = cig.scan_court(REPO / "court")
    assert violations == [], f"gate flags the clean court/ tree: {violations}"


# ============================ BYPASSES: must flag ==========================


def test_plain_market_import_flagged():
    assert _flagged("import qlib\n")


def test_from_market_submodule_flagged():
    assert _flagged("from qlib.data import D\n")


def test_market_import_aliased_flagged():  # alias.name, not asname
    assert _flagged("import qlib as np\n")  # bound as 'np' but the real module is qlib


def test_multi_alias_second_name_flagged():  # V03 multi-alias
    assert _flagged("import numpy, baostock\n")


def test_market_submodule_toplevel_flagged():
    assert _flagged("import qlib.data.handler\n")


@pytest.mark.parametrize(
    "code",
    [
        "def f():\n    import baostock\n    return baostock\n",  # in a function
        "class C:\n    import akshare\n",  # class body
        "if True:\n    import tushare\n",  # conditional
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import qlib\n",  # type-only
        "try:\n    import qlib\nexcept ImportError:\n    qlib = None\n",  # try/except fallback
    ],
)
def test_nested_market_imports_flagged(code):  # V05 — the dynamic smoke's blind spot
    assert _flagged(code)


def test_relative_escape_module_flagged():  # V04 — from ..adapters import x
    assert _flagged("from ..adapters import qlib_cn\n")


def test_relative_escape_names_none_flagged():  # V04 — from .. import adapters (module=None)
    assert _flagged("from .. import adapters\n")


def test_importlib_string_arg_flagged():  # V06
    assert _flagged("import importlib\nimportlib.import_module('qlib')\n")


def test_dunder_import_string_flagged():
    assert _flagged("__import__('baostock')\n")


def test_importlib_aliased_call_flagged():  # V06 — aliased import_module
    assert _flagged("from importlib import import_module as imp\nimp('akshare')\n")


def test_importlib_rebound_receiver_flagged():  # V06 — il.import_module
    assert _flagged("import importlib\nil = importlib\nil.import_module('baostock')\n")


def test_dynamic_import_nonliteral_arg_flagged():  # court has no business doing dynamic imports
    assert _flagged("import importlib, os\nimportlib.import_module(os.environ['X'])\n")


def test_exec_in_court_flagged():  # V08 — coarse heuristic: court has no reason to exec
    assert _flagged("exec('import qlib')\n")


def test_subpackage_recursed():  # V03 — court/sub/*.py must be scanned
    assert _flagged("import qlib\n", path="court/sub/feed.py")


# ============================ FALSE-FLAGS: must pass =======================


@pytest.mark.parametrize(
    "code",
    [
        "from scipy.stats import norm\n",
        "import scipy\n",
        "import numpy as np\n",
        "from numpy import array\n",
        "import numpy.linalg\n",
        "from __future__ import annotations\n",
        "import os.path\n",
        "from collections.abc import Sequence\n",
        "import concurrent.futures\n",
        "from importlib import metadata\n",
        "from court.fdr import fdr_by\n",
        "from .dsr import psr\n",  # intra-court relative
        "from . import sharpe\n",  # module=None, court-internal
        "def _f():\n    import court\n    return court\n",  # the live lazy import in judge.py
        "# this mentions qlib and adapters in a comment\nx = 1\n",  # AST ignores comments
        "s = 'import qlib'  # a string, not an import\n",  # string literal, not an import
    ],
)
def test_legit_imports_pass(code):
    assert not _flagged(code), f"false-flagged legit code: {code!r}"


# ==================== DECLARED LIMITS: pass + documented ===================


def test_runtime_object_injection_not_seen():  # V01/V13 — import != semantic decoupling
    # A market object handed in at runtime couples court with NO import node. The gate
    # PASSES this — it proves court doesn't IMPORT market code, not that court is
    # semantically market-agnostic. Must never be oversold as covering this.
    code = "def judge(app, *, cal=None):\n    return cal.days_per_year() if cal else 252\n"
    assert not _flagged(code)


def test_hardcoded_market_constant_not_seen():  # V09
    code = "PRICE_LIMIT = 0.10\nTRADING_DAYS = 252\n"
    assert not _flagged(code)


# ============================ mechanics / fail-closed ======================


def test_syntax_error_fails_closed():  # ast-mechanics — never skip an unparseable court file
    assert _flagged("def f(:\n    import qlib\n"), "an unparseable court file must fail CLOSED"


def test_scan_court_reports_path_and_module():
    v = _flag("import qlib\n")
    assert v and v[0].module == "qlib" and "probe.py" in v[0].path


# ============================ --staged mode ================================


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _staged(repo):
    env = {"PYTHONPATH": str(REPO), "PATH": __import__("os").environ.get("PATH", "")}
    # -P (isolate mode): do NOT prepend cwd to sys.path. The subprocess runs with
    # cwd=<temp repo whose stub court/ would otherwise shadow the real court/>;
    # since harness/__init__ eagerly imports court.judge (v0.2 certified-run
    # exports), a cwd-shadowed court/ makes the gate fail to even start under a
    # bare python3 that prepends cwd. -P pins imports to PYTHONPATH=REPO.
    return subprocess.run(
        [sys.executable, "-P", "-m", "harness.court_import_gate", "--staged"],
        cwd=repo, capture_output=True, text=True, env=env,
    )


@pytest.fixture()
def repo(tmp_path):
    rp = tmp_path / "repo"
    (rp / "court").mkdir(parents=True)
    _git(rp, "init", "-q", "-b", "main")
    _git(rp, "config", "user.email", "t@example.com")
    _git(rp, "config", "user.name", "t")
    (rp / "court" / "__init__.py").write_text("x = 1\n")
    _git(rp, "add", "-A")
    _git(rp, "commit", "-qm", "seed")
    return rp


def test_staged_market_import_flagged(repo):
    (repo / "court" / "bad.py").write_text("import qlib\n")
    _git(repo, "add", "court/bad.py")
    assert _staged(repo).returncode == 1


def test_staged_scans_index_not_worktree(repo):  # B's V1 class
    f = repo / "court" / "bad.py"
    f.write_text("import qlib\n")
    _git(repo, "add", "court/bad.py")
    f.write_text("x = 1\n")  # clean disk, dirty index
    assert _staged(repo).returncode == 1, "must scan the staged blob, not the clean worktree"


def test_staged_nonutf8_fails_closed(repo):
    (repo / "court" / "weird.py").write_bytes(b"import qlib\xff\xfe\n")
    _git(repo, "add", "court/weird.py")
    assert _staged(repo).returncode == 1


def test_staged_non_court_py_ignored(repo):
    (repo / "adapters").mkdir()
    (repo / "adapters" / "qlib_cn.py").write_text("import qlib\n")
    _git(repo, "add", "adapters/qlib_cn.py")
    assert _staged(repo).returncode == 0, "gate scopes to court/ only (adapters may import qlib)"


def test_staged_clean_court_passes(repo):
    (repo / "court" / "ok.py").write_text("from scipy.stats import norm\nimport numpy as np\n")
    _git(repo, "add", "court/ok.py")
    assert _staged(repo).returncode == 0


# ---- dynamic-import evasions found by the independent referee pass (pre-grok) ----


def test_dynamic_assign_rebind_name_flagged():
    # from importlib import import_module; im = import_module; im('qlib')
    code = "from importlib import import_module\nim = import_module\nim('qlib')\n"
    assert _flagged(code), "assignment-rebinding import_module to a name must still be caught"


def test_dynamic_assign_attr_to_name_flagged():
    # f = importlib.import_module; f('qlib')
    code = "import importlib\nf = importlib.import_module\nf('qlib')\n"
    assert _flagged(code), "assigning .import_module to a name must still be caught"


def test_builtins_dunder_import_flagged():
    # builtins.__import__('qlib')
    code = "import builtins\nbuiltins.__import__('qlib')\n"
    assert _flagged(code), "builtins.__import__ (Attribute) must be caught, like the bare name"


def test_dynamic_chain_rebind_flagged():
    # im = import_module; g = im; g('qlib')  — fixpoint alias tracking
    code = "from importlib import import_module\nim = import_module\ng = im\ng('qlib')\n"
    assert _flagged(code), "a chain of name rebinds must still be caught"


# ---- grok RP-1 (court-gate-review) findings ----


def test_symlink_dir_carrier_flagged(tmp_path):  # BLOCKER — grok #1, enum symlinked-dir
    court = tmp_path / "court"
    (court).mkdir()
    (court / "__init__.py").write_text("x = 1\n")
    (tmp_path / "adapters").mkdir()
    (tmp_path / "adapters" / "cal.py").write_text("import qlib\n")
    (court / "sub").symlink_to(tmp_path / "adapters")  # court/sub -> ../adapters (dir symlink)
    v = cig.scan_court(court)
    assert v, "a symlinked directory under court/ must be flagged (os.walk won't descend it)"


def test_builtins_from_import_alias_flagged():  # grok — from builtins import __import__ as X
    assert _flagged("from builtins import __import__ as bi\nbi('qlib')\n")


def test_exec_via_attribute_flagged():  # grok #4 — builtins.exec
    assert _flagged("import builtins\nbuiltins.exec('import qlib')\n")


def test_exec_rebind_flagged():  # grok #4 — e = eval; e(...)
    assert _flagged("e = eval\ne('import qlib')\n")


def test_spec_from_file_location_flagged():  # grok #5 — code loader, court has no reason to
    code = "import importlib.util\nimportlib.util.spec_from_file_location('m', 'adapters/x.py')\n"
    assert _flagged(code)


def test_dunder_main_import_passes():  # grok #7 — __main__ false-flag
    assert not _flagged("import __main__\n")


def test_getattr_indirection_is_declared_limit():  # grok — deep indirection, out of AST reach
    # getattr(builtins, '__import__')('qlib') PASSES — documented declared limit, not a catch.
    assert not _flagged("import builtins\ngetattr(builtins, '__import__')('qlib')\n")
