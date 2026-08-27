# Panel A report — 统计镜头（Claude 独立面板，盲审）

> 面板员全程未见 grok 输出与指挥官 seam 清单（盲审）。原文如下，一字未改。

# v0.2 设计层审计 — 面板员 A（统计镜头）

**审计对象**：`docs/design/power-calibration.md`（01, v2）、`docs/design/selection-verdict-isomorphism.md`（03, v1）
**方法**：逐字读 + 对照文献笔记 + 全部可复算数值真跑（MC / 数值积分 / CSCV 全组合模拟，脚本在我的 scratchpad，非仓库）

## 总评

**修后施工。** 两张契约的骨架（预注册纪律、ICIR 轴冻结、方向感知裁定、弃权而非捏造）是对的，多数锚点数字复算通过；但有一处 BLOCKER（β_t 附录的对照组测不到它声称的机制）和一处一阶数值错误（P(win) 忽略 t 统计量的实现噪声，低带错约 13–25 倍），都长在"冻结"文本上——这个项目的宪法恰恰禁止事后改预注册，所以冻结前是唯一修复窗口。

- **01 power-calibration：B−**。一句话：预注册工程一流、锚点换算基本全对，但两处一阶统计推导错误恰好都被写进了冻结条款。
- **03 selection-verdict-isomorphism：B**。一句话：裁定结论（DSR 弃权、PBO 换 |R|）站得住且 |R| 声称经模拟证实，但三条"地雷"里两条哑火，`less`/混合方向分支没写死。

---

## Findings（按严重度）

### BLOCKER-1 — 01 §7：β_t 半窗附录的预注册对照测不到"PBO 对常数边际乐观"这个靶

- **位置**：power-calibration.md:183-199（"Compared against the constant-β run at the **same nominal β=s**（not average-β — the point is to expose, not dilute, the drop）"）。
- **证据（CSCV 全 12870 组合模拟，T=480, N=100, S=16, 30 reps）**：
  - const s(4.0)：φ=0.049，P(φ≤0.2)=0.97
  - half-window 同名义 s(4.0)：全样本 ICIR≈**1.98**（均值直接减半），φ=0.368，P(φ≤0.2)=**0.17**
  - const ICIR 2.0（强度匹配对照）：φ=0.388，P(φ≤0.2)=**0.13**
  - half-window 匹配全样本 ICIR 4.0：φ=0.093，P(φ≤0.2)=**0.90**
- **为什么错**：同名义 β 的半窗信号在全样本上就是一个 ICIR≈2.0 的信号。预注册对比（0.97→0.17）里约 85 个百分点是**强度减半**效应，episodicity 在强度匹配下只贡献约 7 个百分点（0.97→0.90）。附录要回答的"unanimous/PBO-TPR 从常数边际到半窗掉多少点"会得到一个巨大的数字，但它归因的机制（PBO 惩罚间歇性）几乎不是原因。文档明确拒绝了正确的对照（"not average-β"），把正确的因果对比当成"稀释"。
- **不改的后果**：预注册解读本身是错的。跑完后要么把错误归因写进 hero 图脚注（自骗，违反禁赢学），要么事后改预注册书（违反宪法 §8）。两条路都撞铁律。
- **修法（一段话的事）**：加一个 matched-realized-ICIR 半窗臂（β 解到全样本 ICIR=4.0），把它定义为 episodicity 的主对比；同名义 β 臂保留为"真实研究者视角"的展示。冻结前改。

### MAJOR-1 — 01 §4.3：P(win) 计算漏掉 t 的实现噪声，低带错一个数量级；"A structurally empty ≤1.5"是错的

- **位置**：power-calibration.md:110-112（"P(win) ≈ 50% at 2.0, ≈ 1% at 1.5"）、117（低带 "A marked under-powered / empty"）、120-121（"Do not uniformly scan 0.1–1.5 for A — it has ~0 conditioned samples"）。
- **证据（40 万次 MC，t_inj ~ N(1.3801×ICIR, 1) vs 99 噪声 max|Z| 的精确抽样）**：

  | ICIR_ann | P(win) MC | 文档口径（确定性 t）|
  |---|---|---|
  | 1.0 | **0.103** | 0.0000 |
  | 1.5 | **0.267** | 0.021（文称 "≈1%"）|
  | 2.0 | 0.510 ✓ | 0.564 |
  | 2.6 | 0.786 | 0.968 |

- **为什么错**：480 天窗口下 t 统计量自身的抽样标准差 ≈1（换成 ICIR 轴 ≈0.72 annualized，比噪声 max 的离散度 0.35 还大），把 t 当常数算 P(max99|Z| < E[t]) 在过渡带以下低估、以上高估。§4.2 自己都要求报告 64 种子实现 ICIR 的 SE——同一个方差在 §4.3 被丢了。2.0 处 "≈50%" 纯属两种近似恰好交叉的巧合。
- **不改的后果**：真跑时 1.5 处 R₀=40 个种子会产生约 10–11 个自然获胜（1.0 处约 4 个），实测数据当场打脸冻结文本"structurally empty / ~0 conditioned samples"；而 A 在这些点本来是免费的（battery 复跑本来就便宜），却被预注册排除出报告。另外 2.3/2.6 处高估 P(win) 会让自适应补种负载预估偏乐观（实际 0.66/0.79 而非 0.86/0.97）。
- **修法**：重算 §4.3 括号里的数字（带实现噪声），删除"structurally empty"断言，低带 A 改为"按实际 n_won 出报告、宽 CI 如实标注"。网格点本身不用动。

### MAJOR-2 — 01 §2 × 03 §6：方向声明翻转整个 battery 形态，"只有 mean-IC 改变、归因通道干净"不再成立；size anchor 与 gate 表口径未钉死

- **位置**：power-calibration.md:42-44（"Only the mean-IC changes; the attribution channel is therefore clean"）vs 222-231（§9 承认 power 声明 `greater`）；§6:176-177（size panel 断言）；§4.3:129-137（gate 表）。
- **证据**：按 03 的 runtime branch，`greater` 下与 killer demo（two-sided）相比变的不只是 mean-IC：DSR 从 informational 变 discriminating（投票 gate 从 4 变 5）、PBO 从 |ICIR| 变 signed、pool-max 统计量从 max|t| 变 max t（iid 理论 95 分位从 3.47 掉到 3.28）、FDR 的 p 从双侧变单侧（BY 单真发现门槛从 |t|=3.900/ICIR 2.83 降到 t=3.728/ICIR 2.70）。§4.3 gate 表的 FDR 行（3.9）是双侧口径，pool-max 行（≳3.3）却更接近 signed 理论值 3.28 或 demo 经验过线点 3.17（我从 report.md 的 199 个 null 复算：第 10 大 = 3.1715）——同一张表内部混用两种方向约定。
- **未写死的三件事**：(a) 99 个噪声 trial 声明什么方向（若噪声仍 two-sided 而 injected greater，pool 级 gate 用谁的 direction 未定义，FDR 家族混口径）；(b) §6 的 β=0 size anchor 是 greater-battery 下的内部重跑，还是复用 killer demo 的 two-sided 结果——前者统计上自洽，后者是在拿另一个法庭当对照；(c) §5 的自然选择扫描仍写 argmax|t|（在 won 分支上与 argmax t 等价，我核过：t_inj>0 且 |t_inj| 最大 ⟹ 有符号最大，但非 won 分支上一致性断言可能因负 t 噪声冠军而失败）。
- **不改的后果**：power 曲线与 size demo 的"对称镜像"叙事在细节上是假的；施工票（05/08）会各自猜口径。
- **修法**：01 里加一段：power 是 greater-battery 的自成体系实验，全部 100 个 trial 声明 greater，size anchor = 同一 battery 在 β=0 的重跑；§2 表加一行 "declared.direction：two-sided → greater（battery 形态随 03 分支改变，disclosed）"；gate 表按 greater 统一重算。

### MAJOR-3 — 03 §3：DSR 弃权的三条"地雷"两条哑火，把工程裁定包装成了统计不可能性

- **位置**：selection-verdict-isomorphism.md:80-94。
- **证据（数值积分，精确值）**：
  - **地雷 1（N→2N is wrong）不成立**：E[max|Z|, N=100] = 2.7470，E[max Z, 200 独立] = 2.7460，差 **0.0009**——比已启用的有符号 DSR 自己容忍的 EVT 近似误差（2.5306 vs 精确 2.5076，误差 0.023）小 25 倍。翻转对的完全负相关在右尾无关紧要（(2Φ−1)^N 与 Φ^{2N} 相差 O(NΦ̄²)）。"两倍臂数"是一个近似质量极好的替代，不是错误。
  - **地雷 2 真实且可量化**：E[max Z, 100] = 2.5076 vs E[max|Z|, 100] = 2.7470，翻转后喂原版 DSR 的门槛低了 **0.24 个跨试验 SR 标准差**——反保守，核实通过。
  - **地雷 3 可被实现消解**：若实现为"翻转序列→在翻转后的序列上重算 γ₃、γ₄、SR"，则 PSR 作用的正是被实际交易的那条序列，是原汁原味的 2012 对象；Mertens SE 的符号不对称性自动正确。剩下的只是把 N 换成 2N 这一步不能挂 Bailey-2014 的引用。
- **为什么错**：弃权裁定本身可以站住——依据是引用铁律（法庭不发明无文献的统计量）+ two-sided 下 pool-max 已精确承载同构负载。但契约声称"三条真实地雷"使两侧 DSR 在统计上站不住，其中两条经不起复算。对一个"统计实现必须与文献逐项对上"的项目，裁定书自身的文献论证不实是同类罪。
- **不改的后果**：下一个较真的评审（或未来的你）复算后会发现裁定书论证掺水，连带质疑站得住的部分；若未来想升级出一个声明式两侧 DSR（作为 informational 参考），会被这段错误论证挡住。
- **修法**：§3 重写为"一条真地雷（LM2）+ 引用铁律"两点论证；LM1/LM3 降级为"N→2N 的近似虽好但无文献可挂"的脚注。裁定结论不变。

### MAJOR-4 — 03 §2/§4：`less` 分支照字面实现是错的；混合方向 scope 未定义

- **位置**：selection-verdict-isomorphism.md:44-51（Q2 表 "greater/less (directional) → metric = signed sharpe/ICIR"）、104-107（G5 注册表修正）。
- **为什么错**：`less` 下选择按 F2 排 −t（最负最优），而 CSCV 的 IS-argmax 取 metric 最大——"signed sharpe/ICIR"原样喂进去会选到**最正**的列，同构恰好反了；正确形式是 −sharpe/−ICIR（或等价地翻转序列）。同理 DSR "enabled (signed, original)" 在 `less` 下对一个负 SR 被告近自动 reject——正确做法是对声明性 `less` 假设翻转序列后跑原版 DSR（预注册方向、无符号搜索、N 不变，这是干净的），但契约没写。另外 pool 级 gate（pool-max/DSR/PBO）读全 scope，若 scope 内 trial 方向异构，"trial's declared.direction"这一派生依据没有定义用谁的。
- **不改的后果**：ticket 08 的 direction-branch 是显式 invariant 测试对象（03 §7），worker 照字面写 `less` 分支必错，而 v0.2 没有 `less` 实验能暴露它——错误会静静躺进内核直到有人用。
- **修法**：Q2 表加一列写清 `less` 的 metric = 负号形式 + DSR 的序列翻转约定；scope 方向异构时 fail-closed（raise），与内核错误语义一致。

### minor-1 — 01 §5：自适应停规则使 B 的估计有偏、B 的 Wilson CI 不严格；A 无恙

- **证据（4 万次流程模拟）**：停规则"补种到 n_won≥20"只看分母不看 pass，故 A = P(pass|won) 的 Wilson 有效（模拟 E[p̂_A]=0.5996 vs 真值 0.6）；但 B = n_won/R 是 stopping-on-win 抽样，向上偏（p_win=0.25 时 +0.0095，约 +4% 相对偏差），且序贯样本下 Wilson 覆盖率不精确。
- **修法**：预注册 B 的估计只用前 R₀=40 个固定种子（或注明负二项校正），一句话的事。

### minor-2 — 01 §7：random-block 次级敏感性在 CSCV 与全样本 gate 下与 half-window 同分布，信息量被高估

- **证据**：50% duty 且对齐 PBO 块边界 = "16 块中 8 块 ON"；CSCV 对块可交换，全样本 t/DSR/FDR 对日重排不变——iid-IC 模型下 random-block、half-window、forward/backward 极性四者 φ 分布**恒等**（模拟：0.370 vs 0.318，sd 0.21，一致）。只有真实数据的 IC 波动 regime 才让它们可分。文档把它当成独立的敏感性检验来卖，实际上只防"真实数据日历巧合"这一件事——这正好也是极性对照的用途，两者重复。
- **修法**：注明该敏感性只针对真实数据 regime 对齐巧合，或砍掉省算力。

### minor-3 — 01 §4.2：冻结标定残留两个自由度

标定用的候选 β 网格和 root-find/插值方法未钉死（"~14 β"只是成本估计）；"φ fixed to one median value" 未给数值也未定义 median of what（100 壳 φ 的中位数 ≈0.97？五族中位的中位？）。对一份以"冻结"为卖点的文档，这两个旋钮该在 run_config 冻结清单里点名。

### minor-4 — 01 §4.2：标定种子根与 killer-demo sweep 种子撞树

`SeedSequence(20260711).spawn(64)` 的 child 0/1 与 sweep seed 20260711 的 `spawn(2)` child 0/1 **同 entropy 同 spawn_key，流完全相同**。虽无实际推断损害（标定先于 run 冻结），但"must not reuse the power run's noise realizations"这一隔离承诺变得无法机械证明。把标定根挪出 20260710–20260730 保留区（如 120260711）。

### minor-5 — 01 §4.3：gate 表两行口径注记

DSR 行复算期望开启点 |t|≈4.43（含信号对跨试验 std 的自抬升）→ ICIR≈3.21，文称 "4.5–5+ / 3.3–3.6+" 略高但同量级；pool-max 行 "≳3.3" 介于 iid 双侧理论 3.47、signed 理论 3.28、demo 经验过线点 3.17 之间，出处未注明。都在 "≈" 容差内；建议注明每行的计算口径（尤其 MAJOR-2 落地后要按 greater 重算）。

### nit

1. §5 排期只写 R₀=40 的 1.5–2 天；cap R=120 的最坏串行 ≈4.2 天（120×44min + injected），ticket 05 应写最坏值。
2. §7 "not daily Bernoulli（high-frequency IC autocorrelation artifact）"理由不准：日 Bernoulli duty 不产生 IC 自相关，它的真问题是与更弱常数 β 在日粒度不可分（"不忠于 episodic"那半句才是对的）。
3. §9 "fed |metric| would … make it incomparable to the size demo" 语病：喂 |metric| 恰好与 size demo **同**口径，不可比的是与 declared `greater` 的同构性。
4. §6 "at β=0 assert P(pass) ≈ nominal α" 过宽：PBO 的 φ≤0.2 不是 size（killer-demo §5.4 自己声明），断言只对 size 型 gate 成立。

---

## 已核 ✓ 清单（复算通过）

| 主张 | 复算值 |
|---|---|
| 冠军 \|t\|=2.6655 → ICIR_ann≈1.93 | 1.9313（与 report −1.9314 一致）✓ |
| 99 噪声 max\|Z\| 中位 ≈2.70 | 2.6979 ✓ |
| P(win)@2.0 ≈ 50% | MC 0.510 ✓（巧合性正确，见 MAJOR-1）|
| FDR-BY 单真发现 ~3.9→2.8（双侧口径）| \|t\|=3.900 → 2.825；c(100)=5.187378 = report c_factor ✓ |
| 单位脚注：daily 0.3–0.8 → ann ≈5–13；0.4 → 6.0 anchor | 4.76–12.70；6.35 ✓ |
| sr* = std×max_z | 0.045229×2.5306=0.11446 ≈ report 0.114482 ✓ |
| Wilson n=20@p=0.5 半宽 ≈0.20 | 0.2007 ✓ |
| 99×26.8s ≈ 44 min；R₀=40 串行 1.5–2 天 | 44.2 min；1.40 天 ✓ |
| 03：\|R\| 下噪声 φ≈0.5 | 全组合模拟 0.494±0.10（signed 0.487；demo 实测 0.4731 同框）✓ |
| 03 地雷 2（翻转喂原版反保守）| 缺口 = 2.747−2.508 = 0.24 SR-std ✓ |
| 03 §5 headline 不变 | 被告在 4 个 discriminating gate 挂 FDR+PBO+pool-max（report 实证），去 DSR 票不改 0/100 ✓ |
| vdW 混合：β 干净混合权重、E[RankIC] 单调于 β | 严格单调，β=0.5 时 0.478（双正态理论 0.483）✓ |
| const ICIR 4.0 "comfortably past PBO" | φ=0.049，P(φ≤0.2)=0.97 ✓ |
| half-window 确实打疼 PBO | φ 0.049→0.37 ✓（但归因混杂，见 BLOCKER-1）|
| 03 §4：full-sample argmax\|SR\| ≡ argmax\|t\| | 同 T 下单调等价 ✓ |
| A 分支 Wilson 在停规则下无偏 | 模拟 0.5996 vs 0.6 ✓ |
| 同种子内 cross-β 复用 / 跨种子禁用 | 公共随机数逐点有效 / 跨种子复用=伪重复缩 CI，推理成立 ✓ |
| DSR ρ̂≈0→N̂≈M 最狠通缩方向保守；ill-conditioned 480<4950 | ✓ |

**未核**（无法在设计层复算）：26.8s/candidate 的单点实测成本；真实数据上 g(β) 标定曲线的形状；"industry ICIR≈0.4 (daily)" 的行业口径本身。

---

## 最锋利的 3 条（只许改三处）

1. **01 §7 加 matched-realized-ICIR 半窗对照臂并定义为 episodicity 的主对比**。否则预注册结论把强度减半（约 85 个百分点）归因给 PBO 的间歇性惩罚（实际约 7 个百分点），事后无法在不违宪的前提下纠正。
2. **01 §4.3 用带实现噪声的 P(win) 重算低带，撤掉 "A structurally empty ≤1.5"**。1.5 处真实 P(win)≈27% 而非 1%——真跑会当场打脸冻结文本，且白白扔掉低带免费的 A 数据点。
3. **01 显式声明 power 为 greater-battery 自成体系实验**：全部 100 trial 声明 greater、size anchor = 同 battery β=0 重跑、§2 "只有 mean-IC 改变"改写、gate 表按 greater 口径统一（FDR 行 3.73/2.70）。不然"对称镜像"的归因叙事在 03 分支生效后是假的。
