# 14 court/sharpe.py + court/dsr.py 实现（v0.1-08b）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge
Blocked by: 08
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-08b-sharpe-dsr/ticket.md

## Question

实现 PSR/DSR 全链：SR 估计与矩（Bessel σ̂、raw kurtosis）、SR 标准误、PSR、
E[max SR]（2014 Eq.(1)，docstring 必标 N≫1 EVT 近似）、N̂=1+(M−1)(1−ρ̂)、ρ̂、DSR。
纯函数，零台账依赖。规格 = `docs/design/court-kernel-spec.md` §5.1–5.2
（rulings C1–C10）；公式与手算向量 = `docs/research/dsr.md` §2–§5。

- TDD：先写 dsr.md §4.1–4.5 五组向量的失败测试（含论文数值例交叉核对
  N=100→0.9004 / N=46→0.9505）+ Normal 恒等式 + 守卫，再实现。
- 文件边界：`court/sharpe.py`、`court/dsr.py` + 两个测试文件。
- 与 13/15/16/17 相互独立，可并行派单。

产出：DSR 判据可独立计算并逐行对得上文献。

## Answer

grok 工人交付 + 一轮返工后收货（2026-07-10，commits `05373c6`+`1bf4b849`）。对抗面板：零 blocker、2 major——① `norm.ppf(1−1/N)` 低精度构造且注释谎称已用缓解（实测 N=1e9 差 4.6e-9、N≈4e15 返回 +inf）→ 换 `norm.isf` + 大 N 回归测试；② NaN 标量穿透比较式护栏 → 全公共函数入口有限性检查（spec §6 新增全局裁定）。minor：钉死锚点收紧为 `==`、DsrResult.z 双重推导去重。返工后 45 测试绿，referee 亲测 isf/NaN 护栏/文档 fixture 精确值全过。
