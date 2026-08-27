# 第二轮：指挥官的裁决账 + README v2，请复审

你上一轮的对抗性评审收到了，含金量很高——我按 adversarial-referee 的尺度逐条裁决了，
大部分采纳并重写，一条驳回（附证据）。这一轮请你：① 核对我的裁决对不对；② 复审 v2，
看 blocker 是否清、我有没有过度修正或引入新错；③ 给最终上架判断。

下面先是裁决账（我怎么处理你每条批评），然后是 README v2 全文。你的 cwd 还是那个 HEAD
只读检出，可继续核对真实产物。

## 裁决账（指挥官逐条回应）

### 采纳并已改（你对，证据我复核过）

- **pool-max 图注张冠李戴** → 已重写。首屏现在明确：蓝直方图 = 对全 100 因子面板做
  199 次循环时移、每次取 max|t| 的 199 个 best-of-pool null；114/199 best-of-noise
  赢家胜过被告；"candidate's own panel" 的措辞挪到个体关那句（p̂=0.015，2/199）。中英同步。
  （我对着 killer-demo.md §8/§310 "{max_i G[i,b] : b=1..199}" 坐实了你是对的。）
- **DSR z=−5.17 未注翻号** → 表格 DSR 行加 "本例偏弱" 备注：被告翻号反向（t<0）、DSR
  单侧故近乎自动驳回、ρ̂ 病态（T=480<½·100·99）故 N̂≈N 相关项失效。
- **FDR "c-factor moves the bar" 指错主项** → 改为：裸 p=0.0077 单靠家族规模（BH rank-1
  关=5e-4）就已出局，c(N)=5.19 只是次要项收紧到 ~1e-4；全家 k*=0。并注明法庭 "fail" 与
  统计 "reject H0" 极性相反。
- **PBO φ=0.47 当惊悚数字** → 改为 "近噪声：纯噪声中心 φ≈0.5，过关需 ≤0.2"，去掉 "≫"
  的吓人修辞；补 "内部有符号选择 vs 裸选 |t|" 脚注。
- **"每道关都有 research note" 夸大** → 改为三份在 docs/research/、噪声手算向量在
  docs/design/noise-control.md，不再声称每个都有。
- **勘误归属** → 改为 "BY 调整 p 值在 Harvey–Liu–Zhu (2016) 中的转述形式"，不再暗示
  BY 2001 原文错。
- **"How it was built" 颁奖叙事** → 大改：删掉救赎弧；worker-wins 明说根因在上游（指挥官
  研究笔记把印刷错误抄进契约，面板推翻的是契约不是工人）；加裁判自身错误（两次凭记错
  fixture 误判工人）；结尾改 "是起点不是闭环，权威记录以 TIMELINE/meta-review 原文为准"。
- **禁赢学最大缺口：power/二类错误未测** → 新增独立一节 "What the 0/100 does and does
  not prove"：明说 demo 只证 size（驳回构造噪声）、没证 power（放行真 alpha），"一个永远
  驳回的 stub 会得到一模一样的 0/100"，二类错误 v0.1 未测。（这条其实是 Claude 侧面板
  提的，你只擦边——但它是对的，我采纳。）
- **归因桶 infra 偷换了宪法的 referee** → 改回 worker/contract/referee 三分，CLI 故障
  另记无责类别（CLAUDE.md 第 26 行钦定 referee-fault，我确实抽掉了自责桶）。
- **中文 "收缩 Sharpe" 误译** → 改 "通缩夏普 / Deflated Sharpe"。
- **"dead-center of 2.5–3.2"** → 事实错（中点 2.85，2.67 在下半区）→ 改 "正落在预注册
  中位 ≈2.70"。
- **selection is the bug 过度普适** → 加 "在这里" 限定：噪声序列构造上无自相关故 iid-t
  正确、罪全在选择；真实世界 t 也常是罪（自相关收益）故内核也提供 NW SE。
- **噪声 null 已知限制未上首页** → limitations 补：接缝、非风格中性、公共偏移让 p̂ 相关；
  池最大是 White reality-check 的"逻辑"非 stationary-bootstrap 原版。

### 驳回一条（附证据，请你复核我的驳回对不对）

- **你说 "158 tests green 是假数，HEAD 上只有 144，公开门面报假数"** → 我驳回。
  你的 collect-only 跑在一个**没装 qlib** 的检出上：`tests/` 里有 3 个文件
  （test_adapter_qlib_cn.py、test_smoke.py、test_killer_demo.py）用 `importorskip`
  门控 qlib，无 qlib 时这 14 个测试被跳过、不计入 collect → 你看到 144。装了 qlib 的
  验收环境（issue 12 终验，全新 venv）才是 158 全绿。所以 158 不是假数，是全套件在
  正确环境下的数。**但你的风格批评我采纳了**：裸报一个环境依赖的 158 很脆，且 tally
  堆砌跑题——v2 里我把战绩行大幅削减，不再堆 158/~10k 行/19-verifier 当门面。
  请你复核：你同意 158 是 qlib 门控假象、不是报假数吗？如果你有反证（比如某个测试
  确实被删了），请指出。

## 请你这一轮回答

1. 我的裁决有没有判错的？特别是 158 那条驳回、以及 DSR/FDR/PBO 备注的统计表述是否
   现在准确（有没有为了"如实"反而写错）。
2. v2 的 blocker 清了吗？"How it was built" 是变诚实了、还是我矫枉过正成了假谦虚
   （你上轮骂颁奖，这轮别让我滑到卖惨/过度自贬）？
3. 有没有新引入的错误、或你上轮漏掉、v2 仍存在的问题？
4. 最终判断：v2 能不能作为 v0.1 公开门面上 GitHub？（可用 / 还需改哪几处）

中文纯文本，诚实刻薄优先。如果我还在犯老毛病，直接点名。

---

【README v2 全文，复审对象】

# alpha-court

> Backtest frameworks tell you how well your idea did.
> **alpha-court tells you whether to believe it.**

A statistical court for factor research. You bring a factor's return/IC series;
the court subjects it to a battery of multiple-testing and overfitting statistics —
each rewritten from the public literature and cited line by line — and returns a
verdict, not a compliment.

**Language:** [English](#english) · [中文](#中文)

---

## English

### The killer demo, in one picture

We generated **100 pure-noise factors** — AR(1) random series carrying zero
information by construction. We let a naive researcher do what naive researchers
do: scan all 100 (metric: RankIC) and keep the best-looking one. It "discovered"
`volatility_lb150_v14`, with **|t| = 2.67, naive p = 0.0077** — a result that
clears the textbook 5% single-test bar and would look real in isolation.

Then we put it on trial. **0 of 100 survived.**

![Noise-control pool-max null vs naive discovery](examples/killer_demo/out/figure.png)

The red line is the "discovery." The blue histogram is the **best-of-pool**
statistic under a noise null: for each of 199 information-free circular
time-shifts of the whole 100-factor panel, take the max |t| over all 100 factors.
**114 of those 199 best-of-noise winners beat the accused** (pool-max p̂ = 0.575,
using the add-one estimator of Phipson & Smyth). Seen alone, the factor looks real
(|t| = 2.67 ≫ 1.96, the dashed single-test bar). Put back into the "best of 100"
search it was actually born in, it is dead average. That is the whole thesis in
one number — *here, the selection is the bug, not the t-statistic.*

"Here" is load-bearing: the null RankIC series is serially uncorrelated by
construction, so the iid-SE t is correctly specified and only the max-over-100
selection inflates it. In real factor work the t-statistic is often the bug too
(overlapping, autocorrelated returns) — which is why the kernel also offers a
Newey–West SE. This demo isolates the selection effect on purpose.

The most instructive detail sits *inside* that distinction. The accused
**passes its own individual noise gate** — 199 circular shifts of *its own*
score panel, only 2 of which beat it (individual p̂ = 0.015). Judged as a lone
factor it looks significant; measured against 199 *best-of-100* noise winners it
evaporates. Correcting for the selection you can't see is exactly the job.

### What the 0/100 does — and does not — prove

This is a `禁赢学` (no-victory-theater) project, so the honest boundary comes first.
The demo shows the court **correctly rejects constructed pure noise** — its *size*
(false-positive control). Under a global null with a unanimous five-gate battery,
≈0 survivors is the *expected* result, and we got 0: that is calibration, not a
lucky catch. Separately, the individual gate lets through **6 of 100** — right on
the ≈5 expected at α = 0.05, the court's own declared error rate showing up on cue.

What the demo does **not** show: the court's *power* to **pass a genuine alpha**.
An always-reject stub would score the identical 0/100. Type-II (false-negative)
behavior is unmeasured in v0.1. Proving the court can *clear* a real signal — not
just condemn noise — is later work, and we don't claim it here.

### The five gates

The demo's verdict battery is unanimous — one rejection kills the candidate. Each
row is reimplemented from public papers. Note the gates are **not** equally
decisive here, and the table says so; the flip-faithful, selection-correcting gate
is the pool-max noise control.

| Gate | What it corrects for | Result on the accused | Note |
|---|---|---|---|
| **FDR (Benjamini–Yekutieli)** | False-discovery rate across the family under dependence | fail — 0 discoveries in the family (k\*=0) | p = 0.0077 already fails on family size alone (BH rank-1 bar = 0.05/100 = 5e-4); BY's dependency factor c(N)=5.19 tightens it further to ~1e-4 |
| **DSR (Deflated Sharpe)** | Sharpe inflated by the number of trials and their correlation | fail (z = −5.17) | **weak here:** accused is a flipped contrarian pick (t < 0), and DSR is one-sided, so it rejects near-automatically; ρ̂ was ill-conditioned (T = 480 < ½·100·99), so the correlation term is effectively inert (N̂ ≈ N) |
| **PBO (CSCV)** | Probability the "best" config is overfit, via combinatorial CV | fail (φ = 0.47) | null-like: pure noise centers φ ≈ 0.5, and pass requires ≤ 0.2. Internal selection is *signed*; naive selection was \|t\|-based |
| **Noise control — pool-max** | Does the best-of-search winner beat best-of-noise? | **fail (p̂ = 0.575)** | the honest, flip-faithful gate — 114/199 noise winners beat it |
| **Noise control — individual** | Single-factor sanity check (calibration slot) | pass (p̂ = 0.015) | — |

(In court vocabulary, **fail** means "not believed / not a discovery" — the
opposite polarity from a statistician's "reject H₀". The battery finds the accused
guilty of being noise.) Literature notes: FDR → `docs/research/bhy.md`, DSR →
`docs/research/dsr.md`, PBO → `docs/research/pbo-cscv.md`; the noise control's
hand-computed vectors live in `docs/design/noise-control.md`.

### Three iron laws

1. **Three things it will never do.** No backtest engine (it reuses
   [qlib](https://github.com/microsoft/qlib) and eats only return/IC series); no
   idea generator (the generation side is deliberately stubbed); and no code,
   data, or identifiers carried over from any prior employer — every statistical
   method is rewritten from public literature and cited.
2. **Kernel/market decoupling.** `court/` may not import any market-specific
   code. Calendars, price limits, and universe definitions live only in
   `adapters/`. A subprocess test asserts this as an executable invariant.
3. **No victory theater (`禁赢学`).** Results are reported as they are. Null
   archives get the same documentation weight as survivors. Nothing half-finished
   is hung on the wall — including the boundary in the section above.

### Honesty by construction (pre-registration)

The demo's design document *is* its pre-registration book: the master seed
(20260710), the decision lines, and the unanimous-verdict aggregation were all
fixed **before the first run**. The winner's |t| = 2.67 landed right at the
pre-registered median (≈2.70) inside the "typically 2.5–3.2" band — we did not
sift seeds to manufacture a scary t near 3. A survivor's verdict text was written
*before* any factor could earn it, so a survivor would be the court declaring its
own error rate, not a surprise. A 20-seed sweep appendix (seeds
20260711–20260730) can be run to show the headline is typical rather than
cherry-picked.

### Quickstart

```sh
pip install -e .
python -m examples.killer_demo          # full pipeline: data → 100 factors → naive pick → court → figure
```

The run downloads the factor data (community
[investment_data](https://github.com/chenditc/investment_data), tag 2026-07-05,
csi300 PIT universe), builds the 100 noise factors, performs the naive selection,
runs the five-gate battery, and writes a four-part verdict report plus the figure
above to `examples/killer_demo/out/`. On macOS, data access pins `kernels=1`. On a
fixed machine with locked dependencies the run is deterministic (byte-identical
figure and config; ledger identical line-by-line once real timestamps are
stripped).

### How it was built

alpha-court applies its own "don't fool yourself" principle to its construction.
Two different models divide the labor: **Claude** as commander/referee (designs
the contracts, cuts self-contained tickets, adjudicates deliveries) and **grok**
as headless workers (read each ticket verbatim, build in an isolated git worktree,
return a facts-only receipt). The evaluator stays outside the worker loop — workers
never grade their own output — and every delivery is re-run independently and
cross-examined by an adversarial panel.

Two things worth stating plainly, because the discipline cuts both ways:

- **A "worker wins" precedent.** One printed recursion in the literature — the
  BY-adjusted-p form as restated in Harvey–Liu–Zhu (2016) — is internally
  inconsistent, and the worker's implementation was the only self-consistent one.
  The root cause was *upstream*: the commander's own research note had transcribed
  the printed (wrong) form into the contract; the panel was forced to overrule the
  contract, not the worker. When the documents were wrong and the code was right,
  the code won.
- **The referee is not exempt.** At the v0.1 milestone the roles were reversed:
  grok adversarially reviewed the commander and graded it a **B**, with three
  standing criticisms (post-hoc rule changes, a dispatch bridge whose own bugs
  undercut the referee's strictness, and asymmetric accountability). Separately,
  the referee twice wrongly flagged a worker on fixtures it had misremembered.
  Those criticisms are now encoded as rules in two skills — a start, not a closed
  loop. The authoritative record is `TIMELINE.md` and the raw meta-review under
  `.scratch/dispatch/`, not this paragraph.

Reworks were attributed per the constitution's three-way scheme —
worker-fault / contract-fault / referee-fault — with CLI-infrastructure failures
(e.g. a headless run that hung) tracked as a separate no-fault category.

### Roadmap

- **v0.1 (done)** — the `court/` kernel (trial ledger, DSR, PBO-CSCV, BHY + noise
  control), a qlib-cn adapter, and the killer demo. End-to-end, honestly reported,
  0/100 survivors.
- **v0.2** — `harness/`: a governance layer that welds the court onto an idea-mining
  agent (pre-registration gate, referee governance, dispatch generalized beyond one CLI).
- **v0.3** — `gates/`: a library of cheap razors (degenerate identities, in-pool
  redundancy, magnitude-vs-turnover, single-year luck heatmaps) and a fuller null museum.

### Status & limitations

v0.1 is a minimal, honest core, not a product.

- **Power untested** — see "What the 0/100 does not prove" above: only rejection
  of constructed noise is demonstrated.
- **Gross paper series** — no transaction costs, no market impact.
- **Single market / window** — csi300, 2024–2026.
- **The noise null is not free** — circular time-shifts have a seam, are not
  style-neutral, and common offsets correlate the p̂ across candidates (variance
  above binomial, disclosed in `docs/design/noise-control.md`). The pool-max gate
  is White's reality-check *logic* (White 2000), not a stationary-bootstrap
  implementation of it.
- **Determinism** is promised only on a fixed machine with locked dependencies,
  not across platforms.

This is by design: prove the court's logic on constructed noise first, then earn
the right to harder claims.

### License

See `.claude/skills/SOURCES.md` for vendored third-party skill provenance (MIT).
Project license: TBD.

---

## 中文

### 一张图讲清的杀手 demo

我们造了 **100 个纯噪声因子**——构造上零信息的 AR(1) 随机序列。然后让一个天真的
研究员做天真研究员会做的事：扫完 100 个（指标 RankIC），留下最好看的那个。它"发现"
了 `volatility_lb150_v14`，**|t| = 2.67，裸 p = 0.0077**——过了教科书单次检验 5% 关，
单独拎出来像真的。

然后我们把它送上法庭。**100 个，0 个幸存。**

红线是那个"发现"。蓝色直方图是噪声零假设下的**池最大**统计量：对全 100 因子面板做
199 次零信息循环时移，每次取 100 个因子的 max |t|。**这 199 个"从噪声里挑出的赢家"里，
有 114 个比被告更强**（池最大 p̂ = 0.575，用 Phipson & Smyth 加一估计）。单独看，因子
像真的（|t| = 2.67 ≫ 1.96，那条虚线是单次检验关）；放回它真正诞生的"百里挑一"搜索里，
它就是中不溜。整个论点浓缩在这一个数里——*在这里，罪在选择，不在 t 值。*

"在这里"是承重词：噪声 RankIC 序列构造上无自相关，所以 iid-SE 的 t 是对的，膨胀全部
来自 100 里取 max 的选择。真实因子研究里 t 值本身也常常是罪（重叠、自相关的收益）——
这正是内核也提供 Newey–West SE 的原因。本 demo 是刻意把选择效应单独拎出来。

最有教育意义的细节就藏在这个区分里。被告**过了自己的个体噪声关**——对*它自己*的
得分面板做 199 次循环时移，只有 2 次比它强（个体 p̂ = 0.015）。当作单个因子看它显著；
拿去跟 199 个*百里挑一*的噪声赢家比就现形。校正你看不见的那层选择，正是法庭的本职。

### 这个 0/100 证明了什么、没证明什么

这是个 `禁赢学` 项目，所以诚实边界放最前面。demo 证明的是法庭**正确驳回了构造的
纯噪声**——它的 *size*（假阳性控制）。在全局零假设 + 五道关全票制下，≈0 幸存是*预期*
结果，我们得到 0：这是校准，不是撞运气抓住的。另外，个体关放行了 **6/100**——正好落在
α = 0.05 下预期的 ≈5，法庭自己申报的错误率如约现身。

demo **没有**证明的：法庭**放行真 alpha** 的 *power*。一个永远驳回的 stub 会得到
一模一样的 0/100。二类错误（假阴性）行为在 v0.1 未测。证明法庭能*放过*一个真信号——
而不只是给噪声定罪——是后续的活，我们在这里不作此主张。

### 五道关

demo 的判决电池是全票制——一票驳回即出局。每一行都从公开论文重新实现。注意这几道关
在本例里**并不等强**，表里如实标出；真正 flip-faithful、校正选择效应的是池最大噪声关。

| 关卡 | 校正什么 | 被告结果 | 备注 |
|---|---|---|---|
| **FDR（Benjamini–Yekutieli）** | 相依结构下全家族的错误发现率 | 未过——全家零发现（k\*=0） | 裸 p = 0.0077 单靠家族规模就已出局（BH rank-1 关 = 0.05/100 = 5e-4）；BY 相依因子 c(N)=5.19 再把关收紧到 ~1e-4 |
| **DSR（通缩夏普 / Deflated Sharpe）** | 被试验次数与相关性抬高的 Sharpe | 未过（z = −5.17） | **本例偏弱：** 被告是翻号的反向因子（t < 0），DSR 单侧，故近乎自动驳回；ρ̂ 病态（T = 480 < ½·100·99），相关性项实际失效（N̂ ≈ N） |
| **PBO（CSCV）** | 组合交叉验证下"最优"配置过拟合的概率 | 未过（φ = 0.47） | 近噪声：纯噪声中心 φ ≈ 0.5，过关需 ≤ 0.2。内部选择是*有符号*的；裸选择按 \|t\| |
| **噪声对照 — 池最大** | 搜索赢家能否胜过噪声赢家？ | **未过（p̂ = 0.575）** | 诚实、flip-faithful 的那道关——114/199 个噪声赢家比它强 |
| **噪声对照 — 个体** | 单因子健全性检查（校准位） | 通过（p̂ = 0.015） | — |

（法庭术语里，**未过** = "不被相信 / 不是发现"，跟统计学"拒绝 H₀"极性相反。电池判定
被告"是噪声"这项罪成立。）文献笔记：FDR → `docs/research/bhy.md`、DSR →
`docs/research/dsr.md`、PBO → `docs/research/pbo-cscv.md`；噪声对照的手算向量在
`docs/design/noise-control.md`。

### 三条铁律

1. **三不做。** 不做回测引擎（复用 [qlib](https://github.com/microsoft/qlib)，只吃
   收益/IC 序列）；不做 idea 生成器（生成端刻意 stub 化）；不搬任何前雇主的代码、
   数据或标识——每个统计方法都从公开文献重写并逐条引用。
2. **内核与市场解耦。** `court/` 不得 import 任何市场特异代码。日历、涨跌停、宇宙
   定义只活在 `adapters/`。一个子进程测试把这条铁律写成可执行断言。
3. **禁赢学。** 结果如实呈现。null 归档与幸存者享同等文档待遇。墙上不挂任何半成品——
   包括上一节那条边界。

### 诚实源自构造（预注册）

demo 的设计文档**就是**它的预注册书：主种子（20260710）、判决线、全票制聚合，全部在
**首跑之前**钉死。赢家的 |t| = 2.67 正落在预注册的中位（≈2.70）上、位于"典型 2.5–3.2"
区间内——我们没有筛种子去凑一个接近 3、看起来吓人的 t。幸存者的判词在任何因子有资格
拿到它*之前*就已写好，所以一个幸存者会是法庭申报自己的错误率，而非意外。可以跑一个
20 种子扫描附录（种子 20260711–20260730）来证明头版是典型值、而非精挑细选。

### 快速开始

```sh
pip install -e .
python -m examples.killer_demo          # 全链：取数 → 100 因子 → 裸选择 → 法庭 → 出图
```

这条命令会下载因子数据（社区
[investment_data](https://github.com/chenditc/investment_data)，tag 2026-07-05，
csi300 PIT 宇宙），构造 100 个噪声因子，执行裸选择，跑五道关电池，把四部判决报告和
上面那张图写到 `examples/killer_demo/out/`。macOS 上取数须钉 `kernels=1`。在固定机器 +
锁定依赖下运行确定（图与配置逐字节一致；台账在剥掉真实时间戳后逐行一致）。

### 它是怎么造出来的

alpha-court 把它自己的"不骗自己"原则施加于自身的构造过程。两个不同的模型分工：
**Claude** 当指挥官 / 裁判（设计契约、切自包含的票、验收交付），**grok** 当无头工人
（逐字读票、在隔离 git worktree 施工、交一份只含事实的收据）。评估器留在工人环外——
工人从不给自己打分——每次交付都由裁判独立复跑、由对抗面板交叉质询。

两件事值得直说，因为纪律是双向的：

- **一起"工人胜诉"判例。** 文献里一处印刷递归——BY 调整 p 值在 Harvey–Liu–Zhu
  (2016) 中的转述形式——自相矛盾，而工人的实现是唯一自洽的。根因在*上游*：是指挥官
  自己的研究笔记把印刷的（错误）形式抄进了契约；面板被迫推翻的是契约，不是工人。
  当文档错、代码对时，代码赢。
- **裁判并不豁免。** v0.1 里程碑时角色反转：grok 对指挥官做对抗性评审，打了 **B**，
  三条留存批评（事后改规则、一座 bug 反噬了裁判自身严苛的派单桥、问责不对称）。另外，
  裁判自己曾两次凭记错的 fixture 误判工人。这些批评现在被写进两个技能的规则里——是
  起点，不是闭环。权威记录是 `TIMELINE.md` 和 `.scratch/dispatch/` 下的 meta-review
  原文，不是这一段。

返工按宪法的三分法归因——worker-fault / contract-fault / referee-fault——CLI 基建
故障（如一次僵死的无头运行）另记为无责类别。

### 路线图

- **v0.1（已完成）**——`court/` 内核（trial ledger、DSR、PBO-CSCV、BHY + 噪声对照）、
  一个 qlib-cn adapter、以及杀手 demo。端到端、如实呈报、0/100 幸存。
- **v0.2**——`harness/`：把法庭焊到一个挖因子 agent 上的治理层（预注册闸、referee
  治理、派单泛化到不止一个 CLI）。
- **v0.3**——`gates/`：一个便宜刀刀片库（恒等式退化、池内冗余、量级 vs 换手、单年
  运气热力图）以及更完整的 null 博物馆。

### 现状与边界

v0.1 是一个最小、诚实的内核，不是产品。

- **Power 未测**——见上文"这个 0/100 没证明什么"：只演示了对构造噪声的驳回。
- **无成本纸面序列**——不算交易成本、不算市场冲击。
- **单一市场 / 窗口**——csi300，2024–2026。
- **噪声零假设不是白来的**——循环时移有接缝、非风格中性，且公共偏移让 p̂ 在候选间
  相关（方差高于二项，`docs/design/noise-control.md` 已申报）。池最大关用的是 White
  reality-check 的*逻辑*（White 2000），不是它的 stationary-bootstrap 原版实现。
- **确定性**只在固定机器 + 锁定依赖下承诺，不跨平台。

这是刻意的：先在构造的噪声上证明法庭的逻辑，再挣得对更难主张的发言权。

### 许可

第三方技能的来源见 `.claude/skills/SOURCES.md`（MIT）。项目许可：待定。
