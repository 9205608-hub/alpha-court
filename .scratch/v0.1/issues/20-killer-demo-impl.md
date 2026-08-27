# 20 examples/killer_demo 实现（v0.1-11a）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge
Blocked by: 11, 18, 19
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-11a-killer-demo/ticket.md

## Question

按 `docs/design/killer-demo.md` 实现 `examples/killer_demo/`：AR(1) 生成 stub
（5族×20，种子树 SeedSequence(20260710)）→ adapter 评估 + ledger 注册 → 裸选择
（max|t_iid| 全窗）→ battery 五关 104 verdict（fdr_by→dsr→pbo(S=16)→pool_max→
individual×100）→ 全票制聚合 → 一图（199 best-of-null 直方图 + 被告竖线 + 1.96
虚线）→ report.md 判决书四部。入口 `python -m examples.killer_demo`
（--seed/--sweep/--skip-download）；测试义务五件套（§11）；E2E 验收 = 真跑那条命令。
禁赢学：设计文档即预注册书，出什么报什么。

## Answer

grok 工人跨两个 session 写完全部代码（14 模块 + 15 测试），两次会话均死于 CLI 基建
（Cancelled 中断 + resume 僵死 2 小时 0 CPU）而非代码——referee 击毙僵尸后代为执行
验收电池（归因：infra-fault，工人代码零责）：158 测试全绿、ruff 净、E2E 真跑 3392s。

**头版（预注册种子 20260710，如实呈报，2026-07-11，commit `0f93e4d`）：**
- **survivors = 0/100 —— 法庭全部驳回**
- 被告 volatility_lb150_v14，|t|=2.6655（落在预注册区间 2.5–3.2 正中，未挑种子）
- 五关：fdr_by ✗ / dsr ✗ / pbo_cscv ✗ / noise_pool_max ✗（p̂=0.575，199 个纯噪声池
  里 114 个的 best-of 比被告强）/ noise_individual ✓——单独看像真的，放回"百里挑一"
  语境即现形，选择效应校正的活教材
- 104 份判决书入台账；一图（199 best-of-null 直方图 + 被告红线 + 1.96 虚线）与
  judgment 同轴呈现幻觉与判决；图注带齐 gross/种子/data tag/engine_version 申报
