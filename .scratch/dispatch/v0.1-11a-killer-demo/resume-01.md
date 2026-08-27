# Resume: v0.1-11a — session was cancelled mid-run; drive the ticket to completion

Your session died (`Cancelled`) after writing the examples/killer_demo/
package and tests but BEFORE running the suite, the E2E, and committing.
All your uncommitted work is intact in this worktree. Finish the original
ticket (.scratch/dispatch/v0.1-11a-killer-demo/ticket.md — re-read it):

1. Run the acceptance battery: fresh `.venv` if missing
   (`python3.11 -m venv .venv && .venv/bin/python -m pip install -e ".[dev,qlib,demo]"`),
   then `.venv/bin/python -m pytest -q` and `.venv/bin/ruff check .` — fix
   anything red (your own files only).
2. Run the real E2E DETACHED — do not block on one long command:
   `nohup .venv/bin/python -m examples.killer_demo --skip-download > e2e.log 2>&1 &`
   then poll `tail e2e.log` with short commands (expect ≈45–60 min for the
   grid). If it crashes, fix and re-run.
3. Verify out/: ledger.jsonl (104 verdicts), figure.png+svg, report.md
   (four parts), run_config.json.
4. Commit ALL work (including examples/killer_demo/out/ — it is evidence):
   `git add -A && git commit -m "v0.1-11a: killer demo"`.
5. Final output = ONLY the JSON receipt (ticket_id `v0.1-11a`), and paste
   the headline VERBATIM in notes_for_referee: survivors/100, accused |t|,
   its five gate outcomes, grid wall-clock. 禁赢学: report whatever it says.
