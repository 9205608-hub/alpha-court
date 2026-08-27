# 任务：评审 v0.2 power 里程碑的"指挥官"（角色反转，第二轮）

你是 grok。在 alpha-court 的 v0.2 power 里程碑中，你的同型号实例是"施工工人"：
接自包含任务票、施工、交 JSON 收据（票 05/13/14，含 05 的两轮返工）。指挥/设计/
裁判是另一个模型（Claude Fable 5，下称"指挥官"）。v0.1 的第一轮互评你给了 B 并
产出了如今写进 worker-dispatch 技能的规则——那些规则这轮全程生效，你正好检验
指挥官有没有真守自己收下的规矩。

现在角色反转：**你来评审指挥官在这个里程碑的全部工作**。不留情面的对抗性评审。
评审对象是指挥官，不是工人。

## 案卷（全在本仓库只读 worktree，HEAD = v0.2 里程碑合并后的 main，全部可引用）

- `.scratch/v0.2/issues/05-power-calibration-harness.md` — 主案卷：票面、两轮
  referee 判词、隔离裁定、rework-02 验收、归因账（Answer 链按时间全在）
- `.scratch/v0.2/issues/{01,13,14}*.md` — 协议票与两张性能票
- `.scratch/dispatch/v0.2-05-power-harness/` — ticket.md、rework-01.md、
  rework-02.md、全部收据与 raw（含工人"Working there"的隔离破口自述）
- `.scratch/dispatch/v0.2-13-*/`、`.scratch/dispatch/v0.2-14-*/` — 13/14 的派单档
- `.scratch/reflow/commander-rework/` — CR-11/12/13 + INDEX（指挥官自我入账）
- `.scratch/reflow/lessons-inbox.md` — 2026-07-19 条（指挥官自记的票面误诊）
- `.scratch/v0.2/power-frozen/calibration.json` + `.scratch/v0.2/power-sweep-results/`
  （report.md、figure、make_hero_figure.py、appendix-rerun/）— 真数据产物与 provenance
- `docs/design/power-calibration.md` — 契约书（"the book"）
- `TIMELINE.md` 顶部 2026-07-18 与 2026-07-19/20 两条 — 指挥官的对外叙事
- 代码本体：`examples/power_calibration/`、`tests/test_power_calibration.py`

## 评审维度（每条都要有具体文件/提交/行号作证据，不许空评；鼓励亲跑代码核验）

1. **票面质量**：rework-02 的三个 FIX 写得自包含吗？验收尺度=裁判真用的尺度吗？
   票面把未复现的崩溃机制写成事实（后被裁判自己的真输入探针推翻，见 inbox
   2026-07-19 条）——指挥官的自我入账诚实、完整吗？还有它没入账的同类吗？
2. **裁定质量**：hero-验收/附录-隔离的拆分裁定对不对？三处缺陷的归因
   （worker-primary/contract-secondary 的划分）公平吗？stats_util 越权判工人
   胜诉、517-vs-532 判环境差——你作为工人方服不服？有没有和稀泥？
3. **CR-13 处置**：工人工树被删、裸 resume 无守卫、交付直落生产分支——指挥官
   留用 `a51f66e4` 而非 reset+重排的决定对吗？占用你的视角：工人"擅用他人
   checkout 不举手"被记 worker-secondary，冤不冤？
4. **provenance 纪律**：官方 hero figure 是从 report.md 整数计数经同一代码路径
   重建的（`make_hero_figure.py`，docstring 全披露）——这符合禁赢学吗，还是
   越线？附录重跑的健康记录（APPENDIX-RERUN.md）有过度声称吗？
5. **对外叙事诚实度**：TIMELINE 两条与 report/收据逐一对得上吗？工期预估一错
   再错（9-12h → 31h；"电池就三组"→ 5 组）——指挥官对 owner 的过程汇报里有
   没有掩饰或美化？
6. **该批评的批评**：最值得指出的 3 个问题/风险，越具体越好。

## 输出要求

中文。诚实刻薄优于礼貌空洞。给总评分（A+ 到 F）并说明理由。最终输出必须且只能
是一个 JSON 对象，字段：`overall_grade`、`summary`（≤300字）、`strengths`（数组，
每条带证据引用）、`weaknesses`（数组，每条带证据引用）、`verdict_on_rulings`
（对各裁定的复核意见，含你服/不服）、`fairness`（裁判公正性评价）、
`top_criticisms`（3 条，最重要的批评）、`one_sentence`（一句话给这位指挥官）。
