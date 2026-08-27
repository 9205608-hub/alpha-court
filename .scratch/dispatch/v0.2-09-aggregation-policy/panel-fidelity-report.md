# Panel report — 契约保真镜头（Claude 收货面板，v0.2-09）

**总评：接受。** 实现与票面逐条对齐、零静默偏离；receipt 唯一 deviation（AC-3 三 legacy fixture 失败）独立复现 + AST 证明与 diff 结构性无关（文件只 import court.ledger + 读 out/，diff 外），归 base 预存债（CR-09 复发 #3，指挥侧已修）。

- F-1（重要，contract-fault 非工人）：AC-3 base 即不可满足——08 regen 把 committed 账本变 chained，三个 legacy fixture 测试失效；lint 只在 base 跑了 ruff + collect，collect ≠ run。
- F-2（minor）：from_payload 接受多余键静默丢弃（票面未冻结；转 07/12）。
- F-3（observation）：TDD 红跑是 import 级红（20×ModuleNotFoundError，合 AC-6 字面；语义测试与既有聚合测试交叉锚定，风险低）。
- F-4（observation）：declare/apply 加了 isinstance 守卫（票面未要求，方向 fail-closed 一致，非越权）。

九组逐条 ✓：dataclass 全守卫/round-trip；declare 守卫 + 零多余链检查；read 双 policy raise + 异 kind 忽略；apply unknown-rule bypass raise；**五函数与 08 版逐行语义相等零"改进"**、identity 五个 is 全 True、`__all__` 治 F401、sweep_rows 留 demo byte 级一致；out/ 零 diff、五 import 点复跑 10 passed；__init__ 诚实 docstring 无幽灵模块、恰四导出、无环；20 测试 ≥12 逐项对号无缺项、egg-info 未误提交、worktree 干净；receipt 与事实完全一致。
