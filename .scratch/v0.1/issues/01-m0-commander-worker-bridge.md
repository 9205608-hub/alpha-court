# 01 M0 指挥→工人桥

Type: task
Status: resolved
Assignee: claude-commander (session 2026-07-10)
Label: wayfinder:task

## Question

打通 Claude Code（指挥/referee）→ grok build 无头 CLI（执行工人）的最小派单链路。产出三件：

1. **工人票格式**：自包含任务书模板（工人读原文不读转述）——背景、约束（含宪章铁律摘录）、验收标准、输出要求，全部写死在一个文件里。
2. **JSON 收据契约**：工人交货的结构化格式——干了什么、改了哪些文件、自测结果、遗留问题。指挥侧按收据验收，工人不给自己打分。
3. **派单脚本**：`scripts/dispatch.sh`（或等价物），封装 `grok -p --prompt-file <ticket> --worktree --output-format json`，收站 stdout/JSON 落到收据文件。

**验收标准 = 用一张最小真实票（[02 工程底座](02-repo-engineering-scaffold.md)）走完全链**：指挥写票 → 脚本派单 → grok 在 worktree 干活 → JSON 收据回来 → 指挥审收据 + 审 diff → 合格则收货。链路通即关票。

边界：只做"能派单能收货"的最小件。预注册闸、referee 对抗复核、多 CLI 泛化都是 v0.2 harness/ 的事，不在此票。

## Answer

桥建成并经两次真实派单验证（2026-07-10）：

- **三件产物**：`scripts/ticket-template.md`（自包含任务书模板）、`scripts/receipt.schema.json`（收据契约，经 grok `--json-schema` 在模型层硬约束——交货物理上不可能不结构化）、`scripts/dispatch.sh`（派单脚本）。契约文档：`docs/agents/worker-bridge.md`。
- **首跑事故（有价值的失败）**：v0.1-02 首次派单时 grok 的 `--worktree` 在 headless 模式静默失效，工人直接跑在指挥 checkout 里；且最终收据在信封 `structuredOutput` 字段而非 `text`（后者是每回合对象串联）。referee 流程当场抓住两个缺陷。
- **修复**：隔离改为指挥侧强制——`git worktree add -b dispatch/<name>-<stamp>`（工位在 `~/.alpha-court/dispatch-worktrees/`）+ `grok --cwd` 钉死；加事后绊线（指挥 checkout HEAD/status 前后必须一致，违者 exit 2）；收据解析改从 `structuredOutput` 取。隔离机制与工人 CLI 解耦，为 v0.2 多 CLI 泛化铺路。
- **E2E 证明**：探针票 v0.1-01-probe 走修复后的桥——隔离工位✓、独立分支✓、绊线静默✓、收据解析✓、referee 独立复核✓、merge + 工位清理✓。活证据：`scripts/BRIDGE-SELFTEST.md`（工人在隔离工位里写下的自己的 pwd 和分支名）。
- **工人诚实度观察**：v0.1-02 收据如实报 `partial` 并在 deviations 里写明差异（该差异实为指挥侧污染，非工人责任）——收据契约的"报事实不自评"设计首战有效。
