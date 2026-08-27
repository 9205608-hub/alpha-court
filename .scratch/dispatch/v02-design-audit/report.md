开始对 v0.2 四张设计契约做只读审计。先把契约、地基文档和代码现实对齐读完，凡是可核验的主张会真跑。继续读地基文档与 map，并开始对关键声称做代码/数值核验。继续核对阈值换算、`DeclaredProtocol` 字段、以及 map/票面的一致性漏洞。发现 power 的 direction 与选择规则可能不同构；继续核这个问题与其它跨契约缝。# alpha-court v0.2 设计层里程碑审计

**工作区：** HEAD `20b3f53` · 只读 · 数值与代码均已真跑

---

## 总评

**修后施工 · C+**

理由：四张里 03 的方法论与 02 的架构主干大体 sound，10 诚实且轻；但 **01 与 03 在「选择规则 ≡ 统计原假设」上自相矛盾**——power 一边 `argmax|t|`（two-sided 选择），一边 `declared.direction=greater`（directional 闸门）。这正是 03 要消灭的 protocol fraud 类问题，却写进了最贵的交付（~1.5–2 天机时）。再叠加：我自己上次 grill 折入的 **P(win|ICIR=1.5)≈1% 是错的**（MC≈26%）、02 的 `universe` 背书对不上 `DeclaredProtocol`、map 把 `needs-triage` 说成「可直接派」——**「设计层收官、可进纯实现」有水分**。不是推倒重画，但至少 3 处图纸必须先改再派 05。

---

## 1. 单张 soundness

### 1.1 power-calibration.md（v2）— **有致命缝，网格大方向对**

**站得住的：**

| 主张 | 证据 |
|---|---|
| 噪声冠军年化 ICIR≈1.93 | `report.md:7` \|t\|=2.6655；`t·√(252/480)=1.9313` ✓ |
| 99 噪声 `max\|Z\|` 中位≈2.70 | iid 解析：`Φ⁻¹(0.5+0.5·0.5^{1/99})=2.698` ✓ |
| P(win)@ICIR=2.0≈50% | MC：`max\|t\|&t>0` → **0.507** ✓ |
| FDR-BY 单发现 ≈\|t\|3.9 / ICIR 2.8 | `c(N)=5.187`，`p≤q/(N·c)=9.64e-5` → \|t\|=**3.900**，ICIR=**2.825** ✓ |
| Wilson n=20@p=0.5 半宽≈0.20 | 算出 **0.201** ✓ |
| 上锚 ICIR 6.0 ≈ 业界日度 0.4 | `0.4·√252=6.35`，量级对 ✓ |
| 闸门开启顺序 FDR/pool-max/DSR | 复算量级合理：pool-max 理论 \|Z\| 5%≈3.47（文写 ≳3.3 略松）；DSR 用 report `sr*≈0.114`+z≈1.65 → \|t\|≈4.15 / ICIR≈3.0，文写 3.3–3.6 略偏高但同带 |
| β→ICIR 标定 K=64、轴不回写 | 自由度控制正确：标定种子与 power 噪声池隔离；主实验 realized ICIR 不回写轴（`power-calibration.md:89-101`） |
| 共享池 cross-β 复用 / 跨种子禁用 | 边界对：假复用会缩 CI（§5） |
| 条件化 A\|won 偏乐观 + 强制 caption | 统计上诚实（§5, §9） |
| β_t 半窗附录 | 打中「恒定 edge 对 PBO 过友好」；双极性 + 对照同名义 β 设计合理（§7） |
| 自适应补种 n_won≥20 | **对 A 无偏**（iid 种子 + 停在 n_won = 从 P(·\|win) 抽样）；我初审以为有选择效应，**复算后撤回** |

**站不住 / 未钉死的：**

**（A）致命：选择规则与 declared.direction 不同构**

- 选择：`won = argmax|t| AND t>0`（`power-calibration.md:143-145`）——仍是 **two-sided 扫描**  
- 闸门：`power run declares greater` → DSR 启用、PBO 有符号、F2 噪声关用 **有向 t**（`:222-231`；`court/judge.py:168-181` 已实现 F2）  
- 03 的铁律（`selection-verdict-isomorphism.md:37-42`）：每关形式必须与 **selection 的 null-direction** 一致  
- 结果：power 用 two-sided 选择 + one-sided 判决——**03 存在的理由在 01 里被自己拆掉**  
- 后果可量化：same ICIR 下  
  - `P(win|max|t|)` vs `P(win|max t)` 在 2.0 为 0.51 vs 0.59  
  - pool-max 5% 阈：`max|Z|`≈3.47 vs `max Z`≈3.28（directional 更好过）  
  - FDR：same t 的 greater p 是 two-sided 的一半  

这不是脚注问题，是 **~2 天机时会标定错对象**。

**（B）「size 镜像」名不副实**

- §2 表称 size 与 killer-demo 一切相同只差 mean-IC  
- killer-demo：`direction=two-sided`，ranking=`|t|`（`report.md:7,136`；`killer-demo.md:44`）  
- power 若全程 `greater`，β=0 的 size 是 **单侧 size**，不是 demo 的 0/100 那条 size  
- 「同轴分面」在方向切换后 **不可直接对照 α 校准位**

**（C）折入我的旧裁定的错数：P(win)@1.5≈1%**

- 文档与 map 均写：ICIR 1.5 → ≈1%，A 在 0–1.5「结构空集」（`power-calibration.md:111,117`；map L41）  
- 出处：我上次 batch grill 用 **固定 λ 与 max noise 比**（`v02-power-grill/raw-batch.json` 表行 `1.50 … ~1%`）  
- **真跑 MC（信号 t~N(λ,1)，99 噪声 max\|Z\|，t>0 守卫）→ P(win|1.5)≈0.265**，不是 1%  
- 固定均值近似忽略了信号 t 的波动；弱端远没有「结构空」  
- 网格「A 密 2.0–5.0」作为 **法庭 ROC 过渡区**仍大致对（闸门开启在 2.4–3.5+），但 **「1.5 以下 A 空」叙事是我贡献的错，折入后未复核**

**（D）较小**

- pool-max ≳3.3 偏经验/偏松；理论 iid `max|Z|` 5%≈3.47 → ICIR≈2.52  
- R₀=40 在过渡带几乎总够 n_won≥20（2.0 起 E[n_won|R40]≥20）；自适应主要是保险，不是必要  

---

### 1.2 selection-verdict-isomorphism.md（v1）— **方法论 sound；边界未写死**

**DSR 弃权三地雷 — 站得住（真跑+公式）：**

1. **N→2N 错**：因子与其翻号共享 \|SR\|，不是 2N 独立臂。用 `E[max SR]` over 2N 会高估 hurdle（MC：错 2N 近似 \|t\|≈3.26 vs 真 `E[max|SR|]`\|t\|≈2.75）。  
2. **翻号后喂原版 DSR 反保守**：`E[max SR] < E[max|SR|]`（MC 比约 1.10；\|t\| 2.51 vs 2.75）。用 signed 极值当 hurdle 审 \|·\| 选出的冠军，系统偏松。  
3. **PSR/Mertens 符号不对称**：SE 含 `−γ₃·SR`（`dsr.md` / Bailey 2012）；对 \|SR\| 套用会改写「被选序列」定义——不是 2014 对象。  

**弃权而非硬造** 符合引用铁律。正确。

**PBO 换 \|ICIR\| — 文献站得住：**

- `pbo-cscv.md:66-74`：R 任意可估、诱导全序即可；对称性来自等块划分，不来自 R 有符号。  
- 对 `max|t|` 选择，R=\|ICIR\| 是同构过拟合问题；null 下 φ≈0.5 仍成立。  
- 文中 PnL 菜单必须 directional 的 02/03 缝（§6）正确。

**role 派生 — 主路径清，边界虚：**

- 主路径：`two-sided → DSR informational + PBO |R|`；`greater/less → DSR discriminating + PBO signed` — 写死了。  
- **未写死：**  
  - 同一 scope 内 trials 的 `direction` 混用时，family 级闸（FDR/PBO/DSR）的 role 跟谁？  
  - `role` 落在哪？amendment 说「像 N 一样派生」，但 `VerdictRecord` schema（`court-kernel-spec.md:422-430`）**没有 `role` 字段**；09 聚合读什么？  
  - informational 的 `decisions` 仍是 pass/reject——聚合必须 **滤 role 而非滤 decision**，契约未给伪代码/不变量测试形状以外的存储契约。

**与 01 的交互：** 03 假设 selection 与 `declared.direction` 一致；01 违反时 03 的 runtime 分支会 **合法地产生错误的「同构电池」**——这是跨契约炸弹，见 §2。

---

### 1.3 prereg-gate.md（v2）— **威胁模型匹配度高；有可绕过缝与字段洞**

**匹配得好的：**

- 缩 scope / 藏 trial（认证路径派生 scope）/ 事后改 declared / 事后挑聚合 — 机制对得上（§2–5, §7 ticket 09）。  
- (A) 认证路径 + (B) 无 seal=uncertified — 诚实，不装物理不可能（§2 Q1；我上次抓的 framing 已折对）。  
- tamper-**evident** 非 proof、锚一次在 seal、不 per-trial git — 正确（§4.3, §6, §10）。  
- `_append_event` 无 `sort_keys`：**已核** `court/ledger.py:404-407` 确无；hash 路径另做 sort 的设计可实现。  
- torn-write：先算 hash 再单行写入 — 与 append-only 兼容。

**攻击者视角仍开的门：**

| 路径 | 是否堵 | 说明 |
|---|---|---|
| 环外 peek → 只 register 赢家 | **未堵** | §6 承认 fine-grained 拆家；**离线搜索再上认证路径**是 agent 自欺主路，闸只护住「进环之后」 |
| 改 `at`/`registered_at` 伪造先后 | **弱** | content hash **排除** wall-clock（§4.1:59-72）；§5「anchor 不得晚于 series」依赖可被改写的 `at` 或外锚。本地可同时改线内时间戳 + 重写链 + amend 锚 → 文案已降级为 evident，但 **fail-closed 清单把「back-dating」写得比机制硬**（§6 列了 back-dating，链本身不防 `at`） |
| `universe` 漂移 | **契约自相矛盾** | Q4/§5 要求 attested == declared 含 **universe**；`DeclaredProtocol` **无 universe 字段**（`ledger.py:46-52`；spec §5.7:391-396）。adapter `_meta` **有** universe（`qlib_cn.py:494`）。**三方对不齐** |
| metric/window 漂移 | 可堵 | 字段两边都有 |
| direction 翻号 | 路径上可堵 | 不可变 + append-only；adapter 不背书 direction 正确（方向是研究声明不是评价语义） |
| 直接调 court | 故意不堵 | uncertified — 正确 |
| 换聚合规则 | 依赖 09 | seal 校验 policy id — 设计有，实现未到 |
| **selection 规则与 direction 不同构** | **未堵** | 02 说 PnL 必须 directional，但 **没有**「selection policy ≡ declared.direction」的机械检查——01 那种自欺写进预注册书也过得了闸 |

**哈希链实现风险（非矛盾，是钉子）：**

- `struct.pack('<d')` 与 JSON 对 `-0.0`：JSON 保留 `-0.0`，struct 区分 ±0——**必须全路径统一 float 规范**，否则 verify 脆弱。  
- `allow_nan=False` 与 NaN pack 可并存——边界应拒绝 NaN 进 series（ledger 已有有限性要求，需接到 hash 前）。  
- storage 无 sort_keys、hash 有 — 可，但 06 必须写清「验的是 content 规范式，不是行字节」。

**「court 不动」：** 文面自打脸——「unchanged (except 06 source_ref + record attestation)」（`prereg-gate.md:35-36`）。06 还要在 court 内做 declared↔attestation 浅检。这是 **小而真的内核变更**，不是零。

---

### 1.4 dispatch-and-governance.md（v1）— **轻量 sound；RP-1 半机械**

- 两接缝核验：`scripts/dispatch.sh:106` `CMD=(grok …)`；`:156-171` `structuredOutput` 抽取 — **正好两处**，裁定准确。  
- 最小 worker 契约（prompt + cwd + receipt schema）够接第二个 CLI；注册表 YAGNI 合理。  
- RP-1 三触发点：**写了触发清单，明确不建 L1 hook**（`:71-75`）。  
  - 痕迹半：`.scratch/dispatch/v02-*-grill/` 已在 — RP-0 机械痕迹成立。  
  - 触发半：**纪律**。没有任何东西阻止「不咨询就冻结契约」——本次审计对象若在无 grill 下改字仍可称 locked。  
- 对「真接第二个 CLI」：契约够用；对「治理心跳不会空转」：承认空转风险，不算骗，但也 **没交付强制力**。

评分：作为流程裁定 **B**；不要假装它焊死了 RP-1。

---

## 2. 跨契约一致性

### 2.1 01 ↔ 03 ↔ F2 — **不一致（最重）**

| 位置 | 说法 |
|---|---|
| 01 §5 | 选择 `argmax\|t\|` + t>0 |
| 01 §9 / 03 §6 | power 声明 `greater`，DSR on，PBO signed |
| F2 / `judge.py:176-179` | `greater` → 排序统计量 = **t**（非 \|t\|） |
| 03 原则 | 闸形式 ≡ selection |

三处 **不能同时为真**。指挥官若说 01↔03 已对齐，**未对齐**。

### 2.2 02 ↔ 03 ↔ 09 — 顺序无环，依赖图有洞

- 「聚合策略先于首 verdict 上链」与「role 判决时派生」：**无逻辑环**——policy 是「只计 discriminating」的抽象规则，role 在 judge 时按 direction 算出即可。  
- **实现依赖洞：**  
  - 09 Blocked by **仅 02**（`map.md:81`；`09-*.md:6`）  
  - 08 Blocked by **仅 03**  
  - 无 09→08：可先落地「全体 verdict 全票制」，再等 08 加 role——**中间态会重新硬编码 demo 那套五关计票**  
- 03/spec 仍写 aggregation「ticket 11」（v0.1 编号，`court-kernel-spec.md:174-175`）— 与 v0.2 的 09 漂移。

### 2.3 02 attestation ↔ DeclaredProtocol ↔ `_meta` — **对不齐**

| 字段 | DeclaredProtocol | qlib `_meta` | prereg 要求 |
|---|---|---|---|
| metric | ✓ | ✓ | 相等 |
| window | ✓ | ✓ | 相等 |
| **universe** | **✗ 无** | ✓ (`:494`) | §5 要相等 |
| n_evaluation_dates | ✗ | ✓ | 结构检查 len(series) |
| data/adapter/qlib version | ✗ | ✓ | 存证，不与 declared 比 |
| direction / se | ✓ | **故意不背书** | 正确 |
| periods_per_year | ✓ | ✗ | 无背书路径 |

`source_ref` 硬编码 `None`（`ledger.py` register 路径）— 契约称 06 打开，**现状与声称一致（待做）**。

### 2.4 01 与 killer-demo「镜像」

- 同：T=480、csi300、N=100、AR1 壳、adapter 路径 — 意图对。  
- 不同：`direction` / 选择统计量 / size 面板语义 — **镜像在方向维破了**。  
- size 锚若在 directional run 的 β=0：**不是** killer-demo size。

### 2.5 killer-demo.md 内部残留

- §6 顶部 v0.2 修订框正确（四判别关 + DSR informational）。  
- 同节下文仍写「accused is decided by **all five gates**」「104 verdicts」（`killer-demo.md:258-265`）— 与修订框冲突，08 再生时必须清，**契约层已留双写**。

---

## 3. 可实现性（map blocking 脑内走）

声明顺序：`06 → 07 → 09`，`08` 并行，`05` 等 01+03。

| 问题 | 判定 |
|---|---|
| 死锁？ | **无经典死锁** |
| 隐藏错位 | **有** |
| 「court 内核不动」 | **不成立**（06 改 register/record/hash/可能浅检） |
| 05 Blocked by 01+03 真实？ | **半真**：等 03 **文本**避免 battery 语义变；但 **未** Blocked by **08**。power 在 `greater` 下 v0.1 已是 signed DSR+signed PBO，形式碰巧接近；**缺 role 标签与聚合滤 role 也可先跑曲线**。真正 blocker 是 **01 自身同构洞**，不是 08 |
| 05 是否走 06/07 认证路径？ | **契约未写死**。`05-*.md` 说 examples/ 或 harness/，验收不要求 seal。power 可完全绕过预注册闸——**v0.2 旗舰实验可以是 uncertified calculator 跑出来的**，与 map 愿景「焊成不会被绕过的法庭」张力大 |
| 票面 vs 契约 | 05 验收「size≈校准位」未定义是 two-sided 还是 greater size；08 票面仍写「按 03 选定的路径实现其一」— 03 已选定却语气含糊；09 不知 role；06 知 attestation 但不知 universe 进不进 declared |
| map「全 ready-for-agent，05 随时派」 | **过满**。票面 `Triage: needs-triage`；设计洞未修；派 05 = 按错图纸烧机时 |

---

## 4. 合起来自洽吗？

**各自相对 sound 的块（03 方法论、02 架构、10 流程、01 的 DGP/网格量级）合起来在一处互相拆台：**

> 03 说「选择 ≡ 判决方向」；01 说「我用 \|t\| 选、用 greater 判」；02 的闸不检查这条；05 会实现这条。

**v0.2 走完（05–09 全落地）后：**

| 宪章承诺 | 状态 |
|---|---|
| 不是 always-reject：有 power 曲线 | **可成立**（若修同构后重跑） |
| size ≠ power 分表 | 可成立，但 size 定义须钉 |
| 预注册闸挡「合法 API 自欺」 | **部分成立**：环内缩 scope/改 declared/换聚合可挡；**环外搜索、拆家、方向–选择不一致**仍开 |
| 选择–判决同构 | 依赖 08 + 01 修正；现状设计层已破 |
| 禁赢学 | 文案强；β_t 附录是真牙齿 |
| 不会骗自己的 agent | **不能对外说满**——最多说「认证 run 上有 tamper-evident 预注册与派生 scope；idea 生成与离线多重试验仍 stub/洞」 |

**对外诚实可说：**

- 有构造信号上的（修正后）TPR 曲线 + 并列 size  
- 认证路径 + seal + 哈希链（evident）  
- two-sided 下 DSR 弃权、PBO 用 \|R\| 的 battery 叙事  

**不能说：**

- 「agent 无法在合法 API 下自欺」（map L8–12 过满）  
- 「power size 就是 killer-demo size 的镜像」（方向未钉前）  
- 「RP-1 已焊死」（只有清单）  
- 「court 零改动完成 v0.2」  

---

## 5. 最锋利的 3 条（施工前只许改三处）

### ① `power-calibration.md` §5+§9 — 钉死 selection ≡ direction

**改法（二选一，推荐 A）：**

- **A（推荐）：** 选择改为 `argmax t`（β>0 自然），`declared=greater`；won 定义去掉「\|t\|+t>0」补丁。size 面板 **显式标**「directional size」，另引 killer-demo two-sided 0/100 作对照，不假装同一次实验的 β=0。  
- **B：** 保持 `max|t|`，则 **必须** `declared=two-sided`；DSR 在 power 上也是 informational——接受「power 也标定不了 DSR 真负载」，§9「exercises DSR properly」整段删掉。

**不改代价：** 1.5–2 天标定的是 **错构协议**；曲线无法与 03/demo 叙事并陈；v0.2 验收「同构」对 power 自我打脸。

### ② `prereg-gate.md` §4–5 + `DeclaredProtocol` — 字段与威胁对齐

- **universe**：要么升入 `DeclaredProtocol`（或 run-level 声明对象），要么从 fail-closed 相等检查里删除，改「attestation 必含且落盘可审计」。现在的写法 **实现不了**。  
- **back-dating**：要么承认 content 链不防 `at` 伪造、把 §6「防 back-dating」降为「外锚 + 物理行序」；要么把 register/evaluate 的序关系 **只** 绑 `prev_hash`（已是），删掉对 wall-clock predate 的硬承诺。  
- 可选加强：seal 时校验 **selection policy 与 direction 同构**（02 接住 01/03 洞）。

**不改代价：** 06/07 工人会卡在「declared.universe」；验收文案与代码必漂；时间线攻击面被 over-claim。

### ③ 依赖图 + 折入错数 — `map` / 09 blocking / power §4.3

- 09 **Blocked by 02, 08**（或 03）：聚合必须感知 `role`。  
- 撤回/改正 **P(win)@1.5≈1%**（我的错）：改为 MC 量级 ~25%，并重写「0–1.5 A 空集」措辞；网格 2.0–5.0 密采样可保留（闸门过渡仍在那），但理由改为 **闸开启带** 而非 **P(win)≈0**。  
- 05 验收写死：是否要求 certified `harness` seal；size 定义；direction/selection 唯一表。  
- map 去掉「随时派 / 设计层收官可直接施工」——改为 **修 ①② 后 ready**。

**不改代价：** 错误统计写入冻结预注册书；09/08 竞态再现五关空转叙事；指挥官「收官」判断被实现打脸。

---

## 对「自己旧裁定」的点名

| 旧裁定 | 本次 |
|---|---|
| ICIR 0.1–1.5 作 A 主带是锁错 → 改 2.0–5.0 | **主结论仍对**（闸门过渡在此）；**论据错了**：1.5 不是 ~1% win |
| P(win)@1.5~1%、@2.0~50% | 2.0 ✓；**1.5 ✗（~26%）** — 折入设计的错数 |
| tamper-proof → evident | 仍对 |
| DSR 弃权 + PBO \|R\| | 仍对；三地雷复算成立 |
| power 用 greater 练 DSR | **与 max\|t\| 选择一起写就错了**——当时只推了闸分支，**没推 selection 同构**；这是我批审的盲点，比漏 DSR 反保守同型 |

---

## 指挥官判断的水分（直接点名）

1. **「四张设计已 resolved → 纯实现」** — 01↔03 同构未 resolve；02 universe 字段未 resolve。  
2. **「05 网格已冻，随时派」** — 冻的是 ICIR 靶点表；**实验身份（选什么、宣什么方向）未冻对**。派 = 烧机时。  
3. **「court 不动」** — 06 明确动 ledger API 与可能的 record 校验。  
4. **「agent 无法合法 API 自欺」** — 愿景句；契约自己承认离线/拆家/非 proof。  
5. **票面仍 `needs-triage`**，map 写 `ready-for-agent` — 流程状态通胀。

---

**一句话收束：** 图纸不是垃圾，03/02 主干值得保留；但 **在修掉 power 的选择–方向自相矛盾、prereg 的 universe/时间承诺、以及我折入的 P(win) 错数之前，v0.2 不是可施工的冻结设计，是带已知协议欺诈种子的半成品。** 评分 **C+ · 修后施工**。