# Rework note v0.2-07 / rework-01 — two frozen-spec fail-opens (contract-fault, NOT your fault)

You are resuming your v0.2-07 session (CertifiedRun / seal / anchor / verify).
**Your delivery is accepted on the frozen v3 contract** — it passed both referee
panels (fidelity + adversarial probes), 36/36 new tests, full suite 447+1 green,
and every on-chain self-deception path (scope→N, direction flip, hidden trials,
smuggled keys) is closed exactly as pinned. You win both findings below: they are
**contract-faults** — the v3 ticket's own wording created them, and implementing
that wording verbatim was correct. This is a NEW ruling with two spec changes,
pasted in full (your worktree's contract predates them; do not go looking for a v4
doc — everything you need is here). Attribution is on the commander's ledger
(CR-10), not yours.

Both were independently REPRODUCED by the referee — evidence verbatim:

```
=== F-1: mid-battery brick revived via open() ===
  judge raised: ValueError — bricked in-memory
  in-memory seal blocked: ValueError
  REOPEN seal SUCCEEDED sid=s-000001, verify PASS -> FAIL-OPEN CONFIRMED (n_verdicts=1)
=== Finding A: anchor silently disabled by deleting manifest ===
  honest verify(anchor) PASS, head=0e72ae5e7a88
  after DELETING manifest, verify(anchor=real) STILL PASS -> Finding A CONFIRMED (anchor not consulted)
```

## FIX 1 (major) — the on-chain `judgment` event closes the reopen-revives-brick hole

Problem: `court.judge` appends verdicts **per-application**; a mid-battery failure
leaves orphan verdicts on the chain. Your in-memory brick is correct, but
`CertifiedRun.open()` then lets `seal()` succeed, and the rebuilt `verdict_ids`
cover exactly the orphans, so `verify` passes. An agent shrinks the battery by
making the N-th statistic throw, reopens (crash-recovery), and seals a run
indistinguishable from an honest N−1-gate run.

**New spec (pinned):**

- Add a court-opaque **`judgment` declaration event**, appended by `judge()`
  **only after `court.judge` returns successfully**, BEFORE any seal:
  payload `{"kind": "judgment", "battery": [<the Application list, verbatim: each
  {"statistic": ..., "params": {...}} in order>], "verdict_ids": [<all ids court.judge
  produced, in order>]}`. Append it via `ledger.append_declaration`. (If
  `court.judge` raises, append NOTHING — the run stays bricked, now durably.)
- `seal()` requires a `judgment` event on the chain whose `verdict_ids` equal ALL
  verdict events on the chain; absent or mismatched → `ValueError`. (The seal's own
  `verdict_ids` continue to equal these.)
- `open()` recovers judged-state from the **`judgment` event**, not from raw verdict
  presence: a ledger with verdicts but NO `judgment` event (a brick or a crash) →
  `judge` is spent (calling it again → `ValueError`) and **`seal()` is refused**
  (`CertificationError` "judged run incomplete: verdicts without a judgment event").
  A ledger WITH a `judgment` event → seal allowed, Judgment rebuilt from it.
- **`verify` gains an invariant** (insert as the new invariant **7.5**, i.e. right
  after the existing scope/verdict_ids invariant 7, before attestation 8): exactly
  one `judgment` event exists; its `verdict_ids` == every verdict event on the chain
  == the seal's `verdict_ids`; the seal's `scope` is still the derived
  registered-and-evaluated set. A ledger sealed without a covering `judgment` →
  `CertificationError`.
- Red-first test (the referee's F-1 scenario must now FAIL to seal/verify): brick a
  run mid-battery, `open()`, assert `seal()` raises; and a hand-crafted ledger with
  orphan verdicts + a seal but no `judgment` → `verify` raises.

## FIX 2 (major) — anchor verification is query-by-recomputed-head, fail-closed

Problem: `verify`'s invariant 9 reads the pin reference from `run_manifest.json`,
which lives **inside the rewrite surface** — a forger deletes/blanks it and the
`if manifest_anchor_ref is not None and anchor is not None` gate is simply skipped,
so a supplied real anchor is never consulted. verify's own honest recomputed
`final_head` is not used to challenge the anchor.

**New spec (pinned):**

- Change the `AnchorBackend` protocol so verification keys on the chain head, not a
  manifest ref: `verify(self, chain_head: str) -> bool` — "has this backend anchored
  THIS head?", answered from the backend's own protected state:
  - `NoopAnchor.verify(head)` → True (test backdoor, unchanged intent);
  - `FileAnchor.verify(head)` → head appears in the backend's own anchor file (the
    `FileAnchor(path)` it was constructed with — NOT a manifest path);
  - `GitAnchor.verify(head)` → a commit exists whose `anchors/<head>.txt` is present
    (query by `head`, e.g. search the anchor commits / `git log`+`git show
    <commit>:anchors/<head>.txt`), NOT by a manifest-stored SHA.
  Keep `pin(chain_head) -> str` and `ref_before_seal() -> str | None` as they are
  (they still populate the seal's `anchor_ref` / the manifest for human/advisory use).
- `verify(path, anchor=backend)`: when `backend is not None`, compute the honest
  `final_head` from the chain and require `backend.verify(final_head) is True`.
  If it returns False, errors, or the backend has no record → **fail-closed
  `CertificationError`** ("anchor supplied but does not attest the recomputed head").
  **Never** gate this check on the manifest's `anchor_ref` — the manifest ref is now
  advisory only (still reported in `VerificationReport.anchor_ref`, never trusted for
  the decision). When `backend is None`, anchor is reported, not verified (unchanged).
- Red-first tests (the referee's Finding A scenarios must now FAIL): (a) honest sealed
  run, `rm run_manifest.json`, `verify(path, anchor=real)` → raises; (b) manifest
  present but `anchor_ref` blanked to null, `verify(anchor=real)` → raises; (c) forge
  the whole chain, supply a `FileAnchor` that anchored the ORIGINAL head →
  `verify(anchor=that)` raises (forged head not attested); (d) honest run with the
  matching anchor still PASSES.

## FIX 3 (minor) — verify asserts exactly one policy declaration

`verify` currently takes the first policy declaration and stops; a hand-crafted
ledger with two `aggregation_policy` declarations passes verify, though
`declare_policy`/`read_declared_policy` both treat >1 as "corrupt pre-registration".
Add an invariant: exactly one `aggregation_policy` declaration on the chain, else
`CertificationError`. One red test.

## Also fold these (minor/nit from the panels — cheap, same pass)

- **F-3/C**: your `test_verify_legacy_no_chain_fails_invariant_2` passes on a loose
  regex (`"uncertified: no chain|chain"`) — a pure legacy file actually dies on
  invariant 1 (missing envelope keys). Either tighten the assertion to the invariant
  that actually fires, or add a "hash-present-but-blank" fixture that truly reaches
  the invariant-2 branch. Make the test name match what it proves.
- **F-4**: the flip-bypass (b) test uses `pytest.raises((CertificationError,
  Exception))` (catches anything) with dead `replace` code above it — tighten to the
  real `CertificationError` + message, drop the dead lines.
- **F-5**: `GitAnchor.pin` hard-codes `-c user.name=test -c user.email=t@t` into the
  PRODUCTION commit path — that overrides the real user's git identity. Make the
  committer identity a constructor parameter (default to the repo's own config; the
  tmp-repo tests pass the test identity explicitly).
- **F-6**: a non-str `manifest.anchor_ref` (e.g. `12345`) is silently coerced to None
  — with FIX 2 the manifest ref is advisory, but still: report it faithfully, do not
  silently drop; if it is unusable, say so in the report rather than nulling it.
- **F-2**: move the replay-on-COPY check into invariant 1 (where the ticket lists it)
  so the "first violated invariant" numbering is honest.

## Unchanged / for your information

- Everything else stands as delivered — do not touch what the panels confirmed
  correct (the §6 boundaries, the raw-order invariants 4/5, the conformance checks).
- File ownership boundary unchanged (your six owned files only).
- The `judgment` event is a court-opaque `declaration` — you do NOT touch `court/`;
  it flows through `append_declaration` exactly like `run_config`/policy.

## Delivery protocol (unchanged)

1. Work in your same worktree; red tests FIRST (record the red exit code in the
   receipt `self_test`), then green.
2. Re-run: `.venv/bin/python -m pytest tests/test_certified_run.py
   tests/test_harness_verify.py -q`, then the full suite `.venv/bin/python -m
   pytest -q` (~30 min), then `.venv/bin/ruff check .`. Before committing:
   `git checkout -- alpha_court.egg-info/`.
3. Commit: `git add -A && git commit -m "v0.2-07 rework-01: judgment event + anchor
   query-by-recomputed-head + one-policy invariant (2 contract-fault fail-opens)"`.
4. Final output: ONLY the JSON receipt (same schema), `ticket_id` =
   `v0.2-07-rework-01`.
