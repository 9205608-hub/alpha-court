# Panel C report — 跨契约一致性 + 可实现性镜头（Claude 独立面板，盲审）

> 面板员全程未见 grok 输出与指挥官 seam 清单（盲审）。原文如下，一字未改。

# v0.2 设计层审计 — 面板员 C（跨契约一致性 + 可实现性）

工作区根：`[HOME]/Desktop/alpha-court/.claude/worktrees/v02-design-audit-ro`（下文路径均相对此根）。四张契约、map、12 张票、spec、killer-demo、court/adapters/examples 代码全部读过；关键数字用 venv python 复算过（噪声冠军年化 ICIR=1.931 ✓、max|Z| 中位 2.701 ✓、β=0 下 n_won≥20 需约 4000 种子 ✓）。

## 总评

**修后派单（B−）**：四张契约各自内部质量高、跨票 amendment（03→01/spec/killer-demo）都真实落了，但三处"图纸间对不上"正好砸在马上要派的 05/06/07 上——01 §5 的算力方案还停在 two-sided 陪审统计量、02 Q4 的 universe 背书在 declared 侧无家可归、05 的真实 blocker 是 08 而 map 宣布"随时派"。每处都是一段文字的修复量，但不修就派，必然返工。

---

## Findings（按严重度）

### BLOCKER-1：01 §5 的陪审统计量还是 `|t|`，与 01 §9 / 03 §6 / spec F2 的 directional 分支直接矛盾

- **位置**：`docs/design/power-calibration.md` §5（Compute 段："cache their IC series, t, **199-column jury |t|**, and the per-offset max-of-99"）vs 同文 §9、`docs/design/selection-verdict-isomorphism.md` §6、`docs/design/court-kernel-spec.md` F2、`court/judge.py:168-182`（`_ranking_statistic` 已实现按 direction 分支）。
- **证据**：power run 申报 `direction="greater"`（01 §9），F2 规定 greater → 定向统计量 **t**（有符号）。judge 端 `pool_max` 的 observed 会按 declared 算 **max t**（judge.py:398-410），但 `null_stats` 是 harness 作为 params 喂进去的——按 01 §5 的缓存方案喂的是 **per-offset max-of-|t|**。court 不会复核 null_stats 的口径（provenance `ranking_stat` 只是原样入账）。
- **施工时怎么炸**：observed（max t）对上一个随机性更大的 null（max|t| ≥ max t，一侧 q95 ≈ 3.28 vs 3.47）→ pool-max 门槛被静默抬高、TPR 被压低，且 verdict 里 `ranking_stat:"abs_t_iid"` 与实际判决统计量说谎——**一个静默错配的检验，恰是本项目立项要杀的东西**。附带两处同源残渣：① 99 噪声陪衬 trial 各自 declare 什么 direction（全 greater？混合？）任何地方没写，混合 family 下 FDR 的 p 口径与 pool 关的 role 派生都悬空；② §4.3 gate-opening 表的 ~3.9（BY）/≳3.3（pool-max）是 two-sided 口径推出来的数（one-sided 应为 3.73/3.28），放在 directional 实验里误导。
- **不改的代价**：05 大跑 1.5–2 天机时产出一张口径错的 hero 曲线，禁赢学层面等同"胜利学"。修复 = 01 §5 加一行 amendment（jury 统计量 = declared.direction 的定向形；greater → t）+ 写死噪声陪衬的 declared + 表格脚注。

### BLOCKER-2：02 Q4 要求核对 `attested.universe == declared.universe`，但 `DeclaredProtocol` 根本没有 universe 字段，且没有任何票接这个缝

- **位置**：`docs/design/prereg-gate.md` §2 Q4、§5（fail-closed 列表明写 "metric/window/**universe**"）vs `docs/design/court-kernel-spec.md` §5.7 / `court/ledger.py:44-51`（DeclaredProtocol = metric/window/periods_per_year/direction/se，无 universe、无任何 `*_version`）；`docs/design/trial-ledger.md` L51 明言 "universe definitions live in adapters/"。
- **证据**：adapter 背书确实带 universe（`adapters/qlib_cn.py:476-506` ✓），但 declared 侧没有可比对象。02 §3/§7 把 court 内检查限定为 metric/window 浅核（这与 schema 自洽），剩下的 universe/`*_version` 归 harness——对着谁核？`propose(hypothesis, declared, spec, params)` 里 declared 就是 DeclaredProtocol；spec/params 对 court 是 opaque、02 没规定 harness 对其施加结构。06 票只列 "metric/window/adapter_version/data_version"（universe 被丢了），07 票通篇不提 universe。
- **施工时怎么炸**：07 的工人要么擅自扩 `DeclaredProtocol`（打脸 02 §3 "court unchanged"，且动 ledger schema → committed 产物再欠一字段），要么把 universe 检查静默降级为"只入账不核对"——Q4 四大不变量之一被架空，而验收票 11 只按 07 的票面验，抓不到。
- **不改的代价**：预注册闸的"series↔declared 一致性"名不符实。修复 = 一行裁定：universe（与 versions）的 declared 侧落在 Run 级声明（harness 持有、上链、seal 复述）还是 DeclaredProtocol 扩字段，并把 06/07 票面补齐。

### BLOCKER-3：05 的真实 blocker 是 **08**（外加与 06/07/09 的关系全未写死），map 却宣布"随时派"——Option 1 防的返工会原样发生

- **位置**：`docs/design/power-calibration.md` §12（Option 1：等 03 定案避免重跑）、`.scratch/v0.2/map.md` L77/L93（"05 Blocked by 01, 03"、"随时派，~1.5–2 天机时"）、`.scratch/v0.2/issues/05-power-calibration-harness.md`、`docs/design/selection-verdict-isomorphism.md` §7（08 交付：verdict 加 `role`、方向感知 metric 注册表、判别关聚合）。
- **证据**：03 是设计文档；让 verdict **carry role**、G5 注册表加 `abs_*`、聚合只计判别关，全是 **08 的代码**（会动 `court/ledger.py` 的 VerdictRecord 与 `court/judge.py`）。05 先跑：directional 分支下数值恰与 v0.1 行为重合（DSR 本就投票、PBO 本就 signed sharpe、F2 已实现），跑得通——但产物 ledger 里的 verdict **没有 role 字段**，08 落地后 power 产物立刻"落后一字段"，与本次 08 要清的 killer-demo `computed.dsr` 缺字段之债（已核：committed `examples/killer_demo/out/ledger.jsonl` 的 dsr verdict 确无 `dsr` 键）一模一样。另外三问契约全部沉默：power harness 走不走 06/07 认证路径（若走：14β×≤120 种子 = 每种子一 Run 一 seal？02 §8 "一 Run 一 family" 对 power 的映射没人定）；聚合读不读 09 的 config（不读则第二聚合代码路径复活，正是 09 立票要杀的自由度）；01 §10 与 05 票均无一字。
- **不改的代价**：要么 1.5–2 天机时白烧重跑，要么 v0.2 收官时 power 产物 schema 与法庭现状不一致。修复 = 05 Blocked by 追加 08（或先冻 verdict schema），01 §10 补一段"认证路径与聚合来源"裁定。

### major-4：哈希链 + 规范序列化没有唯一属主票——06 票面（工人读的原文）不含它，07 的文件边界又碰不到它

- **位置**：`docs/design/prereg-gate.md` §4.1（"07/06 must-add"）、§7（06 bullet 含 "the hash-chain fields + canonical serialization"）、`.scratch/v0.2/map.md` L94（"06 …+ 哈希链 sort_keys"）vs `.scratch/v0.2/issues/06-ledger-provenance.md`（Question 两项 + 验收三条，**零字提链**）；07 票落点 = `harness/`。
- **证据**：链字段写进每条 event（02 §4.3 "compute event_hash → write the single line"）= 改 `court/ledger.py:404-411` 的 `_append_event`——这只能是 06 的文件边界。但本项目派单纪律是"工人读票原文、验收尺度 = 裁判尺度"：06 工人按票面交付 source_ref + attestation 即算通过。顺带：02 §3 "court unchanged (except source_ref + attestation param)" 的括号本身就漏报了链字段这第三处（更大的）court 改动——契约自己低估了自己。
- **施工时怎么炸**：06 收货合格 → 07 开工发现无链可锚 → 要么 07 违规越界改 court、要么退回重开 06 补票；一来一回吃掉半天到一天，且归因会被误记 worker-fault（实为 contract-fault）。
- **不改的代价**：06→07 链条中断。修复 = 06 票 Question/验收各补一条（链字段 + `sort_keys` + float 固定编码 + "篡改一行 → replay 校验失败"的红测）。

### major-5：聚合策略"上链声明事件"没有属主，09 的依赖被严重低估（真实依赖 06，且与 07 的 seal 互相引用）

- **位置**：`docs/design/prereg-gate.md` §4.2（seal 携带 aggregation/selection **policy id**）、§7（09：策略必须"首 verdict 前上链"）vs `court/ledger.py` 事件词表（hypothesis/trial/evaluation/verdict——**没有策略声明事件类型**）、`.scratch/v0.2/issues/09-aggregation-config.md`（落点 = `harness/` + demo；Blocked by: **02 only**）、map L89（09 在"随时可派"前沿）。
- **证据**：策略事件要进链 → 需要 06 的链；事件类型进 ledger 词表 → 动 `court/ledger.py`（09 的文件边界不含）；07 的 seal schema 引用 09 的 policy id，07 却不 block 09、09 也不 block 07——两票并行派单时各自需要对方的 schema 决定。另外 09 验收"事后不可无痕替换"对（未认证的）killer demo 只有链在才成立；若策略只落 `run_config.json` 一类文件，可无痕替换，验收条款自我矛盾。
- **施工时怎么炸**：现在派 09 → 工人只能做文件级 config + demo 引用，"上链"半句落空；07 落地后 09 全部返工搬上链；两个工人在 aggregate 语义上互相等对方的接口。
- **不改的代价**：02/03/09 接缝——契约里最精心的那道缝——在实现层散架。修复 = 裁定策略事件类型归 06（词表扩一型）或归 07（seal 内嵌），09 Blocked by 改为 02, 06(, 07)。

### major-6：并行派单文件冲突图没人画：06/08/12 三票同挤 `court/ledger.py`、08/12 同挤 `court/judge.py`、08/09 同挤 killer-demo 聚合层且重生成顺序无裁定

- **位置**：map L89（前沿 = 04/05/06/08/09/10-refactor/12 全并行）；08 票（role 入 verdict → `court/ledger.py` VerdictRecord + `court/judge.py` + `examples/killer_demo/*` + 重生成 out/）；09 票（demo 改引 harness 聚合 → 同一批 examples 文件）；12 票第 1/2/3/4 条全在 ledger.py/judge.py。
- **证据**：08 若先落，demo 产物按 4 判别关重生成；09 再落，demo 编排层再改再生成（或反序，则 09 的 config schema 先按 5 关全票制定型、08 落地后 schema 得加 role 感知重来）。两票谁先谁后、产物重生成几次，契约与票面均无一字。08 还有一个自身未钉死项：`role` 是 VerdictRecord 新字段还是 computed/params 键、旧 ledger（无 role）replay 兼容还是 fail——03 §2 只说 "every verdict carries role"。
- **不改的代价**：worktree 合并冲突 + demo 产物两度重生成 + 08 工人在 schema 上自由发挥。修复 = map 加一行冲突矩阵与顺序裁定（建议 06 → 08 → 09 串行过 ledger/demo，12 押后），08 票补 role 落点与 replay 兼容裁定。

### major-7：01 的 "exact size mirror" 言过其实，且 β=0 size 锚的估计量没有定义

- **位置**：`docs/design/power-calibration.md` §2（"Only the mean-IC changes"；表格无 declared protocol 行）、Q3（"exact size mirror"）、§6（"at β=0 assert P(pass) ≈ nominal α"）、§4.3（低带 "A structurally empty"）。
- **证据**：two-sided → greater 改的不只是均值：五道关**每关的形式**都变（DSR informational→投票、PBO |ICIR|→signed、FDR p 两侧→单侧、pool-max |t|→t）——β=0 锚测的是 **directional 五关电池**的 size，不是 killer demo（4 判别关）的 size，两者不同口径不可直接互证；"镜像"只在数据/窗口/池层面成立。更硬的：β=0 下自然赢 max|t| 且 t>0 的概率 ≈ 1/200，n_won≥20 需 ~4000 种子 ≫ cap 120（复算 ✓），A 在 β=0 为空集——那么 §6 那句断言算的到底是什么：全池幸存率（killer-demo 式）？强制送审 P(pass)？逐关 size？没写。
- **不改的代价**：05 工人自选一种估计量，size 面板与 killer demo 的对照叙事出现无声口径漂移——这正是 v1 ICIR 锁错的同款病灶（锚定在没想清的口径上）。修复 = §2 表加 "declared protocol" 一行如实标注差异，§6 写死 β=0 面板的估计量。

### major-8：05 票的验收标准只覆盖 01 §10 交付物的一小半（验收尺度 ≠ 裁判尺度），且 β→ICIR 标定"已冻结"名不符实

- **位置**：`.scratch/v0.2/issues/05-power-calibration-harness.md`（验收 = power 曲线 + size 表 + 首屏边界 + 确定性）vs `docs/design/power-calibration.md` §10（hero + **B 曲线 + 分闸 TPR 面板** + size 面板 + **submission-power 表 + β_t 附录**）、§4.2/§12。
- **证据**：submission 表、分闸 TPR、B、β_t 半窗附录在票面验收里全部缺席；§12 声称 "The grid and β→ICIR calibration are frozen now"，但全 repo 找不到任何 β* 表——冻结的只有**程序与 ICIR 目标**，K=64 标定跑从未发生，票面也没让工人跑。
- **不改的代价**：工人交两张图技术性过验、referee 按票面无从驳回；或工人开跑发现没有 β 可用，卡死回询。修复 = 05 票验收逐项对齐 §10 + 显式加"第一步：执行并冻结 §4.2 标定，产出 β* 表入 run_config"。

### minor-9：02 §3 "harness/ (new)" 已过时——`harness/` 现存三个不相干的会话治理模块

- **位置**：`harness/__init__.py`（docstring 还说 "Empty in v0.1"）、`harness/confirm_gate.py`、`trial_counter.py`、`anti_pattern_gate.py` vs `docs/design/prereg-gate.md` §3。07/09 工人将把 Run/seal/config 落进一个已被 CONFIRM-gate 等占用的包，无任何共存/分层说明。改一行契约或票面注记即可。

### minor-10：12 号票第 1 条（字符/字节截断只因 `ensure_ascii=True` 才对）与 02 §4.1（哈希路径 `ensure_ascii=False`）互相埋雷，两票零交叉引用

- **位置**：`.scratch/v0.2/issues/12-kernel-robustness-nits.md` 第 1 条、`docs/design/prereg-gate.md` §4.1、`court/ledger.py:406`。02 区分了存储路径 vs 哈希路径，但 06 工人若顺手把存储序列化改成 `sort_keys/ensure_ascii=False`，撕裂恢复的字节精度静默坏掉。06 票补一句"存储行序列化不动"即可。

### minor-11：map 前沿列了 "10-refactor" 为可派单项，但 `.scratch/v0.2/issues/` 里没有这张票

- **位置**：map L89/L96 vs issues/ 目录（只有 01–12）。派单纪律要求自包含票面；无票不可派。补一张小票或从前沿摘除。

### nit-12：spec 的 03 amendment 写 "aggregation (ticket 11) counts only discriminating"——v0.1 的 11 号（killer demo）与 v0.2 的 11 号（E2E 验收）撞号

- **位置**：`docs/design/court-kernel-spec.md` §4 amendment 段。08 工人读 spec 会把聚合错定位到"验收票"。加个 "(v0.1)" 即可。

---

## 已核 ✓（互引一致，无需动）

- 03 §6 ↔ 01 §9 双向 amendment 文字一致（directional → DSR 启用 + PBO signed，运行时按 declared.direction 分支）✓
- spec F2 已在 `court/judge.py:168-182` 实现（two-sided/greater/less 三分支），03 Q1 的前提为真 ✓
- spec §4 末 03-amendment、killer-demo.md §6 v0.2 revision 注、power-calibration.md §9 patch——03 声称的三处 amend 全部真实落盘且口径一致 ✓
- 02 §7 ↔ 03 §6 的 PnL-directional 接缝两侧表述一致（03 不写死"永远 |metric|"）✓
- adapter `_meta`（qlib_cn.py:476-506）字段 ⊇ 02 Q4 背书清单（metric/window/universe/data_version/adapter_version/qlib_version/n_evaluation_dates）✓
- DeclaredProtocol.Window {start,end} 字符串 ↔ adapter cfg window {start,end} 字符串，metric/window 浅核可等值比较 ✓
- 02 §4.1 "verified: `_append_event` has no sort_keys" 属实（ledger.py:406）✓
- 06 票引用的行号（register :430-436、source_ref None :455、record 裸序列 :463、qlib meta :487-506）全部对得上 ✓
- committed demo ledger 的 dsr verdict 确缺 `computed.dsr`（"落后一字段"之债属实，08 重生成可清）✓
- map 各票 Blocked-by 与票头一致（05:01,03 / 06:02 / 07:02,06 / 08:03 / 09:02 / 11:01–10）✓
- 01 锚定数字复算：冠军年化 ICIR 1.931、max|Z| 中位 2.701 ✓
- court 仅依赖 numpy/scipy(+stdlib)，04 的白名单可行、pandas 确未用 ✓；现黑名单（test_smoke.py:28-35）确如票述只查 qlib*/adapters* ✓
- worker-bridge.md 已带 ticket-10 指针（L94-100），10 的裁定与票面 Answer 一致 ✓
- 02 §7 "07 acceptance 不得断言 in-process 禁调 court" ↔ 07 票面三绕过路径措辞不冲突 ✓；03/07 "统计侧 vs 闸侧" 分工两票同述 ✓

---

## 最锋利的 3 条

1. **BLOCKER-1**：01 §5 缓存 "jury |t|" 是 03 amendment 打补丁时漏改的尸块——directional run 下 judge 算 max t、harness 喂 max|t| null，law court 自己上演统计量错配，而且 court 不会替你发现。一行 amendment 的事，不改则 1.5–2 天机时买一张口径错的 hero 图。
2. **BLOCKER-3**：Option 1 防错了对象——会改 schema 的是 08（实现），不是 03（设计）。map "05 随时派" 若被执行，power 产物将复刻本次 08 要清偿的"committed ledger 落后一字段"之债，v0.2 用来还债的里程碑亲手造新债。
3. **BLOCKER-2**：02 Q4 的 universe 背书核对，declared 侧无字段、06 票丢了这个词、07 票不知道它存在——预注册闸四大不变量之一目前只存在于契约的祈使句里。派 06/07 前需要一句话裁定它住哪。
