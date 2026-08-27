# 13 court/ledger.py 实现（v0.1-08a）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge
Blocked by: 08
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-08a-court-ledger/ticket.md

## Question

实现 trial ledger：三类不可变记录（Hypothesis/Trial/Verdict）+ 单文件 append-only
`ledger.jsonl` 事件日志 + 读取面（trials/series/matrix/verdicts/status），全线
fail-closed。契约 = `docs/design/trial-ledger.md`；施工规格 =
`docs/design/court-kernel-spec.md` §5.7（签名、raise 条件表、rulings B1–B10）。

- TDD：先写 `tests/test_ledger.py` 失败测试（契约行为 + 存储回放 + matrix 对齐 +
  守卫全表），再实现。
- 文件边界：只动 `court/ledger.py` + `tests/test_ledger.py`（`court/__init__.py`
  归 18 号票）。
- 交付经 M0 桥派 grok，referee 独立复核验收（工人不给自己打分）。

产出：可复放的台账模块，六件套实现票的评据基座。

## Answer

grok 工人交付（首派撞 `max_tokens_truncation` 报废重派，加"分块写文件"操作提示后成功），referee 收货（2026-07-10，commit `cb9189a`）。`court/ledger.py`（601 行）+ 27 测试。referee 契约行为矩阵亲测五项全过：重复评估 raise、matrix 错位 raise、撕裂尾行静默恢复、中段损坏 `LedgerCorruptionError`、非有限序列 raise。frozen dataclass 逐类型引契约条款；文件所有权干净（仅 2 文件）。
