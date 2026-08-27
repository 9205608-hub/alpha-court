# 07 预注册闸 enforcement 实现（scope⊇evaluated、direction 锁、留痕 fail-closed）

Type: task
Status: resolved
Triage: done
Blocked by: 02, 06
Label: wayfinder:task

## Question

按 02 拍板实现**闸本体**——court 铁律反身于用它的 agent（RP-0：留痕、可复算、防篡改）。

- **scope 完整性**：judge 的 scope 不得小于"该假设下全部已 evaluated 的 trial"（防 scope
   缩水低估 N，`court/judge.py:261-274` 是 N 派生点）。按 02 定义强制。
- **direction 锁**：declared.direction 锁定后禁 post-hoc 翻号当 one-sided p（与 03 的
   统计侧解法对齐、不打架）。
- **留痕**：闸的判定与依据留可复算、防篡改的痕迹（02 定形态；参考个人工作流体系
   `scripts/prereg-gate.sh` 雏形）。
- **fail-closed**：违反即硬错误，无静默通过；错误语义延续 court §6 全线 fail-closed。
- 落点：`harness/`（按 02 定是 court 运行时约束还是 harness hook）。
- TDD 红绿：先写"scope 缩水绕过""post-hoc 翻号绕过""痕迹可被事后篡改而不被发现"的
   失败测试，再实现闸堵住。

## 验收标准

- referee 独立复跑：三条绕过路径（缩 scope / 翻号 / 篡改痕迹）全部被闸 fail-closed 拦住。
- 合法路径（诚实注册全 evaluated、锁定 direction、原样留痕）畅通。
- 与 06 的证据层串通；ruff 净、零回归。

## 审计修订（2026-07-12，v0.2 设计层审计 D6/D7/D8 — 冲突处以本节为准）

- 锚语义按 02 v3 §4.3（audit D6）：锚证明"sealed chain head 不晚于锚自身时间戳"；
  **"锚早于 series"检查已废除**（v2 该条在锚定于 seal 的设计下恒假）。
- conformance 检查两分家（02 v3 Q4）：`metric`/`window` vs `DeclaredProtocol`；
  `universe`/`*_version`/adapter config vs **`run_config` declaration 事件**（Run 创建
  时的首链事件，07 负责写入与核对）。
- fail-closed 清单以 02 v3 §5 为准（新增：无 run_config → raise；seal 必须末事件；
  二次 seal / seal 后调用 / 野 verdict / 无聚合策略各条）。
- §6 新增四条诚实边界（截尾窗口/环外预筛/进程内伪造/兄弟 run）**原样进 07 的文档与
  测试**——含"honesty test"：seal 前截尾 replay 通过（断言其通过，把边界钉在案上）；
  **禁止**进程内 nonce/HMAC 安全戏剧。

## 09 收货交接注记（2026-07-13，探针面板 ⚠×2 — 07 验收标准必须吸收）

- **⚠-1 链序核对（硬要求）**：court 层 opaque——verdict 已存在的账本上直接
  `ledger.append_declaration(policy_payload)` 能塞进"后补 policy"，且
  `read_declared_policy` 视其合法（探针实证）。**读面缺口**：`declarations()` 与
  `verdicts()` 是分离读面，`DeclarationRecord` 只带时间戳、不暴露链上交错顺序。
  ∴ 07 的 seal 交叉核对**必须从事件流/文件层校验"policy declaration 事件序位 <
  首个 verdict 事件序位"（链序，非时间戳、非存在性）**——只查"policy 存在且 payload
  相等"会被 2d 旁路穿过认证。写进 07 验收 + 红测。
- **⚠-2 payload 原文比较（防夹带键）**：`from_payload` 接受并静默丢弃未知键——
  带夹带键的链上 payload 解析后与规范对象相等、re-serialize 也相等，对象级比较完全
  隐身。∴ 07 的 seal 核对钉死为**在账 payload 原始 dict 级相等**（或后续把
  from_payload 改为拒未知键）。

## 收货裁定（2026-07-16，referee 终裁 — 一轮 rework，全记指挥官账）

**工人交付接受（两条 major 均 worker-wins、零工人返工责任）**：dispatch `v0.2-07`
（`d198d10`，6 文件 +1978）逐字实现冻结的 v3 契约、36 新测试、全量 447+1 绿、双面板确认
链上自欺路径（scope→N/翻号/藏 trial/夹带）全关死、§6 边界行为与设计一致。

**但双面板 + referee 独立复现抓出 v3 契约自身的两个 MAJOR fail-open（contract-fault）**：
- **F-1 reopen 复活砖化**：judge 半程失败砖化后 `open()` 重挂允许 seal、重建 verdict_ids
  恰盖孤儿、verify 放行——蓄意缩 battery 洗成 crash-recovery。根因：battery 不上链 +
  M-1×M-4 两钉死项交互。
- **Finding A 锚被删 manifest 静默停用**：verify inv 9 从攻击者可删的 run_manifest.json
  取 anchor_ref 决定是否问锚——全链伪造 + rm manifest + 喂真锚 → verify PASS。v0.2 立命
  之票的最后防伪线可被静默关闭。
- Finding B（minor）：verify 接受双 policy 账本（与 09 read_declared_policy 不一致）。

**裁定 = 修好再合（诚实条款"绝不挂半成品"）**。契约 → prereg-gate v4 §4.2（judgment
上链事件 + 锚 query-by-recomputed-head fail-closed）；**CR-10 立案**（contract-fault，
`ticket-self-contradiction`，新增"gate/verify 票的可信输入溯源 lint"反复发规则）。rework-01
经原 worker session resume、把两修法全文 paste（attribution contract-fault，非事后立法）。

## Answer（2026-07-16 收货，referee 终裁 — 2 轮 rework，2 major fail-open 全记指挥官账）

**已交付并收货**：dispatch `v0.2-07`（工人 grok，三轮：`d198d10` 初交 + `b05fea7`
rework-01 + `4a97904` rework-02）。`harness/run.py`(CertifiedRun) + `harness/anchor.py`
(Noop/File/Git 三后端) + `harness/verify.py`(九不变量 + 7.5 判决 + CLI) + `__init__` 导出
+ 两测试文件，合计 ~2350 行 / 55+ 测试。裁判独立全量 460+1 绿。

**这是 v0.2 立命之票（court 铁律反身于用它的 agent），也是打磨最狠的一张**：
- **初交接受、两 major fail-open 均 worker-wins（工人逐字实现冻结 v3 契约、改反违约）**：
  ① F-1 reopen 复活砖化（judge 半程失败后 open→seal→verify 放行）；② Finding A 锚被删
  manifest 静默停用（全链伪造+rm manifest+真锚→verify PASS）。**均 referee 亲手复现**
  （`referee-repro.py`）。
- **rework-01**：契约升 prereg-gate v4（judgment 上链事件 + 锚 query-by-recomputed-head
  fail-closed）。裁判亲证两属性翻转成立。**工人赢一判例**：拒绝我 note 里写错的场景
  （删诚实 run 的 manifest 不该失败）、如实申报 → referee-fault 记我账。
- **探针面板打 rework 新面** → 抓第三个 contract-fault（Finding 1：judgment.battery 上链
  却不交叉核，我 v4 §4.2"battery 可审计"是假声称）；referee payload-nested 重封亲证
  （`referee-repro-battery.py`）。
- **rework-02**：battery↔verdict statistic 多重集交叉核（Counter 非 set）+ judgment 位置钉死
  + CLI `--anchor` 三后端（FIX 2 锚防线之前 CLI 不可达）+ v4 §4.2 假声称改准。探针接受、
  1 LOW（畸形 --anchor traceback，仍 fail-closed）归 12。

**归因总账**：worker-fault = **0 个 major/blocker**（三轮零 fault，两 major 全胜诉、一判例
胜诉）+ 1 LOW（畸形 CLI 参数 except 未含 OSError）。commander = **CR-10**（3 个同类
contract-fault fail-open：reopen-brick / anchor-bypass / battery-half-fix + 1 referee-fault
[note a/b 场景写错]），新增反复发规则"gate/verify 票必须做可信输入溯源 lint"。
**验收强度实证：冻结 + 对抗 lint 的契约仍藏 fail-open，只有跨模型双面板 + referee 独立
复现逮得到——这正是本项目存在的理由反身于自己。**
