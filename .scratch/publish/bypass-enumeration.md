# publish-audit bypass enumeration — frozen 2026-07-12

> 4-lens workflow enumeration (encoding / location / semantic / mechanics), 56 vectors,
> run BEFORE writing the bypass red-tests (CR-08 + enumeration-first, the converged
> methodology). Sensitive example strings in this frozen copy are replaced by
> placeholder tokens (`[EMPLOYER-ZH]`, `[EMPLOYER-EN]`, `[EMPLOYER-PY]`, `[ROLE-ACR]`);
> the raw enumeration with real payloads lives in `docs/private/publish-bypass-enum-raw.json`
> (never shipped). Red tests use FAKE tokens for the same reason: test files are tracked
> and ship in the snapshot, so no real sensitive literal may appear in them — the gate is
> pattern-agnostic machinery, so fake-token tests exercise it fully.

## Verified-real findings (checked by hand against the tree, not trusted from the enum)

| id | claim | verdict |
|---|---|---|
| encoding-V5 / semantic-SL-11 | `[EMPLOYER-PY]` embedded in a snake_case JSON key in grok-review-4.json | **CONFIRMED** (`missing_muscle_for_<py>` key exists) |
| encoding-V4 | grok-review-3.json has a plaintext prelude before the JSON (invalid JSON) that also leaks a local `/Users/<user>/` path | **CONFIRMED** |
| semantic-SL-13 | absolute `/Users/<user>/` paths in tracked files | **CONFIRMED** — 44 tracked files |
| semantic-SL-01 | `[ROLE-ACR]` survives name-only redaction and is independently searchable | **CONFIRMED** present in the 4 archive files |
| location-V9 | shipped PNG carries a tEXt chunk | **CONFIRMED** (matplotlib Software tag — benign, but the channel is real) |
| semantic-SL-05 | meta-review-ledger.md carries unredacted employer + framing | **REFUTED** — 0 hits; ledger is clean (enum workers are not exempt from verification either) |
| encoding-V7 | zero-width chars already present | not present today (channel still guarded) |
| encoding-V14 | double-escaped `\\uXXXX` employer forms already present | not present today (still guarded) |

## Vector classes → design resolutions

1. **Encoding evasion** (`\uXXXX` single/double escapes, %-encoding, base64, HTML entities,
   fullwidth/NFKC, zero-width splices, CJK variant chars, UTF-16/BOM, markdown splits):
   the audit scans every file through a *decode battery* (raw, unicode-unescape ×2,
   percent-decode, HTML-entity decode, NFKC, zero-width strip) with **casefolded
   substring** matching (no word-boundary anchoring — pinyin hides inside
   identifiers). Any zero-width char anywhere is itself a hard FAIL.
2. **Carrier evasion** (dot-dirs, filenames, NUL/"binary" skip, symlinks, huge files,
   archives, PNG text chunks, untracked-copy, git metadata): walk includes dot-dirs;
   filenames scanned; binaries raw-byte scanned + PNG chunks parsed (tEXt/zTXt/iTXt
   decompressed and scanned); symlinks are refused; export enumerates `git ls-files -z`
   (tracked only, never `cp -r`); snapshot commit author/message fixed by script
   (noreply email).
3. **Semantic leaks** ([ROLE-ACR], synonym ring, JD-verbatim quotes, private-content
   descriptions, marker-density fingerprint): role acronym added to the hard list;
   framing synonym ring in the rules file; two-zone policy (below); JD quotes were
   removed from the living tree with design-doc §4; residual fingerprint risk accepted
   and declared in PUBLISHING.md.
4. **Gate/export mechanics** (fail-open blocklist, vacuous PASS, wrong tree, sed
   droppings, swallowed errors, TOCTOU, manifest self-leak/placeholder, allowlist creep,
   TIMELINE variants): rules file fail-closed (missing/empty/comment-only/TODO-marker/
   undecodable → exit 2; BOM/CRLF normalized); scanned-count must equal walked-count and
   meet a floor; export-tree shape verified; pure-Python rewriting (no sed); every
   scan error is a finding, never a skip; audit PASS writes a tree-hash receipt the push
   step re-verifies (TOCTOU bind); manifest records file + marker + count only (never the
   original string) and the audit runs on the FINAL tree incl. PUBLISHING.md; no
   suppression/allowlist mechanism exists at all; TIMELINE exclusion matches basename
   casefold.

## Structural design decisions forced by the enumeration

- **The gate must not be the carrier** (location-V3): `harness/publish_audit.py` and
  `harness/publish_export.py` contain **zero** sensitive literals; all patterns load from
  `docs/private/publish-rules.txt` (never shipped, fail-closed).
- **Two-zone framing policy**: employer/personal patterns hard-fail EVERYWHERE in the
  final tree. Job-framing patterns hard-fail in the living zone; in the archive zone
  (`.scratch/**` + `docs/case-study-disclosure-boundary.md`) they are counted, printed,
  and disclosed in PUBLISHING.md instead — archived third-party review artifacts may
  discuss the case study's context, and rewriting their prose beyond identifier masking
  would be evidence-tampering. No other exemption mechanism exists.
- **Local-path masking**: `/Users/<user>` is rewritten to `[HOME]` at export (44 files),
  declared in the manifest.

## grok RP-1 second pass (cross-model) — 11 new bypasses my 4-lens + 50 red-tests missed

Fresh grok (session 019f5708, `--cwd` read-only worktree at 7e1393e) ran the real suite,
built an independent naive gate (38 fail / 10 pass — confirmed discriminative), and crafted
bypass payloads against the committed gate. Graded **C / cannot-ship-as-is**. This is exactly
what RP-1 is for: same-model enumeration systematically under-covers. All ADOPTED and fixed:

| # | grok finding | severity | fix | red-test |
|---|---|---|---|---|
| 1 | personal home path was `[rewrite]`-only, not `[hard]` → audit rubber-stamps a tree still containing `[HOME]` if export rewrite is skipped/partial | **blocker** | audit hard-set = hard ∪ rewrite-LHS | `test_rewrite_only_literal_is_also_hard` |
| 2 | prior-employer fail-closed was TODO-marker only → strip TODO without filling names → hard non-empty → ships | **blocker** | positive `PUBLISH-RULES-CONFIRMED` affirmation required | `test_rules_no_todo_but_unconfirmed_fails_closed` |
| 3 | PNG iTXt compression_flag=1 not decompressed (docstring over-claimed "iTXt decompressed") | major | full iTXt parse + zlib decompress | `test_png_itxt_compressed_bites` |
| 4 | `\UXXXXXXXX` 8-digit unicode escapes outside decode battery | major | `_UNESCAPE8_RE` pass | `test_u8_escape_bites` |
| 5 | framing patterns never scanned via `_binary_needles` (only PNG-extracted text) | major | framing needles on binary too | `test_framing_in_binary_bites_living_zone` |
| 6 | gzip/zlib/zip containers not inflated — compressed hard token invisible | major | archives REFUSED (magic + suffix), not inflated | `test_archive_in_tree_refused` |
| 7 | base64 of English hard token not listed (only [REDACTED-EMPLOYER]'s b64 was) | minor | generic base64-decode pass over 8+ char runs | `test_base64_of_any_hard_token_bites` |
| 8 | CSS/JS `\XXXX\XXXX (real codepoints, redacted here)` and `\xE4` byte-escape text | minor | `_CSSHEX_RE` + `_XHEX_RE` passes | `test_css_hex_escape_bites` |
| 9 | UTF-7 encoding | minor | `_utf7_decode` pass | `test_utf7_bites` |
| 10 | punycode `xn--` form | minor | `_punycode_decodes` pass | `test_punycode_bites` |
| 11 | quoted-printable / MIME encoded-word | minor | `_quopri_decode` pass | `test_quoted_printable_bites` |

### Dogfood catch (the audit found leaks in the gate's OWN shipping files)

Running the fixed audit over the export tree flagged `tests/test_publish_audit.py` and
`harness/publish_audit.py` themselves: a comment carried CSS-hex `\XXXX\XXXX (real codepoints, redacted here)` (decodes to the
real name) and fixtures/`lstrip` carried literal zero-width / BOM chars. Because test & harness
files SHIP (location-V3), they must pass the audit too. Fixed: real codepoints removed from
comments, zero-width/BOM built programmatically (`"\u200b"`, `"\ufeff"`). The gate now passes
its own audit — the strongest possible dogfood.

### Declared NOT covered (honest scope — not silently claimed done)

grok's payload battery also leaked three vectors I consciously do NOT mechanize, because each
is a deliberate self-sabotage rather than an accidental leak, and covering them cheaply is not
possible:
- **cross-file split** — the name split so no single file contains any decodable form; would
  require cross-file reassembly. Out of scope; the export rewrites known literals, and no
  accidental process produces a cross-file split.
- **rot13 / arbitrary reversible ciphers** — unbounded; a decode battery cannot chase every
  cipher. Not covered.
- **email `[at]` obfuscation** (`9205608 [at] gmail.com`) — personal-email spelled out. Low
  risk; owner eyeball-grep before push is the backstop (see PUBLISHING.md one-thing-before-push).

These are recorded, not hidden — the gate is a high-recall cheap knife plus a mandatory owner
eyeball pass, not a proof of non-leakage.

### Honesty corrections (grok honesty_flags, ADOPTED)

- Commit `7e1393e` body said "50 tests (30/12)"; the real count at that commit was 48 (38/10),
  now 59 (49/10) after the RP-1 fixes. Corrected here and in the follow-up commit.
- `red-run-log.md` recorded MY naive baseline (31 fail/15 pass); grok's independent naive was
  38 fail/10 pass. Both are honest records of *different* naive baselines — the methodology is
  real, the exact digits are baseline-dependent, now noted.
- Module docstring previously implied iTXt was decompressed before it was — fixed with the code.
