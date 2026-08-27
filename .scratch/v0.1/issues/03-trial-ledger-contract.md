# 03 Trial ledger 契约设计

Type: grilling
Status: resolved
Label: wayfinder:grilling

## Question

Trial ledger 是整个法庭的地基——"记 N"决定 DSR/PBO/BHY 的输入语义。要定下：

1. **一次 trial 的定义**：什么算一次试验？一个因子的一组参数算一次？同族参数扫描算多次还是带族结构？这直接决定 N 的计数口径（DSR 的 E[max SR] 和 BHY 的校正强度都吃 N）。
2. **trial record schema**：假设 id、因子族、参数、预注册时间戳、收益/IC 序列（存指针还是存值）、评估结果、最终判决状态。
3. **存储形态**：jsonl 台账？sqlite？纯内存 + 导出？v0.1 最小可用即可，但 schema 要给 v0.2 预注册闸留位（预注册时间戳字段现在就要有）。
4. **API 面**：`court/` 对外暴露什么——`Ledger.register(hypothesis) -> trial_id`、`Ledger.record(trial_id, series)`、`Ledger.verdict(trial_id)` 这一类的最小动词集。

产出：契约文档（数据 schema + API 签名），供 [08 court 内核 spec](08-court-kernel-spec.md) 引用。HITL——N 的计数口径是研究判断，需要用户拍板。

## Answer

四项决策已 HITL 拍板（2026-07-10），完整契约见 `docs/design/trial-ledger.md`（英文，08 必须引用）；词汇（Trial / Hypothesis / Verdict / Declared protocol / Effective trial count / Ledger / Scope）已入根目录 `CONTEXT.md`。

1. **trial 定义与 N 口径**：一个 trial = 一次评估（因子构造 × 参数组 × 评估窗口 → 一条性能序列），同族参数扫描 k 组 = k 条 trial，写入时永不塌缩；两层族结构 hypothesis → trial；**N 不落盘**，读取端按统计量各自派生——PBO 取选择池全列数，DSR 由原始 M 经 ρ̂ 校正得 N̂ = 1+(M−1)(1−ρ̂)（族内相关被 ρ̂ 自动吸收），BHY v0.1 一 trial 一假设全量进家族（BY 抗任意相关故合法）。"每假设取代表 + 族内选择校正 p 值"留作 v0.2 策略开关；直接喂族内最优 p 值 = HLZ hidden tests，禁止。
2. **schema**：Hypothesis / Trial / Verdict 三类记录，全部不可变只追加。序列**存值**（inline 带不透明 index 标签，可选 source_ref 纯出处、court 不解引用）；派生统计量不落 trial，判决时从序列现算、连中间量记入 VerdictRecord；trial 状态（registered → evaluated → judged）由记录存在性派生，**无 abandoned 态**（注册未评估的悬挂 trial 本身即 file-drawer 证据）；预注册留位字段现在就有：ledger 盖章的 registered_at + declared 协议（metric / direction / window / periods_per_year / SE 口径）。
3. **存储**：单文件 append-only `ledger.jsonl` 事件日志（hypothesis / trial / evaluation / verdict 四种事件行），打开时重放建内存索引；行序物理保证注册先于评估；崩溃恢复 = 尾部残行丢弃、中段坏行 fail-closed；v0.1 单写者；路径由调用方传入，court 不硬编码。
4. **API 三层**：Ledger 纯记账（open / register_hypothesis / register / record / append_verdict + trials / series / matrix / verdicts / status），统计量纯函数（只吃数组，文献手算向量零胶水直接成 pytest，签名细节归 08），judge 薄编排（取证 → 算 → 写回 VerdictRecord）。`matrix` 构建 index 逐标签不等即 fail-closed，绝不静默对齐。
