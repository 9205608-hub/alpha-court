# 05 power 标定 harness 实现

Type: task
Status: resolved (hero + size 2026-07-19; β_t appendix re-run clean 2026-07-20 — quarantine lifted, ticket closed)
Triage: ready-for-human
Blocked by: 01, 03, 08
Label: wayfinder:task

## Question

按 01 拍板的协议实现 power 标定——**v0.2 最有价值的单件交付**：把"0/100 拒噪声"升级成
"这是法庭在已知信号上的真实判别力曲线"。

- **纵切（tracer-bullet）**：构造真信号面板（01 定形态）→ 走**同一** killer-demo 管线与
  `judge` battery → 出 **TPR@α vs 信号强度** 曲线 + **size 表并列**（构造噪声的假放行率）。
- 复用 killer-demo 的噪声壳与 adapter 管线（同窗口/宇宙/种子树），只叠一层已知信号，
  保证 power 与 size 可比。
- 预注册：强度网格/种子/判决线先于首跑钉死（01 的设计文档即预注册书）；结果**难看也
  如实入报告**。
- 落点：`examples/`（或 `harness/`，按 01/整体架构定）；入口一条命令可复跑。
- 文件边界与派单：TDD 红绿；经 M0 桥派 grok，referee 独立复核 + 亲跑 power 电池。

## 验收标准

- 一条命令跑出 power 曲线 + size 表两份产物；size≈校准位、power 随强度单调上升（若不，
  如实报并入 backlog）。
- 报告首屏写清"构造信号 ≠ 真实 alpha"边界（01 §5）。
- 确定性同 killer-demo（同机+锁依赖逐位）。

## 审计修订（2026-07-12，v0.2 设计层审计 D1/D3/D13/major-8 — 冲突处以本节为准）

- **Blocked by 改为 01, 03, 08**（role/VerdictRecord schema 落地后再烧机时，否则 power
  产物立刻落后一字段——正是 08 要清的那种债）。
- **第一步 = 执行并冻结 β→ICIR 标定**（01 v3 §4.2：K=64 种子根 `320260711`、β 候选网格
  0.02..0.30、PCHIP 插值、φ=100 壳中位数），β\* 表入 `run_config` 后才准开 power 跑。
  ——v2 说"标定已冻结"名不符实：冻结的是程序，β\* 表尚不存在。
- **认证路径裁定**：power 以 **uncertified 直调 court** 运行（标定实验非自欺面），
  每份 power 产物首屏披露；聚合复用 08 的 discriminating-only helper，禁止第二套聚合
  代码路径。
- **验收标准对齐 01 v3 §10 全清单**（v2 票面只覆盖一半）：hero power 曲线 + **B 曲线 +
  分闸 TPR 默认面板** + directional-size 面板（β=0 同 battery 重跑，标注不可与
  killer-demo two-sided size 直比）+ **submission-power 表** + **β_t 附录（matched-ICIR
  主对照臂 + 同名义 β 展示臂 + random-block 敏感性）** + 首屏边界 + 确定性。
- 排期如实写：R₀=40 串行 ~1.5–2 天；**cap R=120 最坏 ≈4.2 天**。
- 实验口径（01 v3）：选择 = **argmax t**（无 flip 补丁）、全部 100 trial 声明
  `greater`、陪审统计量 = 定向 t、gate 表单侧。

## Answer (2026-07-17 — code accepted at referee round-2; real-data acceptance pending)

Dispatched to grok (`019f6e9a`), delivered `examples/power_calibration/` (12 modules)
+ `tests/test_power_calibration.py`. Merged at `efc0d9a9`.

**Referee round-1 (adversarial panel, 5 REFUTE lenses; every finding
commander-reproduced before ruling):**
- **Accepted core (large):** calibration math had ZERO findings (ICIR=mean/std·√252,
  PCHIP β* solve, Wilson CI, 64-seed separate root, β*=mean, no realized-ICIR
  write-back — all REFUTATION FAILED). Verdict vertical slice contract all green
  (aggregation_policy reuse / no second path, won=argmax **signed** t, greater
  battery via court.judge, B frozen at first R₀, noise-cache cross-seed isolation).
  First-screen honesty + uncertified disclosure in place.
- **4 majors → one worker rework (rework-01):**
  - **M2** β=0 directional-size computed `P(pass|won)` (injected wins ~1/N → NaN at
    N=100/R₀=40); book §6 asks `P(pass)≈α`. **worker-primary + contract-secondary.**
  - **M3** β_t appendix never ran the battery (ICIR-only recorder), yet report claimed
    "Answers: TPR drop". **worker-fault** (honest docstring mitigated).
  - **M1** `report_has_size_beside_power` non-enforcing (header substring only).
    **worker-fault**; shipped `__main__` FROZEN_GRID has 0.0 so the real artifact was
    protected.
  - **M4** pyproject packages line breached AC-5; referee **proved it unnecessary** for
    the editable install (lenient MAPPING finder resolves via top-level `examples`),
    but it mirrors the `examples.killer_demo` packaging precedent. **contract-fault
    (AC-5 too tight) → worker WINS the deviation.**
  - minors: submission drops pool_max silently; underpowered hardcoded 20; transform
    named "van der Waerden" but is Hazen `(r−0.5)/m` (comment mislabeled "Blom");
    "unit-variance" only asymptotic.

**Commander-side contract amendments (before rework, `638f515c` — contract-freeze):**
book §6 rules the size estimator = **accused champion's unconditional per-gate pass
rate over all R₀ seeds** (distinct from the hero curve's `P(unanimous|won)`); book §4.2
ratifies `POWER_SEED_ROOT=420260711` (v3 pinned only the calibration root); book §4.1
names the transform Hazen/rankit + qualifies unit-variance as approximate; ticket
iron-law-#8/AC-5 permit the one pyproject line. Logged as **CR-11**
(`ticket-self-contradiction`, 5th; commander self-records the pre-dispatch lint
coverage gap — it missed M2/M3's measurability-at-frozen-scale; anti-recurrence =
lint gains that pass + FIX-1 test asserts β=0 size numbers finite).

**Referee round-2 (rework-01 `7a81ca75`; all 5 fixes independently verified):**
- FIX1: β=0 size now the **unconditional champion** estimand — empirically
  `n_champion_samples==n_seeds`, champion numbers non-NaN, champion unanimous ≈0 on
  pure noise (size ≈α, mirrors killer 0/100); hero A stays `P(unanimous|won)` (dual
  estimands). FIX2: `run_beta_t_power` runs the greater battery via court.judge +
  trial_survives (no second path), emits finite unanimous/PBO drops (constant−matched).
  FIX3: guard asserts the size DATA row; underpowered uses `cfg.n_won_target`. FIX4:
  submission excludes pool_max explicitly. FIX5: Hazen naming.
- Genuine red-first evidence (3 named tests exit 1 before green). Reduced **26+1**
  (no qlib) and full suite **498+2** both **independently re-run** by the referee.
  File ownership clean. deviations: none. **Zero round-2 worker-fault.**

**Attribution ledger (this ticket):**
- worker-fault: M3, M1, "Blom" comment mislabel (all fixed in rework-01).
- contract-fault (commander, CR-11): M2 estimator half, seed-root under-spec + ticket
  false "book's separate roots", AC-5 over-tight.
- worker WINS: pyproject packaging line, `POWER_SEED_ROOT` choice (both ratified).
- referee-fault: none adjudicated; the pre-dispatch lint coverage gap is logged under
  CR-11 as commander/contract accountability (the panel caught M2/M3, system held).

**Remaining = real-data acceptance (commander runs, NOT the worker):**
1. `.venv/bin/python -m examples.power_calibration.calibrate --out examples/power_calibration/out` (minutes) — freezes the β* table.
2. `.venv/bin/python -m examples.power_calibration --out examples/power_calibration/out --calibration examples/power_calibration/out/calibration.json` (~1.5–2 days serial R₀=40; worst ~4.2 days at cap R=120).
Prereqs: `.[qlib]` + csi300 pack under ~/.qlib. Open question to settle first: β_t battery R
(worker default = cfg.r0; reduced = min(r0,2)) — pick R₀ or a dedicated appendix R.
Ticket 05 flips to `resolved` once the real power curve + size table land (separate commit).

## Answer addendum (2026-07-19 — real-data acceptance: hero ACCEPTED, appendix → rework-02)

Full sweep ran 2026-07-18 10:16 → 2026-07-19 17:15 (~31h, 880 arms, head `c987a5b9`,
out `~/.alpha-court/power-sweep-out/`; report/run_config/appendix-json/log committed at
`.scratch/v0.2/power-sweep-results/`; per-seed ledgers stay out of repo by prior ruling).

**Hero + size: ACCEPTED — both pre-registered criteria met.**
- β=0 (40 seeds): zero natural wins, zero submissions; size-panel champion-unanimous
  0.000 Wilson [0, 0.088]; per-gate size at/below nominal (dsr 0.0, fdr_by 0.0,
  pool_max 0.05, pbo_cscv 0.05).
- A / B / submission all monotone across the 14-strength grid; 80% submission power
  at ICIR≈4.0 (β*≈0.0185); saturation from ICIR 5.0.

**β_t appendix + figure: QUARANTINED — 3 defects, each commander-reproduced from
`report.md` + source before ruling; dispatched as rework-02 (resume `019f6e9a`):**
1. `figure.py` errorbar crash on the β=0 NaN hero row → no figure.png/svg
   (sweep EXIT=1 *after* all data landed; data unharmed).
2. t3.0 appendix row mis-calibrated: 3.0 absent from the frozen β* table → silent
   fallback β=target/20=0.15 → realized ICIR 39.0 vs target 3 → row uninformative.
3. `solve_matched_beta` search grid floor 0.05 > required ≈0.037 → matched arms
   clamped at the boundary (realized 5.63/5.73 vs constant 3.79) → reported
   "drops" (incl. headline −0.200) are calibration artifacts, NOT interpretable.
Appendix conclusions are unusable until rework-02 lands and the commander re-runs
the appendix arms (commander-side compute, same boundary as the main sweep).

## Answer addendum (2026-07-19 late — rework-02 ACCEPTED; appendix re-run armed)

Worker delivered `a51f66e4` (resume, session `019f6e9a`). Referee re-ran everything
independently on the canonical venv (`.venv-regen`):
- **Red-first**: 4/5 named tests genuinely red at `fcbfbedd` (ImportError bites).
  FIX-C's own red was vacuous on the real matplotlib — the referee's real-input
  probe (report.md integer counts → `wilson_interval` → `render_figures`)
  reproduced the true crash pre-fix: **negative yerr −2.2e-17 at strength 1.5**
  (p̂=0 Wilson lo float tail), NOT the NaN row the ticket asserted. Post-fix the
  same probe renders clean (figure.png 153KB). Ticket's stated mechanism wrong →
  **referee-fault** (lessons-inbox 2026-07-19, vocab-pending); the worker's
  deviation report adjudicated **TRUE**.
- **Post-fix**: ruff clean; 32 power tests green; **full suite 532 green** (527
  baseline + 5 new). Worker's "517 passed" = its own /tmp venv missing extras —
  environment delta, not failures.
- **stats_util.py ownership deviation: worker WINS** (keyword-only `clamp=True`
  default preserves main-path behavior; verified by re-freeze: all 14 existing β*
  keys bit-identical, single new key 3.0 → β*=0.014609, monotone between 2.9/3.2).
- **Protocol breach → CR-13**: the worker's dispatch worktree had been deleted;
  raw `grok --resume` has no isolation guard, so it worked and committed directly
  on the production branch. Diff audited = exactly the 5 owned files; commit
  retained as the accepted delivery. `bridge-isolation-failure` recurrence #2 ⇒
  promoted; resume-preflight [DESIGNED] (CR-13 carries the re-runnable check).

**Attribution (rework-02)**: FIX-A worker-primary + contract-secondary; FIX-B
worker; FIX-C worker-primary + contract-secondary (all three fixed & verified);
FIX-C misdiagnosis referee-fault; isolation breach tooling + referee-fault
(commander preflight) + worker-secondary (adopted a foreign checkout).

**Attribution amendment (2026-07-20, on the v0.2 role-reversal review's
objection, adopted)**: FIX-B re-ruled **worker-primary + contract-secondary** —
the commander re-centered the calibration β grid to 0.002..0.030 before the
sweep, which made the matched-search 0.05 floor certainly-clamping at
β*≈0.0185, and did not re-verify `solve_matched_beta` on the new scale before
burning 31h; the silent-clamp implementation debt stays with the worker. The
review's other partial objections (FIX-A secondary weight; CR-13
worker-secondary tone) are adjudicated in `meta-review-ledger.md` (v0.2 section)
and CR-13's amended wording.

Official hero figure regenerated through the accepted `figure.py` from report.md
integer counts (`.scratch/v0.2/power-sweep-results/make_hero_figure.py`, full
provenance in its docstring): `figure.png` / `figure.svg` beside `report.md`.
β_t appendix re-run (R=40, targets 4.0/3.0, relative bracket, re-frozen
calibration) launched detached via `.scratch/v0.2/appendix-rerun/runner.py`;
quarantine lifts when honest drops land.

## Answer final (2026-07-20 — appendix quarantine LIFTED; ticket fully closed)

Re-run completed clean (320 arms, 21.5h, EXIT=0, head `8a1aff08`). All
acceptance checks pass: fail-closed validation in the loop; matched β strictly
interior (0.0338/0.0340 ref-4.0, 0.0271/0.0261 ref-3.0); matched realized ICIR
within 0.4–3.7% of constant; t3.0 informative again (const unanimous 0.405 —
cross-consistent with hero A at 2.9/3.2). **Result: |unanimous/PBO drop| ≤ 0.05
at both targets (≤2 seeds at R=40, binomial noise) — no material power loss
under matched episodic β_t; the PBO-optimism concern does not materialize.**
Artifacts + full health record: `.scratch/v0.2/power-sweep-results/appendix-rerun/`.
Status: resolved (hero 2026-07-19; appendix 2026-07-20). Remaining for owner:
merge `claude/continuing-work-ca88e8` → main.
