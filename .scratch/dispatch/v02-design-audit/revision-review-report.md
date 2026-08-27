按 RP-1 复审修订本身：先读 `verdict.md` 与 HEAD 修订范围，再逐条核 D1–D17 并复算数字。HEAD 只是 review prompt；继续定位真正的设计修订 commit 与相关文档状态。修订在 `b15fdff`；工作区已是 v3。开始通读修订 diff 与关键段落，并并行复算数字。并行通读修订后全文并复算关键数字。发现两处 two-sided 残渣；继续深挖 prereg、票面与全文一致性。# RP-1 复审：v0.2 设计审计修订

**审计对象：** `b15fdff`（工作区即修订后 draft；HEAD 另有 prompt commit 不影响内容）  
**方法：** 对着 `verdict.md` D1–D17 读全文 + 跨文档互引 + 数值真跑（400k MC / 数值积分 / 种子撞树）

---

## 总评

**还差 4 处收尾方可终冻结 · B−**

F1-A 与 F2 的主干**真的折进去了**：argmax t、全员 greater、gate 表单侧重算、matched-ICIR 主对照、P(win) 重算、种子根迁移、run_config、锚语义、D8–D11 边界、03 论证重写、`less`/混向、map 冲突矩阵、10a——这些不是「日志里写了修」的空壳。

**不能给 A / 不能直接终冻结**，是因为指挥官做了**高密度段落重写**，却漏了**决策表与派生公式的机械扫尾**。工人若只读 §3 决策表或 §5 的 B 定义，会重新实现被 D1/D3 杀掉的东西。这是修订债，不是新设计洞——但冻结前必须清。

---

## 数字复算（凡声称必跑）

| 声称 | 真跑 | 判定 |
|---|---|---|
| P(win)@0.5…3.2 = 0.05/0.15/0.35/0.60/0.73/0.84/0.92/0.96 | 400k MC `argmax t`：0.047 / 0.150 / 0.347 / 0.596 / 0.733 / 0.841 / 0.915 / 0.960 | ✓（四舍五入到文内精度） |
| 自然赢中位 t=2.46 / ICIR 1.78 | Φ(x)^99=0.5 → t=**2.458** / ICIR=**1.781** | ✓ |
| pool-max 单侧 3.28 / ICIR 2.38 | Φ(x)^99=0.95 → t=**3.281** / ICIR=**2.377** | ✓ |
| FDR-BY 单侧 3.73 / ICIR 2.70 | c(100)=5.1874，p≤q/(N·c) → t=**3.728** / ICIR=**2.701** | ✓ |
| 03：0.24 SR-std | E[max\|Z\|]−E[max Z]=**0.239** | ✓ |
| 03：0.0009 | E[max\|Z\|,100]−E[max Z,200]=**0.000915** | ✓ |
| 03：0.023 EVT | Bailey EVT N=100：2.5306 vs exact 2.5076 → **0.0230** | ✓ |
| 种子撞树 20260711 | `spawn(64)[0:2] ≡ spawn(2)` bit-identical | ✓；新根 320260711 移出保留区 ✓ |

DSR 行 ≈4.4+/3.2+ 是量级估计（非精确闭式），与 Panel A 的 ~4.43/3.21 同带，可接受。

---

## 逐条裁定（D1–D17）

### BLOCKER

| # | 闭环 | 证据 |
|---|---|---|
| **D1** | **✗ 实质闭环 / 字面未清** | §2/Q1b/§5 won/陪审 t/gate 表/size 均已改 F1-A；**但 §5 Derived note B 仍是** `P(max\|t\|=injected, t>0)`（`power-calibration.md:187`），Q3 仍写「exact size mirror」（:63）——B 的操作性定义与 D1 选择规则直接矛盾。jury/gate/won 主路径对了，**B 残渣会让 05 工人画错选择率曲线**。 |
| **D2** | **✓** | §7 主对照 = matched realized ICIR；同名义 β 降为 secondary display 并标明 confounding。CSCV 归因方向与 Panel A 一致。 |
| **D6** | **✓** | 删除「锚必须早于 series」；§4.3 钉死锚证明 chain head ≤ 锚时戳；pre-anchor 单列为可选对象。§5/§6/07 票一致。 |
| **D7** | **✓** | `run_config` declaration 为首链事件；Q4 分家 metric/window↔DeclaredProtocol vs universe/*_version/config↔run_config。**02 / 06 / 07 三处同词同分工**（06 管类型+链，07 写与核）。未扩 `DeclaredProtocol`，不违裁定。 |
| **D13** | **✗ 契约闭环 / 票头未改** | 01 §12 + map + 05 修订节三裁定一致：Blocked by +08、uncertified 披露、聚合复用 08 helper。**但 05 票 frontmatter 仍是 `Blocked by: 01, 03`（:6）**，只靠「冲突以修订节为准」。只读 YAML 的派单/工具会漏 08。 |

### major

| # | 闭环 | 证据 |
|---|---|---|
| **D3** | **✗ 主文对 / 决策表残留** | §4.3 表与 MC 对上；「structurally empty」在 §4.3 正文被推翻。**§3 Q4 决策表仍写「A there is structurally empty」（:64）**——冻结决策表与主文打架。 |
| **D4** | **✓** | §3 重写为一真地雷（0.24）+ 引用铁律；LM1/LM3 退休在案，数字与裁判脚本一致。 |
| **D5** | **✓** | Q2 三分列；`less` = 翻转/负号 metric；混向 scope → raise。08 票同步。 |
| **D8** | **✓** | §5 seal-must-be-final；§6 披露 pre-seal 截尾；07 honesty test 钉「截尾通过」。 |
| **D9** | **✓** | §1 收窄 + §6 第五条环外预筛 + RP-1 追问。 |
| **D10** | **✓** | 无签名 dict 伪造披露；禁 07 进程内安全戏剧；reflog 仅 git-anchor。 |
| **D11** | **✓** | 兄弟 run / restart-until-lucky 披露 + 出示全部 sibling 的 RP-1 规则。 |
| **D14** | **✓** | 06 扩词：链字段 + sort_keys/float 预变换 + declaration/seal + 篡改红测；属主钉死。 |
| **D15** | **✓ 实质** | 事件类型归 06；09 Blocked-by 修订节改 02,06；map 同步。**frontmatter 仍 `Blocked by: 02`（09:6）**——同 D13 类流程债。 |
| **D16** | **✓** | map 冲突矩阵 06→08→09、12 押后；role = `VerdictRecord` 可选字段；spec amendment + 08 票一致。 |

### minor（verdict 清单抽样）

| 项 | 状态 |
|---|---|
| 种子根迁出保留区 | ✓ 320260711 |
| 标定 β 网格 / PCHIP / φ 中位 | ✓ 钉入 §4.2 |
| B 用前 R₀=40 | ✓ §5 |
| R=120≈4.2 天 | ✓ 01+05 |
| random-block 诚实降级 | ✓ |
| gate 表 provenance | ✓ |
| `type` 入 content_hash / at 理据 | ✓ |
| 锚/manifest 序 | ✓ |
| float 递归预变换 | ✓ |
| court 三处改动诚实列出 | ✓ |
| harness 包名共存 | ✓ |
| receipt 验证 + (d) 全无头 | ✓ 10 + 10a |
| tripwire `.scratch/dispatch` 盲区 | ✓ |
| 10 trigger-1 补档注记 | ✓ |
| ticket 11 消歧 | ✓ amendment |
| killer-demo §6 双写 | ✓ 四判别关一致 |
| 12 ensure_ascii 与哈希路径分家 | ✓ 存储不动 / hash 另路 |

---

## 新错清单（修订引入或未扫净的内伤）

| 严重 | 位置 | 问题 |
|---|---|---|
| **major 残渣** | `power-calibration.md:187` | B 定义仍是 two-sided：`P(max\|t\|=injected, t>0)`。与 §5 won=`argmax t` 同节自相矛盾。**工人抄这行 = 重犯 D1。** |
| **major 残渣** | `power-calibration.md:64`（Q4） | 决策表仍写 **「A there is structurally empty」**，而 §4.3 已声明此说错误。决策表通常被当「冻结真理」——比正文脚注更毒。 |
| **minor** | `power-calibration.md:67`（Q7） | 仍写 power 大跑「scheduled around **ticket 03**」；§12 已改 08。决策表与调度裁定不一致。 |
| **minor** | `power-calibration.md:63`（Q3） | 「**exact** size mirror」——§2/§5 已改口 data-side / directional size；「exact」过誉回潮。 |
| **process** | `05-*.md:6`、`09-*.md:6` | 修订节改了 Blocked-by，**YAML 头未改**。map 对、票头错——下一轮派单的经典翻车点。 |
| **process** | `map.md:41-43`「Decisions so far」 | 仍写 01 v2、`max\|t\|`、`Blocked by 01+03`、02「court 内核不动」。收官段（:74+）已重宣，**摘要段是僵尸 v2**。 |
| **nit** | `map.md:47-56`「Not yet specified」 | 01/02/03/10 设计问仍列 open——与收官重宣互斥。历史区该归档或删。 |

未发现**新的统计设计洞**（没有新的错误 P(win) 公式、没有新的选择–判决分叉被写进主路径）。问题形态是：**主路径修了，索引层（决策表 / B 公式 / 票头 / map 摘要）没机械 grep 清场。**

---

## 漏改清单

### 相对 `verdict.md` minor

实质 minor **基本都进了**（种子、B 估计、R=120、provenance、哈希钉、10 条款、10a 票）。  
**漏的是传播面**，不是「某 minor 条目完全没动」：

1. 01 **§3 决策表**未与 §4–§6 修订同步（Q3/Q4/Q7）——verdict 要求改的是设计口径，表是口径的权威摘要。
2. 05/09 **frontmatter Blocked-by** 未与修订节对齐（verdict D13/D15 明确改 blocking）。
3. map **历史 Decisions 行**未重写（状态通胀的同类问题：新段诚实、旧段撒谎）。

### 相对我上次 `report.md`（对等问责）

| 上次批评 | 本次 |
|---|---|
| 01↔03 选择≢判决 | 主路径已修；**B 公式残渣**算未清干净 |
| P(win)@1.5≈1% 我的错 | 已按 argmax t 重算；Q4 表残留 empty 话术 |
| universe 无 declared 侧 | D7 run_config ✓ |
| 05 是否 certified 沉默 | 裁定 uncertified ✓ |
| 05 应否 block 08 | 已加（我上次偏「主要是 01」；裁定走 schema 债，合理） |
| 09 不知 role / block 过窄 | role+06 ✓；票头未改 |
| killer-demo 五关双写 | ✓ |
| court 零改动 overclaim | ✓ 三处诚实列出 |
| 10-refactor 无票 | ✓ 10a |
| map 收官过满 | ✓ 重宣；摘要段仍脏 |
| 建议 02 机械检查 selection≡direction | **未做**——verdict 未列为必改；可接受为 v0.2 外增强 |
| LM1「三地雷成立」（我的 audit-error） | 已按 Panel A 纠正；03 v2 正确退休 |

**无静默丢弃的 major/blocker 级批评。** 漏的是扫尾。

---

## 刻薄结论

这次修订的统计与威胁模型部分，是**认真折入**而不是「§13 日志冲业绩」：数字对、F1-A 选对、D2 对照臂改对、02 边界写得比 v2 诚实一个数量级。

不及格的地方很「指挥官」：**改了长段落，没对冻结表做 `rg 'max\|t\||structurally empty|Blocked by'`。**  
D1 修完后 §5 还留着 `max|t| ∧ t>0` 当 B 的定义——这不是文风问题，是**会进 05 实现**的公式。Q4 决策表还在复读已被 §4.3 判处死刑的「structurally empty」。票头 Blocked-by 与修订节双写，赌工人会读到第二节——在这个项目的派单纪律下，这是**已知翻车模式**。

### 终冻结前最小 diff（4 刀）

1. `power-calibration.md:187` → `P(argmax t = injected | strength)`  
2. `power-calibration.md:64` Q4 → 删 structurally empty，对齐 §4.3「低带 A 如实报 n_won」  
3. `power-calibration.md:63,67` → exact→data-side；ticket 03→**08**  
4. `05`/`09` frontmatter Blocked-by 与修订节对齐；`map.md` Decisions 三行改 v3 摘要  

做完这 4 刀，**可终冻结（A−）**。现在：**B−，还差扫尾，不配写「设计层收官可直接施工」**——但已经比审计对象 v2 强一个档，**不必推倒重写**。