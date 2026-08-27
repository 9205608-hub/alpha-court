# Meta-review ledger

The artifact `/adversarial-referee` requires: **every criticism from a role-reversal
review is adjudicated on the record** — adopted (with what it became) or
rejected-with-reason. No silent drop. Reviews archived verbatim under
`.scratch/reflow/meta-reviews/`.

## 2026-07-11 — grok role-reversal reviews of the workflow-system design (this session)

Three passes, same grok session (`019f4d2f…`), resumed each time so it could check
whether the prior round's criticisms were actually addressed.

### grok #1 (design of D1–D5) — `meta-reviews/grok-review-1.json`

| criticism | disposition |
|---|---|
| Commander is the sole unaudited executor of the whole reflow loop = self-grading the meta-layer (violates court's own iron law) | **ADOPTED** → RP-0 (tamper-evident self-binding); the cross-cutting law of the system |
| Attribution label = legislative power, self-assigned | **ADOPTED** → attribution is a structured field the worker may dispute (adversarial-referee) |
| Anti-overfitting threshold (D3) becomes a laziness shield | **ADOPTED** → operational definition of "expensive"; frozen root_cause_id vocab |
| inbox pruning = selective-forgetting backdoor | **ADOPTED** → tombstone, not erase; in-repo for git tamper-evidence |
| D4b transient RPC is gameable | **ADOPTED (designed)** → persistent worker-binding ledger; RPC dropped |

### grok #2 (did the cure work?) — `meta-reviews/grok-review-2.json`

| criticism | disposition |
|---|---|
| Cure is an empty-shelves prescription: zero landed artifacts, yet killer-demo already dispatched | **ADOPTED** → landed the teeth this session; CR-06; backlog-discharge is the acceptance gate |
| Existence hook only checks file exists → confession-template theater | **ADOPTED** → content-contract template (7 fields) + reflow-gate |
| "survives your reading" filter still in the skill | **ADOPTED** → filter killed (adversarial-referee) |
| root_cause_id vocab could be gamed by splitting | **ADOPTED** → vocab frozen; changes need RP-1 |
| RP-1 high-frequency heartbeat is over-engineered pre-teeth | **PARTIALLY REJECTED** → heartbeat kept (it caught this very blocker); narrowed so the first heartbeat verifies teeth landed. Surfaced to the user; user's earlier choice of cadence=3 stands. |

### grok #3 (are the teeth real?) — `meta-reviews/grok-review-3.json`

| criticism | disposition |
|---|---|
| 6 teeth verified real (freeze gate exit 1, trap, filter gone, CRs exist, gate red/green, no escape valve) | **ACKNOWLEDGED** (external confirmation, not a fault) |
| reflow-gate is a substring SHAPE gate, not a content gate; `x/y/z` fields still PASS; [LANDED] over-claimed "content" | **ADOPTED** → relabelled "existence+shape" in doc + skill; substance is RP-1's job (two-layer defense) |
| CR-05 anti-recurrence mislabels the crime: dirty-tree gate ≠ post-dispatch rework override | **ADOPTED** → built `scripts/rework-lint.sh` (post-dispatch half), red-tested against 08d's historical note; CR-05 split honestly |
| meta-review ledger doesn't exist while the skill demands it | **ADOPTED** → this file |
| CR-06 evidence pointer dangles (scratchpad outside repo); self-praise tone | **ADOPTED** → pointer fixed to archived review; wording made honest about the demo jumping the gate |
| Teeth only in uncommitted worktree; main + in-flight demo still toothless | **ADOPTED (surfaced to user)** → requires commit + merge to main; the user's call, raised explicitly |
| reflow-gate / rework-lint not wired as Stop hook; RP-1 template, worker-binding ledger, receipt.schema attribution field, CR-03 fixture_ref schema, tombstone-rewrite hook still absent | **QUEUED (honest [DESIGNED])** → in the build order, not claimed as done |
| CR line-number pointers drifting after edits | **ADOPTED (minor)** → anti-recurrence checks are grep-based not line-based; evidence line refs to be re-pinned at commit |

**Net**: grok #3 upgraded the verdict from "empty shelves" to "baby teeth erupted, canines pending, one false tooth (CR-05) — now fixed." No criticism silently dropped.

### grok #4 (are the two P1 quant skills real?) — `meta-reviews/grok-review-4.json`

Triggered not by the machine but by the **user** ("跟 grok 交流没？") after the commander built honest-validation + factor-research-flow, self-assessed them, merged one, and said "no external review needed." The trigger firing from a human is itself the finding (CR-07). First dispatch died on a `grok --resume` zero-CPU hang (~2h, infra-fault); re-dispatched fresh, returned in 85s.

| criticism | disposition |
|---|---|
| Commander self-exempted its own skills from RP-1 and rationalized it — the B-grade double-standard, recurring | **ADOPTED** → CR-07; new vocab `commander-self-exempt-from-review` |
| `prereg-gate` is bypassable (stub prereg → run → backfill looser thresholds → passes): checks commit ordering, not content freeze; I over-claimed "content" | **ADOPTED** → honest downgrade in skill + doc; real tooth = content-hash into run_config (DESIGNED); pattern logged as CR-08 (`gate-tests-happy-path-not-bypass`, n≥3 with reflow-gate + CR-05) |
| factor-flow's "no hook because judgment" washes a gap into a virtue — net/residual/ADV ARE mechanizable once params frozen | **ADOPTED** → skill rewritten: predicates are DESIGNED-not-built and the stack is gross paper (no cost model) |
| honest-validation rule 6 (LLM refutation as factor belief gate) is process-astronaut | **ADOPTED** → reframed to delayed OOS / paper trading; RP-1 keeps the skill honest, does not certify a factor |
| ~70% overlap with `quant-mentor`; real increment = court binding + null-archival + (weak) prereg-gate | **ADOPTED** → "honest scope" note added to the skill |
| Missing desk muscle (multiple-testing budget, IC half-life/rolling OOS, regime, crowding, implementation shortfall, residual-IC pipeline, capacity screen, portfolio layer) | **ADOPTED (queued)** → build-order item 6; many genuinely v0.2+ |

**Net**: the P1 muscles are real `court` wiring but thin on novel value over `quant-mentor`, and the one tooth was theater. Corrected in place; factor-research-flow held from merge until corrected. Two commander-rework entries (CR-07, CR-08) opened. The loop's most honest moment: a human, not the machine, had to fire grok #4.

### grok RP-1 review — résumé case study — `meta-reviews/case-study-review-raw.json`

Dispatched fresh (`grok --prompt-file … --always-approve --cwd …`, no `--resume`) on the Simplified-Chinese `docs/case-study.md`, *after* an internal 5-slice claim-audit had already fixed 6 issues. grok independently re-ran the verification (report.md numbers, `skill-review-gate` red-test, file anchors, throughput counts, pre-reg timing — all confirmed). Grade **B / revise**.

| criticism | disposition |
|---|---|
| Pre-registration claimed as honored, but the pre-registered 20-seed sweep appendix (killer-demo.md §7.4) was never run (`report.md`: "Sweep not run"; no `out/sweep/`) — a 禁赢学 doc silently omitting part of its own protocol | **ADOPTED (major)** → §3 discloses the sweep as an un-executed honesty debt; only the main-run freeze is claimed |
| B-grade → "turned three criticisms into hard rules I carry across projects" washes a "competent, not yet worthy of your own strictness / C+ hygiene / structural double-standard" verdict into a discipline medal (standing sin) | **ADOPTED (major)** → §4.3 states the reviewer's actual one-sentence verdict + that the double-standard is unresolved; medal framing removed |
| "~4,900 lines of product Python" counts `examples/` (≈2.0k demo fixture) as product (court+adapters = 2931) | **ADOPTED** → LOC/run-count facade cut; throughput reduced to 20 issues / ~14 dispatched / 8 reworks / 144 tests |
| §4/§5 tie CR-08 to skill-review-gate, but the gate mechanizes **CR-07**; concept-graft | **ADOPTED** → CR-07 (the gate) and CR-08 (standing failure mode; real tooth still DESIGNED) separated |
| §6 "needs no assertion" then asserts "a real tool" + "AI process designed and used" — residual ceremony | **ADOPTED** → §6 leads with the concrete 0/100 result; process downgraded to "construction traces, not a product" |
| Throughput still opens §4 as facade; translationese ("aspirational", ceremony sentences) | **ADOPTED** → throughput de-emphasised; "aspirational" → 中文; ceremony trimmed |
| **Disclosure**: commit `d0618fc` subject named the target employer in public-tracked git history — body clean, history not | **ADOPTED** → commit reworded to remove the employer name (branch un-pushed) |
| Disclosure-boundary Status checklist stale (all `[ ]`) — reads as process-theater | **ADOPTED** → Status tracker updated to reality |
| `docs/design/quant-workflow-system.md` names the target employer + résumé strategy in public git | **QUEUED** → already a registered pre-publish cleanup item; not this artifact |

**Net**: the internal audit caught the first layer; the independent cross-model second eye caught what it missed — chiefly the seed-sweep honesty debt and the B-grade-as-medal relapse, both verified against the repo. grok's strongest-part call: §1 defendant autopsy (the only self-award-free, quant-dense section). All criticisms adjudicated here, none dropped.

### distinctness review — two new workflow-station skills (`data-pipeline-hygiene`, `research-session-protocol`)

Triggered by the user re-framing the workflow boundary ("workflow = the research pipeline *around* court, not court"). Built via a workflow that drafted each station then ran an adversarial **distinctness** check — the commander's known failure mode is reskinning court / quant-mentor as "new muscle". Both drafts came back **partly-reskin**; every flag was cut before commit:

- **research-session-protocol**: court-wiring in the hand-off (§5); verbatim 禁赢学 rule 5 / factor-research-flow §1 / quant-mentor #1 restatements; an arbitrary "K≈10–20" (a mood dressed as a threshold — the exact sin this project condemns); a seed-per-row identity the adapter's zero-RNG makes wrong; a false "isomorphic to prereg-gate.sh". **Fixed:** K derived from the multiplicity haircut; honest-N reframed as effective multiplicity for *any* correction (not court internals); sign-flip / mechanism / kill-test compressed to citations + the session-scoped increment; replay identity = (data_tag + fork coords); N_eff + garden-of-forking-paths added; worked example added.
- **data-pipeline-hygiene**: `COST_DECLARATION` (a cost string) mis-cited for a *tradability* trap (T7); `evaluate_shifted` mis-attributed as a label-shift probe (it shifts the *score*, §7.3); a restated FRF §2 invariance line; a US/crypto timezone import; P10 restating existing adapter code. **Fixed + added** the quant-specific traps a both-sources desk hits: cross-source code reconciliation (`SH600000` vs `sh.600000`), baostock string/empty→NaN semantics, delisting terminal return, index announce-vs-effective lag, and a worked leak example (a level look-ahead that *passes* the court).

Verdict after fixes: each skill carries an explicit "what this is NOT" boundary vs court / quant-mentor / honest-validation / factor-research-flow / the sibling station, and tags every mechanizable-but-unbuilt part [DESIGNED]. **Not merged to main — a fresh cross-model (grok) RP-1 review is the gate before that (`skill-review-gate.sh`).** The distinctness adversary was same-model (Claude), so it is a first pass, not the RP-1 cross-model eye.

### grok RP-1 review — two station skills — `meta-reviews/stations-review-{prompt.md,raw.json}`

Fresh cross-model grok RP-1 (no `--resume`, `--always-approve`, `--cwd`) *after* the same-model distinctness pass — grok ran Python to check the multiplicity math and **logged into baostock live** to verify fields. Grades: **data-pipeline-hygiene B/revise; research-session-protocol C/cannot-ship-as-is**. Every L2 [LANDED] binding verified correct except one mis-cite; the C was earned by a wrong number in the one place it most matters. All adopted:

| criticism | disposition |
|---|---|
| **RSP [BLOCKER]** worked-example K-math wrong: \|t\|=2.5 fails the bar at K=16 (survives to K≲4), \|t\|=3 fails at K=40 (K≲18); "Šidák/BHY" blurs FWER and FDR | **ADOPTED** → independently re-derived (K ≲ α/p\*, confirmed in python); budget rule rebuilt with a correct \|t\|→K table, FWER (Bonferroni/Šidák) split from FDR (BH/BHY), best-of-N flagged as White Reality-Check; worked example redone in \|t\| terms (K=16 for expected \|t\|≈3; K=60 needs \|t\|≥3.34) |
| **RSP [major]** "honest N = empirical-null pool" / "199 offset jury is the null your N feeds" — court concept-crossing (the very workflow/court conflation the user first caught) | **ADOPTED** → N → DSR trials / FDR family / best-of-N selection; the 199-offset jury (`B_OFFSETS`) is an *independent* null-resolution parameter, not fed by N |
| **RSP [major]** worked RankIC=0.031 → \|t\|≈2.5 not derivable without T / IC-vol | **ADOPTED** → rebuilt in \|t\| terms with an explicit "needs T, mean IC, IC vol" caveat |
| **DPH [major]** [LANDED] summary still mis-cited `COST_DECLARATION` (a §4.4 *cost* string) as the T7 *tradability* tooth (body already separated them) | **ADOPTED** → summary fixed; golden-fingerprint re-attributed to the adapter's determinism battery (not this station's gate); `tradability_declaration` marked [DESIGNED] |
| **DPH [minor]** worked-leak "sails through DSR/PBO/pool" uncalibrated; T5 over-reassures | **ADOPTED** → softened to "plausibly court-passing"; T5 cross-refs T10 |

grok's cross-boundary check: hygiene vs RSP is clean (same `adjustflag` knob, different failure modes); the residual risk was RSP's downward conflation with court, now removed. This archived review now rides with the two skills, so a future main-merge's `skill-review-gate` co-presence is satisfied by a review that **actually covers this pair** (closing the false-pass logged in the inbox for this case). Substance still ultimately a human/RP-1 call, by design. Every criticism adjudicated here, none dropped.

### distinctness + correctness pass — P2 stations (backtest-reuse-guard built; research-brief **CUT**)

A workflow drafted two P2 candidates; each adversary carried a `should_exist` verdict (set to judge `research-brief` harshly, since reskinning is the standing failure mode). Same-model pass, before the grok RP-1 below.

- **research-brief — CUT (`should_exist = cut-as-reskin`, mostly-reskin).** Shown to be: §1 = honest-validation §1 + RSP §3; §2 = RSP's kill-test at a different granularity; §3 = quant-mentor #12 + factor-research-flow §3 relabeled; §4 = repeats the "court can't see net-of-cost" fact the whole workflow already teaches. The one genuinely-distinct nugget (a decision-type → metric typology as a pre-idea selector) discharges no named gap. **Rejected rather than padded** — the distinctness gate doing its job (the thing I promised the user I'd let it do).
- **backtest-reuse-guard (工位三) — BUILT (`should_exist = build`, distinct).** The anti-NIH station: reuse the oracle (qlib returns/IC, vectorbt/openalgo PnL loop, court statistics), write only the factor + orchestration, keep `court/` decoupled. Correctness fixed: the flagship worked example **called the court API wrong** — `Application(dsr=…)` → `Application("dsr", {...})` (positional `NamedTuple`, `court/judge.py`); statistic name is `"noise_control"`, not `empirical_null_p`; `judge(ledger, scope, [...])` — a wrong API call in a *reuse-the-audited-API* skill is the exact anti-pattern (now called out in-text too). Pearson-vs-Spearman "usually larger" → "either direction". Reskin trimmed: dropped the court-index-y judge/ledger register row; grounded the 工位 numbering (added 工位二 to research-session-protocol). All 12 register function names verified present in `court/`. Not merged to main — **grok RP-1 is the next gate.**

### grok RP-1 review — backtest-reuse-guard (工位三) — `meta-reviews/backtest-reuse-guard-review-{prompt.md,raw.json}`

Fresh grok RP-1 (ran python to test the API incl. edge cases + ran the smoke test). Grade **B/revise**; the API call the same-model pass had fixed verified **correct** (Application positional, `"noise_control"`, judge signature `(ledger, scope, config)`, all 12 register names, decoupling test 2 passed). Two majors + minors adopted:

| criticism | disposition |
|---|---|
| **[major]** the 工位二↔court seam was mis-wired: worked example said honest N "feeds DSR's `n_trials`", but under `court.judge` `_apply_dsr` reads only `selected_trial_id`+`confidence` and derives multiplicity from `ledger.matrix(scope)` column count (grok verified: `n_trials=999` param silently ignored; single-trial scope raises) — same family as the RSP blocker | **ADOPTED** → honest N realized as *the trials registered into the ledger scope* (log all, not just the winner); only a *direct* `court.dsr` takes `n_trials`. Fixed in worked example / §4 / boundary / See-also — and it is a *deeper* anti-self-deception point (can't claim N=40 without 40 trials on the ledger). Independently confirmed by reading `_apply_dsr`. |
| **[major]** §2 register ≈ 83% court/adapter API index (a phone book, not portable muscle); "useful even without alpha-court" rested only on §1+§4 | **ADOPTED** → relabeled §2 the *in-repo oracle map* (L2 binding) + added greppable anti-patterns (`def sharpe`, `np.corrcoef`-as-IC, `for..dates` equity loop, duplicate `n_trials`/`pbo`) as the run-anywhere tooth |
| **[minor]** empirical-null≡White Reality Check overreach; `fdr_by` labeled "BHY"; `DEFAULT_LABEL_EXPR` non-literal; adapter `evaluate` shown as free fn; §1.5 ghost section | **ADOPTED** → Phipson–Smyth p̂ (pool-max ≈ WRC *semantics*); Benjamini–Yekutieli (not the fn name "BHY"); exact literal with spaces; `.evaluate` shown as a method; §1.5 → §1/§3 |

grok **agreed cutting `research-brief`** (`agree-cut`): the pre-idea decision-type→metric selector discharges no named gap; if a real mapping table ever exists, fold it into `factor-research-flow` §0/§1 rather than revive the skill. grok's strongest-part call: §3 decoupling law + honest smoke-tooth limit (import-time only, not CI-wired) + §4 divergent-duplicate thesis. Every criticism adjudicated here, none dropped.

### grok RP-1 review — 工位二 trial-count tooth — `meta-reviews/trial-counter-review-{prompt.md,raw.json}`

Fresh grok RP-1 on the built tooth. It **ran pytest (5 green then 8)** and **independently reproduced the CR-08 discrimination** (a naive in-memory counter fails the kernel-restart red-test; file-backed passes) — the CR-08 claim is real, not theater. Grade **B/revise**; a blocker + majors, all adopted (each reproduced before fixing):

| criticism | disposition |
|---|---|
| **[BLOCKER]** reconcile/CLI PASSes on an **empty/absent** ledger — actively greenlights a phantom N (reproduced: `reconcile(empty, K=12, N=12)` → ok=True) | **ADOPTED** → `no_evidence` flag (actual==0 & reported_n>0 → not ok); CLI now FAILs "no evidence"; red-test `test_bypass_empty_dir_phantom_n` written first (red), then fixed |
| **[major]** `trial-ledger.jsonl` collides with `court.Ledger` / `docs/design/trial-ledger.md` (concept-crossing, same family as the earlier "N = empirical-null pool") | **ADOPTED** → renamed `session-trial-count.jsonl` + `TrialCountError`; skill states "≠ court.Ledger" |
| **[major]** honest limits missed multi-dir **sharding** + fresh-empty-dir (run 40 across two dirs, each reconcile passes) | **ADOPTED** → stated limit (one canonical session_dir) + `test_bypass_sharding_is_a_stated_limit` pins it |
| **[major]** [LANDED] + "no teeth" softening reads astronaut given the empty-ledger PASS + unwired CONFIRM | **ADOPTED** → narrowed to "[LANDED, narrowly] file-backed counter + manual reconcile helper"; "no teeth" line removed |
| **[minor]** malformed/null/float `arms` → silent crash / truncation (2.9→2) | **ADOPTED** → `count_trials` fails loud (`TrialCountError`); strict positive-int; `test_malformed_ledger_fails_loud` |

The pattern held honestly: I wrote *some* bypass red-tests (under-report, kernel-restart) but **missed others** (phantom-N, sharding); the cross-model eye caught them. CR-08 is "write the bypass red-test first" — and the RP-1 review is *how you find the bypasses you didn't think of*. 8 tests green, ruff clean. Every criticism adjudicated here, none dropped.

### 工位三 anti-pattern grep gate — built via a 4-lens bypass-enumeration workflow

The 工位三 [DESIGNED] tooth, built with the trial-counter lesson applied *harder*: the bypass set itself needs more than one mind, so **before** writing the red-tests a 4-lens workflow (false-positives / evasions / scoping / structural-limits, grounded in the real `court/` source) enumerated the bypasses — far past what I'd list alone. Design-shaping catches:

- the repo lives under `alpha-court/`, so a **substring** exclusion on "court" silently skips the whole tree → exclude by path **component**;
- court's own kwargs / return-fields (`n_trials=`, `pbo`, `deflat`) and a legitimate court **call** false-positive on bare tokens → anchor patterns to a `def` / inline formula / named correlation, never a bare token (a grep that cries wolf gets ignored);
- evasions the naive pattern missed: `.std(ddof=1)`, `np.std(`, 244/250 annualization, `.corrwith(` / `spearmanr` / `pearsonr`, `for … in trading_dates`, vectorized `.cumprod()`, `re.IGNORECASE`;
- stated grep-blind limits (pinned by tests): hand-*expanded* arithmetic (DIY Pearson; the worst duplicate — a Sharpe SE dropping the skew/kurtosis correction), aliasing, multi-line, `.ipynb` (reported-skipped, never silent).

`harness/anti_pattern_gate.py` + `tests/test_anti_pattern_gate.py` (8 tests: positives / false-positive-avoidance / stated-limits / exclusion-by-component / the `alpha-court` substring trap / notebook-reported). CR-08 discrimination is inherent — a naive bare-token grep fails the false-positive negatives (it flags the court source + a court call). backtest-reuse-guard's greppable list → [LANDED, high-recall]. **grok RP-1 queued next** (this enumeration was same-model; the cross-model eye is the next gate before merge).

#### grok RP-1 review — 工位三 anti-pattern gate — `meta-reviews/antipattern-gate-review-{prompt.md,raw.json}`

Fresh grok RP-1 (ran pytest + FP/evasion/exclusion probes + the strip FSM). Grade **C/revise** — harsher than the trial-counter, and right: even the 4-lens *same-model* enumeration + I missed real bugs a cross-model eye running the real regex found. Every one reproduced, then fixed:

| criticism | disposition |
|---|---|
| **[BLOCKER]** single-line docstring `"""…corrcoef…"""` flagged (my fence tracking only handled multi-line; even marks slip through) | **ADOPTED** → replaced hand-rolled #/fence stripping with a `tokenize`-based string+comment blanker (single/multi-line strings, escapes, config strings); red-test added |
| **[BLOCKER]** skill self-contradiction: greppable list [LANDED] but Honest form still [DESIGNED] | **ADOPTED** → Honest form reuse-lint → [LANDED, advisory]; CI wiring + static AST check stay [DESIGNED] |
| **[major]** cry-wolf migrated to research: vol `std*sqrt` (no mean), `.corr(` orthogonality, bare date-loop, and **`examples/killer_demo/report.py:_pbo_row`** → repo self-scan *always FAILs* | **ADOPTED** → Sharpe-inline now also requires `mean`; bare date-loop dropped (grep-blind limit); `examples/` excluded; `.corr(`/vol/`cumprod` stated as high-recall barks; `test_repo_self_scan_is_clean` pins it |
| **[major]** `_STAT_DEF` missed `def dsr/fdr/empirical_null` though the remedy promised them | **ADOPTED** → pattern + remedy aligned (dsr/fdr/bhy/empirical_null/noise_control/cscv/…); red-tests |
| **[major]** `_strip_comment` FSM ignored `\`-escapes → an escaped quote hid a same-line `corrcoef` (false negative) | **ADOPTED** → tokenize handles escapes; red-test (escaped-quote line still flagged) |
| **[major]** import-alias evasion `pearsonr as pr` | **ADOPTED** → `spearmanr/pearsonr/kendalltau` are bare tokens now (the *import* line is caught); red-test |
| **[minor]** directly-passed `court/x.py` scanned despite the tree-walk excluding it | **ADOPTED** → `scan_paths` checks path components for direct files too; red-test |
| **[major]** honest-limit label overclaimed ("high-recall") | **ADOPTED** → relabeled "high-recall, not precise" + expanded the limit list (arithmetic, aliasing, multi-line, synonyms, notebooks) |

10 tests green, ruff clean, repo self-scan PASS. **The session's deepest lesson**: a bypass red-test is only as complete as the bypass *set*, and even a **4-lens same-model** enumeration under-covers what a **cross-model eye running the real regex** finds (single-line docstring, escaped quote, examples-always-fail). CR-08's "write the bypass red-test first" and RP-1's "find the bypasses you didn't think of" are **one loop**. Every criticism adjudicated here, none dropped.

### CONFIRM-time budget gate — built via a 3-lens fail-open enumeration

The research-session-protocol [DESIGNED] budget gate, wiring `trial_counter` into the prereg step. The session's recurring bug is a gate that fails *open* on degenerate input (trial_counter's phantom-N; the anti-pattern gate's examples-always-fail), so **before** the red-tests a 3-lens workflow enumerated the degenerate-input surface. It front-loaded a **catastrophic** one I'd never have written a test for: **`json.loads` accepts the `NaN` token by default, and `NaN < actual` / `NaN > 0` are both False — so an un-validated gate certifies ANY reported N against a 100-trial ledger.** Plus the full taxonomy: `Infinity`, float, bool (int subclass), numeric string, null, negative, 0, missing key; missing/empty/relative/nonexistent/file `session_dir`; malformed/empty/non-object/absent prereg file; a swallowed `TrialCountError`.

`harness/confirm_gate.py` + `tests/test_confirm_gate.py` (9 tests). Design: `reported_n` must be a finite `int ≥ 1` (rejects `NaN`/`Infinity` via `json.loads(parse_constant=…)` + type/range checks), `session_dir` must be an existing directory, reconcile errors REFUSE (fail-closed), the gate keys on `r.ok` (all flags, never `under_reported` alone). What it adds over `trial_counter reconcile`: the strict validation + prereg-artifact wiring; distinct from `prereg-gate.sh` (commit ordering). Inherited trial_counter limits (NIH/wipe/shard) pinned. RSP budget-gate → [LANDED]. **grok RP-1 queued next** — this fail-open enumeration was same-model; the cross-model eye running real degenerate inputs is the next gate before merge (the loop that caught the phantom-N and the docstring bug the prior same-model passes missed).

#### grok RP-1 review — CONFIRM budget gate — `meta-reviews/confirm-gate-review-{prompt.md,raw.json}`

Fresh grok RP-1 (ran pytest + systematic degenerate-input probes). Grade **B/revise** — and the headline is a *confirmation*: after the 3-lens fail-open enumeration + implementation, grok **found NO type-level fail-open** (`NaN`/`Infinity`/`1e3`/`1.0`/bool/str/duplicate-key/BOM/fullwidth all refused; the NaN catastrophe is closed at the prereg boundary while raw `trial_counter.reconcile(s, nan, nan)` still returns ok=True on a 100-trial ledger). The enumeration-first approach held. Real fixes:

| criticism | disposition |
|---|---|
| **[major]** docstring said a *relative* `session_dir` is refused, but the code only `is_dir()`-checked → a relative path resolving in cwd PASSED (cwd-decoy) | **ADOPTED** → require `is_absolute()`; red-test; reproduced first |
| **[major]** skill "fail-closed on *every* degenerate input" oversells — the ledger's *identity* isn't verified (a decoy dir / symlink with honest-looking small N passes) | **ADOPTED** → narrowed to "fail-closed on malformed input"; decoy/identity named as an inherited limit in skill + docstring |
| **[minor]** `check_prereg(None/int/bytes)` → TypeError, not fail-closed at the API boundary | **ADOPTED** → `try/except TypeError` → refuse; red-test |
| **[minor]** `r.ok` "never under_reported alone" overstated (declared_k=n ⇒ over_budget ≡ under_reported) | **ADOPTED** → comment softened |
| **[minor]** skill "CONFIRM-time auto-wiring is not" next to [LANDED] read as a contradiction | **ADOPTED** → reconciled ("both real, callable+CLI, neither CI-wired") |

11 tests green, ruff clean. grok's strongest-part: the NaN/Infinity catastrophe is genuinely closed at the boundary. **Meta**: this is the first tooth where the same-model **enumeration-first** pass left the cross-model eye *no new type-level fail-open* — the front-loaded bypass enumeration did its job; grok's catches were honesty-of-labeling + two path edges, not a phantom-N-class blocker. The loop is converging: (bypass-enumeration workflow) + (cross-model RP-1) together cover what neither does alone. Every criticism adjudicated here, none dropped.

### skill-review-gate range-level false-PASS — fixed (2-lens enumeration)

The inbox hole (`079feda`): the gate's range-level co-presence was satisfied by an *unrelated* review. Fixed: per changed skill, require `<name>` **word-bounded** in a review's **added** lines. A 2-lens enumeration first showed the naive "grep the review for the name" is *itself* weak — substring (`research`⊂`research-session-protocol`, `implement`⊂`implementation`), an omnibus review that incidentally lists names, a stale review dragged in by a no-op touch. So: word-bounded (hyphen is a word char), **added**-lines-only (resists the touch), ALL-skills-covered, `--diff-filter=d` (deletions need no review). Verified against reality: the original `1ce25a7` sin still FAILs; all four real merges still PASS (their reviews name the skill); the exact unrelated-review case is now a red-test. `scripts/skill-review-gate.sh` + `tests/test_skill_review_gate.py` (8 tests). Honest residual limits in the gate header — a common-word skill name, an omnibus review that incidentally lists the name, and active-faking (paste the name) still pass; verifying a review is *about* the skill stays RP-1's/human's job (the CR-08 substance ceiling). **grok RP-1 queued next.**

#### grok RP-1 review — skill-review-gate fix — `meta-reviews/skillgate-fix-review-{prompt.md,raw.json}`

Fresh grok RP-1 (built temp git repos + probed real ranges). Grade **B/revise** — again the cross-model eye running real `git` caught what the 2-lens *same-model* enumeration missed:

| criticism | disposition |
|---|---|
| **[major]** `grep '^\+'` also matched the `+++ b/<path>` diff **header** — a skill named like a path token (`b`/`scratch`/`reflow`/`json`/`md`) was vouched for by ANY review's path | **ADOPTED** → `grep '^\+[^+]'` (added content only); red-test (`skill 'json' + unrelated .json review` → FAIL), reproduced first |
| **[major]** `${name}` interpolated **unescaped** into `grep -E` — a metachar name (`foo.bar`, `a\|b`) matched non-literally | **ADOPTED** → escape ERE metachars (`sed 's/[^A-Za-z0-9_-]/\\&/g'`); red-test (`foo.bar` not matched by `fooXbar`) |
| **[minor]** a reversed base/head silently PASSed "no skill change" | **ADOPTED** → hard-fail exit 2 when head is a strict ancestor of base; red-test |
| **[minor]** nested `skills/a/b/SKILL.md` mis-extracted the name | **ADOPTED** → single-level skill glob `[^/]+` |
| **[minor]** honest-limits missed the diff-header / metachar cases + that a review-*prompt* naming the skill counts | **ADOPTED** → header updated |

grok's strongest-part: the contract-core holes ARE dead — the original `1ce25a7` sin and the historical false-PASS (`a1c12ce^..d1a9fe0`, case-study covering the two stations) both FAIL; all four real merges still PASS. 11 tests green, ruff clean, `bash -n` ok. **Meta**: the two majors (diff-header `+++` leak, unescaped metachar) are bash-level footguns a same-model enumeration doesn't stumble on but a cross-model eye *executing real git* does — (enumerate-first) + (cross-model RP-1) caught them together. Every criticism adjudicated here, none dropped.

## 2026-07-13 — grok RP-1 review of the publish-audit gate + candidate public tree

Context: publishing the private dev repo as a **public GitHub snapshot** (highest stakes —
a leak into public git history is irreversible). Built enum-first (4-lens workflow, 56 vectors)
→ 50 bypass red-tests → naive-discriminative check → real gate. Fresh grok (session
`019f5708`, `--cwd` read-only worktree at `7e1393e`, real pytest + independent naive gate +
crafted payloads + byte-grep of the export tree). Ticket + raw archived:
`meta-reviews/publish-gate-review-prompt.md` (shipped); grok's raw JSON output is kept in
`docs/private/meta-reviews-raw/` (unshipped — third-party output in uncontrolled encodings that a
literal rewrite cannot fully normalize; available on request), its verdict fully transcribed in
the table below.

Grade **C / cannot-ship-as-is** — the cross-model eye found **11 bypasses (2 blockers, 4
majors, 5 minors)** that the same-model enum + 50 red-tests missed. All ADOPTED, each reproduced
first, each with a red-test (details table in `.scratch/publish/bypass-enumeration.md`):

| criticism | severity | disposition |
|---|---|---|
| home path was `[rewrite]`-only, not `[hard]` → audit rubber-stamps a tree still containing `[HOME]` if export rewrite is skipped/partial | **blocker** | **ADOPTED** → audit hard-set = hard ∪ rewrite-LHS; red-test reproduced the leak first |
| prior-employer fail-closed was TODO-marker-only → strip TODO w/o filling → ships | **blocker** | **ADOPTED** → positive `PUBLISH-RULES-CONFIRMED` affirmation required (absence of TODO ≠ affirmation); red-test |
| PNG iTXt compression_flag=1 not decompressed (docstring over-claimed it was) | major | **ADOPTED** → real iTXt parse + zlib; red-test |
| `\UXXXXXXXX` 8-digit escapes outside decode battery | major | **ADOPTED** → 8-hex pass; red-test |
| framing never scanned in binary (only PNG-extracted text) | major | **ADOPTED** → framing needles on binary; red-test |
| gzip/zip/xz containers not inflated → compressed token invisible | major | **ADOPTED** → archives REFUSED (magic+suffix); red-test |
| base64 of English token / CSS-hex / UTF-7 / punycode / quoted-printable slip the battery | minor ×5 | **ADOPTED** → decode battery extended (b64 / `\XXXX` / `\xXX` / utf-7 / punycode / quopri); red-tests; all 6 confirmed invisible to a naive matcher |
| commit body "50 tests (30/12)" — real was 48 (38/10) | honesty | **ADOPTED** → corrected (now 59: 49/10); noted in enum doc |
| PUBLISHING.md "cross-model reviewed" presented as done before this review | honesty | **ACKNOWLEDGED** → now true post-review+fix |

**Dogfood catch (emergent):** running the *fixed* audit over the export tree flagged the gate's
OWN shipping files — `tests/test_publish_audit.py` (a comment with real CSS-hex codepoints + literal
zero-width fixtures) and `harness/publish_audit.py` (literal BOM in an `lstrip`). Because test &
harness files ship (location-V3), they must pass the audit too. Fixed by building exotic chars
programmatically and removing real codepoints from comments. **The gate now passes its own audit** —
and this same discipline had to be re-applied to the *ledger/enum doc themselves* when appending
this record reintroduced the pattern. That recursion is the point: the knife is sharp enough to cut
the hand that documents it.

**Declared NOT covered (honest scope, not silently claimed done):** cross-file name-split, rot13 /
arbitrary ciphers, email `[at]`-obfuscation. Each is deliberate self-sabotage, not accidental leak;
the backstop is the mandatory owner eyeball-grep before push (PUBLISHING.md one-thing-before-push).

Post-fix: 59 tests green, ruff clean; end-to-end dry-run (real rules, TODO-stripped + sentinel):
export 257 files → audit **PASS 0 findings / 15 archive-zone warnings**; independent byte-grep for
all real forms ([REDACTED-EMPLOYER]/[REDACTED-EMPLOYER]/[REDACTED-EMPLOYER]/[REDACTED-EMPLOYER]/email/%-form/b64/home/`\u`-escape) → **0 residual**
(matches grok's own step-3). TOCTOU receipt binds + rejects a post-audit byte flip.

**Meta:** the two blockers are precisely the same-model blind spot RP-1 exists for — a rewrite-only
literal the audit never re-checked, and a fail-closed that a conscious owner could strip without
affirming. Neither surfaced in a 4-lens *same-model* enumeration; both fell to a cross-model eye
*running the real gate against real payloads*. (enumerate-first) + (cross-model RP-1) again covered
what neither does alone. Every criticism adjudicated here, none dropped.

## 2026-07-13 — grok RP-1 review of the git-hook enforcement (candidate B)

Context: wiring two manual gates (anti-pattern lint, skill-review) into pre-commit /
pre-merge-commit. Built enum-first (4-lens workflow, 66 vectors, `.scratch/githooks/`) → 35
bypass red-tests → impl. Fresh grok (session `019f5973`, `--cwd` read-only worktree at `7644641`,
real `git clone` + `install-hooks.sh` + pytest + crafted bypass commits + a real linked worktree).
Prompt archived `meta-reviews/githook-review-prompt.md` (shipped); grok's raw envelope kept in
`docs/private/meta-reviews-raw/` (uncontrolled encoding).

Grade **B / revise** — the core teeth are real and **naive-discriminative** (grok independently
swapped in a naive run-gates = worktree-scan + skill-on-HEAD + `exit $?`, and the 5 load-bearing
hook tests turn RED: index-vs-worktree, AND-not-swallowed, fail-closed-on-crash, staged-skill-
visible ×2). **Honesty ceiling explicitly upheld** (grok honesty_flags: *none* — the grok #5
"friction as enforcement" trap is avoided; `--no-verify` is asserted-as-bypass, not pretended
prevented). 6 findings, the 4 preventable ones ADOPTED, each reproduced + red-tested first:

| criticism | severity | disposition |
|---|---|---|
| suffix test `path.suffix == '.py'` is case-sensitive → a staged `evil.PY`/`Factor.PY` hand-roll (Python on a case-insensitive FS) is not scanned | major | **ADOPTED** → casefold the `.py`/`.ipynb` suffix; red-test `test_staged_uppercase_py_suffix_scanned` |
| a staged `.py` SYMLINK (index mode 120000) → `git show :path` returns the target path string, scanned as harmless text → PASS (smuggle a hand-roll via a symlink to an excluded dir) | major | **ADOPTED** → fail-CLOSED on a staged `.py` symlink (its blob is a path, not lintable source); red-test `test_staged_symlink_py_fails_closed` |
| skill-review hard-codes `main`; rename `main`→`master` and it silently skips ("nothing to land on") for a staged skill | major | **ADOPTED** → trunk resolvable via `git config alphacourt.trunk` (default main); if trunk unresolvable AND a skill is staged → fail CLOSED; red-test `test_hook_trunk_renamed_blocks_unreviewed_skill` |
| `# type: ignore  # reuse-ok: <reason>` false-blocks (one COMMENT token not starting with the marker) | minor | **ADOPTED** → match `reuse-ok:` anywhere in the comment token (search, not anchored); a no-colon prose mention still blocks; red-test `test_ack_after_type_ignore_still_exempts` |
| `core.hooksPath=.githooks` set but `.githooks/` absent (rm/stale checkout) → git silently no-ops | major/partial | **ACKNOWLEDGED as a declared hole** — the uninstalled/stale-worktree class (enum V9); if the hook file is gone nothing can run. grok confirms it is the most likely *accidental* real-world miss; documented, not falsely closed |
| one physical line, multiple findings, one `# reuse-ok:` exempts the whole line | minor/declared-hole | **ACKNOWLEDGED** — the CR-08 substance ceiling (the gate can't judge the reason); documented |

grok's **worktree verdict** (the point I hadn't tested): the hooks fire correctly from a linked
worktree — `core.hooksPath` is shared via the common config, `run-gates.sh` resolves `$ROOT` via
`git rev-parse --show-toplevel` (the linked worktree root, not the main tree), and a hand-roll from
a linked worktree BLOCKS. No cross-bind bug. The only worktree hole is the uninstalled/stale one
(V9, declared).

grok also confirmed several things DON'T fail open (independent real runs): PATH-without-python →
fail-closed; broken `.venv` python → fail-closed; missing `skill-review-gate.sh` → fail-closed;
detached HEAD hand-roll → BLOCK; `--no-ff` merge with hand-roll/unreviewed-skill → pre-merge-commit
BLOCKS; write-tree with unstaged (working-only) hand-roll → correctly index-only PASS. And it
validated the skill-range decision (Option A): skill-only commit BLOCKS, skill+review co-staged
PASSES, amend-skill-without-review BLOCKS — the co-stage discipline mechanized, as designed.

**Meta:** the fixes are the **V17 family the enum NAMED but the suite let stay green** — the exact
CR-08 "under-test a known vector" pattern, caught here not by the same-model suite but by the
cross-model eye *running the real hook against real payloads* (`evil.PY`, a symlink, a renamed
trunk). (enumerate-first) surfaced V17; (cross-model RP-1) forced it from "admitted" to "tested +
closed". Post-fix: 39 tests green, ruff + `bash -n` clean. Every criticism adjudicated here.

## 2026-07-13 — grok RP-1 review of the static court-import gate (candidate A)

Context: a static AST gate enforcing iron law #2 (court/ market-agnostic), complementing the
import-time dynamic smoke. Built enum-first (4-lens workflow, 63 vectors, `.scratch/court-import/`)
→ 46 bypass red-tests → impl → wired into the armed pre-commit hook.

**Infra note (RP-1 heartbeat, not a verdict):** the first grok dispatch died at turn 3
(`stopReason: Cancelled` — the CLI's known flakiness). Re-dispatched fresh per the referee's
infra-fault rule (worker code un-blamed); the re-run finished clean (EndTurn, 10 turns).

**Independent referee pass (parallel to grok):** while grok re-ran, the commander's own
adversarial probe already caught 3 dynamic-import evasions the 46 red-tests missed (assignment
rebind of import_module, attr-to-name rebind, `builtins.__import__`) and fixed them red-test-first
BEFORE grok returned — the "independent re-run" half of the referee discipline working.

Fresh grok (session `019f599a`→re-run, `--cwd` at `92a1af6`, real clone + pytest + independent
naive gates + crafted court/*.py) graded **C / revise**, 8 findings. CR-08: **naive-discriminative**
(none green-on-naive; grok's own naives — body_only / rel_always_ok / first_alias_only /
full_dotted — each turn the matching reds RED), but the C is the **recurrence**: the 63-vector enum
*named* major carriers (symlink-dir, V06 rebind, V14 builtins) yet red-tests were written only for
the easy spellings. All ADOPTED, each reproduced + red-tested first:

| criticism | severity | disposition |
|---|---|---|
| symlinked DIRECTORY under court/ (`court/sub -> ../adapters`) invisible: os.walk(followlinks=False) doesn't descend it, and --staged's .py filter skips the mode-120000 entry | **blocker** | **ADOPTED** → scan_court flags symlinked dirs AND files; scan_staged lists all court/ paths and flags any 120000 symlink; red-test `test_symlink_dir_carrier_flagged` |
| dynamic import: secondary Name rebind + `builtins.__import__` (Attribute) | major | **ADOPTED (already found+fixed independently)** → `_is_of_kind` matches Attribute `.attr in {import_module,__import__}` + fixpoint alias tracking; `from builtins import __import__ as X` also tracked; red-tests |
| exec/eval/compile only matched as a bare Name (`builtins.exec(...)`, `e=eval; e(...)` slip) | major | **ADOPTED** → exec/eval/compile via Attribute + rebind (same `_is_of_kind`/alias machinery); red-tests |
| code-loaders `spec_from_file_location`/`SourceFileLoader`/`run_module`/`run_path` not flagged (enum listed; design left it open) | minor | **ADOPTED** → flagged coarsely (court has no reason); red-test |
| design/docstring "level ≥ 2 always escapes" is wrong for package depth > 1 (code is correct) | minor over-claim | **ADOPTED** → doc reworded: escape level = package-depth + 1; the code resolves the absolute top-level (no hard threshold) |
| `import __main__` false-flagged (not in stdlib_module_names) | minor false-flag | **ADOPTED** → `__main__` allowed; red-test |
| deep indirection (`getattr(builtins,"__import__")(...)`, `vars()[...]`, partial, methodcaller) not caught | declared-limit | **ACKNOWLEDGED** → labelled a declared limit in the docstring + a red-test asserting the PASS is documented, not a claimed catch |
| `import numpy.<market>` top-reduces to numpy = allowed | declared-limit | **ACKNOWLEDGED** → name-shadow/namespace-borrow is a declared limit (names trusted, not provenance); not real loadable market code |

grok confirmed the **honesty ceiling holds**: docstring + commit state import ≠ semantic decoupling
(runtime cal object / 252 / 10% / hard path), with locking tests; "no evidence of selling the gate
as full market-agnostic proof." grok also verified the **relative resolver matches Python semantics**
(court/sub/deep `from ...adapters` = court.adapters ALLOW, `from ....adapters` FLAG) and the
**stdlib probe** (301 names on this interpreter, zero market top-levels collide → no false-allow).

**Meta:** the headline blocker (symlink-dir) is the exact CR-08 recurrence the *previous* tooth was
graded on — enum named it, red-test never written, gate green. Caught here by the cross-model eye
running the real fixture; and the 3 dynamic-import evasions were caught by the commander's own
independent probe first. (enumerate-first) + (independent referee pass) + (cross-model RP-1) — the
three together closed what any one missed. Post-fix: 98 tests green (56 court + others), ruff clean,
clean court/ tree still 0 violations. Every criticism adjudicated here.

---

## 2026-07-20 — v0.2 power-milestone role-reversal meta-review (fresh grok, read-only worktree @ 99cc29b4; archive `.scratch/dispatch/meta-review-commander-v02/`)

**Grade B+.** One-sentence: "你会审自己、也肯判工人赢，但还没把「写进票面的每个因果」和「烧机时前的每个预检」抬到你要求工人达到的同一失败闭环。" Post-flight tripwire: worktree untouched. Every criticism adjudicated below — none dropped.

| # | Criticism / objection | Ruling | Action (same day unless noted) |
|---|---|---|---|
| W1/TC1 | Unreproduced crash mechanism written into frozen rework-02 (FIX-C "NaN row" + "today raises" AC) — CR-03 family, one layer up | **ADOPTED** | Already self-inboxed 07-19; ledger records grok's elevation (the false fact was load-bearing in the AC). Vocab RP-1 naming pending. |
| W2/TC2 | No acceptance-preflight before the 31h burn (targets ⊄ frozen β*; matched solver untested on re-centered β scale); "contract-secondary" prose under-charged | **ADOPTED, mechanized** | `tests/test_acceptance_preflight.py` (2 tests; verified historically red at `c987a5b9`: missing=[3.0]). Inbox entry `?acceptance-preflight-missing`. |
| W3 | FIX-B attribution "纯 worker" unfair — commander re-centered β grid, never re-verified the matched solver | **ADOPTED** | 05 Answer amended: FIX-B → worker-primary + contract-secondary. |
| W4 | rework-02 ownership list contradicted its own FIX-B (stats_util unreachable) | **ADOPTED** | CR-14 (`ticket-self-contradiction` #6); pre-dispatch lint gains symbol-trace step. |
| W5a | CR-13 tooth still [DESIGNED]; naked resume still permitted | **ADOPTED (standing)** | resume-preflight = next-session priority tooth (with bypass red-tests per CR-08); until then CR-13's standing rule governs. |
| W5b | CR-13 not in the INDEX "table" | **REJECTED-with-reason** | INDEX has been prose-format since CR-09; CR files are the record. CR-13/14 both indexed in prose. |
| W6a | "31h 零浪费" glossed that 240/880 arms were later quarantined | **ADOPTED** | Correction recorded here + in the 07-20 TIMELINE entry: data survived intact, but the appendix arms' *information* did not — "零浪费" was an overclaim. |
| W6b | "PBO-optimism 未实现" ≈ non-detection dressed as refutation | **ADOPTED** | APPENDIX-RERUN.md re-worded: non-detection at R=40 (invisible below ~0.12), not proof of absence. |
| W6c | map.md "~9-12h" vs actual 31h | **ADOPTED-as-record** | Historical estimate stands unedited (no retro-polish); the miss itself is the record. |
| V-FIX-A partial (secondary weight) | Freeze+launch were commander-side; arm-0 preflight would have caught it | **ADOPTED-in-part** | Weight noted here; split retained; W2's mechanized tooth is the substantive answer. |
| V-CR13 worker-secondary tone | "擅用" 语气过重 — worker was pushed into the only writable tree | **ADOPTED (tone), tag retained** | CR-13 wording softened, dispute recorded per the worker-dispute rule. |
| V-appendix wording partial | — | **ADOPTED** | Same as W6b. |

**Verdicts accepted without objection** (hero/appendix split; stats_util worker-win; 517-vs-532 env delta; CR-13 retain-a51f66e4; FIX-C misdiagnosis self-charge) stand as ruled. Fairness finding ("no systematic anti-worker bias; discount concentrated in attribution ratios") accepted.
