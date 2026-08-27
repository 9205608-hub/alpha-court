# Publishing provenance / 发布来源披露

**中文** — 本仓库的公开形态是私有开发仓的**脱敏快照**（单向镜像）：

- 公开侧不含开发期 commit 历史。凡依赖 commit 顺序的主张（预注册先于结果、绕过红测先于
  实现），证据在私有历史中，可应要求完整出示。
- 遮盖动作**最小、可见、逐项列在下方清单**：归档的第三方外审原件中，机构名等标识以
  `[REDACTED-EMPLOYER]` 标记遮盖，本机绝对路径以 `[HOME]` 遮盖（原件在私有仓保持
  原样——证据品不在真相源上篡改）；一份内部工作日志（`TIMELINE.md`）整体不进入公开快照。
- 归档区（`.scratch/`）保留其历史语境原文；对其中语境词的计数披露见下方清单。
- 除清单所列外，公开版本与私有真相源**无内容差异**。
- 每次快照同步都必须先通过发布审计门（`harness/publish_audit.py`）——该门自身带
  绕过红测，并经跨模型外审。

**EN** — This repository's public form is a **desensitized snapshot** (one-way mirror)
of a private development repository:

- The public side carries no development commit history. Claims that rely on commit
  ordering (pre-registration before results; bypass red-tests before implementation)
  are evidenced in the private history, available in full on request.
- Redactions are **minimal, visible, and itemized below**: institution identifiers inside
  archived third-party review artifacts are masked as `[REDACTED-EMPLOYER]`, and local
  absolute paths as `[HOME]` (the originals remain untouched in the private repo —
  evidence artifacts are never edited at the source of truth); one internal work log
  (`TIMELINE.md`) is excluded as a whole.
- The archive zone (`.scratch/`) keeps its historical context verbatim; contextual-term
  counts for that zone are disclosed in the manifest below.
- Beyond the manifest below, the public version has **no content difference** from the
  private source of truth.
- Every snapshot sync must pass the publish-audit gate (`harness/publish_audit.py`),
  which is itself bypass-red-tested and cross-model reviewed.

## Redaction manifest（导出时生成 / generated at export time）

<!-- PUBLISH-MANIFEST:BEGIN -->
- files exported: **519**
- files excluded: `.scratch/dispatch/v0.3-00-blade-plumbing/ticket.md`, `TIMELINE.md`
- visible redactions (file — marker × count):
  - `.scratch/court-import/bypass-enum-raw.json` — [HOME] × 4
  - `.scratch/dispatch/v0.1-01-bridge-probe/raw-20260710-164902.json` — [HOME] × 7
  - `.scratch/dispatch/v0.1-01-bridge-probe/receipt-20260710-164902.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-02-repo-scaffold/raw-20260710-164104.json` — [HOME] × 7
  - `.scratch/dispatch/v0.1-04-dsr-literature/raw-20260710-171728.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-04-dsr-literature/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-04-dsr-literature/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-05-pbo-cscv-literature/raw-20260710-171735.json` — [HOME] × 3
  - `.scratch/dispatch/v0.1-05-pbo-cscv-literature/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-05-pbo-cscv-literature/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-06-bhy-literature/raw-20260710-171741.json` — [HOME] × 3
  - `.scratch/dispatch/v0.1-06-bhy-literature/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-06-bhy-literature/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08a-court-ledger/raw-20260710-221535.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08a-court-ledger/receipt-20260710-221535.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08b-sharpe-dsr/raw-20260710-220550.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08b-sharpe-dsr/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08b-sharpe-dsr/receipt-20260710-220550.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08b-sharpe-dsr/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08c-pbo-cscv/raw-20260710-220557.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08c-pbo-cscv/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08c-pbo-cscv/receipt-20260710-220557.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08c-pbo-cscv/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08d-tstats-fdr/raw-20260710-220604.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08d-tstats-fdr/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08d-tstats-fdr/receipt-20260710-220604.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08d-tstats-fdr/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08e-noise-control/raw-20260710-220610.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08e-noise-control/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-08e-noise-control/receipt-20260710-220610.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08e-noise-control/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-08f-judge/raw-20260710-223952.json` — [HOME] × 8
  - `.scratch/dispatch/v0.1-08f-judge/receipt-20260710-223952.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-09-qlib-cn-data/raw-20260710-171748.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-09-qlib-cn-data/raw-resume.json` — [HOME] × 10
  - `.scratch/dispatch/v0.1-09-qlib-cn-data/receipt-20260710-171748.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-09-qlib-cn-data/receipt-resume.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-10a-adapter-impl/raw-20260711-001636.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-10a-adapter-impl/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.1-10a-adapter-impl/receipt-20260711-001636.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-10a-adapter-impl/receipt-rework-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.1-11a-killer-demo/raw-20260711-010211.json` — [HOME] × 5
  - `.scratch/dispatch/v0.1-11a-killer-demo/receipt-20260711-010211.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-05-power-harness/raw-20260717-134408.json` — [HOME] × 2
  - `.scratch/dispatch/v0.2-05-power-harness/raw-rework-01.json` — [HOME] × 2
  - `.scratch/dispatch/v0.2-05-power-harness/raw-rework-02.json` — [HOME] × 12
  - `.scratch/dispatch/v0.2-05-power-harness/raw-rework-02.json` — [REDACTED-EMAIL] × 3
  - `.scratch/dispatch/v0.2-05-power-harness/receipt-20260717-134408.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-05-power-harness/rework-02.stderr` — [HOME] × 1
  - `.scratch/dispatch/v0.2-06-ledger-evidence/raw-20260713-003354.json` — [HOME] × 8
  - `.scratch/dispatch/v0.2-06-ledger-evidence/receipt-20260713-003354.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-06-ledger-evidence/rework-01-raw.json` — [HOME] × 5
  - `.scratch/dispatch/v0.2-07-certified-run/raw-20260716-200904.json` — [HOME] × 6
  - `.scratch/dispatch/v0.2-07-certified-run/receipt-20260716-200904.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-07-certified-run/referee-repro-battery.py` — [HOME] × 1
  - `.scratch/dispatch/v0.2-07-certified-run/referee-repro-rework.py` — [HOME] × 1
  - `.scratch/dispatch/v0.2-07-certified-run/referee-repro.py` — [HOME] × 1
  - `.scratch/dispatch/v0.2-07-certified-run/rework-01-raw.json` — [HOME] × 7
  - `.scratch/dispatch/v0.2-07-certified-run/rework-02-raw.json` — [HOME] × 4
  - `.scratch/dispatch/v0.2-08-selection-verdict/raw-20260713-104920.json` — [HOME] × 9
  - `.scratch/dispatch/v0.2-08-selection-verdict/receipt-20260713-104920.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-09-aggregation-policy/raw-20260713-160854.json` — [HOME] × 8
  - `.scratch/dispatch/v0.2-09-aggregation-policy/receipt-20260713-160854.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-10a-dispatch-seam/raw-20260716-232934.json` — [HOME] × 13
  - `.scratch/dispatch/v0.2-10a-dispatch-seam/receipt-20260716-232934.json` — [HOME] × 2
  - `.scratch/dispatch/v0.2-12-robustness-nits/raw-20260731-004153.json` — [HOME] × 5
  - `.scratch/dispatch/v0.2-12-robustness-nits/receipt-20260731-004153.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-robustness-nits/resume-note-01.md` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-robustness-nits/resume-note-01.stderr` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-rp1-review/raw-20260812-232459.json` — [HOME] × 3
  - `.scratch/dispatch/v0.2-12-rp1-review/raw-resume-note-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-rp1-review/receipt-20260812-232459.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-rp1-review/receipt-resume-note-01.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-rp1-review/resume-note-01.md` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-rp1-review/resume-note-01.stderr` — [HOME] × 1
  - `.scratch/dispatch/v0.2-12-rp1-review/ticket.md` — [HOME] × 1
  - `.scratch/dispatch/v0.2-13-kernel-perf/raw-20260717-214417.json` — [HOME] × 9
  - `.scratch/dispatch/v0.2-13-kernel-perf/raw-rework-01.json` — [HOME] × 4
  - `.scratch/dispatch/v0.2-13-kernel-perf/receipt-20260717-214417.json` — [HOME] × 1
  - `.scratch/dispatch/v0.2-14-sharpe-lean/raw-20260718-021233.json` — [HOME] × 6
  - `.scratch/dispatch/v0.2-14-sharpe-lean/receipt-20260718-021233.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-00-blade-plumbing/panel-verdict-20260813.json` — [HOME] × 4
  - `.scratch/dispatch/v0.3-00-blade-plumbing/raw-20260813-153647.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-00-blade-plumbing/raw-20260813-153647.normalized.json` — [HOME] × 2
  - `.scratch/dispatch/v0.3-00-blade-plumbing/raw-rework01-20260813-162643.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-00-blade-plumbing/raw-rework01-20260813-162643.normalized.json` — [HOME] × 2
  - `.scratch/dispatch/v0.3-00-blade-plumbing/receipt-rework01-20260813.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-00b-blade-roster/raw-20260813-215738.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-00b-blade-roster/raw-20260813-215738.normalized.json` — [HOME] × 2
  - `.scratch/dispatch/v0.3-00b-blade-roster/receipt-20260813-215738.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-01-identity-pool/raw-20260813-170918.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-01-identity-pool/raw-20260813-170918.normalized.json` — [HOME] × 2
  - `.scratch/dispatch/v0.3-01-identity-pool/receipt-20260813-170918.json` — [HOME] × 1
  - `.scratch/dispatch/v0.3-02-magnitude-turnover/raw-20260813-170932.json` — [HOME] × 2
  - `.scratch/dispatch/v0.3-02-magnitude-turnover/raw-20260813-170932.normalized.json` — [HOME] × 4
  - `.scratch/dispatch/v0.3-02-magnitude-turnover/receipt-20260813-170932.json` — [HOME] × 2
  - `.scratch/dispatch/v0.3-03-single-year-luck/raw-20260813-170943.json` — [HOME] × 2
  - `.scratch/dispatch/v0.3-03-single-year-luck/raw-20260813-170943.normalized.json` — [HOME] × 4
  - `.scratch/dispatch/v0.3-03-single-year-luck/receipt-20260813-170943.json` — [HOME] × 2
  - `.scratch/dispatch/v02-design-audit/panel-c-report.md` — [HOME] × 1
  - `.scratch/dispatch/v02-design-audit/referee-verify.py` — [HOME] × 1
  - `.scratch/githooks/bypass-enum-raw.json` — [HOME] × 4
  - `.scratch/publish/bypass-enumeration.md` — [HOME] × 1
  - `.scratch/publish/bypass-enumeration.md` — [REDACTED-EMPLOYER] × 1
  - `.scratch/reflow/meta-review-ledger.md` — [HOME] × 1
  - `.scratch/reflow/meta-review-ledger.md` — [REDACTED-EMPLOYER] × 4
  - `.scratch/reflow/meta-reviews/case-study-review-prompt.md` — [REDACTED-EMPLOYER] × 2
  - `.scratch/reflow/meta-reviews/case-study-review-raw.json` — [REDACTED-EMPLOYER] × 9
  - `.scratch/reflow/meta-reviews/grok-review-2.json` — [REDACTED-EMPLOYER] × 1
  - `.scratch/reflow/meta-reviews/grok-review-3.json` — [HOME] × 2
  - `.scratch/reflow/meta-reviews/grok-review-4.json` — [REDACTED-EMPLOYER] × 6
  - `.scratch/reflow/meta-reviews/publish-gate-review-prompt.md` — -Users-[REDACTED-USER] × 1
  - `.scratch/reflow/meta-reviews/publish-gate-review-prompt.md` — [HOME] × 1
  - `.scratch/reflow/meta-reviews/publish-gate-review-prompt.md` — [REDACTED-EMAIL] × 1
  - `.scratch/reflow/meta-reviews/publish-gate-review-prompt.md` — [REDACTED-EMPLOYER] × 6
  - `.scratch/v0.2/power-sweep-results/appendix-rerun/rerun.log` — [HOME] × 1
  - `.scratch/v0.2/power-sweep-results/sweep.log` — [HOME] × 8
  - `docs/case-study-disclosure-boundary.md` — [REDACTED-EMPLOYER] × 3
  - `scripts/BRIDGE-SELFTEST.md` — [HOME] × 1
  - `scripts/publish-push.sh` — [REDACTED-EMAIL] × 1
- archive-zone framing-term hits (terms not reproduced here; policy above):
  - `.scratch/dispatch/readme-review/raw-r1.json` — 1 hits
  - `.scratch/next-session-kickoff.md` — 1 hits
  - `.scratch/reflow/meta-review-ledger.md` — 2 hits
  - `.scratch/reflow/meta-reviews/case-study-review-prompt.md` — 6 hits
  - `.scratch/reflow/meta-reviews/case-study-review-raw.json` — 8 hits
  - `.scratch/reflow/meta-reviews/grok-review-1.json` — 2 hits
  - `.scratch/reflow/meta-reviews/grok-review-2.json` — 6 hits
  - `.scratch/reflow/meta-reviews/grok-review-4.json` — 1 hits
  - `.scratch/reflow/meta-reviews/publish-gate-review-prompt.md` — 7 hits
  - `.scratch/reflow/meta-reviews/stations-review-prompt.md` — 1 hits
  - `docs/case-study-disclosure-boundary.md` — 3 hits
- binary files shipped (raw-byte scanned by the audit): `.scratch/v0.2/power-sweep-results/figure.png`, `examples/killer_demo/out/figure.png`
<!-- PUBLISH-MANIFEST:END -->
