# 10 adapter 接口与因子评价口径

Type: grilling
Status: resolved
Blocked by: 03, 09
Label: wayfinder:grilling

## Question

定下 `adapters/qlib_cn` 的对外契约——它是 court 与市场之间唯一的门：

1. **court 吃什么**：收益序列 / IC 序列的精确形状（频率、对齐、缺失值语义），与 [03 trial ledger 契约](03-trial-ledger-contract.md) 的 series 口径对上。
2. **因子值 → 序列怎么算**：复用 qlib 现成的信号分析件（三不做：不自造回测）——RankIC 序列怎么取、分位多空组合收益用 qlib 哪条路径、换手/成本在 v0.1 里算不算（倾向：不算，如实标注）。
3. **市场特异逻辑关在哪**：交易日历、ST/涨跌停/停牌处理、宇宙定义（csi300？）全部在 adapter 内消化，court 侧零感知。v0.1 demo 的最小处理集是什么（哪些坑必须处理、哪些如实声明不处理）。
4. **接口签名**：`FactorEvaluator.evaluate(factor_values) -> TrialSeries` 一类的最小 API。

依赖 [09 qlib-cn 数据研究](09-qlib-cn-data-research.md) 的事实。HITL——评价口径是研究判断。产出：契约文档，供 demo 设计与实现票引用。

## Answer

2026-07-10 HITL grilling 六项拍板（逐题用户确认），契约全文 = [`docs/design/adapter-interface.md`](../../../docs/design/adapter-interface.md)：

1. **court 吃什么**：双路径都实现——daily RankIC（`calc_ic` 的 Spearman `ric` 输出）+ 分位多空收益（`calc_long_short_return` 的 `(r_long−r_short)/2`，quantile=0.2 等权）；`declared.metric` 两值都真实可吃；**杀手 demo 主口径 = RankIC**，多空做搭配视图（是否上图归 11）。
2. **因子值→序列**：语义锚定 `qlib.contrib.eva.alpha`（pyqlib 0.9.7）两个一等公民函数，实现共享内核、qlib 函数当 pytest oracle；label = qlib 官方惯例 `Ref($close,-2)/Ref($close,-1)-1`（Alpha158 同款，t 信号 → t+1 收盘成交 → t+2 收盘）；**成本换手不算**——gross 纸面口径，meta/契约/图注三处如实申报（噪声陪审团按构造换手可比，豁免对称、审判公平）。
3. **09 遗留双双关闭**：价格用 `$close` 复权价（`$factor` 备现金价反推，`$adjclose` 声明不用——量纲未对账的包私有字段）；investment_data **钉死 tag `2026-07-05`**，禁用 latest，bump 流程文档化，`data_version`（declared_tag + 实测日历末日 + 实测标的数）入每份 EvalResult meta，喂 07 复现链。
4. **市场特异最小处理集**：csi300 **动态 PIT 成员**（qlib 区间过滤原生行为）；停牌/缺失 = 逐日截面 pairwise 剔除 NaN（不填充）+ 最小截面护栏（默认 50，不足 fail-closed 报错，绝不漏 NaN 给 court）；声明不处理：ST（指数规则已剪）、涨跌停可交易性、停牌股 t+1 不可成交。
5. **API**：`QlibCNFactorEvaluator(config)` + `evaluate(scores, metric)` → EvalResult + `evaluate_shifted(scores, metric, offsets)` → EvalGrid（每候选一调、内部向量化 199 偏移，100 候选循环留 demo 侧）；**跨路径逐位等值是 pytest 不变量**（共享内核保证）；adapter 不碰 ledger、不算统计量；index = 信号日 t 的 ISO 日期字符串（court 只做相等比较），评估日期集 = t+2 仍在窗口内的信号日，全体 trial 共享同一 index → `matrix()` fail-closed 对齐按构造通过。
6. **确定性**：同机 + 锁依赖 + 同数据 tag ⇒ 逐位可复现；强制 kernels=1、instrument/日期显式排序、adapter 零 RNG（偏移量由 demo 主种子抽好原样传入）；双层测试 = 合成面板双跑 array_equal（常驻 CI）+ 钉死 tag 黄金指纹（缺数据 skip）；跨平台逐位一致明确不承诺。

补充缺省（referee 按 qlib 默认补、已向用户披露）：quantile=0.2、min_cross_section=50，均为可配置参数入 meta。
