# Rework note v0.2-07 / rework-02 — three small closures (all contract-fault, NOT your fault)

Your rework-01 is accepted: the referee re-reproduced that BOTH target fail-opens
are genuinely closed (F-1 reopen-brick now raises "verdicts without a judgment
event"; the anchor is fail-closed and query-by-recomputed-head — forged head not
attested → raises; honest run without a manifest still passes, no over-kill). The
adversarial probe panel confirmed no new fail-open and no false-positive. **You win
rework-01 clean.** Your deviation on Finding A scenarios (a)/(b) was correct and is
adopted — deleting an honestly-anchored run's manifest must NOT fail it; that was a
spec error in my note (referee-fault, logged).

This rework-02 closes three **small contract-faults** the probe panel surfaced (my
spec, not your build). All are cheap; the first is the only one that matters.

## FIX 1 (major) — cross-check `judgment.battery` against the actual verdicts

Referee-reproduced (`.scratch/dispatch/v0.2-07-certified-run/referee-repro-battery.py`):
an honest run with battery `[fdr_by, fdr_bh]` (2 verdicts on chain) can be
full-chain-reforged with `judgment.battery` shrunk to `[fdr_by]` — the verdict events
untouched, verdict_ids still covering both — and **verify PASSES** (no manifest, no
anchor; and the shipped CLI never uses an anchor). Nothing reads or cross-checks the
`battery` field, so the design's claim "the battery is on-chain and auditable" is
false: the field can lie.

**The real protection already holds** — N cannot shrink, because verdict_ids must
cover ALL verdict events (invariant 7) and a gate's verdict cannot be hidden. This
fix only makes the descriptive `battery` field trustworthy so it cannot contradict
the verdicts it summarizes.

**New spec (pinned) — verify invariant 7.5 gains a cross-check:** the multiset of
`statistic` values in `judgment.battery` (i.e. `[app["statistic"] for app in
battery]`) must equal the multiset of `statistic` values of the covered verdict
events (each verdict event carries its `statistic`). Mismatch → `CertificationError`
("invariant 7.5: judgment battery does not match verdict statistics"). Order need
not match (aggregation is order-independent); the multiset must. Red-first test: the
referee's shrunk-battery reforge must now raise.

(If you would rather DROP the redundant `battery` field entirely and have any
consumer derive it from the verdicts, that is also acceptable and arguably cleaner —
but then `judge()` must stop writing it, the design doc's "battery on-chain" affordance
goes away, and you must say so in the receipt. The cross-check is the smaller diff and
keeps the affordance; pick one, don't ship a field that isn't checked.)

## FIX 2 (minor, defense-in-depth) — pin the judgment event's position

The probe panel reforged the `judgment` event to sit BEFORE a verdict and verify
passed (`_check_raw_order` doesn't constrain judgment position). It's not a new hole
(any reorder needs full reforge = the anchor's domain), but the judgment is
success-only and belongs after every verdict. Add to `_check_raw_order` (invariant 4):
the single `judgment` event's raw index must be greater than every `verdict` event's
raw index (and it already must precede the seal). One red test (judgment-before-verdict
reforge → raises).

## FIX 3 (minor, reachability) — let the CLI supply an anchor

`python -m harness.verify <ledger>` always calls `verify(..., anchor=None)`, so FIX 2's
anchor defense — the ONLY defense against a full-chain rewrite — is unreachable from
the shipped command-line path; a human verifying by CLI never checks the anchor. Add an
optional CLI argument: `--anchor file:<path>` → `FileAnchor(path)`, `--anchor
git:<repo_dir>` → `GitAnchor(repo_dir)`, `--anchor none`/absent → current behavior
(reported, not verified). When supplied, pass the backend into `verify()`. Print in the
report whether the anchor was verified or merely reported. One test per backend form
(exit 0 when the anchor attests, exit 1 when it does not).

## Unchanged

- Everything rework-01 delivered stands — the judgment event, the query-by-head anchor,
  the one-policy invariant, the honest-run-passes behavior. Do not touch what the panels
  confirmed correct.
- File ownership unchanged (your six owned files). No `court/` changes.

## Delivery protocol (unchanged)

1. Red tests FIRST (record the red exit code), then green.
2. Re-run the two test files, then the full suite (~30 min), then `ruff check .`.
   `git checkout -- alpha_court.egg-info/` before committing.
3. Commit: `git add -A && git commit -m "v0.2-07 rework-02: battery cross-check +
   judgment position + CLI anchor (3 contract-fault closures)"`.
4. Final output: ONLY the JSON receipt, `ticket_id` = `v0.2-07-rework-02`.
