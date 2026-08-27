# Ticket: v0.1-09 — qlib China data availability research + local smoke validation

You are a headless worker agent for the alpha-court project. This ticket is
self-contained — everything you need is in this file. Do not invent scope
beyond it.

## Context

alpha-court audits factor-research results. Its first data adapter will feed
Chinese A-share daily data from **qlib** (Microsoft's open-source quant
platform, pypi package `pyqlib`) into the statistical kernel. The pitch
"A-share home market + qlib community data pack = globally reproducible"
only works if the community data is actually downloadable and sane TODAY, on
this machine. Your job: find the current best acquisition path, actually
download the data, validate it, and write up the facts.

This ticket mixes research (web) and hands-on validation (shell). You have
web search/fetch and shell access.

## Hard constraints (project iron laws — violations = rejected delivery)

1. Report facts as they are — if the data is broken, stale, or the install
   fails, that IS a valid finding; write it down honestly.
2. Repo changes: create/modify ONLY `docs/research/qlib-cn-data.md`.
3. **Exception to worktree isolation (explicitly granted here):** the qlib
   data cache goes to the standard user-level location
   `~/.qlib/qlib_data/cn_data` so later sessions reuse it. A Python
   virtualenv `.venv` may be created inside the worktree (it is gitignored).
   Touch nothing else outside the worktree.
4. Language: English.

## Task

1. **Research (web)**: identify the acquisition paths for qlib's China daily
   data as of now (2026) — the official `qlib.tests.data.GetData` /
   `get_data` route, community mirrors, and the dump-your-own
   (`scripts/dump_bin.py` + a price source) route. Note for each: freshness
   (data end date), size, maintenance status, known issues (GitHub issues are
   a good source).
2. **Install (shell)**: create `.venv` in the worktree, install `pyqlib`
   (plus anything it needs). Record the Python version used and any tricks
   needed (build failures, version pins, platform issues on macOS arm64).
   If `pyqlib` will not install on the default python3, try other available
   interpreters (e.g. python3.11/3.10 if present) and record what worked.
3. **Download**: fetch the China daily data pack into
   `~/.qlib/qlib_data/cn_data` using the most reliable path found. Record the
   exact command, duration, and on-disk size (`du -sh`).
4. **Smoke-validate (shell)**: in the venv, `qlib.init` against the data and:
   - list total instrument count, and the calendar's first/last trading date
   - load daily close/volume for the csi300 universe over the most recent
     ~2 years available: report row count, per-field NaN rates
   - spot-check 2-3 well-known tickers (e.g. SH600519 Kweichow Moutai):
     print a few recent rows; sanity-check that prices are positive and
     adjusted fields exist (note which price fields are raw vs adjusted)
   - note how suspensions/halts appear (missing rows vs NaN rows)
   Record every command and its real exit code.
5. **Write `docs/research/qlib-cn-data.md`** with sections:
   - Acquisition paths compared (table: route, freshness, size, reliability)
   - What was actually done on this machine (commands, versions, timings)
   - Data quality findings (calendar range, universe sizes, NaN rates,
     adjustment fields, suspension representation, any anomalies)
   - **Recommendation for the v0.1 demo**: which universe (e.g. csi300),
     which time window, and why; what a fresh machine must run to reproduce
     (exact download instructions)
   - Open risks (staleness, mirror availability, licensing notes)

## Acceptance criteria

1. `test -f docs/research/qlib-cn-data.md` → exit 0
2. `test -d ~/.qlib/qlib_data/cn_data` → exit 0 (unless every acquisition
   path failed — then the doc must say so and status = blocked/partial)
3. The doc contains real measured numbers (dates, row counts, NaN rates,
   sizes) from THIS machine, not copied claims.
4. `git status --porcelain` after your final commit → empty
5. `git log --oneline -1` message: `v0.1-09: qlib-cn data availability`

## Out of scope

Writing any adapter code; factor computation; any evaluation of factors;
non-daily frequencies; US/crypto data.

## Delivery protocol

1. Work in your current directory (a fresh git worktree) + the two granted
   exceptions above.
2. Run the acceptance-criteria commands yourself; record each command and its
   real exit code for the receipt. Report failures honestly — an honest
   `partial` beats a dishonest `done`.
3. Commit: `git add docs/research/qlib-cn-data.md && git commit -m "v0.1-09: qlib-cn data availability"`.
4. Your final output must be ONLY the JSON receipt (schema enforced by the
   dispatch harness). Gather first: `branch` = `git branch --show-current`,
   `commit` = `git rev-parse HEAD`, `worktree_path` = `pwd`,
   `ticket_id` = `v0.1-09`.
