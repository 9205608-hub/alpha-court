# 05 PBO/CSCV 文献研读

Type: research
Status: resolved
Assignee: dispatched to grok worker via M0 bridge (worker ticket: ../../dispatch/v0.1-05-pbo-cscv-literature/ticket.md)
Label: wayfinder:research

## Question

从公开文献干净重写 Probability of Backtest Overfitting（经 CSCV）所需全部算法细节，产出实现级研读笔记（asset: `docs/research/pbo-cscv.md`）：

- Bailey, Borwein, López de Prado & Zhu (2017), "The Probability of Backtest Overfitting", Journal of Computational Finance（及其 SSRN 2013 版本）
- 需要逐条落下的：CSCV 的组合对称切分（S 个等长子块、C(S, S/2) 种组合）；每种组合上 IS 最优策略在 OOS 的相对排名 → logit λ；PBO = P(λ < 0) 的估计；对输入矩阵 M（T×N，N 个 trial 的收益序列）的形状与对齐要求。
- 每步给出：原文出处、伪代码、复杂度（C(16,8)=12870 这类组合数的计算成本评估）、可手算的小规模测试向量（如 S=4）。
- 记录实现陷阱：序列长度不齐怎么办、S 的默认取值与敏感性、性能指标用 SR 还是可插拔。

AFK 票。约束：只引公开文献，不搬任何前实习单位内部实现。

## Answer

grok 工人交付 `docs/research/pbo-cscv.md`（652 行），对抗验证三镜头全 pass-with-nits、零 blocker 零 major，3 个 minor 返工后收货（2026-07-10，commits `e9ec55b`+`2e0a2f2`）：

- CSCV 全流程带伪代码 + S=4/N=3/T=8 手算测试向量（6 个组合逐一展开，referee 重算一致，PBO=1/2），可直接做 pytest 基准。
- **两处论文自身勘误被显式标记**：印刷版 C(16,8)=12,780（正确为 12,870）；Alg. 2.3(c) 把训练集 J 误标为 "testing set"。
- **关键实现口径**：λ_c<0 ⟺ r̄<(N+1)/2，与论文 Eq.(2.2) 字面的 N/2 阈值在偶数 N 时不一致（论文内部不自洽，本笔记按 λ 规则实现并显式声明）——实现票必须按此口径写测试。
- 留给实现票：metric 可插拔（默认 SR）、平局约定、不等长序列拒绝策略。
