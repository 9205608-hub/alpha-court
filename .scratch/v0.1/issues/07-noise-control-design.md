# 07 噪声对照设计

Type: grilling
Status: resolved
Assignee: claude-commander (session 2026-07-10, HITL with user)
Blocked by: 03
Label: wayfinder:grilling

## Question

法庭第四件套：给每个受审因子配"匹配噪声陪审团"，用经验 null 分布当参照系。要定下：

1. **null 因子怎么生成**：纯随机信号打在真实收益上？截面 permutation？block bootstrap 保时序结构？匹配什么（换手率、行业/风格暴露、覆盖度）才算"公平陪审团"？
2. **判据**：受审因子的表现要在 null 分布的第几百分位才不算噪声？和 DSR/BHY 的关系是互补证据还是链式闸门？
3. **驳回记录**：被噪声对照杀掉的 trial 在 ledger 里怎么记（null 归档最小形态，禁赢学要求尸体可复查）。
4. **随机数纪律**：种子管理，保证 demo 全程可复现。

产出：设计文档，供 [08 court 内核 spec](08-court-kernel-spec.md) 引用。HITL——"匹配什么才公平"是研究判断。依赖 [03 trial ledger 契约](03-trial-ledger-contract.md) 的 trial 语义。

## Answer

四项 HITL 拍板（2026-07-10），完整设计见 `docs/design/noise-control.md`（英文，08/11 必引）；词汇 **Null jury** 入 `CONTEXT.md`：

1. **生成协议 = 循环时移**：候选因子自己的打分面板整体循环平移 δ∈[60 交易日, T−60]，对未平移的收益重新评估——换手率/覆盖度/截面边际分布按构造自动匹配，唯一被摧毁的是打分与未来收益的对齐（正是受审内容）。架构上生成在 adapter/demo 侧，court 只吃数组（03 契约 §4.2/§7.3 严丝合缝）。接缝伪影 O(horizon/T) 如实申报不修补。
2. **统计量 = 一个纯函数两种模式**：`empirical_null_p`，p̂=(1+#{null≥观测})/(K+1)（Phipson-Smyth 2010 加一修正，永不为零，平局算对候选不利）；个体模式（候选 vs 自己的 199 人陪审团）是可复用原语，池最大模式（best-of-真池 vs best-of-null池 分布，White 2000 Reality Check）是杀手 demo 的头版。与 DSR/BHY 的聚合方式明确让渡给 11 号票。
3. **陪审团只活在判决书里**：K 个统计量值 + recipe + 主种子 + 逐个偏移量 + engine_version 全записа VerdictRecord，null 序列不注册为 trial——①避免污染 03 契约"全量进 BHY 家族"的 N；②file-drawer 纪律管被告不管合成陪审员。确定性可重生 = 可审计。
4. **公共偏移网格 199**：一张 100×199 评估网格同时供养两种模式（列=个体陪审团，行 max=池最大 null 分布）；公共偏移保留池内因子相关性（对 max-null 更忠实）；跨候选 p̂ 相关性作为已声明事实交给 11。α=0.05 默认；种子纪律 SeedSequence spawn + 偏移量原样落盘。

手算测试向量 4 组已写入设计文档 §8（含平局与 1/200 分辨率下限）。
