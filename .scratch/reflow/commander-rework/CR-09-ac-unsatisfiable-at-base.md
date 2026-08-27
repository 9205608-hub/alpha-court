# CR-09 — AC-4 (`ruff check .`) was unsatisfiable at the dispatch base: the commander had polluted the tracked tree

- **root_cause_id**: `ticket-self-contradiction`
- **attribution**: contract-fault (commander)
- **occurrences**: **4** (v0.1: δ=0 vs `0<δ<T`; v0.2-06: AC-4 `ruff check .` dirty at
  base b4897c68; v0.2-09: AC-3 full-suite unsatisfiable at base 8086e06f;
  **v0.2-10a: AC-4 `python3 -m pytest` unsatisfiable at base 581a9ee3** under the
  *named interpreter* — 2 `test_court_import_gate` staged tests fail on the miniforge
  base `python3` (cwd-shadows the real `court/` because harness/__init__ eagerly
  imports court.judge since 07/09), while `.venv-merged` python passes. The commander's
  env-AC check ran `pytest --collect-only` with `.venv-merged`, not a full run with the
  system `python3` the AC names — verified the wrong interpreter AND the wrong depth.
  Worker's honest `partial` + deviation was CONFIRMED correct (fails gate-alone, base,
  zero worker changes); referee reproduced and fixed the test infra (`-P` isolate).
  — v0.2-09 detail: the
  commander's 08-regen commit chained `examples/killer_demo/out/ledger.jsonl`, breaking
  3 ledger-chain tests that used it as their LEGACY fixture; the commander ran ruff +
  pytest-collect at base per the promoted rule but never re-ran the tests that CONSUME
  the changed artifact. Worker receipt disclosed it precisely; referee confirmed and
  repaired the fixtures commander-side, zero worker rework.)
- **evidence**: worker receipt `.scratch/dispatch/v0.2-06-ledger-evidence/receipt-20260713-003354.json`
  (`status: partial`, deviation: 30 pre-existing ruff errors under tracked `.scratch/`,
  worker verified identical at BASE with its own files stashed); referee re-run confirmed —
  all 30 errors live in `.scratch/dispatch/v02-design-audit/referee-verify{,-2}.py`,
  committed by the commander during the design audit (commits `9e33ac8`/`a9c2b8a`).
  The adversarial ticket-lint (`ticket-lint.md`) checked AC *executability* but never
  **executed** the AC commands at base — it caught the diff-baseline BLOCKER by running
  git, and missed this one by not running ruff.
- **fix**: `pyproject.toml` ruff `extend-exclude = [".scratch"]` — the evidence archive
  is not product code; archived artifacts stay verbatim (editing them post-hoc to appease
  a linter would mutate evidence). `ruff check .` is a product-tree gate again.
- **anti-recurrence** (promoted rule, D4 direct-adopt — binds the commander;
  **strengthened at occurrence #3**): the pre-dispatch lint must (a) **execute every
  environment-class AC command at the dispatch base** (ruff / pytest collection /
  venv install), AND (b) when any commander commit since the last green full suite
  **changed a file that tests consume** (committed artifacts, fixtures, schemas),
  re-run the consuming tests before dispatching, AND (c, added at occurrence #4) run
  each env-AC with the **exact interpreter and depth the AC names** — if the AC says
  `python3 -m pytest` (system python3, full run), verify with system python3 and a full
  run, NOT a `.venv` and NOT `--collect-only`. Re-runnable assertion: a dispatch whose
  receipt discloses a pre-existing-at-base AC failure is a CR-09 recurrence.
- **polluted-rework**: none — the worker routed around it correctly (honest `partial`
  + stash-verified attribution); zero worker rework cycles spent. The worker's
  attribution claim is CONFIRMED and the `partial` upgrades to accepted-on-referee-fix.
