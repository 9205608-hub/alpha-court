# 02 预注册闸 enforcement 模型设计（HITL grilling）

Type: grilling
Status: resolved
Triage: ready-for-human
Label: wayfinder:grilling

## Question

v0.2 核心。v0.1 审计判定：**ledger 有预注册的"座位"、没有"闸"**——字段能承载，语义强制
不存在，agent 可在合法 API 下自欺（scope 缩水 = 低估 multiplicity）。本票拍板闸的
enforcement 模型（RP-0：预注册必须留痕、可复算、防篡改；court 铁律反身于用它的 agent）。

审计给出的具体洞（每条要在设计里给出裁定）：

1. **declared ↔ series 一致性无强制**：`record(trial_id, series)` 只收裸序列，adapter
   的 metric/window/version 无路进账，**记录的序列从不对照 declared protocol**
   （`court/ledger.py:463-480` vs `adapters/qlib_cn.py:487-506`；审计 arch major）。
   闸要不要在 record() 时校验 series 确实按 declared.metric/window 产出？靠什么证据？
2. **source_ref 公共 API 不可达**：`register()` 恒写 `source_ref: None`、签名无此参数
   （`court/ledger.py:430-436, 455`；审计 arch major）——declared↔adapter run 的溯源链
   记不下来。闸的证据层需要它，本票定 source_ref 的语义与写入路径（实现归 06）。
3. **scope 缩水 = 多重检验欺诈**：N 从 scope 派生（`court/judge.py:261-274`），少注册/
   缩 scope 就低估 N。闸怎么定义并强制"scope ⊇ 该假设下全部 evaluated trials"？
4. **direction 后 post-hoc 翻号**：ledger 存了 declared.direction 但**不审计选择规则**
   （裸选 max|t| 允许翻号当 one-sided）。闸要不要锁 direction、禁 post-hoc 翻号？
   （与 03 选择–判决同构交叉，本票定"闸侧"约束，03 定"统计侧"解法。）
5. **落点与留痕**：闸是 court 内的运行时约束，还是 harness 的 Stop/pre-record hook？
   RP-0 要求留痕防篡改（`~/.claude` 非 git，痕迹形态要能复算）——闸的痕迹存哪、怎么防
   事后改。（接个人工作流体系 RP-0/RP-1；prereg-gate.sh 已有雏形可参考。）

## 产出

`docs/design/prereg-gate.md`（英文设计契约 + rulings），06/07 实现票必引。拍板后关票。

## Answer

**Resolved 2026-07-11.** grilling（Q1–Q5）+ 一次批量 grok 复审折回（`.scratch/dispatch/v02-02-grill/`，
判"可冻结、Q1–Q5 无 power 级锁错，但 3 处实现/口径钉死项"）。设计契约 = `docs/design/prereg-gate.md` v2。

- **Q1** (A) 由构造杜绝（**认证路径上** agent 不选 scope/不能环外评估）+ (B) 防篡改 seal 兜底——
  (A) 非物理禁止直调 court，(B) 让绕过"无有效 seal 可检测"才是牙。
- **Q2** court 保持纯（铁律二）；`harness/` = 认证路径；**认证挂在 run seal、不挂单条 verdict**；
  直调 court = 合法但 uncertified。
- **Q3** ledger 内内容哈希链（完整性）+ **seal 时一次外锚**（可插拔 backend，git 默认非硬依赖）；
  "tamper-**evident**" 非 tamper-proof（本地 git 可 amend/reset 抹锚）。
- **Q4** 不变量：declared 先于 series（物理行序+链）/ scope=完整集（harness 派生）/ adapter 背书
  `metric/window/universe/version`（**不背书 direction/se**）+ 背书==declared + 廉价结构校验 /
  declared 一经 series 不可变。诚实边界：信任 adapter 背书、**不重算 ground truth**。
- **Q5** trial 级增量（每 trial 先锁+无隐藏，非 N 事先钉死）；**一 Run = 一 multiplicity 家族 =
  一 judge = 一 seal**。归组细拆 = 固有局限（锁定可见但不自动阻止，RP-1 兜底）。
- **grok 钉死折入 v2**：tamper-proof→evident；外锚一次于 seal 非 per-trial git；哈希覆盖 content
  不覆盖真钟 + `sort_keys`+float 固定编码（已核 `_append_event` 确无 sort_keys）；证书 = ledger
  `seal` 事件权威（manifest 副本 / git 可选 / commit message 禁；不动 VerdictRecord）；一 run 一
  family；09 聚合 config 必在首 verdict 前上链（02/03/09 接缝）。

**实现归 06（证据层）→ 07（闸本体）→ 09（聚合上链）**，grok 明确 **06 先于 07**（07 无 06 的
attestation/source_ref 串不起 E2E）。**关票。**
