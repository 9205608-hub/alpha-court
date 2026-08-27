# v0.2 E2E 验收报告（票 11，referee 亲执）

- 日期：2026-07-31；验收基座：`610f9f82`（v0.2-12 八 slice 已落地）
- 验收人：指挥官兼 referee（Claude）；延续 v0.1 12 号票尺度
- 结论：**通过（PASS，附 1 条 LOW observation + 1 项发布前提）— v0.2 完成，map 关闭**
- 发布前提：ticket 12 的 grok RP-1 跨模型审查（配额恢复后、快照发布前补做；
  issue 12 Answer 载明）

## 逐条裁定

### 1) 法庭上过真案 ✅

- **hero 大跑（05 裁定证据）**：880 arm/31h 预注册跑，产物
  `.scratch/v0.2/power-sweep-results/`（report + figure + appendix-rerun 全套）。
- **size 与 power 并列**：report.md §"Directional size (β=0)" 紧随 hero 表；
  首屏诚实块声明 UNCERTIFIED / 构造 oracle ≠ 可发现 alpha / 无成本。
- **判别力**：A 曲线 14 档全单调（0.000→1.000），80% 提交 power @ ICIR≈4.0；
  **size 校准**：champion-unanimous 0.000，Wilson [0, 0.088]，分闸全在名义位下。
- **本次亲验（at-HEAD E2E）**：killer demo 干净工树 `610f9f82` 真数据重跑
  （226s，csi300 PIT，480 评估日）：HEADLINE 逐字复现（0/100 幸存、
  accused=volatility_lb150_v14、|t|=2.6655、五闸判决全同）；**404 事件账本
  与 committed 版逐字段比对，唯一差异字段 = `at`（墙钟）**——哈希、序列、
  判决全部逐位一致。52566a27 与 610f9f82 两个基座各验一次，同结果。

### 2) 预注册闸挡得住自欺 ✅（referee 独立构造 8 探针，8/8 fail-closed）

探针脚本 scratchpad `ticket11-probes.py`（自选数值，非复跑测试套件）：

| 探针 | 结果 |
|---|---|
| P1a scope 缩水（API 面） | judge() 无 scope 参数——scope 派生自链上全部已评 trial，非调用方可选 |
| P1b scope 缩水（野判决） | 缩水 scope 的手工 verdict 被"judgment 须覆盖链上全部 verdict"不变量拒绝 |
| P2a post-hoc 翻号 | 混向 scope judge 拒收（heterogeneous direction），**零 verdict 落链** |
| P2b 封印后翻号字节篡改 | verify 拒：trial event_hash mismatch |
| P3 verdict computed 篡改 | verify 拒 + `Ledger.open` replay 同拒（双门） |
| P3 篡改前对照 | 干净封印账本 verify 通过（探针非空转） |
| P4 证据链 replay（06） | 封印链重放完整：trials=3 / verdicts=1 / declarations=3（run_config+policy+judgment） |

### 3) 选择–判决同构 ✅（1 条 LOW observation）

- committed demo 账本 104 个 verdict **role 零缺失**：DSR（two-sided）
  = informational ×1 弃权不投票；fdr_by/pbo_cscv/noise_control
  = discriminating ×103。弱关不计入幸存（champion 过 individual 噪声关
  仍被驳回——报告如实展示）。
- **聚合口径先于判决落盘**：认证路径上 run_config + policy 为开链首批
  declaration、判决在后（P4 亲验 + `test_create_writes_run_config_and_policy_
  as_first_events`）。demo 为非认证 court 直驱路径，聚合规则显式于
  killer-demo.md §6 + `aggregate.py`（复用 `harness.aggregation_policy`
  权威实现）。
- **LOW observation**：demo 报告正文未点名幸存规则（"survivor = 全部判别关
  unanimous pass"），役割表与脚注可推知但未明说。→ v0.3 backlog #6，随下次
  产物重生成补一句（避免纯措辞改动引发全账本 `at` churn）。

### 4) 解耦守卫升级 ✅

issue 04 裁定关票（2026-07-31）：白名单实质由 `harness/court_import_gate.py`
（AST 门，allowlist=stdlib∪{court,numpy,scipy}，pre-commit + pytest 真树双挂）
以更强形式满足；**反证亲跑**——`court/__init__.py` 注入 `import pytest` →
门 CLI exit 1 精确报行、真树测试 FAIL、旧黑名单 smoke 对同一注入依然全绿
（原盲区当场演示）；复原全绿。运行时 sys.modules 名字白名单处方实证不可实现
（8 个科学栈自身顶层名），归档于 issue 04 Answer。

### 5) 诚实条款逐条 ✅

- power 难看也如实报：低强度档 A=0.000 原样入表，underpowered 标旗不平滑；
  附录三缺陷（figure 崩 / t3.0 失信息 / matched 钳边界）单独成文重跑翻正。
- size ≠ power 分表：§"Directional size"独立成节，与 hero 表并列且声明
  estimand 差异。
- 构造信号 ≠ 真实 alpha：power 报告首屏声明；demo 报告 caption 声明
  gross paper series 无成本。
- null 归档同权：morgue 表 100 行全量入报告，与 headline 同文档。

### 6) 铁律逐条 ✅

- court/ 零市场特异：court-import-gate PASS @`610f9f82`（含本日两次
  pre-commit 实跑）；smoke 黑名单冗余保留。
- 统计实现文献引用：dsr/pbo/fdr/sharpe/judge 均带 References
  （Bailey & López de Prado 2014；CSCV；BHY），docstring 逐项在位。
- ledger schema：v0.2-12 只改校验不改字节（存储序列化冻结原样）；
  committed demo 产物在新 fail-closed 校验下回放全绿（556 测含
  killer/certified 面）；确定性逐位复算成立（见 §1）。

### 7) 交接 ✅

v0.3 待办清单留档 `.scratch/v0.3/backlog.md`（宪章三主线 + 四条 v0.2 顺延
+ spencer-quant 关联项）。

## 附：本轮验收产生的工程侧修复

- `dispatch.sh` sessionId 打印 SyntaxError（成功派单误报 exit 1）→ `828e9363`。
- grok 配额中断 → 票 12 改指挥官实施 + RP-1 后置（tooling-fault 入账，
  零 worker-fault；工人工树留作审计现场）。
