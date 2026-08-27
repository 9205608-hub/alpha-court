# alpha-court — 项目宪法

一句话：**一个不会骗自己的挖因子 agent**。回测框架告诉你 idea 表现多好，alpha-court 告诉你该不该信。
单一真相源 = `docs/private/00-项目宪章.md`（定位/受众/边界/路线全在里面，改方向必改它）。
**`docs/private/` 永不入公开 git 历史**，.gitignore 已屏蔽，不得移出。

## 铁律

1. **三不做**：不做回测系统（复用 qlib，只吃收益/IC 序列）；不做 idea 生成器（生成端 stub 化）；不搬任何前实习单位内部代码/数据/标识——统计方法一律从公开文献重写并逐条引用。
2. **内核与市场解耦**：`court/` 不得 import 任何市场特异代码；日历、涨跌停、宇宙定义全部关在 `adapters/`。
3. **禁赢学**：demo 结果如实呈现；null 归档与幸存者同等文档待遇；对外展示前必须 E2E 真跑通。
4. **统计实现必须带文献引用**（DSR: Bailey & López de Prado；PBO: CSCV；多重检验: BHY），公式与代码逐项对得上。
5. 语言：与用户中文沟通；代码、docstring、公开文档用英文（README 双语）。

## 开发工作流

- **指挥 + referee = Claude Code（本 session）**：研究设计、拆票、验收。评估器在环外——工人的产出必须由指挥侧审，工人不给自己打分。
- **执行工人 = DeepSeek Harness（`dsh --profile headless`）**（2026-08-15 owner 裁定"改用 ds，全线"；grok CLI 08-13、Cursor 08-15 均已退役）：
  派工一律走 `scripts/dispatch.sh <ticket.md>`（默认 `-k ds`，重票 `-m deepseek-v4-pro`），派前先 `set -a; . ~/Desktop/智能投研助手/run_research.local.sh; set +a` 注入 key。
  任务书必须自包含（工人读原文不读转述）。⚠ dsh 无 `--resume`：中断的票把返工说明并进原票**重派**——每次派工都是从 HEAD 新建的工树，前次工作只有先合并/cherry-pick 前一条 `dispatch/*` 分支或贴进票面才带得过去；票面必带检查点 commit + `.scratch/dispatch/<id>/STATUS.md`。通道总表见 `~/.claude/CLAUDE.md`。
- **工程纪律 = Matt Pocock skills v1.1**（已装 `.claude/skills/`，MIT，来源见 SOURCES.md）：
  首次开工先跑 `/setup-matt-pocock-skills`（issue tracker 建议先选 local files，上 GitHub 后迁移）；
  大工程规划用 `/wayfinder`；单版本链 = `/grill-with-docs` → `/to-spec` → `/to-tickets` → `/implement`（内含 tdd + code-review）。
- **跨模型互审 = 本项目自研技能**（v0.1 实战沉淀，含工人对指挥官的 meta-review 三大批评作为硬规则；建造=DeepSeek／审查+裁判=Claude，跨厂商铁律）：
  施工票过桥用 `/worker-dispatch`（票面规则：契约冻结、paste-then-point、验收尺度 = 裁判尺度、派单前对抗性 lint）；
  收货用 `/adversarial-referee`（独立复跑 + 多镜头面板 + 比例原则 + "工人可胜诉" + 指挥官对等问责 + 里程碑角色反转互评）。
  裁定归因三分法：worker-fault / contract-fault / referee-fault，逐票入账。
- **TIMELINE.md**：倒序最新在上，有效会话收尾往顶部追加（绝对日期）。

## Agent skills

### Issue tracker

Issues live as local markdown under `.scratch/<feature>/` (no GitHub remote yet; migrate to GitHub Issues once the public repo exists). External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`), recorded as the `Status:` line in issue files. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root (created lazily by `/domain-modeling`). See `docs/agents/domain.md`.

## 当前阶段

v0.1 内核 + 杀手 demo（100 噪声因子 → 裸选择"发现"假 alpha → 法庭全部驳回）。
路线图与架构分层见宪章。
