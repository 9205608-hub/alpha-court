# 12 v0.1 E2E 验收与诚实条款核对

Type: task
Status: resolved
Blocked by: 08, 11, 13, 14, 15, 16, 17, 18, 19, 20
Label: wayfinder:task

## Question

v0.1 收官闸门（注意：实际还依赖 08/11 之后切出的全部实现票完成——那些票登记后把编号补进本票的 Blocked by）：

- 干净环境一条命令跑通杀手 demo（下载数据 → 100 噪声因子 → 裸选择 → 法庭判决 → 出图）
- 逐条核对宪章诚实条款：结果如实呈现（驳回几个写几个）、null 归档可复查、无半成品挂出
- 逐条核对铁律：court/ import 树零市场特异依赖；每个统计函数的文献引用与公式对照表齐全
- TIMELINE.md 记录；为收尾阶段（README/录屏/上 GitHub）留交接清单

产出：验收报告。通过 = v0.1 完成，地图关闭。

## Answer

v0.1 终验通过（2026-07-11，referee 亲自执行）：

1. **干净环境一条命令**：全新 detached worktree + 全新 venv + `python -m examples.killer_demo`
   （不带 skip-download，幂等下载路径验证）→ 3418s 跑通。**确定性承诺精确成立**：
   头版逐字一致；figure.png 与 run_config.json 逐字节一致；404 行 ledger 与 report.md
   剥真实时间戳后逐行一致（台账盖真钟是预注册设计，非漂移）。
2. **诚实条款逐条**：✅ 结果如实呈现——survivors=0/100 连同"被告过个体关、死于池最大关"
   的细节全链入账（issue/map/commit/报告四处一致）；|t|=2.6655 落预注册区间 2.5–3.2
   正中，未挑种子；✅ null 归档可复查——104 份判决书带 computed 中间量、停尸表逐行
   指回 trial_id、噪声判决偏移量原文落盘；✅ 无半成品——20/20 票关闭、158 测试绿。
3. **铁律逐条**：✅ court/ 导入树零市场特异（无 qlib 环境 129 绿 + 1 skip、子进程断言
   常驻）；✅ 统计实现文献引用全链——三份研读笔记（手算向量直通 pytest）+ spec 公式
   对照表 + 两处勘误（bhy.md §3.2、adapter §7.1/§7.3）审计径完整。
4. **收尾阶段交接清单**（宪章路线图"收尾"）：双语 README（首屏对量化研究员说话，
   头版 = 0/100 + 一图；"How it was built" 跨模型互审叙事素材在 TIMELINE 与
   meta-review 档案）；演示录屏（`python -m examples.killer_demo` + report 走读）；
   GitHub 建仓（.scratch 迁 GitHub Issues per docs/agents/issue-tracker.md 迁移注记；
   确认 docs/private/ 零泄漏后公开）；可选：--sweep 20 种子扫描附录跑一次入 README。

**v0.1 完工，本地图关闭。**
