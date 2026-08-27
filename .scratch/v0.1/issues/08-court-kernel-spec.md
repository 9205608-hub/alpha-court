# 08 court/ 内核 spec 与切票

Type: task
Status: resolved
Assignee: claude-commander (session 2026-07-10, spec assembly + ticket cutting)
Blocked by: 03, 04, 05, 06, 07
Label: wayfinder:task

## Question

把四件套的契约与文献笔记汇编成可施工的 spec，并切成可派单的实现票：

- 输入：[03 trial ledger 契约](03-trial-ledger-contract.md)、[04 DSR](04-dsr-literature.md)、[05 PBO/CSCV](05-pbo-cscv-literature.md)、[06 BHY](06-bhy-literature.md)、[07 噪声对照](07-noise-control-design.md)
- 走 /grill-with-docs → /to-spec → /to-tickets 链
- spec 必须写死：模块边界（ledger / metrics / verdict 的文件级布局）、每个统计函数的签名 + 文献公式对照表 + 测试向量、`court/` 依赖白名单（numpy/pandas/scipy，零市场特异 import）
- 切出的实现票 = 自包含工人票（经 [01 M0 桥](01-m0-commander-worker-bridge.md) 派给 grok），每张内嵌 tdd 要求：先写文献测试向量的失败测试再实现

产出：spec 文档 + 新一批实现票（登记回地图，清掉对应雾区）。

## Answer

指挥侧汇编完成（2026-07-10）。走 /grill-with-docs → /to-spec → /to-tickets：grilling
的对象是五份源文档——把每份文档显式甩给 08 的决策点走成判决树，能从文档推出的按文档
引用，文档留白的指挥侧拍板并逐条记录理由。

**Spec = `docs/design/court-kernel-spec.md`**（英文施工契约）：

- **模块布局**：`court/` 扁平八模块（ledger/sharpe/dsr/pbo/tstats/fdr/noise/judge），
  一票一组不相交文件；`court/__init__.py` 只归 08f——五张并行工人票合并零冲突是
  布局的决定性理由（spec §2）。
- **35 项裁定**（spec §4，A1–G5）关掉全部委托决策，要点：非有限序列 record 时 raise；
  ID 顺序编号 h-/t-/v-；矩约定 Bessel σ̂ + population 高阶矩 + raw kurtosis；
  E[max] N=1 精确返回均值、N 实数值、docstring 必标 N≫1 EVT 近似；ρ̂ 允许 (−1,1]
  负值为保守外推；病态条件 T<½M(M−1) 是披露不是报错；PBO metric 必传 callable
  （解耦并行票）、λ<0 严格计数 ⟺ r̄<(N+1)/2；p 值正态渐近（HLZ 口径）、默认 SE=iid、
  NW 必须显式 lags；`fdr_bh`/`fdr_by` 命名（代码禁 "BHY"）、q 必传；
  `empirical_null_p` 平局对候选不利、α=0.05 参数默认；judge 判决极性表
  （统计学发现 ⟺ 法庭 pass——FDR rejection set 命名反转是钦定雷区）；scope 内
  未评估 trial 一律 raise。
- **公式对照表**：每个函数 → 论文式号 → 研读笔记锚点（spec §5 各模块表）。
- **数值守卫**：五份文档 pitfalls 节收敛成 §6 一张表，错误语义全线 fail-closed
  （raise，不修补不夹逼不静默丢弃）。
- **pytest 计划**（spec §7）：五份文档全部手算向量零胶水逐个映射成用例（dsr §4.1–4.5、
  pbo §5 S=4 fixture、bhy §6 N=10 双程序、noise §8 四向量、ledger 契约行为矩阵），
  另补 08 自产 t 统计向量（t_iid=2√3、t_NW(L=1)=3√2，算术在 spec 内可复核）；
  容差 1e-9，约定钉死处用精确相等（c(10)==2.9289682539682538、φ==0.5）。

**切票**（spec §8）：六张垂直切片自包含工人票，登记为 issue 13–18：

| Issue | Dispatch | 交付 | Blocked by |
|---|---|---|---|
| 13 | v0.1-08a | court/ledger.py | 08 |
| 14 | v0.1-08b | court/sharpe.py + dsr.py | 08 |
| 15 | v0.1-08c | court/pbo.py | 08 |
| 16 | v0.1-08d | court/tstats.py + fdr.py | 08 |
| 17 | v0.1-08e | court/noise.py | 08 |
| 18 | v0.1-08f | court/judge.py + 公共 API | 13–17 |

13–17 相互独立可并行过桥；每张内嵌 tdd 红绿纪律（先写文献向量失败测试并在收据
声明）、文件所有权边界、referee 可独立复跑的验收命令。12 号票 Blocked by 已补
13–18。CONTEXT.md 零新词条（spec 全用既有 canonical terms）；无 ADR（裁定按本仓
惯例记入设计文档本体）。派单与验收归指挥 session。
