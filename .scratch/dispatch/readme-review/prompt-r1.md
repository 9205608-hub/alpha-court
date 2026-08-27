# 任务：对抗性评审 alpha-court 的公开 README（草稿 v1）

你是 grok-4.5。在这个项目（alpha-court）里，你既是"施工工人"（14 张票、26+ 次无头运行），
也在 v0.1 里程碑做过一次角色反转的 meta-review——你评审了"指挥官"（Claude）的全部工作，
打了 **B**，三条批评是：① 事后立法（多张 rework 以"工树契约 stale + 本单勘误覆盖"改规则）；
② 派单桥与裁判人设不匹配（两次隔离/绊线事故说明工具未生产级就上重型对抗审）；
③ 票面自相矛盾与弱 AC，返工归因被污染。

现在指挥官写了这个项目的**公开 README**（要放上 GitHub、给量化研究员看的门面），
请你做一次**不留情面的对抗性评审**。你评审的是这份 README 文案本身——它是否诚实、
准确、经得起一个挑剔的量化研究员逐行读。

## 你的工作区（只读，用来核对事实）

你的 `cwd` 是本仓库在 HEAD（c7a0d0f，v0.1 完工）的一个只读检出。**不要修改任何文件**，
只读取、核对、然后把评审意见作为文本输出。可交叉核对的真实产物：

- `examples/killer_demo/out/report.md` — demo 的四部判决报告（头版数字、停尸表、被告尸检、
  校准附录的权威来源）
- `examples/killer_demo/out/run_config.json`、`out/figure.png` — 配置与那张 hero 图
- `docs/research/{dsr,pbo-cscv,bhy}.md` — 三份统计文献研读笔记
- `docs/design/killer-demo.md` — demo 的预注册书（种子/判决线/聚合先于首跑钉死）
- `TIMELINE.md`、`.scratch/v0.1/map.md`、`.scratch/v0.1/issues/*.md` — 全程流水与 20 张票判词
- `CONTEXT.md` — trial/hypothesis/verdict/null jury 的术语表
- `.scratch/dispatch/meta-review-commander/raw.json` — 你上次那份 B 级 meta-review 原文

**注意**：磁盘上的 `README.md` 是旧占位符，不是本次评审对象。评审对象是下面【README 草稿】
里粘贴的全文（指挥官刚写、尚未落盘到 HEAD）。请以粘贴版为准。

## 评审维度（每条都要有具体证据：引用 README 原句 + 对照真实产物的文件/数字）

1. **事实准确性**：README 里的每个数字/主张，跟 `report.md` 等真实产物对得上吗？
   逐一核对：|t|=2.67、naive p=0.0077、pool-max p̂=0.575、114/199、individual p̂=0.015、
   6/100 过个体关、DSR z=−5.17、PBO φ=0.47、20 票、26+ 次运行、9 次返工、158 测试、~10000 行。
   有没有编造、四舍五入误导、或张冠李戴？
2. **禁赢学 / 有没有过度包装**：这份 README 是如实呈现还是在自吹？特别是——
   它有没有把你那份 B 级 meta-review 的批评**洗白或藏起来**？"How it was built"那节把角色反转
   评审写成了卖点，这是诚实还是自我表扬？"worker wins"判例的叙述公允吗（还是在给指挥官贴金）？
   有没有把"构造噪声上的 demo"说得像"证明了能抓真 alpha"这种越界主张？
3. **统计框架能否扛住挑剔量化研究员**：核心主张"the selection is the bug, not the t-statistic"、
   pool-max 那张图的解读（"114/199 纯噪声陪审团比它强"）、五道关的描述——统计上站得住吗？
   有没有措辞会让一个 Renaissance/Two Sigma 级别的人当场皱眉？比如：把 FDR 结果写成"reject"
   但括注"family c-factor moves the bar"是否准确？pool-max 与 White reality check 的类比恰当吗？
   循环时移陪审团当零分布，有没有被过度简化？
4. **受众契合与可读性**：首屏（一张图 + 0/100）抓得住量化研究员吗？哪里啰嗦、哪里术语
   没解释、哪里该砍？中英双语两版是否等价、有无一版明显更弱？
5. **该砍该补**：最该删的 3 处、最该补的 3 处。

## 输出要求

中文，纯文本（不要 JSON）。诚实刻薄优于礼貌空洞——你上次的 meta-review 就是这个调性，保持。
结构建议：先给一个总评（这份 README 能不能作为公开门面：可用 / 需改 / 重写，以及一句话理由），
然后按上面五个维度逐条给证据化意见，最后给一个"如果只改 3 处，改哪 3 处"的清单。
如果你发现指挥官又在犯你 meta-review 里点过的老毛病（自我表扬、避重就轻、把败绩写成胜绩），
直接点名。

---

【README 草稿 v1，评审对象】

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
do: scan all 100 and keep the best-looking one. It "discovered"
`volatility_lb150_v14`, with **|t| = 2.67, naive p = 0.0077** — a result that
clears the textbook 5% bar and would look publishable in isolation.

Then we put it on trial. **0 of 100 survived.**

![Noise-control pool-max null vs naive discovery](examples/killer_demo/out/figure.png)

The red line is the "discovery." The blue histogram is the same statistic
computed on 199 information-free jurors (circular time-shifts of the candidate's
own score panel). **114 of those 199 pure-noise jurors beat it.** Seen alone, the
factor looks real (|t| = 2.67 ≫ 1.96, the dashed single-test bar). Put back into
the "best of 100" context it was actually born in, it evaporates: pool-max
p̂ = 0.575. That is the whole thesis in one number — *the selection is the bug,
not the t-statistic.*

The most instructive detail: the accused **passes its own individual
noise-control gate** (p̂ = 0.015) and still dies, because the court also asks the
question the researcher never did — *how does your best-of-100 winner compare to
199 best-of-noise winners?* Correcting for the selection you can't see is exactly
the job.

### Why this exists

A quant researcher scanning hundreds of factor variants faces a machine for
manufacturing false positives: multiple testing, in-sample selection, and
overfit backtests all conspire to make noise look like alpha. Backtest engines
happily report the Sharpe of whatever you feed them. They do not tell you that
the winner of a 100-way search needs a very different bar than a single
pre-specified bet.

alpha-court is the missing second opinion. It does **not** run backtests and it
does **not** generate ideas — it consumes the return/IC series a backtest already
produced and rules on whether the finding is believable after honest correction
for how it was found.

### The five gates

The demo's verdict battery is unanimous — one rejection kills the candidate.
Each statistic is reimplemented from public papers, with a research note that
carries hand-computed test vectors straight into the test suite.

| Gate | What it corrects for | Result on the accused | Literature |
|---|---|---|---|
| **FDR (Benjamini–Yekutieli)** | False-discovery rate across the whole family under dependence | reject (p = 0.0077, but the family c-factor moves the bar) | `docs/research/bhy.md` |
| **DSR (Deflated Sharpe Ratio)** | Sharpe inflated by the number of trials and their correlation | reject (z = −5.17) | `docs/research/dsr.md` |
| **PBO (CSCV)** | Probability the "best" config is overfit, via combinatorial cross-validation | reject (φ = 0.47 ≫ 0.2) | `docs/research/pbo-cscv.md` |
| **Noise control — pool-max** | Does the best-of-search winner beat best-of-noise? (White's reality-check logic) | **reject (p̂ = 0.575)** | `docs/research/` (Phipson–Smyth, White) |
| **Noise control — individual** | Single-factor sanity check (calibration slot) | pass (p̂ = 0.015) | — |

Across all 100 factors, exactly **6 pass the individual gate** — right on the
≈5 expected at α = 0.05. That is calibration evidence, not a leak: the court's
own declared error rate showing up on cue.

### Three iron laws

1. **Three things it will never do.** No backtest engine (it reuses
   [qlib](https://github.com/microsoft/qlib) and eats only return/IC series); no
   idea generator (the generation side is deliberately stubbed); and no code,
   data, or identifiers carried over from any prior employer — every statistical
   method is rewritten from public literature and cited.
2. **Kernel/market decoupling.** `court/` may not import any market-specific
   code. Calendars, price limits, and universe definitions live only in
   `adapters/`. A subprocess test asserts this as an executable invariant.
3. **No victory theater.** Results are reported as they are. Null archives get
   the same documentation weight as survivors. Nothing half-finished is hung on
   the wall.

### Honesty by construction (pre-registration)

The demo's design document *is* its pre-registration book: the master seed
(20260710), the decision lines, and the unanimous-verdict aggregation were all
fixed **before the first run**. The winner's |t| = 2.67 landed dead-center of the
pre-declared "typically 2.5–3.2" band — we did not sift seeds to manufacture a
scary-looking t near 3. A survivor's verdict was written *before* any factor
could earn it, so a survivor would be the court declaring its own error rate, not
a surprise. A 20-seed sweep appendix (seeds 20260711–20260730) can be run to show
the headline is typical rather than cherry-picked.

### Quickstart

```sh
pip install -e .
python -m examples.killer_demo          # full pipeline: data → 100 factors → naive pick → court → figure
```

The run downloads the factor data (community
[investment_data](https://github.com/chenditc/investment_data), tag 2026-07-05,
csi300 PIT universe), builds the 100 noise factors, performs the naive selection,
runs the five-gate battery, and writes a four-part verdict report plus the figure
above to `examples/killer_demo/out/`. On macOS, data access pins `kernels=1`.
The run is deterministic on a fixed machine and locked dependencies (byte-identical
figure and config; ledger identical line-by-line once real timestamps are stripped).

### How it was built (and why that matters)

alpha-court is itself an experiment in *not fooling yourself* — applied to its own
construction. Two different models divide the labor:

- **Claude (commander / referee)** designs the contracts, cuts self-contained
  implementation tickets, and adjudicates deliveries. The evaluator stays outside
  the worker loop: workers never grade their own output.
- **grok (headless workers)** read each ticket verbatim, build in an isolated git
  worktree, and return a schema-constrained receipt of facts — not a
  self-evaluation.

Every delivery is re-run independently by the referee and cross-examined by an
adversarial panel. This caught real defects, including **two errata in the
published papers themselves** — one where the printed Benjamini–Yekutieli
recursion is internally inconsistent, and the worker's implementation turned out
to be the only self-consistent form. When the documents were wrong and the code
was right, the code won (recorded as a "worker wins" precedent).

The sharpest instance of the discipline: at the v0.1 milestone the roles were
**reversed** — grok adversarially reviewed the commander's entire body of work,
graded it a **B**, and its three top criticisms (post-hoc rule changes, a
dispatch bridge whose bugs undercut the referee's own strictness, and asymmetric
accountability) were converted into hard rules in two self-authored skills. A
court that refuses to fool itself has to accept the same treatment it hands out.

Tallies for v0.1: 20 tickets closed, 26+ headless worker runs, 9 reworks
(attributed three ways: worker-fault / contract-fault / infra-fault), a 19-verifier
adversarial panel, 2 literature errata, ~10,000 lines, 158 tests green.

### Roadmap

- **v0.1 (done)** — the `court/` kernel (trial ledger, DSR, PBO-CSCV, BHY + noise
  control), a qlib-cn adapter, and the killer demo. End-to-end, honestly reported,
  0/100 survivors.
- **v0.2** — `harness/`: a governance layer that welds the court onto an idea-mining
  agent (pre-registration gate, referee governance, dispatch generalized beyond one CLI).
- **v0.3** — `gates/`: a library of cheap razors (degenerate identities, in-pool
  redundancy, magnitude-vs-turnover, single-year luck heatmaps) and a fuller null museum.

### Status & limitations

v0.1 is a minimal, honest core, not a product. The demo runs on a **gross paper
series** (no transaction costs, no market impact), a single market (csi300), and a
2024–2026 window. Determinism is promised only on a fixed machine with locked
dependencies, not across platforms. This is by design: prove the court's logic on
constructed noise first, then earn the right to harder claims.

### License

See `.claude/skills/SOURCES.md` for vendored third-party skill provenance (MIT).
Project license: TBD.

---

## 中文

### 一张图讲清的杀手 demo

我们造了 **100 个纯噪声因子**——构造上零信息的 AR(1) 随机序列。然后让一个天真的
研究员做天真研究员会做的事：扫完 100 个，留下最好看的那个。它"发现"了
`volatility_lb150_v14`，**|t| = 2.67，裸 p = 0.0077**——过了教科书 5% 关，单独拎出来
像是能发论文的结果。

然后我们把它送上法庭。**100 个，0 个幸存。**

红线是那个"发现"。蓝色直方图是同一个统计量在 199 个零信息陪审团上的取值（被告自己
得分面板的循环时移）。**这 199 个纯噪声陪审团里，有 114 个比它更强。** 单独看，因子
像真的（|t| = 2.67 ≫ 1.96，那条虚线是单次检验关）；放回它真正诞生的"百里挑一"语境，
它就现形了：池最大 p̂ = 0.575。整个论点就浓缩在这一个数里——*罪在选择，不在 t 值。*

最有教育意义的细节：被告**过了自己的个体噪声关**（p̂ = 0.015）却依然被驳回，因为法庭
还问了研究员从没问过的问题——*你从 100 个里挑出的赢家，跟 199 个从噪声里挑出的赢家
比，如何？* 校正你看不见的那层选择，正是法庭的本职。

### 为什么需要它

一个扫上百个因子变体的量化研究员，面对的是一台批量制造假阳性的机器：多重检验、
样本内选择、过拟合回测，合谋把噪声打扮成 alpha。回测引擎乐于报告你喂给它的任何东西
的 Sharpe，却不会告诉你：一个百路搜索的赢家，需要的关卡跟一个事先指定的单注，是
天差地别的两把尺子。

alpha-court 就是那个缺失的第二意见。它**不做回测**，也**不生成 idea**——它吃回测
已经产出的收益/IC 序列，然后裁定：在为"你是怎么找到它的"做了诚实校正之后，这个发现
还值不值得信。

### 五道关

demo 的判决电池是全票制——一票驳回即出局。每个统计量都从公开论文重新实现，配一份
研究笔记，把手算的测试向量直通进测试套件。

| 关卡 | 校正什么 | 被告结果 | 文献 |
|---|---|---|---|
| **FDR（Benjamini–Yekutieli）** | 相依结构下全家族的错误发现率 | 驳回（p = 0.0077，但家族 c 因子抬高了关卡） | `docs/research/bhy.md` |
| **DSR（收缩 Sharpe）** | 被试验次数与相关性抬高的 Sharpe | 驳回（z = −5.17） | `docs/research/dsr.md` |
| **PBO（CSCV）** | 组合交叉验证下"最优"配置过拟合的概率 | 驳回（φ = 0.47 ≫ 0.2） | `docs/research/pbo-cscv.md` |
| **噪声对照 — 池最大** | 搜索赢家能否胜过噪声赢家？（White reality-check 逻辑） | **驳回（p̂ = 0.575）** | `docs/research/`（Phipson–Smyth、White） |
| **噪声对照 — 个体** | 单因子健全性检查（校准位） | 通过（p̂ = 0.015） | — |

100 个因子里，恰好 **6 个过了个体关**——正好落在 α = 0.05 下预期的 ≈5 附近。这不是
漏洞，是校准证据：法庭自己申报的错误率如约现身。

### 三条铁律

1. **三不做。** 不做回测引擎（复用 [qlib](https://github.com/microsoft/qlib)，只吃
   收益/IC 序列）；不做 idea 生成器（生成端刻意 stub 化）；不搬任何前雇主的代码、
   数据或标识——每个统计方法都从公开文献重写并逐条引用。
2. **内核与市场解耦。** `court/` 不得 import 任何市场特异代码。日历、涨跌停、宇宙
   定义只活在 `adapters/`。一个子进程测试把这条铁律写成可执行断言。
3. **禁赢学。** 结果如实呈现。null 归档与幸存者享同等文档待遇。墙上不挂任何半成品。

### 诚实源自构造（预注册）

demo 的设计文档**就是**它的预注册书：主种子（20260710）、判决线、全票制聚合，全部在
**首跑之前**钉死。赢家的 |t| = 2.67 落在预先申报的"典型 2.5–3.2"区间正中——我们没有
筛种子去凑一个接近 3、看起来吓人的 t。幸存者的判词在任何因子有资格拿到它*之前*就已
写好，所以一个幸存者会是法庭申报自己的错误率，而非意外。可以跑一个 20 种子扫描附录
（种子 20260711–20260730）来证明头版是典型值、而非精挑细选。

### 快速开始

```sh
pip install -e .
python -m examples.killer_demo          # 全链：取数 → 100 因子 → 裸选择 → 法庭 → 出图
```

这条命令会下载因子数据（社区
[investment_data](https://github.com/chenditc/investment_data)，tag 2026-07-05，
csi300 PIT 宇宙），构造 100 个噪声因子，执行裸选择，跑五道关电池，把四部判决报告和
上面那张图写到 `examples/killer_demo/out/`。macOS 上取数须钉 `kernels=1`。在固定机器
和锁定依赖下运行确定（图与配置逐字节一致；台账在剥掉真实时间戳后逐行一致）。

### 它是怎么造出来的（以及为什么这重要）

alpha-court 本身就是一场"不骗自己"的实验——施加于它自己的构造过程。两个不同的模型
分工：

- **Claude（指挥官 / 裁判）** 设计契约、切自包含的施工票、验收交付。评估器留在工人
  环外：工人从不给自己的产出打分。
- **grok（无头工人）** 逐字读票、在隔离 git worktree 施工、交一份 schema 约束的事实
  收据——而非自评。

每次交付都由裁判独立复跑、由对抗面板交叉质询。这抓出了真实缺陷，包括**发表论文自身
的两处勘误**——其中一处，印刷版的 Benjamini–Yekutieli 递归自相矛盾，而工人的实现反而
是唯一自洽的形式。当文档错、代码对时，代码赢（记为一起"工人胜诉"判例）。

纪律最锋利的一次：v0.1 里程碑时角色**反转**——grok 对指挥官的全部工作做了一次对抗性
评审，打了 **B**，它排前三的批评（事后改规则、一座 bug 反噬了裁判自身严苛的派单桥、
问责不对称）被转化成两个自研技能里的硬规则。一座拒绝骗自己的法庭，必须接受它施加给
别人的同一套待遇。

v0.1 战绩：20 张票全关、26+ 次无头工人运行、9 次返工（三分归因：工人 / 契约 / 基建）、
一个 19 人的对抗验证面板、2 处文献勘误、约 10,000 行、158 测试全绿。

### 路线图

- **v0.1（已完成）**——`court/` 内核（trial ledger、DSR、PBO-CSCV、BHY + 噪声对照）、
  一个 qlib-cn adapter、以及杀手 demo。端到端、如实呈报、0/100 幸存。
- **v0.2**——`harness/`：把法庭焊到一个挖因子 agent 上的治理层（预注册闸、referee
  治理、派单泛化到不止一个 CLI）。
- **v0.3**——`gates/`：一个便宜刀刀片库（恒等式退化、池内冗余、量级 vs 换手、单年
  运气热力图）以及更完整的 null 博物馆。

### 现状与边界

v0.1 是一个最小、诚实的内核，不是产品。demo 跑在**无成本纸面序列**上（不算交易成本、
不算市场冲击）、单一市场（csi300）、2024–2026 窗口。确定性只在固定机器 + 锁定依赖下
承诺，不跨平台。这是刻意的：先在构造的噪声上证明法庭的逻辑，再挣得对更难主张的
发言权。

### 许可

第三方技能的来源见 `.claude/skills/SOURCES.md`（MIT）。项目许可：待定。

