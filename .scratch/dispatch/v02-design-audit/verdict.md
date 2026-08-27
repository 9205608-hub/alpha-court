# v0.2 设计层里程碑审计 — 裁定书

日期：2026-07-12。审计对象：四张 v0.2 设计契约（01 power / 03 同构 / 02 预注册闸 / 10 dispatch+治理）@ HEAD `20b3f53`。

## 审计设置（RP-1 触发点 3：里程碑审）

五路独立、全盲（互不见对方输出，均未获喂任何疑点清单）：

| 路 | 身份 | 产物 |
|---|---|---|
| grok（无头 high-effort，只读 worktree） | 曾参与全部四张契约批审的工人/审计者 | `report.md`（修后施工 · C+） |
| Panel A（Claude 独立子面板） | 统计镜头（01+03） | `panel-a-report.md`（修后施工，01=B−，03=B） |
| Panel B（Claude 独立子面板） | 机制/威胁模型镜头（02+10） | `panel-b-report.md`（修后施工，02=C+，10=B+） |
| Panel C（Claude 独立子面板） | 跨契约一致性+可实现性镜头 | `panel-c-report.md`（修后派单，B−） |
| 指挥官 | 通读盲写 seam 清单，先于一切输出 commit | `commander-seams.md`（S1–S4） |

裁判（指挥官）对争议与关键主张独立复算：`referee-verify.py` / `referee-verify-2.py`
（MC P(win)、截尾攻击复现、E[max] 数值积分、种子撞树、半窗机制轻量复现）；票面指控
（06 无链无 universe、05 验收缺项、09 Blocked-by、10-refactor 无票）逐条 grep 原文核实。

## 总裁定

**修后施工。四路总评强收敛（C+ / B− / C+·B+ / B−），无一路判"可直接施工"。**
**"v0.2 设计层收官、进入纯实现"判断撤回**——修下述 5 个 BLOCKER 后才收官。
指挥官盲写的 4 条 seam 全部被至少一路独立命中（S1=D6、S2=D7、S3=D1、S4=D13），
且各路挖得都比 seam 深。

## 跨模型互抓（本次审计的方法论实证，入 meta-review-ledger）

1. **grok 自曝旧错**：P(win|ICIR=1.5)≈1% 是它上轮批审折入的数——固定均值近似漏掉 t 的
   实现噪声；真值 ≈0.267（grok MC、Panel A MC、裁判 MC 三方一致）。
   **"批审意见折入冻结文本前未独立复算"故障模式第二次实证**（第一次是 ICIR 锁错的反面）。
2. **Panel A 抓 grok 的新错**：grok 本次报告称 03 三地雷"复算成立"，其 LM1 的
   "错 2N 近似 |t|≈3.26" 实为 √(2·ln200) 渐近项；裁判数值积分：E[max|Z|,100]=2.7470 vs
   E[max Z,200]=2.7460，**差 0.0009，比 DSR 已容忍的 EVT 误差（0.0230）小 25 倍**——
   LM1 哑火，Panel A 胜诉。**裁判也会错的对等问责：grok 作为审计者本次记一笔。**
3. **裁判独立复现**：Panel B 的截尾攻击（真 Ledger 删末行 evaluation → replay 零报警）
   复现成立；Panel A 的半窗机制混淆轻量复现成立（强度匹配下 φ 0.05→0.14，
   强度减半才是 0.38 的主因）；种子撞树 `SeedSequence(20260711).spawn` 撞 sweep 实证 True。

## 裁定明细（对表矩阵）

严重度 = 裁判终审。命中路：G=grok, A/B/C=面板, S=指挥官 seam。归因：design-fault =
契约/指挥侧；audit-error = 审计路自身错误。

### BLOCKER（5 条，不修不派单）

| # | 裁定 | 命中 | 归因 |
|---|---|---|---|
| **D1** | **01↔03 选择–判决不同构**：power 用 `max\|t\|` 选择（two-sided）+ `greater` 判决；01 §5 缓存方案仍写"199 列陪审 **\|t\|**"（03 amendment 漏改的尸块）；99 噪声 trial 的 declared 未写死；§4.3 gate 表混用两侧（FDR 3.9）与单侧（pool-max ≈3.3）口径；"exact size mirror"过誉——β=0 锚在 greater battery 下含 DSR 投票，非 killer-demo 的 size；β=0 时 n_won≥20 需 ~4000 种子 ≫ cap 120，§6 的 size 断言估计量未定义。**需 HITL 拍板选择规则**（见修复方案 F1） | G+A+C+S3 | design-fault（03 打补丁时未闭环回 01 §5；正是 03 要杀的"选择≢判决"写进最贵交付） |
| **D2** | **01 §7 β_t 半窗附录对照测错机制**：同名义 β 对比中 ~85 个百分点来自强度减半、episodicity 仅 ~7pp（CSCV 全组合模拟 + 裁判轻量复现）；契约明文拒绝了正确对照（"not average-β"）。跑完只能在"错误归因入 hero 脚注"与"事后改预注册"两个违宪选项里选 | A（独家） | design-fault |
| **D6** | **02 锚时序自相矛盾**：§4.3"锚一次于 seal"（结果之后）vs §5"锚不早于 series → seal 无效"（要求结果之前）vs §7 先例（锚在前语义）。按字面每个带锚 seal 恒无效；07 工人无从实现 | B+S1（G 擦边） | design-fault |
| **D7** | **02 conformance 等式左边缺半边**：Q4/§5 要查 attested==declared 含 universe/*_version，`DeclaredProtocol` 无此字段；06 票丢词、07 票不知情；更深层——`label_expr/provider_uri/data_tag`（"地面真相的定义"）整个 run 不锁：一 run 内换标签定义/数据包，§5 全绿、seal 有效。**修法收敛于 Panel B 的 run 级 `run_config` 上链声明事件**（不动 DeclaredProtocol、不违"court unchanged"） | G+B+C+S2（四路全中） | design-fault |
| **D13** | **05 的真 blocker 是 08 + 三问沉默**：role 入 verdict 是 08 的 schema 改动，05 先跑必复刻"committed ledger 落后一字段"之债（Option 1 防错了对象——防 03 设计变，没防 08 schema 变）；power 走不走 06/07 认证路径（走则"一 Run=一 family"对 ~14β×R 种子的映射无人定；不走则 v0.2 旗舰实验是 uncertified 产物，与"焊成不会被绕过的法庭"张力大）、聚合读不读 09 config、05 票验收只覆盖 01 §10 交付的一半、β→ICIR"已冻结"名不符实（β* 表不存在，标定从未跑）——契约与票面全部沉默 | G+C+S4 | design-fault + map 状态通胀 |

### major（10 条）

| # | 裁定 | 命中 | 处置 |
|---|---|---|---|
| D3 | 01 §4.3 P(win) 数字错：1.5→**0.267** 非 ~1%（1.0→**0.103** 非 0）；"A structurally empty ≤1.5"错；2.0 的 ≈50% 是两种近似巧合交叉。低带 A 免费数据被预注册白白排除；2.3/2.6 补种负载被高估 | G(自曝)+A+裁判 | 重算 §4.3 全部括号数（带实现噪声）、删 "structurally empty"、低带 A 改"如实按 n_won 报告" |
| D4 | 03 §3 三地雷两条哑火：LM1 被数值证伪（差 0.0009）、LM3 可由"翻转序列重算矩"实现消解；仅 LM2 真（0.239 SR-std 反保守缺口）。**弃权结论不变**（引用铁律 + pool-max 承载同构），论证重写 | A（独家，胜 G） | §3 重写为"LM2 + 引用铁律"两点论证；LM1/LM3 降脚注 |
| D5 | 03 `less` 分支照字面实现是错的（signed metric 喂 argmax 选到最正列，同构反了；DSR 对 less 需翻序列跑原版）；混合方向 scope 的 family 级 role 未定义 | A（独家） | Q2 表补 `less` 负号形式 + 翻转约定；异构方向 scope → raise |
| D8 | 截尾攻击零痕迹（实测）：seal 前无锚窗口，删末行 evaluation 与诚实"未评估"逐字节不可区分；§9"tamper→verify fails"对删除不成立 | B（独家，裁判复现） | §5 补"seal 必须是账本末事件"；§6 补披露第四条 |
| D9 | 认证路外预筛洗白：§1"the full search the agent ran"被 Q2 的 legitimate uncertified 否定——环外扫 1000 挑 5 上认证路，得有效 seal N=5 | G+B | §1 措辞收窄 + §6 补第五条边界 + RP-1 追问规则 |
| D10 | 进程内伪造 attestation（无签名 dict）可得有效 seal，(B)"绕过可检测"对此路径为假；"leaves a reflog"过誉 | B（独家） | §2/§6 重框 seal 证明范围；禁止 07 做进程内安全戏剧 |
| D11 | run 拆分/run 购物未挡未披露（§8 只封合并方向）；restart-until-lucky 零成本 | B（G 擦边） | §6 补条 + "出示任一 sealed run 须出示全部兄弟 run"RP-1 规则 |
| D14 | 哈希链+规范序列化无属主票：06 票面零字提链（grep 证实），07 文件边界碰不到 ledger——06→07 链条必断 | C（独家） | 06 票补链字段+sort_keys+float 编码+篡改红测 |
| D15 | 聚合策略"上链事件"无属主、无事件类型；09 只 block 02（真实依赖 06，与 07 seal 互引） | C+G | 裁定事件类型归属（建议 06 扩词表）；09 Blocked-by 改 02,06(,07) |
| D16 | 并行派单冲突矩阵缺失：06/08/12 同挤 ledger.py、08/09 同挤 demo 且重生成顺序无裁定；08 的 role 落点（VerdictRecord 新字段 vs computed 键）与旧账本 replay 兼容未钉 | C+G | map 补冲突矩阵；顺序裁定 06→08→09、12 押后；08 票补 role 落点 |

### minor / nit（合并同类，全部入修复清单不丢弃）

- **02**：back-dating 防护措辞收窄为 reorder 防护（B）；`type` 是否入 content_hash 一句话定死 + `registered_at` 笔误（B）；fail-closed 缺条：seal 后追加/二次 seal/空策略/野 verdict（B）；anchor_ref 与 manifest 顺序环（B）；float 编码需递归预变换注记（B）；**`harness/` 包名已被 workflow 线三模块占用**（C，合并后新事实）；12 票 ensure_ascii 与 02 §4.1 互埋雷（C）。
- **01**：B=P(win) 在停规则下有偏 +4%，改用前 R₀=40 固定种子估计（A）；random-block 敏感性与半窗在 iid 下同分布、信息量降级注明（A）；标定残留两自由度（β 候选网格、φ median 未定值）（A）；**种子撞树实证 True**——标定根 20260711 与 sweep 保留区冲突，挪出（A+裁判）；R=120 最坏串行 ≈4.2 天入 05 票（A）；DSR/pool-max 表行口径出处注明（A+G）。
- **10**：receipt schema 无 commander 侧验证 + 工人契约补"全无头"条款（B）；tripwire 对 `.scratch/dispatch` 盲区一句披露（B）；**10 自身无 grill 档案**——本审计即补此档，10 的 trigger-1 记录在案（B）。
- **流程**：map 状态通胀（票面 needs-triage vs map "ready-for-agent"）（G+C）；10-refactor 无票（C，grep 证实）；spec amendment "ticket 11" v0.1/v0.2 撞号加 "(v0.1)"（C+G）；killer-demo.md §6 修订框与下文五关旧文双写（G）；02 §3 "court unchanged" 括号漏报链字段这第三处改动（B+C+G）。

### 审计路自身的错（对等问责，无静默丢弃）

| 路 | 错 | 裁定 |
|---|---|---|
| grok（本次） | LM1"复算成立"（3.26 = 渐近项误用） | audit-error，记账；不影响其它裁定的效力 |
| grok（上轮批审） | P(win|1.5)≈1% 折入冻结文本 | 源头 grok、**折入未复核是指挥官的责**——两笔分记 |
| 裁判脚本 | referee-verify-2.py 末行 placeholder 打印无意义 | 无害，注记于此 |
| Panel A/B/C | 经裁判复核，未发现不实主张 | — |

## 修复方案（按票走，两类）

**F1 [HITL，唯一需用户拍板的设计决策]** D1 的选择规则二选一：
- **A（grok+Panel A 收敛推荐）**：power 是 greater-battery 自成体系实验——选择改
  `argmax t`、全部 100 trial declare greater、size 锚 = 同 battery β=0 重跑并显式标
  "directional size"、gate 表按单侧重算（FDR 3.73/pool-max 3.28）、§2"只有 mean-IC 改变"
  改写、killer-demo 的 two-sided 0/100 引为另一法庭的对照而非同实验 β=0。
- **B**：保持 `max|t|` 镜像——则 declared 必须 two-sided，DSR 在 power 上也 informational，
  §9"exercises DSR properly"整段删（接受 power 标定不了 DSR 真负载）。

**F2 [机械修，指挥官起草 + 批量过 grok 后落盘]** 其余全部 BLOCKER/major/minor：
02 修 D6/D7/D8–D11 + minors（含 run_config 上链裁定）、03 修 D4/D5、01 修 D2/D3 +
minors（含种子根迁移）、map/票面修 D13–D17 + 流程 minors。修订后的契约版本号递增
（01→v3、02→v3、03→v2），修订段落注明本审计为出处。

## 档案

`prompt.md`（审计票）、`raw.json`/`report.md`（grok）、`panel-{a,b,c}-report.md`、
`commander-seams.md`（盲写时间戳先于一切输出）、`referee-verify*.py` + 输出、本裁定书。
