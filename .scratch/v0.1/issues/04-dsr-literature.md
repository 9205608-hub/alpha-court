# 04 DSR 文献研读与公式核对

Type: research
Status: resolved
Assignee: dispatched to grok worker via M0 bridge (worker ticket: ../../dispatch/v0.1-04-dsr-literature/ticket.md)
Label: wayfinder:research

## Question

从公开文献干净重写 Deflated Sharpe Ratio 所需的全部公式，产出实现级研读笔记（asset: `docs/research/dsr.md`）：

- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality", Journal of Portfolio Management
- 需要逐条落下的公式：非正态修正的 PSR（Probabilistic Sharpe Ratio，含偏度/峰度项）；N 次试验下期望最大 Sharpe E[max SR]（含欧拉-马歇罗尼常数的近似式）；试验方差 V[SR] 的估计口径；DSR 最终判据。
- 每个公式给出：原文编号、符号表、与代码变量的一一映射计划、至少一组可手算的测试向量（用于 tdd）。
- 记录实现陷阱：年化 vs 原频率、自相关时的 SR 方差、N 与 V[SR] 从 ledger 哪里来。

AFK 票。约束：只引公开文献，不搬任何前实习单位内部实现。

## Answer

grok 工人交付 `docs/research/dsr.md`（782 行），对抗验证面板（数值重算/公式引用/票面验收三镜头）裁决：重算全过、零 blocker 零 major，6 个 minor 打回返工后逐项修复收货（2026-07-10，commits `67958bf`+`11e53cc`）：

- 覆盖 PSR（2012 Eq.(8)/(11)，含 Mertens 方差的展开式↔坍缩式代数等价声明）、E[max SR]（2014 Eq.(1)，显式标注 ≈ 与 N≫1 的 EVT 近似条件）、DSR 判据（2014 Eq.(2)，SR̂₀→SR̂* 改名已声明）。
- 每个公式带论文式号+符号表；测试向量手算到 ≥6 位有效数字（referee 独立重算一致），可直接做 pytest 基准。
- 实现陷阱：年化口径、自相关、独立 trial 数 vs 台账原始计数、跨 trial SR 方差估计、相关矩阵病态条件 T < ½M(M−1)（论文 App. A.3 原始条件，非 M>T 特例）。
