# v0.2 harness/ 治理层 — wayfinder map

Label: wayfinder:map
Created: 2026-07-11

## Destination

把 v0.1 的统计引擎从"可信的计算器"焊成"**不会被绕过的法庭**"：一层 `harness/`
治理，让一个挖因子 agent（生成端仍 stub）**无法在合法 API 下自欺**。v0.2 走完 =
两件事成立——① **法庭上过真案**：power 被标定（注入构造真信号，报 size 与 power 两张
表；不再是"0/100 与永远驳回同形"）；② **预注册闸落地**：declared protocol 先于序列
锁定、留痕防篡改、scope 不得缩水、选择规则 ≡ 统计原假设——court 的铁律反身于用它的人。

## Backlog 来源（本 map 的证据基座）

- **v0.1 里程碑技术审计**（2026-07-11）：grok 整体审计 + Claude 独立三镜头面板，判
  「稳但有保留 · B / solid-with-caveats」。原文档案 `.scratch/dispatch/v01-audit/`；
  三条真 bug 已修（commit `9cd4a5a`：DSR clamp / p_from_t 尾 / DSR 值落盘），架构与
  产品债留给本 map。全程账见 `TIMELINE.md` 2026-07-11「里程碑技术审计」条。
- **宪章 v0.2 愿景**：`harness/` = 预注册闸 hooks + referee 对抗复核治理 + dispatch
  泛化到任意 CLI（v0.1 map「Out of scope」）。
- **RP-0/RP-1 接续**（个人工作流体系 session 拍板）：预注册必须留痕、可复算、防篡改
  （RP-0）；外部裁决是心跳非典礼（RP-1）。v0.2 的预注册闸与 referee 治理是这两条原则
  在 court 产品侧的落地——court 铁律反身于指挥官/agent。

## Notes

- **硬约束（宪章铁律，延续 v0.1，每张票受约束）**：三不做（不回测/不生成 idea/不搬前
  雇主）；`court/` 零市场特异 import；禁赢学（power 难看也如实报，size≠power 必分表）；
  统计实现带文献引用。
- **携带执行**：实现类 task 票经 M0 桥派 grok，指挥 session 当 referee 独立复核验收；
  设计/决策票（grilling）是 HITL，留给用户在场的 session。
- **切片纪律（tracer-bullet）**：实现票是**纵切**（端到端交付一个可观察能力），不是横
  切的"层"。设计票先行、把委托决策走成判决树，再切可派单的实现票（沿用 v0.1 节奏）。
- **语言**：票面中文为主；代码、docstring、对外文档英文。

## Decisions so far

<!-- one line per resolved ticket: gist + link -->

- [01 power 标定协议](issues/01-power-calibration-protocol.md) — grilling 七支拍板 + 批量 grok 复审 + **2026-07-12 五路审计修订（v3）**：预注册书 `docs/design/power-calibration.md` **v3**、强度网格冻结（A 密 2.0–5.0 = 闸开启带）。信号构造 (b)（真收益 + 掺未来收益 oracle）；**选择 = argmax t、全员 declare greater、陪审统计量 = 定向 t、gate 表单侧**（审计 D1）；横轴 = 实现年化 ICIR；P(win) 带实现噪声重算（1.5→~0.35 非 ~1%，审计 D3）；1 真+99 噪声 data-side 镜像（battery 形态随方向变，如实标注）；共享噪声池 + R₀=40 自适应补种（B 用前 40 固定种子）；分闸 TPR + β_t 附录（**matched-ICIR 主对照臂**，审计 D2）；标定种子根 320260711。调度：**05 Blocked by 01+03+08**（审计 D13），uncertified 直调 court 首屏披露。
- [03 选择–判决同构](issues/03-selection-verdict-isomorphism.md) — grilling Q1–Q3 + grok Q2 亲证 + **审计修订（v2）**：设计裁定 `docs/design/selection-verdict-isomorphism.md` **v2**。把 spec F2 的方向感知推广到 DSR/PBO：**DSR two-sided 弃权**（论证经审计 D4 重写 = 一真地雷 0.24 SR-std + 引用铁律；v1 三地雷中两条已数值证伪退休在案）、**PBO 换 |ICIR|**；directional 下 DSR 启用+PBO 有符号；**`less` = 负号 metric/翻转序列、混向 scope raise**（审计 D5）；`role` = VerdictRecord 可选字段、旧账本兼容（审计 D16）。全票制只计判别关；killer-demo 头版 0/100 不变。实现归 08。
- [02 预注册闸模型](issues/02-prereg-gate-model.md) — grilling Q1–Q5 + 批量 grok 复审 + **审计修订（v3）**：设计契约 `docs/design/prereg-gate.md` **v3**。court 侧改动诚实列三处（source_ref+attestation / 哈希链+规范序列化 / declaration+seal 事件类型，全归 06）；**run 级 `run_config` declaration 首链事件**锁 universe/versions/adapter 配置（审计 D7）；锚 = seal 时一次、证明 chain head ≤ 锚时戳（审计 D6 废除"锚早于 series"矛盾条款）；seal 必须末事件（审计 D8）；§6 六条诚实边界（+截尾窗口/环外预筛/进程内伪造/兄弟 run，审计 D8–D11）。一 Run=一 family=一 judge=一 seal。实现 06→07→09。
- [10 dispatch 泛化 + referee 治理](issues/10-dispatch-gen-referee-gov.md) — grilling Q1–Q2 + **审计修订**：设计裁定 `docs/agents/dispatch-and-governance.md`。两接缝隔离 + 最小 worker 契约（**+commander 侧 receipt jsonschema 验证、+(d) 全无头**，审计）+ 注册表 YAGNI；tripwire `.scratch/dispatch` 盲区在案披露；三 RP-1 触发点 + trigger-1 补档注记。实现票 = **10a**。

## Not yet specified

（2026-07-12：四张设计问全部 resolved 并经五路审计修订，原清单归档至各契约；本节暂空。）

## Out of scope（v0.2 明确不做）

- **idea 生成端**——三不做，永久 stub（harness 只提供"如果有生成端，法庭如何治理它"的
  接口，不实现生成）。
- **gates/ 便宜刀刀片库**（恒等式退化、池内冗余、量级 vs 换手、单年运气热力图）→ v0.3。
- **null 博物馆完整形态** → v0.3。
- **美股/crypto adapters** → qlib-cn 先行。
- **20 种子 sweep 全跑 / 真实市场因子上案**——power 标定用**构造**信号先证逻辑（05），
  真实因子库是 power 标定通过后才挣得的下一步。
- **任何回测引擎 / idea 生成器功能**——三不做，永久出界。

## Ticket 索引

| # | 类型 | 一句话 | Blocked by |
|---|---|---|---|
| 01 | grilling | power 标定协议（构造信号/强度网格/TPR@α/size-vs-power 报告） | — |
| 02 | grilling | 预注册闸 enforcement 模型（锁定/留痕/scope/direction；落点） | — |
| 03 | grilling | 选择–判决同构解法（裸选 vs DSR 单侧/PBO 有符号） | — |
| 04 | task | 解耦守卫升级：test_smoke 黑名单 → 白名单 | — |
| 05 | task | power 标定 harness（注入构造信号 → battery → power 曲线） | 01, 03, 08 |
| 06 | task | ledger provenance：source_ref 可达 + declared↔series 一致性 | 02 |
| 07 | task | 预注册闸 enforcement（scope⊇evaluated、direction 锁、留痕 fail-closed） | 02, 06 |
| 08 | task | 选择–判决对齐实现 | 03 |
| 09 | task | 聚合口径显式化 + 落盘（全票制从 demo 移进 harness config） | 02, 06 |
| 10 | grilling | dispatch 泛化到任意 CLI + referee 治理（RP-1 心跳） | — |
| 11 | task | v0.2 E2E 验收 | 01–10 |
| 12 | task | 内核 robustness nits 批处理（审计 minors，低优先） | — |
| 13 | task | adapter IC kernel 慢路径（masked-rank）向量化（15.2×，power sweep 多天→~3h；oracle 等价 rtol=1e-12 逐位冻结）✅ | — |
| 14 | task | court.sharpe.sharpe_ratio 去掉白算的 skew/kurtosis（PBO metric 45×，battery 31min→~40s；φ 逐位冻结）✅ | — |

**🏁 v0.2 设计层收官（2026-07-12 审计后重宣）**：四张设计 grilling 于 2026-07-11
resolved；**2026-07-12 五路盲审里程碑审计（`.scratch/dispatch/v02-design-audit/`）
判"修后施工"、抓出 5 BLOCKER**——v2 版"收官、随时派"宣告**撤回**。审计修订已折入
（01→v3、02→v3、03→v2、spec/killer-demo/票面同步），**收官以本行重宣为准**。

**开图前沿（open + unblocked + unclaimed，按号）**：04 / 12。11 等全部。
**✅ 14 lean sharpe 收货（2026-07-18，零 worker-fault 首交即对）**：`court.sharpe.sharpe_ratio`
去掉白算的 skew/kurtosis（直接 mean/std）。pilot+门分解诊断出 05 sweep 第二瓶颈——`sharpe_ratio`
经 `series_moments` 每次算 scipy skew+kurtosis 却只返 mu/sigma，PBO 调它 ~257万次/battery → 928s/PBO →
31min/battery → ~12 天。referee 亲验：sharpe_ratio==old==series_moments.sr_hat **逐位相同（2000 series
0.0 diff）** + raises 保真 + **PBO φ/n_lambda_neg 逐位相同**（n_splits 8/10），n_splits=12 via judge
70s→2.08s。series_moments/DSR/PSR 不动。合并；全量 **527 passed / 85s（比修复前 712s 快 8×）**。
**14 非 contract-fault**——派前我在真尺度 profile 门分解 + 验 φ 逐位，票面一次到位（CR-11/12 anti-recurrence 生效）。
**🎯 05 sweep 现 ~9-12h 过夜可跑**（13 kernel 15× + 14 PBO 45×，两瓶颈全消；β* 表冻结验证）——只差最后这一跑。
**✅ 13 kernel 性能收货（2026-07-17，1 轮 rework）**：`_shared_kernel` IC 慢路径向量化
（`_masked_avg_ranks` stable-sort + `_masked_row_pearson`）。referee 双轮——round-1
worker 交付**快路径**向量化（正确但我 referee 亲验发现对真 csi300 零帮助：**0/480 快路径**，
PIT churn 让每日期走慢路径），round-1 = **我的契约 mis-scope（CR-12）**；我 prototype 慢路径
7.6× 逐位后 rework-01 重定向，worker 交付统一 masked-rank 路径 + dense-score label-rank 缓存。
**指挥官真 csi300 独立复现：31.58s→2.08s = 15.2×、max diff 0.0（逐位含 tie-heavy）**；带 qlib
24 adapter 测试全绿（oracle rtol=1e-12 + fail-closed + golden fingerprint + churn/dense perf 门）、
全量 522。合并 `b62f00ba`。**worker 两轮全胜诉**（零 worker-fault，CR-11+CR-12 皆我契约错，同源
= pre-dispatch 未在真尺度验关键量）。sweep 现 ~3h，且加速所有未来真数据跑。
**✅ 05 代码收货（2026-07-17，1 轮 rework）**：power harness `examples/power_calibration/`
（12 模块 + 583 行测试）合并 `efc0d9a9`。referee 双轮——round-1 抓 4 major（M2 β=0 size 算
成 P(pass|won) 在 R₀ 下 NaN、M3 β_t 从不跑 battery、M1 纸老虎守卫、M4 pyproject 越界），
**全部指挥官亲手复现**；契约补丁先冻结（book §6 size 估计量 = 冠军无条件率、§4.2 批准
POWER_SEED_ROOT、§4.1 Hazen 正名、AC-5 ratify pyproject = CR-11 contract-fault）；round-2
五修独立复现全过（FIX1 冠军无条件 size 实测非 NaN ≈α、FIX2 β_t 真跑 battery 出 finite
drop），reduced 26+1、全量 498+2 独立复跑，零 round-2 worker-fault。**归因**：worker-fault
= M3/M1/"Blom"注释；contract-fault(CR-11) = M2 半/seed-root/AC-5；**工人胜诉** pyproject +
seed-root 两 deviation。**剩真数据验收**（指挥官跑：calibrate 冻 β* + sweep 1.5–4 天机时），
05 出真 power 曲线+size 表后翻 resolved。详见 issue Answer + CR-11。
**✅ 10a 已收货（2026-07-17，零工人返工）**：dispatch 两接缝隔离 + stdlib receipt 校验；
fidelity 面板逐行验行为保持 + 校验器无漏。AC-4 miss = CR-09 #4（07/09 让 harness/__init__
eagerly import court.judge、court_import_gate staged 测在系统 python3 下 cwd 遮蔽——referee
`-P` 修 base + 规则加固）。工人诚实 partial + deviation 亲证属实。
**🏁 预注册闸链全落地（2026-07-16）**：02→06→07→09 + 03→08 全 resolved 并合并。**07
（认证 Run/seal/anchor/verify — v0.2 立命之票）2 轮 rework 收官**：初交两 major fail-open
（reopen-brick / anchor-bypass）均 worker-wins，rework-01/02 修 + prereg-gate 升 v4，探针
又逮 battery-half-fix（第三个 contract-fault）也修；460+1 绿。归因：worker 三轮零 major-fault
（两胜诉+一判例），commander CR-10（3 contract-fault + 1 referee-fault）。详见
`issues/07-prereg-gate-enforcement.md` Answer。
**✅ 09 已收货（2026-07-13，零返工）**：单轮交付，双面板全接受（保真九组 ✓ 零静默偏离；
探针 49/49 零 fail-open、10 case 与旧实现 oracle 级等价）；聚合单一代码路径落成
（identity 级）、demo 输出字节级冻结兑现；唯一 deviation = CR-09 复发 #3（指挥侧 regen
破 legacy fixture，已修 + 规则加固）。⚠×2 已写入 07 票面。
**✅ 08 已收货（2026-07-13，零返工）**：单轮交付，双面板全接受（保真零 findings；探针
PBO φ 逐位相等 + DSR 构造等价精确成立），裁判全量 244+1 绿；唯一 ⚠（replay 侧 role
值域）+ 4 nit 归 12 号票批处理。真数据重生成 = referee 侧验收步骤，单独 commit。
详见 `issues/08-selection-verdict-alignment.md` Answer。09 按串行序（06→08→09）可派。
**✅ 06 已收货（2026-07-13）**：两轮交付（初交 + rework-01），referee 双面板（契约保真 +
对抗探针 30+ 零 fail-open）+ 独立复跑 227+1 绿后合并；归因与 seam 记录见
`issues/06-ledger-provenance.md` Answer。07 注意 Answer 里留的 seam（记录导出 +
canonical 函数认领）。

**文件冲突矩阵与串行裁定（审计 D16）**：06/08/12 同挤 `court/ledger.py`、08/12 同挤
`court/judge.py`、08/09 同挤 killer-demo 编排层——**串行 06 → 08 → 09 过
ledger/judge/demo，12 押后批处理**；04/10a 与上述无冲突可并行。demo 产物重生成
**一次**（08 落地后、09 只改编排引用不再重生成）。

**解锁的实现票**：
- **06** ledger 证据层（source_ref + attestation + **哈希链/规范序列化 + declaration/seal
  事件类型**——审计 D14：06 是 court/ 全部改动的唯一属主）→ **07** 预注册闸本体（等 06）；
- **08** 选择–判决对齐（role=VerdictRecord 可选字段 + less 负号分支 + 混向 raise +
  killer-demo 真数据重生成）；
- **09** 聚合 declaration 上链（等 02+06）；**04** test_smoke 白名单；**12** 内核 nits
  （注意：存储行序列化不动，哈希路径才 sort_keys——见 02 §7）；**10a** dispatch 两接缝
  + receipt 验证（票见 `issues/10a-dispatch-seam-refactor.md`）。
- **05** power 大跑（等 08；第一步 = 执行并冻结 β→ICIR 标定表；uncertified 直调 court，
  首屏披露；最坏 R=120 ≈ 4.2 天串行）。

**不在 v0.2 的 v0.1 收尾遗留**（另走"v0.1 诚实抛光"，非本 map）：README sweep 措辞软化为
"已实现未执行"、五道关表点明"本例实际一道关"、20 种子 sweep 从未跑 + 满 100 因子真数据
E2E 无自动化测试的覆盖补强——这些是 v0.1 门面/测试债，power 标定（01/05）不替代它们。

---

**MAP CLOSED 2026-07-31** — 11 号验收通过（acceptance-report.md），v0.2 全票 resolved（04=裁定关票；12=代码落地、RP-1 为快照发布前提）。
