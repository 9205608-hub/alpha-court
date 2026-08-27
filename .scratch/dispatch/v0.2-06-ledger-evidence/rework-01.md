# Rework note v0.2-06 / rework-01 — non-str dict keys break the hash chain (1 major + 3 batched minors)

You are resuming your v0.2-06 session (ledger evidence layer). Your delivery
passed the referee's independent re-runs (219 passed + 1 skip full suite,
diff boundary clean, 30+ adversarial probes zero fail-open — the tamper
matrix, seal semantics, legacy/mixed, canonical float/bool/unicode edges all
held) and your AC-4 deviation was adjudicated **contract-fault (commander)**:
the 30 ruff errors are the commander's own audit scripts committed under
`.scratch/`, confirmed at BASE exactly as you reported. Your stash-verified
attribution was clean work.

One panel finding requires a fix before merge. Referee reproduced it
independently — evidence verbatim:

```
# spec = {"nested": {2: "x", 10: "y"}}  (int keys — a perfectly legal caller dict)
write with int keys: OK, tid = t-000001
reopen: LedgerCorruptionError - event_hash mismatch for type='trial': stored '22d5e5e8…'
# spec = {1: "a", "b": 2}  (mixed-type keys)
mixed keys: TypeError - '<' not supported between instances of 'str' and 'int'
```

## MAJOR-1 (must fix): `canonical_json` is undefended against non-str dict keys

Mechanism: `_pretransform_for_hash` transforms values only; at write time
`json.dumps(sort_keys=True)` sorts int keys numerically ([2, 10]) and
serializes them as strings; on replay `json.loads` yields str keys which sort
lexicographically (["10", "2"]) → different canonical string → different
content_hash → **an honestly-written ledger self-reports as tampered**
(false-positive `LedgerCorruptionError` — the worst failure direction this
project has). Mixed-type keys escape as a naked `TypeError` from
`sorted()`, violating hard constraint 4 (caller errors raise `ValueError`).

**Fix (pinned):** in `_pretransform_for_hash`, when transforming a dict,
raise `ValueError` naming the offending key if any key is not `str` (check
recursively, including inside lists/tuples). This rejects the input **at
write time** — before anything is written and before the in-memory chain
head moves. The replay side needs no change (`json.loads` keys are always
str). Do NOT coerce keys to str (silent repair is forbidden).

**Tests (red first):**
- `register` with an int-key dict anywhere in `spec`/`params` →
  `ValueError` at write time, nothing appended, ledger still usable;
- mixed-type keys → `ValueError` (not `TypeError`);
- same for `record(attestation=...)` opaque keys and
  `append_declaration`/`append_seal` payloads (any nested non-str key);
- a control: str-key nested dicts still round-trip with a verifying chain.

## Batched minors (fix in the same pass)

1. **Reverse-direction mixed-file test.** Your mixed-file test covers only
   hashless-into-chained; the implementation also catches chained-then-
   hashless (referee verified live) — add the missing test so the suite
   proves both directions.
2. **Strengthen `test_flip_type_raises`.** As written, a schema crash would
   also turn the test green (flipping trial→declaration breaks the schema
   anyway). Assert the failure is the CHAIN catching it: match the exception
   message on `event_hash mismatch`.
3. **`source_ref` runtime type guard.** Signature says `str | None`; a dict
   currently slips through and gets stored. Add
   `isinstance(source_ref, str)` check (raise `ValueError` on non-str
   non-None) — consistent with fail-closed constraint 4. One test.
4. **(2-line reorder, optional but cheap) advance `self._chain_head` only
   after the fsync'd write returns** in `_append_event`, so a failed write
   cannot leave the in-memory head ahead of the file within a surviving
   process.

## Unchanged / for your information

- Everything else stands as delivered — do not refactor beyond the items
  above. File ownership boundary unchanged (`court/ledger.py`,
  `tests/test_ledger_chain.py`; `tests/test_ledger.py` only if a guard test
  naturally belongs there).
- The by-reference storage of caller dicts (attestation/spec/params) was
  ruled consistent with the v0.1 precedent — no change requested.
- `canonical_json`/`content_hash`/`link_event_hash` staying public
  module-level functions was ruled fine (ticket 07 will consume them).

## Delivery protocol (unchanged)

1. Work in your same worktree; run the red tests first (record the red
   exit code), then fix to green.
2. Re-run: `.venv/bin/python -m pytest tests/test_ledger.py
   tests/test_ledger_chain.py -q` and `.venv/bin/ruff check court/ tests/`
   (the full-tree ruff AC-4 has been struck from your acceptance — it was
   commander pollution, now fixed commander-side).
3. Amend or add a commit: `git add -A && git commit -m "v0.2-06 rework-01:
   reject non-str dict keys on the hash path + batched minors"`.
4. Final output: ONLY the JSON receipt (same schema), `ticket_id` =
   `v0.2-06-rework-01`.
