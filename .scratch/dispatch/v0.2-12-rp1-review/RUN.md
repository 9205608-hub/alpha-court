# RP-1 发射说明（grok 配额恢复后）

前置：`grok` 登录态/订阅正常（2026-07-31 报 free 限额——CLAUDE.md 记录为
SuperGrok 已登录，owner 需核实是否掉登录/掉订阅）。

发射（在任意干净 alpha-court checkout，HEAD 含 610f9f82）：

    bash scripts/dispatch.sh .scratch/dispatch/v0.2-12-rp1-review/ticket.md -t 80

收货：receipt 的 open_questions 即 findings 清单，按 /adversarial-referee
逐条裁定（复现→采纳/驳回→归因入账）。RP-1 通过后方可走快照发布轮
（.scratch/v0.2/acceptance-report.md 载明的发布前提）。
