# 16 court/tstats.py + court/fdr.py 实现（v0.1-08d）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge
Blocked by: 08
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-08d-tstats-fdr/ticket.md

## Question

实现 t/p 计算（iid 与 Newey-West SE、声明方向的正态渐近 p）与 FDR step-up 双程序
`fdr_bh`/`fdr_by`（代码禁用 "BHY" 名——HLZ 的 BHY 即 BY，名字撞车是文档在案的坑）。
规格 = `docs/design/court-kernel-spec.md` §5.4–5.5（rulings E1–E8）；程序与手算
向量 = `docs/research/bhy.md` §2–§7。

- 口径钉死：step-up 补齐 1..k* 全段（rank 5 canary）；边界 p=τ 计入（≤）；
  调整 p 后向 min 递归 + 截断 + 稳定排序映射回原序；`harmonic_number(10)`
  精确 == 2.9289682539682538（升序 float64 求和约定）；q 必传无默认；
  NW 必须显式 lags（v0.1 禁自动选带宽）。
- TDD：先写 bhy.md §6 N=10 fixture（BH k*=9 / BY k*=3）+ spec §5.4 的
  t 向量（t_iid=2√3、t_NW=3√2）失败测试，再实现。
- 文件边界：`court/tstats.py`、`court/fdr.py` + 两个测试文件。并行。

产出：FDR 家族控制与 p 值供给链可独立计算并逐行对得上文献。

## Answer

grok 工人交付 + 一轮返工后收货（2026-07-10，commits `5454784`+`256096d`）——**本项目首个"工人胜诉"判例**：面板初判 blocker（BY adjusted-p 初值与 bhy.md §3.2 印刷递归不符），随后证明 HLZ 发表版递归自身违反 spec §7 恒等式 `adjusted≤q ⟺ reject`（反例 p=(0.04,0.04) 见勘误），工人的 `min(1, c(N)·P₍N₎)`（R/statsmodels 惯例）是唯一自洽形式，拒绝集 480 次 fuzz 零差异。裁定：代码行为不动，bhy.md §3.2 挂勘误、spec E6 重钉；工人修引用注释 + 4 minor（0-d 标量拒收、单调性松弛清零、c_factor N=0 哨兵文档化、t 管线值 1 ulp 重钉精确断言）。28 测试绿。
