# 19 adapters/qlib_cn 实现（v0.1-10a）

Type: task
Status: resolved
Assignee: dispatched to grok worker via M0 bridge
Blocked by: 10, 18
Label: wayfinder:task
Worker ticket: ../../dispatch/v0.1-10a-adapter-impl/ticket.md

## Question

按 `docs/design/adapter-interface.md` §7 实现 `QlibCNFactorEvaluator`：
evaluate / evaluate_shifted 共享内核（等值不变量 array_equal 级）、qlib
`eva.alpha` 当 oracle（rtol ≤ 1e-12）、kernels=1、fail-closed、§7.4 meta 全字段、
§7.5 四件测试义务；秩预计算让 100×199 网格秒级跑完。court/ 保持零 qlib。

## Answer

grok 工人交付 + 一轮返工后收货（2026-07-11，commits `0bd0567`+`0101f12`+referee 补一行 importorskip）。对抗面板双镜头（契约保真 + NaN 语义数值裁决）抓到 1 blocker：秩预计算"各自支撑"约定偏离 qlib 联合掩码语义——不止稀疏 NaN，PIT 成员变动使偏差覆盖真实数据 100% 交易日（实测单日最大 2.3e-2，合同 1e-12）。返工 = 联合掩码内重排秩（稠密日保留快路径）；referee 独立探针复验原翻车场景 max 5.6e-17 全过。代价如实：IC 网格 1.3s→26.8s/候选（100 候选约 45 分钟，预算内）；多空路径 1.1s 不变。majors 修复：meta.config 全字段（合同 §7.1 澄清）、金指纹 layer-2 测试落位；minors：config 严格类型校验（49.9 截断案）、δ=0 勘误 ratify、注释与死代码清理。143 测试绿；无 qlib 环境优雅 skip。
