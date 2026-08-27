# v0.1 内核 + 杀手 demo — wayfinder map

Label: wayfinder:map
Created: 2026-07-10

## Destination

v0.1 端到端可演示：`examples/` 杀手 demo 真跑通——100 个纯噪声因子 → 裸选择"发现" t≈3 假 alpha → 法庭全部驳回，一图讲清存在理由。支撑它的 `court/` 四件套（trial ledger / DSR / PBO-CSCV / BHY+噪声对照）与 qlib-cn adapter 全部实现、统计公式逐条对上文献引用、结果如实呈现。地图走完 = 每一块要么已验收落地，要么有一张完全指定、可派单的实现票。**[2026-07-11 地图关闭：20/20 票全部 resolved，v0.1 完工]**

## Notes

- **硬约束（宪章铁律，每张票都受约束）**：
  1. 三不做——不做回测系统（复用 qlib，只吃收益/IC 序列）；不做 idea 生成器（生成端 stub）；不搬任何前实习单位内部代码/数据/标识，统计方法从公开文献干净重写并逐条引用（DSR: Bailey & López de Prado 2014；PBO: CSCV, Bailey et al.；多重检验: Benjamini-Hochberg-Yekutieli）。
  2. 解耦——`court/` 不得 import 任何市场特异代码；日历、ST/涨跌停、宇宙定义全部关在 `adapters/`。
  3. 禁赢学——demo 结果如实呈现，null 归档与幸存者同等待遇。
- **本 effort 携带执行**（覆盖 wayfinder 默认的 plan-don't-do）：实现类 task 票经 M0 指挥→工人桥派给 grok 无头 CLI；指挥 session 当 referee 验收，工人不给自己打分。决策票（grilling/prototype）仍是 HITL，留给用户在场的 session。
- **技能路由**：决策票用 /grilling + /domain-modeling；文献票用 /research；spec 用 /grill-with-docs → /to-spec → /to-tickets；施工票内含 /tdd + /code-review。
- **语言**：票面中文为主（内部工作文档）；代码、docstring、对外文档英文。

## Decisions so far

<!-- one line per closed ticket: gist + link -->

- [01 M0 指挥→工人桥](issues/01-m0-commander-worker-bridge.md) — 桥建成：ticket 模板 + schema 硬约束收据 + dispatch.sh（指挥侧 `git worktree add` + `--cwd` 强制隔离，事后绊线）；首跑暴露 grok `--worktree` headless 失效并修复；探针票 E2E 全绿。
- [02 工程底座](issues/02-repo-engineering-scaffold.md) — grok 工人交付、referee 独立复核收货：pyproject（court 依赖白名单 numpy/pandas/scipy）+ 四层转包 + 冒烟测试把解耦铁律写成可执行断言。
- [09 qlib-cn 数据可得性研究](issues/09-qlib-cn-data-research.md) — 官方包停更 2020-09；用社区包 chenditc/investment_data（2026-07-05, 813M, 日历到 2026-07-03）；demo 建议 csi300 + 2024-07→2026-07 窗口；macOS 取数须 kernels=1。
- [04 DSR 文献研读](issues/04-dsr-literature.md) — `docs/research/dsr.md`：PSR/E[max SR]/DSR 全公式带式号+手算测试向量（对抗面板重算全过）；Eq.(1) 是 N≫1 的 EVT 近似；病态条件 T<½M(M−1)。
- [05 PBO/CSCV 文献研读](issues/05-pbo-cscv-literature.md) — `docs/research/pbo-cscv.md`：CSCV 伪代码 + S=4 手算向量；抓出论文两处勘误（12,780、Alg 2.3(c) 训练/测试标签）；实现口径钉死 λ<0 ⟺ r̄<(N+1)/2（与 Eq.(2.2) 字面 N/2 在偶数 N 不一致，论文内部不自洽）。
- [06 BHY 文献研读](issues/06-bhy-literature.md) — `docs/research/bhy.md`：BH/BY 程序 + N=10 双程序手算表（c(10)=7381/2520）；HLZ 引用全部按发表版 RFS 编号；BH 1995 自称 step-down 的历史术语坑已注明。
- [03 Trial ledger 契约](issues/03-trial-ledger-contract.md) — HITL 拍板：trial = 最细粒度原子（一次评估一条序列），两层族结构 hypothesis→trial，N 不落盘、读取端按统计量派生（PBO 全列 / DSR ρ̂ 校正 / BHY 一 trial 一假设）；序列存值、判决独立 append-only、无 abandoned 态；单文件 `ledger.jsonl` 事件日志；API 三层（记账 Ledger / 纯函数统计 / judge 编排）。契约 = `docs/design/trial-ledger.md`，词汇入 `CONTEXT.md`。
- [07 噪声对照设计](issues/07-noise-control-design.md) — HITL 拍板：循环时移陪审团（δ≥60 交易日，换手/覆盖/边际按构造匹配）；一个纯函数 `empirical_null_p`（Phipson-Smyth 加一修正）双模式——个体陪审团 + 池最大（White 2000）；陪审团只活在 VerdictRecord 里不注册 trial（护住 BHY 家族 N）；公共偏移网格 199 一网供两模式。设计 = `docs/design/noise-control.md`。
- [10 adapter 接口与因子评价口径](issues/10-adapter-interface.md) — HITL 拍板：双评价路径（demo 主 RankIC = calc_ic 的 ric；多空 = calc_long_short_return，quantile 0.2）、label = Ref($close,-2)/Ref($close,-1)-1、$close 复权口径、无成本 gross 如实申报；csi300 动态 PIT + NaN pairwise 剔除 + 最小截面护栏 fail-closed；investment_data 钉 tag 2026-07-05；API = evaluate/evaluate_shifted 共享内核（qlib eva.alpha 当 oracle，跨路径逐位等值），index = 信号日 ISO 字符串；确定性 = 环境钉定级逐位 + 双层测试。契约 = `docs/design/adapter-interface.md`。
- [08 court 内核 spec 汇编与切票](issues/08-court-kernel-spec.md) — 指挥侧对五份源文档 docs-grilling，35 项委托决策闭合（spec §4）：扁平八模块布局（并行票零合并冲突）、fail-closed 全线、判决极性表（统计发现⟺法庭 pass）、五文档手算向量零胶水 pytest 计划。spec = `docs/design/court-kernel-spec.md`；切出六张实现票 13–18（13–17 并行、18 收口），dispatch 票 `v0.1-08a…08f` 就绪待派。
- [13 court/ledger.py 实现](issues/13-court-ledger-impl.md) — grok 交付（首派 max_tokens 报废、加分块提示重派成功）；referee 契约行为矩阵五项亲测全过（撕裂恢复/中段损坏/重复评估/matrix 错位/非有限值）。27 测试。
- [14 sharpe+dsr 实现](issues/14-sharpe-dsr-impl.md) — 面板零 blocker 2 major 返工收货：`norm.isf` 换装（N=1e9 差 4.6e-9、N≈4e15 曾 +inf）+ NaN 标量入口有限性护栏（spec §6 新增全局裁定）。45 测试。
- [15 pbo 实现](issues/15-pbo-cscv-impl.md) — recompute 满分；1 major 返工：D5 裁定修订补 T≥2S 护栏（空矩阵曾静默 φ=0.0 = 零证据最有利被告）。11 测试。
- [16 tstats+fdr 实现](issues/16-tstats-fdr-impl.md) — **首个"工人胜诉"判例**：面板证明 HLZ 印刷版 BY adjusted-p 递归自相矛盾，工人的 min(1, c(N)·P) 是唯一自洽形式（bhy.md §3.2 挂勘误、spec E6 重钉、t 管线值 1 ulp 重钉）；代码行为零改动。28 测试。
- [17 noise 实现](issues/17-noise-impl.md) — 面板双 pass（独立参考实现逐位一致）；一处 docstring 措辞返工。13 测试。
- [18 judge 收口](issues/18-judge-impl.md) — grok 交付 referee 收货：judge 薄编排 + 公共 API 44 名，全套件 129 测试；E2E 亲测三统计量 battery 落三份 VerdictRecord、判决范围正确、重开俱在、全参数必传 fail-closed。**court/ 内核完工**。
- [19 adapters/qlib_cn 实现](issues/19-adapter-impl.md) — 面板抓 blocker：秩排序偏离 qlib 联合掩码语义（PIT 效应覆盖 100% 交易日）；返工联合掩码重排秩后 referee 探针 5.6e-17 全过；金指纹 + meta.config 落位。143 测试。
- [20 examples/killer_demo 实现](issues/20-killer-demo-impl.md) — **头版：survivors=0/100**，被告 |t|=2.67 落预注册区间正中、死于池最大关（p̂=0.575）却过个体陪审团——选择效应活教材；104 判决书 + 一图 + 四部判决报告；158 测试。工人代码零责的两次基建故障由 referee 代跑验收（infra-fault 入账）。
- [11 杀手 demo 设计](issues/11-killer-demo-design.md) — HITL 拍板十二项：纯 RNG AR(1) 持久面板 5族×20 全谱 φ（100 hypo×1 trial，spec 全配方披露）；裸选择 = 全窗 max|t| 允许翻号；battery = fdr_by→dsr→pbo(φ≤0.2,S=16)→pool_max→individual×100 共 104 verdict，窗口钉 T=480；聚合 = 全票制一驳即死；禁赢学 = 预注册主种子 20260710 + 预写判词 + 20 种子扫描附录；一图 = 单面板池最大零分布+双基准线；入口 `python -m examples.killer_demo`；report.md 判决书四部（v0.3 博物馆种子）。契约 = `docs/design/killer-demo.md`（demo 的预注册书）。
- [12 v0.1 E2E 验收](issues/12-v01-acceptance.md) — **终验通过，地图关闭**：干净环境一条命令 3418s 跑通；确定性精确成立（头版/图/manifest 逐位一致，台账剥真钟后逐行一致）；诚实条款与铁律逐条核对全过；收尾阶段（README/录屏/GitHub）交接清单已留。

## Not yet specified

（空——全部雾区已毕业成票或决议：adapter 实现 = [19](issues/19-adapter-impl.md)；demo 实现与一图 = [11 设计](issues/11-killer-demo-design.md) 拍板 + [20](issues/20-killer-demo-impl.md)；null 归档呈现 = killer-demo.md §10 判决书四部；工人票接线在 13–17 实战定型，`-n` best-of-n 留给 demo 期观察。）

## Out of scope

- **harness/ 治理层**（预注册闸 hooks、referee 对抗复核、dispatch 泛化到任意 CLI）→ v0.2。M0 桥只做"能派单能收货"的最小件，不做治理。
- **gates/ 便宜刀刀片库**（恒等式退化、池内冗余 ρ、量级 vs 换手、单年运气热力图）→ v0.3。
- **null 博物馆完整形态** → v0.3；v0.1 只留最小驳回记录。
- **双语 README、演示录屏、GitHub 上线** → 收尾阶段（宪章路线图）。
- **美股/crypto adapters** → qlib-cn 先行，其余后补。
- **任何回测引擎功能、任何 idea 生成器**——三不做，永久出界。
