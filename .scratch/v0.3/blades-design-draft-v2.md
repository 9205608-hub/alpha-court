# v0.3 gates/ 刀片库设计 v2（2026-08-13 凌晨跨模型对抗审后修订；**同日上午 owner 拍板 OQ-A/B/C，本稿冻结**）

> v1 经 Codex 5.3（异厂商）对抗审：3 BLOCKER + 7 MAJOR + 1 MINOR，全部
> file:line 实证（raw 存 `.scratch/v0.3/blades-review-codex-raw.json`）。
> 指挥官抽验核实后**11 条全采纳**（无驳回项）。v2 = 结构性重构版。
> 变更全文见 §6 采纳台账。

## 0. 立意（不变）

秒级便宜刀在 battery 烧机前砍掉不值得审的候选，砍必留痕（null 博物馆
供给侧）。公理：A1 便宜（秒级零拟合）、A2 市场无关（只吃 series/透明
标量，blocks 等标签 opaque、court 禁止从任何字符串推断日历）、A3 证据
先于裁决。

## 1. 核心结构决策（v2 重构，对应 BLOCKER 1-3）

### 1.1 入账口径：blade 证据走 declaration，绝不碰 verdict

- seal/verify 硬不变量：judgment.verdict_ids == 链上全部 verdict
  （harness/run.py:443、verify.py:421）——任何"informational verdict"都会
  污染认证链。**BladeReport 以 `declaration` 事件承载**（kind=
  `blade_report`，payload=report JSON，court-opaque），ledger/replay/
  verify 零改动。
- 同理，阈值标定（§3）以 `declaration` kind=`blade_calibration` 上链。

### 1.2 执行位置与"拦截"的真实语义：screen = 不 evaluate

- derived scope = evaluated/judged trials（run.py:95）。**刀片跑在
  register 之后、record(evaluation) 之前**。flag 且 spec 声明
  `on_flag: screen` 时，harness **拒绝 record 该 trial 的 evaluation**——
  trial 以 registered 状态留在链上 + blade_report declaration 说明原因
  → 自然不入 scope、不入 judgment，认证不变量全程无恙。
- 禁止形态（v1 的错）：先 evaluate 再"从 battery 缩编"——会撞 invariant 7
  （seal scope == derived scope）。

### 1.3 flagged 与 hard_gate 分层（对应 MAJOR 4）

- v0.3 刀片**只有两种效力**，spec 逐刀声明：
  - `on_flag: record`——纯证据，declaration 入账，battery 照跑；
  - `on_flag: screen`——如 1.2，不 evaluate。
- **v0.3 不提供 discriminating 判决刀**。若未来某刀要投判决票，必须按
  battery 待遇做整套 size/power 标定，另立项。

## 2. 四刀契约（v2 修订）

共同：纯函数，`BladeReport{blade, flagged, statistics, evidence, params}`；
numpy/scipy only（court_import_gate 白名单，harness/court_import_gate.py:53）；
绘图/IO 一律 examples/ 或 adapter 侧。**v0.3 每刀只吃 trial declared 的单条
series**（ledger 单 series 契约，court/ledger.py:50-56；IC+returns 联判走
双 trial 关联，v0.4 再议——对应 MAJOR 5）。

### 2.1 identity_degeneracy

- 变换族修剪（对应 MAJOR 9）：**T = {lag k: |k| ≤ K}**（identity = k=0）。
  negate 冗余（|ρs| 对称）、rank 冗余（Spearman 本身只用秩）——按有效
  假设数 |refs|×(2K+1) 标定阈值。
- 统计量：max/次大 |spearman(x, lag_k(r))|；flag: max ≥ rho_max（标定见 §3）。

### 2.2 pool_redundancy

- 不变：候选 vs 池成员 max/top-5 |pearson| 与 |spearman| 双报；
  flag: max ≥ rho_pool。与 2.1 分刀理由不变（归因分层）。

### 2.3 magnitude_vs_turnover（语义收缩，对应 MAJOR 7）

- **纯经济地板刀，无显著性语义**：net(c) = r_gross − c·tau；报 break-even
  c*、成本网格净均值表。flag 条件：**E[net] ≤ 0 @ spec 声明的 c_ref**
  （即 t_min 概念删除；显著性完全留给 battery 的 FDR/noise 门，
  court/judge.py:301-321,546）。

### 2.4 single_year_luck（检验学钉死，对应 MAJOR 10）

- 贡献定义冻结：block b 的贡献 = Σ_{i∈b} x_i（符号保留），集中度用
  **HHI(|贡献|)**（绝对值，防符号不稳）。
- 判则合并成**单一标定对象**：flag ⇔ LOBO_min ≤ 0 **OR** HHI-p < p_min，
  **两条 OR 规则在 null 世界联合标定整体假阳率**（不再各自拍阈值）。
- 标定不达标（联合假阳率压不到目标）→ 本刀降级 `on_flag: record` 出厂。
- blocks = adapter 显式提供的 opaque 整数标签；court 禁止解析日期
  （docs/design/trial-ledger.md:49 先例）。

## 3. 阈值标定预注册（对应 MAJOR 6 / OQ1 / OQ5）

- 新增 `blade_calibration` declaration（首个 blade_report 之前上链）：
  {seed_root, null 配方（复用 v0.2 noise battery 纯噪声世界）, 目标假阳率,
  各刀最终阈值, 标定 run 指纹}。
- 标定只在合成 null 上做，与真数据隔离；标定后阈值进 spec 哈希，改阈值 =
  改 spec = 重新预注册。权限线沿用 power-calibration.md:311 先例
  （frozen before any run, never silently re-tune）。

## 4. 切票草案（v2）

1. 票 0（新增，先行）：`blade_calibration` declaration 机制 + harness
   screen 接线（1.1/1.2 的地基，动 harness 不动 court kernel）。
2. 票 1：gates/base.py + identity_degeneracy + pool_redundancy + 红先测试。
3. 票 2：magnitude_vs_turnover（复用 court.sharpe 的均值路径）。
4. 票 3：single_year_luck（含 null 联合标定脚本）。
5. 票 4：null 博物馆消费 blade_report（v0.3 item 2 对接）。
   票 1-3 并行；票 0 先行；票 4 殿后。

## 5. 开放问题拍板（2026-08-13 上午 owner 拍板，随本稿冻结）

- **OQ-A 已拍**：目标假阳率 = **单刀 1%，四刀联合 ≤5%**（进 §3
  blade_calibration 预注册；改动 = 改 spec = 重新预注册）。
- **OQ-B 已拍**：默认 **`on_flag: record`**——flag 只上链留痕、battery
  照跑；spec 逐刀显式声明才 screen。刀片首季攒实绩校准信任后再议收紧。
- **OQ-C 已拍**：**K = 5**（进标定；identity 刀有效假设数 = |refs|×11）。

## 1.4 增补：刀阵容钉链（2026-08-13 下午，票 0 收货 panel MAJOR-2 裁决）

- **发现（探针坐实）**：screen 是"挂刀条件性"的——blade-less `open()` 重开
  即可把已 screen 的 trial 照常 evaluate 入 scope，seal+verify 全绿；spec
  的 screen 声明在无刀 run 里被静默忽略。根因=run_config/policy 都钉在链上
  并在 open() 交叉核验，**刀阵容没有钉**。工人忠实执行了冻结合同，非工人
  过错（attribution: design-gap）。
- **增补裁决（票 v0.3-00b 实现）**：新增 declaration kind=`blade_roster`
  （首次带刀 evaluate 前上链：阵容名单+各刀 params 指纹），`open()` 时
  fail-closed 交叉核验：链上有 roster 而未挂等价阵容 → 拒绝 evaluate；
  链上无 roster 而 spec 含 screen 声明 → 拒绝 record。沿 §1.1 declaration
  承载原则，ledger/verify 仍零改动。
- 本增补经 3-lens 对抗 panel 证据支撑（probe P3/P3b/P9 存
  `.scratch/dispatch/v0.3-00-blade-plumbing/panel-verdict-20260813.json`）。

## 6. 采纳台账（对抗审 11 条 → 处置）

| # | 严重度 | 一句话 | 处置 |
|---|---|---|---|
| 1 | BLOCKER | verdict 复用撞 seal/verify 全链不变量 | 采纳：declaration 承载（§1.1） |
| 2 | BLOCKER | 新事件类型被 ledger fail-closed 拒 | 采纳：不加类型（§1.1） |
| 3 | BLOCKER | battery 前拦截撞 derived-scope | 采纳：screen=不 evaluate（§1.2） |
| 4 | MAJOR | informational 与默认 block 自相矛盾 | 采纳：record/screen 两档+无判决刀（§1.3） |
| 5 | MAJOR | 单 trial 单 series 契约 | 采纳：v0.3 单 series（§2 共同） |
| 6 | MAJOR | 阈值标定必须预注册 | 采纳：blade_calibration 上链（§3） |
| 7 | MAJOR | net-t 与 battery 推断门抢戏 | 采纳：纯经济地板（§2.3） |
| 8 | MAJOR | blocks 禁日历推断要明写 | 采纳（§2.4） |
| 9 | MAJOR | negate/rank 在 \|spearman\| 下冗余 | 采纳：T=lag 族（§2.1） |
| 10 | MAJOR | LOBO+HHI 检验学未定义 | 采纳：贡献冻结+OR 联合标定+降级条款（§2.4） |
| 11 | MINOR | import 白名单明确跟随 | 采纳（§2 共同） |

驳回：无。指挥官对 1/9/7 做了独立抽验（seal 断言在 run.py/verify.py 原文、
Spearman 对称性手推、judge.py 推断门存在性）后才整批采纳——不迷信审稿人，
但这轮审稿人全对。
