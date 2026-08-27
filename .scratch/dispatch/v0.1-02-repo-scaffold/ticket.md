# Ticket: v0.1-02 — Python engineering scaffold for alpha-court

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court is a Python library that audits quantitative factor-research
results: a "statistical court" (`court/`) that consumes return/IC series and
rules on whether an apparent alpha should be believed (trial ledger, Deflated
Sharpe Ratio, PBO/CSCV, BHY multiple-testing correction, noise controls).
The repo is currently an empty skeleton: five top-level directories
(`court/`, `harness/`, `gates/`, `adapters/`, `examples/`) each holding only a
`.gitkeep`. This ticket lays the engineering foundation so later tickets can
add real code test-first.

Layer meanings (for docstrings):
- `court/` — statistical court kernel: trial ledger + deflation/overfitting
  statistics. Market-agnostic by iron law.
- `harness/` — agent governance layer (pre-registration gates, referee,
  dispatch). Empty in v0.1 beyond the package marker.
- `gates/` — cheap pre-screening checks ("cheap knives"). Empty in v0.1.
- `adapters/` — data/backtest adapters (qlib China data first). The ONLY layer
  allowed to know about markets.
- `examples/` — runnable demos. NOT a Python package (plain directory).

## Hard constraints (project iron laws — violations = rejected delivery)

1. Do NOT build backtesting functionality.
2. Do NOT build idea/factor generation logic.
3. Do NOT add any statistics code in this ticket at all — scaffold only.
4. `court/` must not import any market-specific code or library (no qlib, no
   exchange calendars, no universe definitions). Its runtime dependency
   whitelist is exactly: numpy, pandas, scipy. qlib may appear ONLY as an
   optional dependency group intended for `adapters/`.
5. Code, docstrings, comments: English.
6. Do not modify: `CLAUDE.md`, `README.md`, `TIMELINE.md`, anything under
   `docs/`, `.scratch/`, `.claude/`, or `.gitignore`.

## Task

1. Create `pyproject.toml` at the repo root:
   - project name `alpha-court`, version `0.1.0.dev0`, `requires-python >=3.10`
   - description: "Backtest frameworks tell you how well your idea did.
     alpha-court tells you whether to believe it."
   - license MIT; build backend `setuptools`; explicitly list packages
     `court`, `harness`, `gates`, `adapters` (do NOT auto-discover, so
     `examples/` and scratch dirs never leak into the wheel)
   - runtime dependencies: `numpy`, `pandas`, `scipy` (no upper pins)
   - optional dependency groups:
     - `qlib`: `pyqlib` (for adapters; NOT required for the kernel)
     - `dev`: `pytest`, `ruff`
   - ruff configuration in `[tool.ruff]`: target py310, line length 100,
     lint rule sets `E`, `F`, `I`, `UP`; and a `[tool.ruff.lint.isort]` section
     if needed for import sorting
   - pytest configuration in `[tool.pytest.ini_options]`: testpaths `tests`
2. Turn `court/`, `harness/`, `gates/`, `adapters/` into packages: add an
   `__init__.py` to each with a short English module docstring describing the
   layer (use the layer meanings from Context). Delete the `.gitkeep` in those
   four directories. Leave `examples/.gitkeep` as is.
3. Create `tests/test_smoke.py` with two tests:
   - `test_packages_importable`: imports `court`, `harness`, `gates`,
     `adapters` successfully.
   - `test_court_market_agnostic`: in a fresh subprocess
     (`sys.executable -c ...`), import `court` and assert that no module whose
     name starts with `qlib` appears in `sys.modules`, and that importing
     `court` succeeds without `adapters` being imported. This is the
     executable form of iron law 4.
4. Create a virtualenv `.venv` in the worktree, `pip install -e ".[dev]"`,
   and make everything pass.

## Acceptance criteria

Run each of these from the repo root and record the real exit codes:

1. `python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` → exit 0
2. `.venv/bin/python -m pytest` → exit 0, 2 tests passed
3. `.venv/bin/ruff check .` → exit 0
4. `.venv/bin/python -c "import court, harness, gates, adapters"` → exit 0
5. `git status --porcelain` after your final commit → empty (everything committed; `.venv/` is gitignored already)

## Out of scope

- Any statistics implementation, any qlib download or data code
- CI/CD configuration, pre-commit hooks
- README or docs changes
- Type-checking config (mypy/pyright) — later ticket

## Delivery protocol

1. You are in a fresh git worktree. Work here; never touch paths outside it.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit ALL work: `git add -A && git commit -m "v0.1-02: engineering scaffold"`.
4. Your final output must be ONLY the JSON receipt (the schema is enforced by
   the dispatch harness). Gather the values first:
   - `branch` = `git branch --show-current`
   - `commit` = `git rev-parse HEAD`
   - `worktree_path` = `pwd`
   - `ticket_id` = `v0.1-02`
