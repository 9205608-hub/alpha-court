# 06 BHY 多重检验研读

Type: research
Status: resolved
Assignee: dispatched to grok worker via M0 bridge (worker ticket: ../../dispatch/v0.1-06-bhy-literature/ticket.md)
Label: wayfinder:research

## Question

从公开文献干净重写 Benjamini-Hochberg-Yekutieli FDR 控制所需公式，产出实现级研读笔记（asset: `docs/research/bhy.md`）：

- Benjamini & Hochberg (1995), "Controlling the False Discovery Rate", JRSS-B；Benjamini & Yekutieli (2001), "The Control of the False Discovery Rate in Multiple Testing under Dependency", Annals of Statistics
- 需要逐条落下的：BH 阶梯判据；BY 依赖修正因子 c(N)=Σ1/i；p 值从哪来（因子 IC 序列的 t 检验？Newey-West 修正与否）；与 Harvey, Liu & Zhu (2016) "…and the Cross-Section of Expected Returns" 中金融语境用法的对照。
- 每步给出：原文出处、与代码变量的映射、手算测试向量（一组假 p 值→哪些被拒绝）。
- 记录实现陷阱：单边 vs 双边检验、因子间相关性强时 BH vs BY 的选择依据、和 ledger 的 N 口径对齐。

AFK 票。约束：只引公开文献，不搬任何前实习单位内部实现。

## Answer

grok 工人交付 `docs/research/bhy.md`（745 行），对抗验证：数值重算全过（c(10)=7381/2520 精确一致），但验收镜头判 fail——1 个 blocker（文档内含 Python 代码块，违反 NO-code 铁律）+ 1 个系统性 major（全部 HLZ 精确引用误用 NBER 工作论文编号，参考文献却列发表版 RFS；referee 对照真 PDF 给出逐条映射）。返工后逐项修复收货（2026-07-10，commits `fa4f560`+`ad6baa8`）：

- BH 阶梯判据（1995）、BY 依赖修正 c(N)=Σ1/i（2001）、HLZ 金融语境（RFS 2016，发表版编号 §3.3.2/§3.4.1-3/脚注 24/26/§3.7.2）。
- N=10 双程序（BH & BY）手算表：BH 拒 9、BY 拒 3；阈值比恰为 c(10)（对象已修正为 critical-value ratio）。
- 历史术语坑已注明：BH 1995 原文自称 "step-down"（2001 前旧术语，与现代惯例相反），术语锚点改挂 BY 2001。
- 实现陷阱：step-up 方向、q 值单调化、tiny-p 是下溢/精度问题而非上溢、N=1 行为。
