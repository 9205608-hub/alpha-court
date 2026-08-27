# 裁定记录 —— skills-ds-edition 审阅（2026-08-15，指挥官对等问责）

审阅判决 B / revise。逐条裁定（adopted = 已改进同一提交；rejected 须给理由）：

| # | 严重度 | 裁定 | 落点 |
|---|---|---|---|
| 1 `-w` 同名重派"能看到前次工作" | blocker | **adopted**（指挥官事实错误，来源=HQ 看板旧说法未核脚本 → 归因 commander-fault） | worker-dispatch "No headless resume" 段 + Rework protocol 段重写；CLAUDE.md 同句改正 |
| 2 模板自相矛盾（阶段 commit vs 一次 commit ALL） | major | adopted | ticket-template Delivery protocol 3 改为逐检查点 commit |
| 3 票头字段泄给工人 | major | adopted | 指挥侧字段移到 sidecar `.scratch/dispatch/<id>/preflight.md`；票内只留检查点/STATUS 契约 |
| 4 main 上的 skill 描述分支功能 | major | adopted | 加一段：main 的 dispatch.sh 仍 grok-only，ds 机制在分支 |
| 5 收据定义排除文档票；"待验证不入账"与"不得静默丢弃"冲突 | major | adopted | 收据按产物类型定义；待验证入账 status=pending |
| 6 optional 桶未定义 / 降级漏洞 | major | adopted | 定义 optional + 两条守卫（因 AC 未覆盖而降级→contract-fault 检查；权威错误一律入 jurisprudence） |
| 7 max-turns 非"handled"；-n/-t/-e 未标 grok-only | minor | adopted | Mechanics 用法行重写 |
| 8 resume-worker 守卫措辞过度 | minor | adopted | 改为"拒收 ds/cursor 信封并让你重派" |
| 9 "open item" 未被追踪 | minor | adopted | 改为"NOT enforced by any script and not yet tracked" |
| 10 无收据数字 + 私有路径 | minor | adopted | 291/PTCG 改为泛化表述；私有路径改为泛指 |
| 11 STATUS.md 成本/位置/轮询未脚本化 | minor | adopted | 钉到 `.scratch/dispatch/<id>/STATUS.md`，referee 排除，轮询=指挥手动 |
| 12 "schema-constrained" 过度声称 | minor | adopted | 改为"commander-side schema-validated" |

未采纳：无。**跨厂商（dsh）复审待补**——本次审阅官与指挥官同厂商，按项目铁律只算内审；下一次触碰这两个 skill 时先补 ds 外审。
