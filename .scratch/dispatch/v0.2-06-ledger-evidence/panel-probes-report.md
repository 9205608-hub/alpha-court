# Panel report — 对抗探针镜头（Claude 收货面板，v0.2-06）

**总评：接受（ACCEPT）**。30+ 真跑探针（脚本在面板 scratchpad，worktree 零改动）覆盖票面全部钉死语义：**零 fail-open、零误杀**。该抓的篡改全 raise `LedgerCorruptionError`，该过的诚实边界（`at` 改写、后缀截尾、全链重写）如契约披露地 PASS；写时 ValueError / replay LedgerCorruptionError 双相对称完整落地。独立复核：ledger+chain+smoke 58 passed；core 204 passed；ruff clean；文件边界干净；新测 31（≥18）；两个强制测（honesty §6 + killer-demo legacy）都在且写法正确（先 copy 到 tmp）。

## 逐探针（预期→实测→判定）
- 篡改矩阵 1a–1f/1i/1j（改值/改字符/翻 type/换行/删中行/伪造行断链/改 hash 字段）→ 全 raise ✓；1g 伪造行+重算全后缀 → PASS ✓ 符合披露边界（§6 链只保 surviving lines 序一致）；1h 只改 `at` → PASS ✓（at 不入 content）。
- 后缀截尾 2a/2b（删末 1/3 行）→ PASS ✓ 诚实边界；2c 删中行 → raise ✓。
- seal 3a 六 mutating 入口全 `ValueError: ledger is sealed` ✓；3b seal 后合法链接事件 → open raise ✓；3c 双 seal → raise ✓；3d seal 后 torn 半行 → truncate、seal 在、head=seal 前完整头 ✓（票面钉死）。
- legacy/mixed 4a 真 killer-demo → open OK、chain_head None、100 trials/104 verdicts ✓；4b legacy append 无 hash 字段 ✓；4c/4d legacy 插带 hash 行（中/末）→ raise mixed ✓；4e chained 插无 hash 行 → raise ✓。
- canonical 5a 0.0 vs -0.0 不同 hash ✓；5b bool 不当 float ✓；5c 大 int ✓；5d 嵌套递归 ✓；5e/5e2 unicode ✓；5e3 存储 ensure_ascii=True 与 hash 路径 False 不对称=有意且正确（hash 对 parse 后 dict 算）✓ INFO；5f content_hash 确定性 + event_hash 因 prev 而异 ✓；5g 空 chained head=="0"*64 reopen 稳定 ✓；5h 已填充 head 跨 reopen 稳定 ✓。
- attestation 6 写时 10 例全 ValueError ✓；replay 5 例手工违约+重算合法链 → 全 `attestation invariant violation on replay` ✓；合法 round-trip/opaque 键/None 合法/控制组 ✓。
- torn 7a 尾半行 → truncate+续链正确+物理移除 ✓；7b 中行坏 JSON → raise ✓；7c 末行合法 JSON 但 hash 不符 → raise（不能伪装 torn）✓；7d 末行缺 type 信封键 → 当 torn 截断 ✓ 等价后缀截尾、无新增攻击面。
- 并发 8 同路径双实例交替 append → 产出文件 reopen 即 raise prev_hash mismatch ✓ fail-CLOSED（单写者假设在契约内，非静默坏文件）。
- 残余 9a 首事件 prev≠genesis → raise ✓；9b 手工重复 evaluation 重算链 → raise ✓；9c chained→legacy 降级（剥全 hash）→ 当 legacy 打开 ✓ 披露边界（防线在 07 的 seal chain_head 复核：None ≠ 记录 head 即被拒）；9d legacy seal 后有事件 → raise ✓（seal-final 与链正交）；9e legacy 尾部合法 seal → OK ✓；9f float 2.0 vs int 2 不同 hash ✓；seal 自身入链、head==seal.event_hash、reopen 稳定 ✓。

## 需入账的语义说明（✓ 符合披露边界，非 finding）
1. 1g/9c 同源：全链重写/降级 legacy 本层不检测——正是 §6 披露边界的直接后果；防线在 ticket-07（certified run 要求 chained + seal 记 chain_head）。
2. 7d：末行缺信封键走 torn-truncate，仅末行、等价后缀截尾。
3. 5e3：存储与 hash 的 ensure_ascii 不对称有意且正确。

## 归因
无 worker-fault / contract-fault / referee-fault 需入账。建议裁定：接受。
（附：killer-demo E2E 进程 100% CPU 为 PBO/CSCV 组合数所致、非死锁——AC-3 后经全量套件 219+1 确认。）
