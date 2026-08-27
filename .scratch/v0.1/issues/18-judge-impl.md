# 18 court/judge.py + 公共 API 集成（v0.1-08f）

Type: task
Status: resolved
Blocked by: 13, 14, 15, 16, 17
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-08f-judge/ticket.md

## Question

内核收口票：实现 judge 薄编排（唯一同时认识台账与统计的组件）+ 定稿
`court/__init__.py` 公共 API。规格 = `docs/design/court-kernel-spec.md` §5.8
（rulings F2、G1–G5）；判决书语义 = `docs/design/trial-ledger.md` §5.3/§7.4；
噪声判决落盘 = `docs/design/noise-control.md` §6。

- 每次统计应用 = 一条 VerdictRecord（scope 原样、computed 可逐行审计、
  engine_version 自动盖章）；不做聚合（战役编成归 11 号票）。
- 判决极性表是本票最大雷区：统计学"发现"（H0 被拒/过槛）⟺ 法庭 "pass"——
  FDR rejection set 命名反转必须按 spec §5.8 极性表双向测试。
- scope 内 trial 未评估 → raise（fail-closed；显式排除因 scope 落盘而可审计）。
- TDD：先写玩具台账 E2E 失败测试（四统计极性双向 + 守卫 + 公共 API 导入），
  再实现。
- 文件边界：`court/judge.py`、`court/__init__.py`、`tests/test_judge.py`；
  不得改动 13–17 交付的模块（发现偏差报 blocked，跨票修复归 referee）。

产出：`import court` 即得完整内核 API；register→record→judge→verdict 全链
在测试里真跑通。v0.1 内核完成的定义性一票。

## Answer

grok 工人交付，referee 收货（2026-07-10，commit `cddfd1d`）。`court/judge.py`（440 行）+ `court/__init__.py` 公共 API（44 名）+ 651 行判决测试。全套件 129 测试绿。referee 端到端亲测：微型台账 6 噪声 trial → 三统计量 battery → 三份 VerdictRecord 落盘，判决范围正确（DSR/PBO 只判 selected、FDR 覆盖全家族），重开台账判决俱在；全参数 fail-closed 必传（confidence/phi_threshold/metric/selected_trial_id 无一默认）。附带观察：小样本下 FDR 放过 1/6、PBO 放过被选者——battery 互补与禁赢学条款的现实预演，记入 11 号票参考。
