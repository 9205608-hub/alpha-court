# 11 杀手 demo 设计

Type: grilling
Status: resolved
Blocked by: 03, 07, 10
Label: wayfinder:grilling

## Question

设计 `examples/` 杀手 demo 的完整剧本——项目存在理由的一图证明：

1. **100 个噪声因子怎么造**：纯随机信号（种子固定）打在真实 A 股数据上，因子族怎么伪装得像真的（动量壳、反转壳、波动壳……生成端 stub 的菜单形态）。
2. **"裸选择"怎么上当**：naive 流程——跑 100 个、挑 in-sample 最好的、报告 t≈3 的"发现"。要让上当过程有代表性（这就是没有法庭的世界的日常）。
3. **法庭怎么驳回**：同一批 trial 走 ledger → DSR → PBO → BHY → 噪声对照，预期全部驳回。如果没全驳回（禁赢学：如实呈现），narrative 怎么处理。
4. **一图讲清**：一张图同时呈现"裸选择的幻觉"与"法庭的判决"——形态（裸 t 值分布 vs 校正后判据？）等内核输出定型后细化。
5. **可复现性**：种子、数据版本、运行入口（一条命令跑通）。

依赖 [03 ledger 契约](03-trial-ledger-contract.md)、[07 噪声对照设计](07-noise-control-design.md)、[10 adapter 口径](10-adapter-interface.md)。HITL。产出：demo 设计文档，供实现票引用。

## Answer

2026-07-10 HITL grilling 关票，十二项拍板全部由用户逐题确认，设计契约落
`docs/design/killer-demo.md`（英文，demo 实现票必引；该文档同时是 demo 的预注册书——
种子/判决线/聚合规则先于首跑钉死，跑后不许回调）。

1. **壳本体**：纯 RNG AR(1) 持久面板（零信息是构造性事实，审计零负担）；族壳 = spec 元
   数据 + 族专属 φ（换手 realism 的唯一实参）；无横截面标准化、面板稠密无 NaN 注入。
   否决"真公式算在打乱数据上"（审计负担 + 与陪审团时移手法撞车）。
2. **族菜单**：5 族 × 20 变体，φ 全谱（动量 .90–.97 / 反转 .20–.60 / 波动 .95–.99 /
   流动性 .97–.995 / 价值质量 .995–.999），伪 lookback 纯装饰且在 spec 里如实披露
   （伪装的欺骗对象是选择程序，不是审计者）。
3. **hypothesis 映射**：100 hypo × 1 trial（N=100 贯穿四件统计与全部叙事；契合 03 契约
   备注；v0.2 代表政策切换不动 demo 数字）。
4. **种子树**：SeedSequence(20260710).spawn(2) → 候选支再 spawn(100)（单因子独立可复
   现）+ 偏移支；199 偏移从 [60,420] 无放回抽取、原文落盘。
5. **裸选择**：max |t_iid| 允许翻号（two-sided，有效 200 臂）、全窗 in-sample 无 holdout；
   用与法庭同一个 t 函数——"法庭不质疑你的 t，质疑你的推断"字面成立。grilling 中修正
   一处机制错误：零假设下 IC 序列无自相关（与 φ 无关），裸选择的罪全在选择不在 SE。
6. **battery**：fdr_by(q=.05, 全员) → dsr(conf=.95, 判被告) → pbo_cscv(S=16, φ≤0.2,
   metric=sharpe≡ICIR, 判被告) → noise pool_max(α=.05, 判被告) → noise individual×100
   (α=.05, 校准展示位，预期 ~5 过为正常)。共 104 条 verdict。窗口钉 T=480 评估日
   （480=16×30，PBO 整除约束由窗口吸收）；rho_ill_conditioned=True 如实入 verdict 并在
   报告披露；DSR 单侧性/PBO 有符号选择两处 subtlety 脚注申报。
7. **聚合（03/08 让渡的 judge config）**：全票制——判过它的每条 verdict 全 pass 才幸存；
   头版 = 幸存数/100；记分只作呈现信息。
8. **禁赢学**：主种子 20260710 预注册单次审判、出什么报什么（预期落点 |t|≈2.5–3.2，
   P(max≥3)≈24%，绝不为凑 3 挑种子）；幸存者判词预写（= 法庭已申报误差率的实现）；
   20 个预注册种子（20260711–30）扫描附录全量报告作经验校准。
9. **一图**：单面板——199 个 best-of-null |t| 直方图 + 被告竖线（naive p vs 法庭 p̂ +
   尾部阴影计数）+ 1.96 裸显著虚线；幻觉与判决同居一轴。caption 必含 gross 申报串、
   主种子、data tag、engine_version、口径。
10. **入口**：`python -m examples.killer_demo` 一条龙（幂等下载→生成→评估→审判→出图），
    --seed/--sweep/--skip-download；out/ = ledger.jsonl + figure.png/svg + report.md +
    run_config.json（全链 manifest）；干净机器清单 + 同平台逐位/跨平台判决级承诺。
11. **尸体呈现（v0.3 博物馆种子）**：report.md 判决书四部——头版（幸存数+图+被告五关
    battery 表）/ 停尸表（100 行，行行指回 ledger trial_id）/ 样本尸检（被告全证据链
    逐段对照文献口径）/ 校准附录（个体 pass 名单 + 种子扫描表）。
12. **实现票形状**：单张 demo 票，Blocked by adapter 实现票 + 18；测试义务五件套
    （种子确定性/一致性断言/窗口算术/聚合单元/报告 smoke），E2E 验收 = 那条命令真跑。
