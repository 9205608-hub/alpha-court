# 15 court/pbo.py 实现（v0.1-08c）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge
Blocked by: 08
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-08c-pbo-cscv/ticket.md

## Question

实现 CSCV/PBO：T×N 矩阵 → S 连续等长块 → 全部 C(S,S/2) 对称组合 → IS 最优在
OOS 的相对排名 logit → φ。规格 = `docs/design/court-kernel-spec.md` §5.3
（rulings D1–D6）；算法与手算向量 = `docs/research/pbo-cscv.md` §3/§5/§6。

- 口径钉死：φ 只数严格 λ<0（λ=0 不计）；λ<0 ⟺ r̄<(N+1)/2，不实现论文
  Eq.(2.2) 字面 N/2；论文 Alg. 2.3(c) 标签勘误不得复现。
- metric 为必传 callable（无默认）——解耦 sharpe 依赖，judge 侧再接线。
- TDD：先写 §5 S=4 fixture 失败测试（六 logit 按组合序逐位断言 + φ=0.5）+
  守卫（奇 S、T%S≠0、N=1、非有限 metric 整跑 raise），再实现。
- 文件边界：`court/pbo.py` + `tests/test_pbo.py`。与 13/14/16/17 并行。

产出：选择过程过拟合概率可独立计算并逐行对得上文献。

## Answer

grok 工人交付 + 一轮返工后收货（2026-07-10，commits `82a0ec4`+`624f14c`）。对抗面板：recompute 满分（独立参考实现 + S=4 fixture 零差异），1 major——D5 结构护栏漏了 T≥2S（原 spec 转录 §6.4 不全，空矩阵静默返回 φ=0.0 = 零证据最有利被告判决）→ 裁定修订 D5 + 补护栏。referee 亲测 T=0/T=S/T<2S 全 raise、合法输入不受影响。11 测试绿。
