# 10 dispatch 泛化到任意 CLI + referee 治理设计（HITL grilling）

Type: grilling
Status: resolved
Triage: ready-for-human
Label: wayfinder:grilling

## Question

宪章 v0.2 的另两块（治理层的"流程侧"，与 01–09 的"court 侧"并行）：

1. **dispatch 泛化**：M0 桥当前 grok-only（`scripts/dispatch.sh`）。泛化到任意 headless
   CLI（worker 抽象、receipt schema 复用、隔离与绊线不变）。定 worker 接口最小契约。
2. **referee 治理 = RP-1 心跳**：把 `adversarial-referee`（独立复跑 + 多镜头 + 双向问责）
   焊成流程的常设环节，而非临时召唤。定三必审触发点（冻结契约前/升格勒工人规则前/
   里程碑）+ 固定外审 prompt 模板（防指挥官把框架写软）。接个人工作流体系 RP-1 与
   `meta-review-ledger`。
3. **边界**：本票是**流程/治理设计**，不碰 court 统计内核；与个人工作流体系 session 的
   L1 元技能划清（哪些留 alpha-court L2、哪些已全局化）。可能进一步拆实现票。

## 产出

设计裁定（`docs/agents/` 或 `harness/` 文档 + worker 接口契约）；如需实现，拆子票。
拍板后关票。

## Answer

**Resolved 2026-07-11.** grilling Q1–Q2（这张轻，治理/流程不碰统计内核）。设计裁定 =
`docs/agents/dispatch-and-governance.md`；worker-bridge.md scope-guard 加指针。

- **Q1 = C（dispatch 泛化 = 隔离接缝，非造注册表）**：dispatch.sh 只有两处 grok 特异——CMD
  调用数组 + `envelope.structuredOutput` 收据解析；重构成 `worker_invoke()` /
  `worker_extract_receipt()` 两函数 + 最小 worker 契约（票入/隔离 cwd/schema 收据出）；**只接线
  grok**，加 worker = 加一个分支非重写 dispatch.sh；配置注册表 YAGNI 推迟到真出现第二 worker。
  实现 = 小 ready-for-agent 任务（两接缝重构 + worker-bridge.md 一节），隔离/tripwire/schema 不动。
- **Q2 = B（referee 治理 = 记录绑定接 L1，非重建）**：守 D2 三层归属——治理逻辑/gate 归 L1 全局
  （worker-dispatch/adversarial-referee 技能 + RP-0/RP-1 + reflow/prereg-gate），alpha-court L2
  只留具体桥 + meta-review 档案 + 本绑定。**三 RP-1 触发点绑定 alpha-court**：①设计契约冻结前批量
  过 grok（本 session 逐票实践、ICIR 锁错就在这抓）②升格勒工人规则前过外部 REFUTE ③里程碑角色反转
  互评。**RP-0"机械痕迹"已兑现**（每次咨询逐个 commit 到 `.scratch/dispatch/`）；触发那半是纪律，
  完整 enforcement hook 归 L1/日后接线，10 只承诺痕迹 + 触发清单。

**四张 v0.2 设计 grilling（01/02/03/10）全部关闭**——v0.2 设计层收官。**关票。**
