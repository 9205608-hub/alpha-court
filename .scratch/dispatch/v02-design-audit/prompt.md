# 任务：alpha-court v0.2 设计层里程碑审计（审设计契约，不审代码实现）

你是 grok-4.5。在这个项目里你是 v0.1 主力施工工人，也做过两次审计：一次角色反转
meta-review（审指挥官过程，打 B），一次 v0.1 里程碑技术审计（审产品，判"稳但有保留 · B"，
你漏了 DSR 反保守那条、Claude 独立面板抓到）。**这次审的是 v0.2 的四张设计契约本身**——
在 ~1.5–2 天的实现施工开始之前，把设计缺陷抓在图纸上。

一个必须正视的事实：**这四张契约的 grilling 你都参与过批审**（`.scratch/dispatch/
v02-power-grill/`、`v02-03-grill/`、`v02-02-grill/` 是你的裁定，其中 ICIR 锁错、
tamper-proof 过誉都是你抓的）。你现在审的是**折入你的意见之后冻结的版本**——审自己参与
设计的东西有盲点，v0.1 你就漏了自己代码里最重的 bug。这次刻意去找：**你当时没抓到的、
以及"折入你的裁定"这个动作本身引入的新错**。你的旧裁定不是免检品。

一句话问题：**这四张契约，每张单独 sound 吗？四张互相一致吗？按 map 的实现顺序走得通吗？
合起来是不是一个自洽的 v0.2？** 指挥官现在的判断是"设计层收官、可进纯实现"——请你用证据
支持或推翻。

## 你的工作区（只读，HEAD=20b3f53，v0.2 设计层收官 + workflow 线合并后）

`cwd` 是本仓库只读检出。**不要改任何文件**，读完把审计意见作为文本输出。
python / git 可用——**凡是能真跑核验的主张（数值、公式、代码行为、git 事实）就真跑，
不许臆断**（你上次审计跑 python 逮错的先例就是标准）。

### 审计对象（四张契约，逐字读）

- `docs/design/power-calibration.md`（v2，网格已冻结）
- `docs/design/selection-verdict-isomorphism.md`（v1）
- `docs/design/prereg-gate.md`（v2）
- `docs/agents/dispatch-and-governance.md`（v1）

### 地基与对照材料（契约的每个声称都可以对着这些核）

- 内核 spec：`docs/design/court-kernel-spec.md`（含 C4/G5 勘误与 03 amendment）
- 既有契约：`docs/design/{trial-ledger,noise-control,adapter-interface,killer-demo}.md`
- 文献锚：`docs/research/{dsr,pbo-cscv,bhy}.md`
- v0.2 地图与票：`.scratch/v0.2/map.md`、`.scratch/v0.2/issues/*.md`（blocking 图在 map）
- 代码现实（契约说"court 不动/`_append_event` 无 sort_keys/adapter `_meta` 已有背书字段"
  之类的声称，逐条对代码核）：`court/`、`adapters/qlib_cn.py`、`examples/killer_demo/`
- 真实判决数字：`examples/killer_demo/out/report.md`
- `CONTEXT.md`（术语）、`README.md`、`TIMELINE.md`（全程账）

## 审计维度（每条要有 file:line 或跑出来的数字级证据，不许空评）

### 1. 单张 soundness（×4，最重）

以每张契约自己的目标审它：

- **01 power 标定**：实验设计统计上成立吗？条件化（A 只在 won 上估计）的偏差处理够吗？
  冻结网格（A 密 2.0–5.0）的推导对吗——那几个"闸门开启阈值"的换算你能复算吗？
  β→ICIR 标定程序（K=64 冻结种子、轴不回写）有没有自由度漏洞？R₀=40 自适应补种到
  n_won≥20 的种子协议会不会引入选择效应？共享噪声池 cross-β 复用/跨种子禁用的边界对吗？
  β_t 半窗附录设计打得中 PBO 乐观偏吗？
- **03 选择–判决同构**：DSR two-sided 弃权的三条地雷论证（N→2N 错/翻号反保守/PSR 偏度
  不对称）站得住吗？PBO 换 |ICIR| 的"CSCV 度量 agnostic"论证对文献（`pbo-cscv.md`）站得住
  吗？role: discriminating/informational 的派生规则有没有边界情况没写死？
- **02 预注册闸**：威胁模型（agent 自欺：缩 scope/藏 trial/事后改 declared/回填聚合）与
  机制（认证路径 + 哈希链 + seal + attest）匹配吗？**站在攻击者立场找绕过**：合法 API 下
  还有哪条自欺路径没堵？fail-closed 清单（§5）漏了哪种违规？哈希链设计（内容不含真钟、
  sort_keys、固定 float 编码、torn-write 兼容）有没有自相矛盾或实现不了的点？
- **10 dispatch+治理**：最小 worker 契约够不够真接第二个 CLI？RP-1 三触发点绑定有没有
  空转（写了触发点但没有任何东西保证触发）？

### 2. 跨契约一致性

四张互引处逐个对：01↔03 的 directional 分支（power 声称 declared=greater 时 battery 全形
态，与 03 的 role 规则、spec F2 的定向统计量，三处说法完全一致吗？）；02↔03↔09 的聚合上
链缝（"聚合策略先于首 verdict 上链"与 role 判定时派生，谁先谁后有没有环？）；02 的
attestation 字段清单 ↔ ledger schema（spec §5.7 `DeclaredProtocol`）↔ adapter 实际的
`_meta`（`adapters/qlib_cn.py` 真代码）三方对得上吗？01 与 killer-demo 的"镜像"声称
（size 锚在 directional run 里还是不是 killer demo 的 size？）。任何两处说法不一致、
字段对不上、语义漂移都点名。

### 3. 可实现性

按 map 的 blocking（06→07→09→08→05）走一遍脑内实现：有没有隐藏死锁？票面
（`.scratch/v0.2/issues/0[5-9]*.md`）的范围与契约承诺有没有错位（契约答应的事没票接、
票接的事契约没定）？"court 内核不动"的声称在 06 的实际改动清单下还成立吗？05 的
Blocked by 清单（01+03）真实吗——power harness 需不需要 08 的实现、走不走 06/07 的
认证路径，契约写死了吗？

### 4. 合起来自洽吗

v0.2 走完（05–09 全落地）之后，宪章"不会骗自己的挖因子 agent"的承诺哪些成立、哪些仍是
洞？有没有两张契约各自 sound、合起来互相拆台的地方？v0.2 收官时对外能诚实说什么、
不能说什么？

### 5. 最锋利的 3 条

若只许在施工前改三处设计，改哪三处（文件+节 + 为什么 + 不改的代价）。越具体越好。

## 输出要求

中文纯文本。诚实刻薄优于礼貌空洞。先给**总评**（v0.2 设计层作为施工图纸：可直接施工 /
修后施工 / 须返工，一句话理由 + 一个字母评分 A–F），然后按五维逐条给证据化意见，最后是
"最锋利的 3 条"。如果指挥官"设计层收官"的判断有水分（该定没定的地方说成定了），直接点名。
如果你发现自己当年批审折入的裁定本身是错的，如实报——这正是这次审计的价值。
