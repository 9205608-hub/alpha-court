独立核验开始：先定位产物与 git 历史，再逐条真跑取证。头版数字已对齐；接着真跑 ledger replay，并核验 roles、DSR/PBO 与报告叙事。发现噪声对照的 p̂ 取样可能看错事件；继续做干净的 ledger 重放，并核对校准附录与若干边角。# 独立核验报告：killer-demo 真数据重生成（v0.2-08 收尾）

**总评：产物可收。**  
第二只眼未抓到阻塞级真问题。08 方向机 / role / `abs_sharpe` 在 100 因子真数据上行为与 `killer-demo.md` §6 v0.2、`selection-verdict-isomorphism.md` v2 一致；头版选择统计跨 numpy/scipy/python 版本逐字稳定；ledger 链可 replay、可被篡改检测。下面只有精度与元数据层面的 nits，不构成拒收。

对照基线：`0f93e4d7`（v0.1-11a）→ `198a2733`（regen HEAD 附近）。

---

## 1. 头版逐字稳定（确定性承诺）

**结论：头版选择数字字节级相等；battery 表有意变更（role / PBO 口径），不是漂移。**

| 字段 | 旧版 `0f93e4d7` | 新版 HEAD | 相等？ |
|---|---|---|---|
| Survivors | `0/100` | `0/100` | 是 |
| Accused | `volatility_lb150_v14` (`t-000055`) | 同左 | 是 |
| direction / \|t\| / t / naive p / ICIR | `contrarian, \|t\|=2.6655, t=-2.6655, naive p=0.007686, annualized ICIR=-1.9314` | **整行字节相同** | 是 |
| Figure 元信息（T=480, seed, data tag, engine） | 同 | 同 | 是 |

**更强指纹（不在头版，但支持“同一批 IC 序列”）：**

- 100 条 evaluation series SHA-256：**0 mismatch**（含 accused `sha16=e72191cfec5f59b8`）
- FDR `t` 向量：**bit-identical**；`argmax|t|` 仍为 index 54 = `t-000055` = −2.665544143748227
- FDR `p` 向量：54/100 个值差 **1 ULP（1.11e-16）**；四位/六位小数与头版展示 **0 处变化**
- morgue 表 `name/family/φ(AR1)/|t|/naive p/FDR p/indiv/status`：**仅** accused 的 `1/5 → 1/4`（口径修订，见下）

**Battery 故意变的（不算头版失稳）：**

| 项 | 旧 | 新 | 是否合理 |
|---|---|---|---|
| Role 列 | 无 | 有 | 08 契约 |
| DSR | reject，无 abstain 文案 | reject + informational + abstain 脚注 | 设计 |
| PBO φ | `0.4731`（`metric=sharpe`） | `0.5197`（`metric=abs_sharpe`） | 同构修复，φ≈0.5 仍在噪声中心 |
| accused gates | `1/5` | `1/4` | 判别关 4 票 |

**nit（非拒收）：** 跨版本不是“全浮点 bit-stable”。`t`/series 是；`p` 有 ULP 尘埃。头版与报告可见位数仍逐字相等。环境实际是 **numpy 2.4.6→2.5.1 + scipy 1.17.1→1.18.0 + python 3.11.2→3.12.8**，比“只换 numpy”更猛，头版仍稳。

---

## 2. 账本内部

**结论：chained + role 齐全 + DSR 债清 + PBO metric 正确；`Ledger.open` 副本 replay 通过。**

| 检查 | 证据 |
|---|---|
| 首事件 chained | `prev_hash=0…0`（genesis），`event_hash` 已写 |
| 事件计数 | 404 = 100 hyp + 100 trial + 100 eval + **104** verdict |
| role 分布 | **103 discriminating + 1 informational**；`missing_role=0` |
| 结构 | `noise_control×101`（100 individual + 1 pool_max）+ fdr + dsr + pbo |
| informational 身份 | 唯一一条 = `statistic=dsr`，`decisions={'t-000055':'reject'}` |
| `computed.dsr` | **有**：`1.140609058210923e-07`（v0.1 缺该键已清） |
| PBO `params.metric` | **`abs_sharpe`**；`phi=0.5197358197358197`，`C=12870` |
| 真跑 replay | 副本 `Ledger.open` → 100 trials / 104 verdicts；`chain_head` == 末事件 hash |
| 篡改检测 | 改中间 `event_hash` → `LedgerCorruptionError: event_hash mismatch` |

对照旧账本：`0f93e4d7` **无** `event_hash`、**无** `role`、DSR `computed` **无** `dsr` 键、PBO metric=`sharpe`。重生成确实落地了 06/08 债。

**DSR 路径数值与旧版 bit 级一致**（`sr_star` / `N̂` / `ρ̂` / `z` / `sr_selected` 全等），只是多写了 `dsr` 概率值。

---

## 3. 报告叙事 vs 设计

**结论：无旧叙事残留；与 §6 v0.2 / isomorphism v2 对齐。**

扫过 `report.md` 全文：

| 旧叙事（应消失） | 结果 |
|---|---|
| PBO signed / internal selection is signed | **0 hit** |
| five gates / `0/5` / `1/5` | **0 hit** |
| “DSR is one-sided by construction; rejects immediately” 当投票关 | **0 hit** |

| v0.2 应有标记 | 结果 |
|---|---|
| Role 列 + discriminating/informational | 有 |
| DSR abstains under two-sided | 有 |
| `metric=abs_sharpe` | 有 |
| accused `1/4` | 有 |
| 脚注引用 §5.4 / §6 v0.2 | 有 |

脚注现文案与设计一致：DSR informational、不入票；PBO abs metric 同构于 \|t\| 扫描。尸检段 `#### dsr → **reject** (role=informational)` 与 battery 一致——**decision 仍记 reject，role 标 informational**（设计是“算并展示、不计票”，不是第三态 `abstain` 决策值）。

---

## 4. `run_config` 变化的诚实性

**结论：diff 只有环境戳；没有偷塞 v0.2-09 的 policy/aggregation。**

```diff
- numpy_version: 2.4.6
+ numpy_version: 2.5.1
- scipy_version: 1.17.1
+ scipy_version: 1.18.0
- python_version: 3.11.2 ...
+ python_version: 3.12.8 | conda-forge ...
```

不变且关键：`master_seed`、`offsets`、`accused_*`、`n_survivors=0`、`gate_verdicts`、window/T/S/B/阈值。

| 该有吗？ | 现状 | 判定 |
|---|---|---|
| policy / discriminating-only aggregation 口径 | **无** | 正确（票说 v0.2-09 才落） |
| role 字段 | **无** | 可接受的预 09 缺口，不是撒谎 |
| `gate_verdicts.dsr=reject` 仍扁平五关 | 仍有 | **轻 nit**：摘要仍把 informational DSR 和判别关并列，读 config 的人看不到 role；report/ledger 已正确 |

不是“该记没记的 v0.2-09 字段”，也没有伪造环境之外的业务参数变化。

---

## 5. 08 代码在真数据上的行为

**结论：方向机 / role / abs_sharpe / 判别关聚合正常；头版 0/100 与四判别关叙事自洽。**

### 方向与 role

- 100 trial 全部 `declared.direction=two-sided`
- DSR → **informational**（唯一）
- FDR / PBO / pool_max / 100×individual → 全部 **discriminating**
- informational **未**进入 survivor 计票（自复算 disc-only survivors = **0**）

### Accused `t-000055` 四判别关

| Gate | role | decision |
|---|---|---|
| fdr_by | discriminating | **reject** |
| pbo_cscv (`abs_sharpe`) | discriminating | **reject**（φ≈0.52） |
| noise pool_max | discriminating | **reject**（p̂=0.575） |
| noise individual | discriminating | **pass**（p̂=0.015） |
| dsr | informational | reject（**不计票**） |

→ 判别关口径下 **1 pass / 3 reject → 死**；morgue `1/4` 与 ledger **0 mismatch**。  
individual 过关不能救命：死于 **FDR 或 PBO 或 pool-max**（三者皆 reject），与“多重检验 + 选择同构 + 池最大”叙事一致。

### 其余 individual pass 的 5 个非被告

`t-000006/028/050/077/089`：individual pass，但 **一律死于 FDR**（faced=2，passed=1）。校准附录 6/100 individual pass ≈ 5% 期望，合理。

### φ / abs_sharpe 是否可疑？

- PBO φ **0.5197**（旧 signed **0.4731**）——全局 null 下两者都应 ≈0.5；换 abs 后仍贴噪声中心，**不像算错**。
- `n_lambda_negative/C = 6689/12870 = φ`，内部自洽。
- morgue 列名 `φ` 是 **AR(1) 生成器参数**（0.2–0.999），不是 PBO φ——**旧命名债**，不是本次 regen 引入的错误。

### DSR 与 contrarian accused

- `t=-2.6655`、`sr_selected=-0.12166`、`dsr≈1.14e-7` → 负 SR 上 one-sided DSR 必然 reject；标 informational 后不进票，避免“用错误同构关把被告再杀死一次”的叙事污染。行为正确。

---

## 第二只眼可记账的 nits（非拒收）

1. **原始 p 向量非 bit-stable**（54×1ULP），报告/头版不可见——承诺应表述为“头版与可见位数稳定”，而非“全 float 跨版本 bit-identical”。
2. **`run_config.gate_verdicts` 仍扁平五关**，不含 role——09 的事；现在不算违约，但摘要层略钝。
3. **morgue `φ` 列名**易与 PBO φ 混淆（预存）。

---

## 裁定

| 维度 | 裁定 |
|---|---|
| 头版确定性 | **通过**（选择统计字节稳；battery 有意变） |
| 账本链 / role / DSR 债 / abs_sharpe | **通过**（真跑 replay + 篡改检测） |
| 叙事 vs 设计 | **通过**（旧五关/signed PBO 已清） |
| run_config 诚实 | **通过**（仅环境戳；无抢跑 09） |
| 08 真数据行为 | **通过**（0/100；accused 死于 3 个判别 reject，individual pass 不救命） |

**产物可收。** 本轮第二只眼：**worker 胜诉空间 ≈ 0**；无 contract-fault / worker-fault 级缺陷可写入 attribution ledger。若硬要记一条 light observation：跨版本 p-ULP 与 `run_config` 仍无 role——都不挡 v0.2-08 验收关门。