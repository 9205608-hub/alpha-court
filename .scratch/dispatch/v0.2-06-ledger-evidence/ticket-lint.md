# Ticket-lint report — v0.2-06（派单前对抗性 lint，Claude verifier）

> 结论：修后派。1 BLOCKER + 2 major + 4 minor + 2 nit，全部已折入票面终稿。

- **BLOCKER-1**：AC-5 `git diff main...HEAD` 在工人分支上含指挥官全部未合并提交（实测 67 files/+4701）→ 改为工人首 commit 前记 `BASE=$(git rev-parse HEAD)`、diff 对 $BASE。
- **major-1**：§6 "extend or add" 与 AC-2 显式跑两文件矛盾（pytest 对不存在文件 exit 4）→ test_ledger_chain.py 改为 MANDATORY。
- **major-2**：seal 之后的 torn 行 truncate vs corruption 未裁定 → 裁定：torn 行非事件，seal 后 torn 尾行仍按 v0.1 truncate（与 trial-ledger invariant 4 一致）。
- **minor-1**：torn-only 文件的 legacy/chained 判定 → 裁定：判定在截断之后，截断后为空 = chained。
- **minor-2**：空 chained ledger 的 chain_head 与 legacy 的 None 撞车 → 裁定：空 chained = genesis "0"*64，None 只属 legacy。
- **minor-3**：window mapping 恰含 {start,end} 两键；n_evaluation_dates 非 bool int。
- **minor-4**：replay 到违约 attestation → LedgerCorruptionError（对齐 duplicate-evaluation 先例）。
- **nit-1**：收据字段措辞 self_test；**nit-2**：declaration/seal 事件行键名写死。
- 正面核验：current code facts 全部实核无误；现有 25 测试无一会被新字段咬红（逐断言过）；哈希链定义与 prereg-gate v3 §4.1 逐字一致；killer-demo ledger 首行确无 event_hash 且实跑 replay 通过；issue/契约无遗漏承诺。
