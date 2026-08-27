# 01 power 标定协议设计（HITL grilling）

Type: grilling
Status: resolved
Triage: ready-for-human
Label: wayfinder:grilling

## Question

**v0.1 审计最大缺口**：法庭只被证明能**驳回构造噪声**（size），从没被证明能**放行真
alpha**（power）。README 已诚实披露"0/100 与永远驳回的 stub 同形，二类错误未测"
（`README.md` limitations）。v0.2 要让法庭**上一次构造的真案**。

本票拍板 power 标定协议（禁赢学：power 难看也如实报，且 size 与 power 必分表）：

1. **构造信号形态**：加性 alpha 面板（在 AR(1) 噪声上叠一层已知强度的可预测收益）vs
   可控 RankIC 均值注入？信号要与 killer-demo 的噪声壳同构（同 adapter 管线、同窗口、
   同宇宙），只多一层已知真信号——否则 power 曲线不可比。
2. **强度网格**：信号强度扫哪些点（如年化 ICIR 0 → 某上界的若干档）？每档多少个"真
   因子" + 多少噪声陪衬（决定 selection 语境）？
3. **报告口径**：TPR@α（在约定阈值上开始放行的比率）vs 信号强度曲线；同时报 size
   （构造噪声的假放行率，接 killer-demo 校准位）。**size 表与 power 表并列，禁止只报
   好看那张**。
4. **预注册**：power 实验的种子/强度网格/判决线先于首跑钉死（延续 killer-demo 的设计
   即预注册书；RP-0 留痕）。
5. **诚实边界**：构造信号 ≠ 真实市场 alpha；本实验证的是"法庭在已知信号上是否具判别
   力"，不是"能抓真 alpha"——报告首屏就要写清这层。

## 产出

`docs/design/power-calibration.md`（英文设计契约 = power 实验的预注册书），11 号验收票
与 05 实现票必引。拍板后关票，决策行入 map。

## Decisions（grilling-locked 2026-07-11，pending 一次批量 grok 复审）

七支决策树已逐题拍板，全文编码在 `docs/design/power-calibration.md`（DRAFT v1）。摘要：

- **Q1/Q1b**：主曲线 A = 法庭 ROC，**条件在真信号自然赢得 max|t|**；submission-power 单列
  附表（强制送审，DSR 非-max 偏保守脚注）；B = 自然胜出率（派生备注）。
- **Q2**（grok 亲裁）：**(b)** 保留真收益、因子掺未来收益（`β·oracle + √(1−β²)·noise`）；
  强度轴报**实现年化 ICIR**（β 预注册、只当内部旋钮，β→ICIR 冻结标定吸收方差通道）。
- **Q3**：1 真 + 99 噪声（N=100 镜像 size）；多真信号仅附录。
- **Q4**：预注册 β 网格跨真因子 ICIR 可信带 + 含 β=0 size 锚；网格首跑前冻结、落网格外不偷调。
- **Q5**：共享噪声池复用（省一个数量级）；R≈30–50 种子/强度；P(放行|已赢) 配 Wilson CI，
  欠功效如实标。
- **Q6**：hero = power 曲线；分闸 TPR + unanimous 都报；size 分面板；首屏诚实声称范围。
- **Q7**：只注入 β>0（β>0 让 DSR 终于干真活）；pool-max 一致性断言分支处理；DSR 偏严脚注；
  与 03 号票交叉引用。

## Answer

**Resolved 2026-07-11.** 七支决策树逐题 grilling 拍板 + 一次批量 grok 复审折回，预注册书
`docs/design/power-calibration.md` 定稿 **v2、强度网格已冻结**。

- **批量 grok 复审抓到一个真·锁错**（`.scratch/dispatch/v02-power-grill/`）：v1 把 β 网格锚
  到年化 ICIR 0.1–1.5——**会把主曲线 A 画在空集上**（N=100 噪声冠军已坐在年化 ICIR≈1.93，
  真信号要自然赢 max|t| 需 ICIR≳2.0）。校正为 §4.3 冻结网格：**A 密在 2.0–5.0**，0–1.5 只
  服务 B/submission，6.0 上界锚，强制单位脚注（项目年化 = 日度×√252≈16，业界"ICIR≈0.4"是
  日度非年化）。这是"多方交流才能达到最好"的实锤——错在指挥侧，跨模型批审 caught。
- **其余折入**：K=64 冻结 β→ICIR 标定（横轴报实现年化 ICIR，吸收方差通道）；成本模型订正
  （26.8s = 199-offset 网格非 battery）+ 共享噪声池缓存 + R₀=40 自适应补种至 n_won≥20（cap
  120）+ 跨种子复用禁止；won⇒argmax|t| 且 t>0（翻号护栏）；分闸 TPR 默认出图；β_t 半窗主
  附录（双极性）+ 随机 30 日块辅。
- **调度裁定（用户拍板 Option 1）**：05 power 大跑 `Blocked by: 01, 03`——网格/标定现在冻，
  等 03（选择–判决同构）定案再大跑，零浪费机时（避免 03 改 gate 致整图作废重跑 ~1.5–2 天）。

**产出兑现**：`docs/design/power-calibration.md`（v2，power 的预注册书）。11 验收票与 05 实现
票必引。**关票。**
