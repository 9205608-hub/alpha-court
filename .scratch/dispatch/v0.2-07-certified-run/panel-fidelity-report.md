# Panel report — 契约保真镜头（Claude 收货面板，v0.2-07）

**总评：接受（本镜头无工人返工项）** — pinned 段落逐字落地、⚠-1/⚠-2 被 verify 不变量 4/5 实质接住；唯一 major 是两条指挥官钉死项相互打架的逃生门（contract-fault，上报裁定而非退工人）。独立复跑：36/36 新测试、全量 447+1、ruff 净、diff 恰 6 文件。

## Findings

### F-1（major，contract-fault）mid-battery 砖化可经 open() 复活封印，verify 放行
judge([fdr_by, dsr(缺参)]) 半程失败 → 内存 seal 拒（砖化✓）→ 同文件 CertifiedRun.open() → seal() 成功、verify 通过。根因：M-4 钉"court.judge 抛错=永不可 seal"，M-1 钉"open 见 verdict=judge 已消费、seal 允许、Judgment 从链上重建"——重建 verdict_ids 恰好盖住孤儿 verdict、inv 7 反而通过。battery/config 不上链 → 事后缩 battery（故意让第 N 个统计量抛错→重开→封）与 crash-recovery 不可区分。工人对两钉死项均忠实实现（run.py:315-345 砖化、:210-256 恢复），责任在契约。

### minor（工人）
- F-2 verify 的 replay-on-COPY 被挪到 inv 8 之后（票面列在 inv 1）——报错编号归属偏离。
- F-3 legacy 文件实际死于 inv 1 而非 inv 2；测试正则 `"uncertified: no chain|chain"` 宽松掩盖。
- F-4 翻号 (b) 测试 `pytest.raises((CertificationError, Exception))` 近乎空断言 + 死代码；行为本身正确。
- F-5 GitAnchor 把 `-c user.name=test -c user.email=t@t` 硬编码进生产 pin()（票面框定为 tmp 测试 workaround）。
- F-6 manifest.anchor_ref 非 str 垃圾被静默降 None（与 fail-closed 精神相悖，票面未枚举）。
- F-7 verify 接受双 policy 账本（首个比较），与 09 read_declared_policy 的"corrupt"判定不一致。

### nit
- N-1 run.py:266 `_ledger._path` 私有穿透（自带 noqa）。
- N-2 evaluate Series 构造做 str()/float() 强转（票面钉 tuple 原样；court replay 同强转、语义等价，未申报）。
- N-3 judge 空 scope 也消费名额并砖化（票面只钉 ValueError；fail-closed 方向、比票面严、未申报）。

## 逐条已核 ✓（11 组全过）
1 create ✓ / 2 open pinned 全套 ✓（含 judged-state 重建）/ 3 propose ^h-\d{6}$ ✓ / 4 evaluate conformance raw== ✓ / 5 judge pinned ✓（reopen 逃生门见 F-1）/ 6 seal pinned 全套 ✓（**policy 副本取径逐行读码确认取 DeclarationRecord.payload 原 dict、非对象再序列化**）/ 7 anchor.py 三后端 pinned 映射全对 ✓（硬编码身份见 F-5）/ 8 verify 九不变量逐条 ✓（编号归属两处走样 F-2/F-3）/ 9 CLI exit 0/1 ✓ / 10 测试 vs 票面清单齐全 ✓（36≥25、四条 §6 边界 docstring+测试锁、无 security theater、egg-info 未提交）/ 11 receipt 三数字逐位一致、红跑结构红已披露 ✓。

**镜头结论**：接受。F-1 请指挥官单独裁定归 contract-fault 入账 + 后续硬化。F-2~F-7 建议并入一张小型 follow-up。
