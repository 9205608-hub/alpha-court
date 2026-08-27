# 任务：复审 v0.2 设计层审计修订（RP-1：折入后、终冻结前）

你是 grok-4.5。刚完成的五路盲审里程碑审计（你是其中一路，总评"修后施工 C+"；档案
`.scratch/dispatch/v02-design-audit/`，终审 `verdict.md`）抓出 5 BLOCKER + 10 major。
指挥官已按裁定书起草全部修订并 commit（HEAD 即修订后状态）。**你现在审的是修订本身**：
改对了没有、有没有改出新错、有没有该改没改的。

## 工作区（只读，HEAD = 修订后 draft）

`cwd` 是本仓库只读检出。改动范围看 `git log -1` 与 `git show --stat HEAD`；
逐文件 diff：`git show HEAD -- <path>`。审计对象：

- `docs/design/power-calibration.md`（v2→v3：D1 同构化 argmax t/全员 greater/陪审定向 t、
  gate 表单侧重算、D2 matched-ICIR 主对照臂、D3 P(win) 重算、种子根迁移 320260711、
  §12 D13 三裁定、§13 修订日志）
- `docs/design/prereg-gate.md`（v2→v3：D6 锚语义修复、D7 run_config declaration 事件、
  D8–D11 四条诚实边界、§5 fail-closed 扩充、§4.1 哈希细节钉死、§11 日志）
- `docs/design/selection-verdict-isomorphism.md`（v1→v2：D4 三地雷→一真地雷+引用铁律、
  D5 less 负号分支+混向 raise、D16 role 落点、§8 日志）
- `docs/agents/dispatch-and-governance.md`（receipt 验证条款、(d) 全无头、tripwire 披露、
  trigger-1 补档注记）
- `docs/design/court-kernel-spec.md`（amendment 段 role 落点 + ticket 11 消歧）、
  `docs/design/killer-demo.md`（§6 双写清理）
- `.scratch/v0.2/map.md`（收官重宣、blocking 修正 05:+08 / 09:+06、冲突矩阵）、
  `.scratch/v0.2/issues/05/06/07/08/09/12 审计修订节 + 新票 10a`

## 审什么（凡可复算必真跑，python 可用）

1. **每条 BLOCKER/major 的修订是否真闭环**：对着 `verdict.md` 的 D1–D17 逐条打勾/打叉。
   特别核：D1 改后 01 内部还有没有 two-sided 残渣（陪审统计量、gate 表、size 锚、
   §5 的 won 定义、§9）；D6 改后锚语义前后一致吗；D7 的 run_config 事件在 02/06/07
   三处说法一致吗；D13 的三裁定（05 等 08、uncertified、聚合复用）在 01 §12/map/05 票
   三处一致吗。
2. **新数字对不对**：01 v3 §4.3 的 P(win) 表（argmax t 口径：0.05/0.15/0.35/0.60/0.73/
   0.84/0.92/0.96 @ 0.5–3.2）、自然赢中位 2.46/ICIR 1.78、pool-max 单侧 3.28/ICIR 2.38、
   FDR-BY 单侧 3.73/ICIR 2.70——全部真跑复算。03 v2 的 0.24 SR-std / 0.0009 / 0.023。
3. **有没有改出新矛盾**：修订段与各文档未动段落之间；四张契约互引之间；票面修订节与
   契约 v3 之间。
4. **该改没改的**：verdict.md 的 minor 清单里有没有漏掉的；你上次审计报告里有没有
   被静默丢弃的批评（对照你自己的 report.md 逐条）。

## 输出

中文。总评（可终冻结 / 还差 X 处 / 有新错，A–F）；然后逐条：D# → 闭环✓/✗ + 证据；
新错清单（若有，给 file:line）；漏改清单（若有）。刻薄优于空洞。
